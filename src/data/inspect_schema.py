"""Step 1.2 — schema inspection (SERVER).

Nothing here assumes column names or language-code formats. Every source is
loaded as-is (streaming, small slices) and described, and a human reads the
report before code_maps.py and profile_languages.py are written against it.

Per source it reports: repo files and gating, configs and splits, column names
and dtypes, three example rows (long fields truncated), and every config name
or column that looks like a language identifier, classified by format. Sources
with a full local copy (from 01_download_data.sh) additionally get a complete
scan of their identifier columns and a per-identifier Unicode script profile,
which is what the multi-script handling in code_maps.py needs.

Outputs
  results/schema_inspection.md        full report (also printed while running)
  results/schema/<source>__*.csv|txt  complete identifier lists, so code_maps.py
                                      can be written and tested on LOCAL

Usage (repo root, venv active):
  python -m src.data.inspect_schema
  python -m src.data.inspect_schema --only belebele,nllb200 --sample-rows 200
"""

from __future__ import annotations

import argparse
import itertools
import json
import platform
import re
import subprocess
import time
import traceback
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable

import datasets
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from datasets import get_dataset_config_names, load_dataset
from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.utils import get_session

from src.utils.io import RAW_DIR, REPO_ROOT, RESULTS_DIR, SCHEMA_DIR, num_proc, write_result

# --------------------------------------------------------------------------- sources


@dataclass(frozen=True)
class Source:
    key: str
    repo: str
    role: str
    repo_type: str = "dataset"
    local_dir: Path | None = None  # full copy written by 01_download_data.sh


SOURCES: tuple[Source, ...] = (
    Source("muri_it", "akoksal/muri-it", "clean repair data (combined release)",
           local_dir=RAW_DIR / "muri-it"),
    Source("muri_it_language_split", "akoksal/muri-it-language-split",
           "clean repair data (per-language configs of the same corpus)"),
    Source("nllb200", "facebook/nllb-200-distilled-600M",
           "contamination generator; only its language codes are inspected", repo_type="model"),
    Source("flores200", "facebook/flores", "primary eval, chrF++ (gated)"),
    Source("flores_plus", "openlanguagedata/flores_plus",
           "maintained FLORES successor (gated); codes may differ from FLORES-200"),
    Source("belebele", "facebook/belebele", "comprehension eval"),
    Source("tulu3_sft", "allenai/tulu-3-sft-mixture", "English backbone / source pool for Step 2",
           local_dir=RAW_DIR / "tulu-3-sft-mixture"),
)

VIEWER_SIZE_URL = "https://datasets-server.huggingface.co/size"

# --------------------------------------------------------------------------- identifier formats

ID_FORMATS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("lang_Scrp (FLORES-style)", re.compile(r"^[a-z]{3}_[A-Z][a-z]{3}$")),
    ("lang_Scrp-lang_Scrp (pair)", re.compile(r"^[a-z]{3}_[A-Z][a-z]{3}-[a-z]{3}_[A-Z][a-z]{3}$")),
    ("xxx (ISO 639-3-like)", re.compile(r"^[a-z]{3}$")),
    ("xx (ISO 639-1-like)", re.compile(r"^[a-z]{2}$")),
    ("XX/XXX (upper-case code)", re.compile(r"^[A-Z]{2,3}$")),
    ("lang+subtags (BCP-47-like)", re.compile(r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})+$")),
    ("word(s) / name", re.compile(r"^[^\W\d_][\w '()\-.,/]*$")),
)
CODE_LIKE = {name for name, _ in ID_FORMATS[:6]}


def classify_id(value: Any) -> str:
    if not isinstance(value, str):
        return f"non-string ({type(value).__name__})"
    for name, pattern in ID_FORMATS:
        if pattern.match(value):
            return name
    return "other"


def format_breakdown(values: Iterable[Any], n_examples: int = 6) -> list[tuple[str, int, list[str]]]:
    """[(format, n_distinct_values, examples)] sorted by count, over distinct values."""
    groups: dict[str, list[str]] = defaultdict(list)
    for v in dict.fromkeys(values):
        groups[classify_id(v)].append(str(v))
    return sorted(((fmt, len(vs), vs[:n_examples]) for fmt, vs in groups.items()),
                  key=lambda t: -t[1])


def dominant_format(values: Iterable[Any]) -> str:
    bd = format_breakdown(values)
    if not bd:
        return "-"
    total = sum(n for _, n, _ in bd)
    fmt, n, _ = bd[0]
    return fmt if n == total else f"{fmt} {n}/{total}"


# --------------------------------------------------------------------------- script detection


# Name prefixes that are script-neutral, or whose first word is not the script name.
_NEUTRAL_PREFIXES = ("COMBINING", "MODIFIER", "ZERO WIDTH")
_SCRIPT_RENAMES = {"CJK": "HAN", "OL": "OL CHIKI", "MEETEI": "MEETEI MAYEK",
                   "CANADIAN": "CANADIAN SYLLABICS", "NEW": "NEW TAI LUE"}


@lru_cache(maxsize=1 << 16)
def char_script(ch: str) -> str | None:
    """Coarse Unicode script of a letter/mark (first word of its Unicode name), else None."""
    if not unicodedata.category(ch)[0] in ("L", "M"):
        return None
    name = unicodedata.name(ch, "")
    if not name:
        return "UNNAMED"
    if name.startswith(_NEUTRAL_PREFIXES):
        return None
    first = name.split()[0]
    return _SCRIPT_RENAMES.get(first, first)


def script_counts(text: str) -> Counter:
    return Counter(s for s in map(char_script, text) if s)


# --------------------------------------------------------------------------- report plumbing


class Report:
    """Markdown report that is printed as it is built."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, text: str = "") -> None:
        print(text, flush=True)
        self.lines.append(text)

    def h(self, level: int, text: str) -> None:
        self()
        self("#" * level + " " + text)
        self()

    def kv(self, key: str, value: Any) -> None:
        self(f"- **{key}:** {value}")

    def code(self, lines: Iterable[str]) -> None:
        self("```")
        for line in lines:
            self(line)
        self("```")

    def table(self, header: list[str], rows: Iterable[Iterable[Any]]) -> None:
        self("| " + " | ".join(header) + " |")
        self("|" + "---|" * len(header))
        for row in rows:
            self("| " + " | ".join(_md_cell(c) for c in row) + " |")

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def truncate(obj: Any, max_chars: int = 160, max_items: int = 4) -> Any:
    if isinstance(obj, str):
        return obj if len(obj) <= max_chars else f"{obj[:max_chars]}…(+{len(obj) - max_chars} chars)"
    if isinstance(obj, dict):
        return {k: truncate(v, max_chars, max_items) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        out = [truncate(v, max_chars, max_items) for v in obj[:max_items]]
        if len(obj) > max_items:
            out.append(f"…(+{len(obj) - max_items} items)")
        return out
    return obj


def _short(obj: Any) -> str:
    return json.dumps(truncate(obj), ensure_ascii=False, default=str)


@dataclass
class SourceSummary:
    source: Source
    errors: list[str] = field(default_factory=list)
    n_configs: int | None = None
    config_format: str = "-"
    id_columns: dict[str, str] = field(default_factory=dict)  # col -> "N distinct, format"
    rows_by_split: dict[str, int] = field(default_factory=dict)
    rows_by_split_origin: str = ""


def guarded(label: str, summary: SourceSummary, rep: Report, fn: Callable[[], Any]) -> Any:
    """Run one inspection step; on failure record it and carry on with the next step."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — every failure is reported, none is fatal
        msg = f"{type(e).__name__}: {str(e).strip().splitlines()[0][:300] if str(e).strip() else ''}"
        hint = ""
        if "gated" in str(e).lower() or "401" in str(e) or "403" in str(e):
            hint = (f" — accept the terms at https://huggingface.co/datasets/{summary.source.repo}"
                    " with the same HF account, then `huggingface-cli login` on the server")
        rep(f"- **ERROR in {label}:** `{msg}`{hint}")
        summary.errors.append(f"{label}: {msg}")
        traceback.print_exc()
        return None


# --------------------------------------------------------------------------- inspection steps


def inspect_repo_files(src: Source, rep: Report):
    api = HfApi()
    if src.repo_type == "model":
        info = api.model_info(src.repo, files_metadata=True)
    else:
        info = api.dataset_info(src.repo, files_metadata=True)
    siblings = info.siblings or []
    total = sum(s.size or 0 for s in siblings)
    by_ext: Counter = Counter()
    for s in siblings:
        by_ext[Path(s.rfilename).suffix or s.rfilename] += s.size or 0
    rep.kv("revision", info.sha)
    rep.kv("gated", getattr(info, "gated", None))
    rep.kv("files", f"{len(siblings)} files, {total / 1e6:.1f} MB")
    rep.kv("bytes by extension", ", ".join(f"{e} {b / 1e6:.1f} MB" for e, b in by_ext.most_common(6)))
    rep.kv("first files", ", ".join(f"`{s.rfilename}`" for s in siblings[:8]))
    return info


def inspect_configs(src: Source, info: Any, rep: Report, summary: SourceSummary) -> list[str]:
    try:
        configs = list(get_dataset_config_names(src.repo))
        origin = "get_dataset_config_names"
    except Exception as e:  # fall back to the card metadata, which is public even when gated
        card = (getattr(info, "card_data", None) or {}) if info is not None else {}
        configs = [c.get("config_name") for c in (card.get("configs") or []) if c.get("config_name")]
        origin = f"README card metadata (get_dataset_config_names failed: {type(e).__name__})"
        if not configs:
            raise
    summary.n_configs = len(configs)
    summary.config_format = dominant_format(configs)
    rep.kv("configs", f"{len(configs)} (from {origin})")
    rep.kv("first configs", ", ".join(f"`{c}`" for c in configs[:10]))
    if len(configs) > 10:
        rep.kv("last configs", ", ".join(f"`{c}`" for c in configs[-5:]))
    rep("- **config-name formats:**")
    for fmt, n, ex in format_breakdown(configs):
        rep(f"  - {fmt}: {n} — e.g. {', '.join(f'`{x}`' for x in ex)}")
    path = write_result("\n".join(configs) + "\n", f"schema/{src.key}__configs.txt")
    rep.kv("full list", f"`{path.relative_to(REPO_ROOT).as_posix()}`")
    return configs


def inspect_viewer_sizes(src: Source, rep: Report, summary: SourceSummary) -> None:
    """Row counts per config/split from the HF dataset-viewer API (no data download)."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = get_session().get(VIEWER_SIZE_URL, params={"dataset": src.repo}, headers=headers, timeout=120)
    r.raise_for_status()
    payload = r.json()
    splits = (payload.get("size") or {}).get("splits")
    if not splits:
        rep(f"- dataset-viewer size API returned no split table; top-level keys: {list(payload)}")
        return
    df = pd.DataFrame(splits)
    keep = [c for c in ("config", "split", "num_rows", "num_bytes_parquet_files") if c in df.columns]
    df = df[keep]
    path = write_result(df, f"schema/{src.key}__viewer_rows.csv")
    per_split = df.groupby("split")["num_rows"].sum().to_dict()
    per_config = df.groupby("config")["num_rows"].sum()
    rep.kv("viewer row counts", f"partial={payload.get('partial')}; per split: "
           + ", ".join(f"{s}={n:,}" for s, n in per_split.items()))
    if len(per_config) > 1:
        q = per_config.quantile([0, 0.25, 0.5, 0.75, 1]).astype(int).tolist()
        rep.kv("rows per config (min/q1/median/q3/max)", " / ".join(f"{v:,}" for v in q))
    rep.kv("full table", f"`{path.relative_to(REPO_ROOT).as_posix()}`")
    if not summary.rows_by_split:
        summary.rows_by_split = {str(k): int(v) for k, v in per_split.items()}
        summary.rows_by_split_origin = "viewer API"


ID_NAME_RE = re.compile(r"lang|locale|iso|script|dialect|code|flores|nllb|source|dataset", re.I)


def find_id_columns(rows: list[dict], columns: list[str]) -> list[str]:
    """Short string columns that are named like, or behave like, identifiers."""
    out = []
    for col in columns:
        vals = [r.get(col) for r in rows]
        strs = [v for v in vals if isinstance(v, str)]
        if not strs or len(strs) < 0.9 * len(vals):
            continue
        mean_len = sum(map(len, strs)) / len(strs)
        distinct = len(set(strs))
        if mean_len <= 40 and (ID_NAME_RE.search(col) or distinct <= max(50, len(strs) // 10)):
            out.append(col)
    return out


def inspect_stream(src: Source, config: str, rep: Report, summary: SourceSummary,
                   n_rows: int) -> tuple[list[str], list[dict]]:
    rep.h(3, f"streamed slice: config `{config}`")
    dsd = load_dataset(src.repo, config, streaming=True)
    splits = list(dsd.keys())
    rep.kv("splits", ", ".join(f"`{s}`" for s in splits))
    split = "train" if "train" in splits else splits[0]
    ds = dsd[split]
    t0 = time.time()
    rows = list(itertools.islice(iter(ds), n_rows))
    rep.kv("sampled", f"first {len(rows)} rows of `{split}` ({time.time() - t0:.1f}s)")
    if not rows:
        return [], []

    features = ds.features
    columns = list(features) if features else list(dict.fromkeys(k for r in rows for k in r))
    rep()
    rep.table(["column", "declared feature", "observed python types"],
              [(f"`{c}`",
                str(features[c])[:90] if features and c in features else "(not declared)",
                ", ".join(f"{t}×{n}" for t, n in Counter(type(r.get(c)).__name__ for r in rows).most_common()))
               for c in columns])
    rep()
    rep("Example rows (strings truncated to 160 chars, lists to 4 items):")
    rep.code(itertools.chain.from_iterable(
        [f"[{i}]"] + [f"  {c}: {_short(row.get(c))}" for c in columns] for i, row in enumerate(rows[:3])))

    id_cols = find_id_columns(rows, columns)
    rep()
    if not id_cols:
        rep("- **identifier-like columns:** none detected in this slice")
    for col in id_cols:
        counts = Counter(r.get(col) for r in rows)
        rep(f"- **identifier-like column `{col}`** — {len(counts)} distinct in {len(rows)} sampled rows; "
            f"top: {', '.join(f'`{v}`×{n}' for v, n in counts.most_common(8))}")
        for fmt, n, ex in format_breakdown(counts):
            rep(f"  - {fmt}: {n} — e.g. {', '.join(f'`{x}`' for x in ex)}")
        summary.id_columns.setdefault(col, f"{len(counts)} distinct in slice, {dominant_format(counts)}")
    return id_cols, rows


def inspect_local_copy(src: Source, rep: Report, summary: SourceSummary, id_cols: list[str],
                       sample_rows: list[dict], script_samples: int) -> None:
    """Complete scan of identifier columns over the downloaded parquet shards."""
    rep.h(3, f"full local copy: `{src.local_dir.relative_to(REPO_ROOT).as_posix()}`")
    files = sorted(src.local_dir.rglob("*.parquet"))
    files = [f for f in files if ".cache" not in f.parts]
    if not files:
        rep("- no parquet files found — run `bash scripts/server/01_download_data.sh` first "
            "(slice-level results above still stand)")
        summary.errors.append("local copy missing")
        return
    split_of = {f: f.name.split("-")[0] for f in files}
    rows_by_split: Counter = Counter()
    for f in files:
        rows_by_split[split_of[f]] += pq.ParquetFile(f).metadata.num_rows
    summary.rows_by_split = dict(rows_by_split)
    summary.rows_by_split_origin = "local parquet metadata"
    rep.kv("parquet files", f"{len(files)}; rows per split: "
           + ", ".join(f"{s}={n:,}" for s, n in rows_by_split.items()))
    schema = pq.read_schema(files[0])
    rep("- **arrow schema (first shard):**")
    rep.code(f"{fld.name}: {fld.type}" for fld in schema)

    cols = [c for c in id_cols if c in schema.names]
    if not cols:
        rep("- no identifier-like columns to scan")
        return
    max_distinct = 5000
    counts: dict[str, dict[str, Counter]] = {c: defaultdict(Counter) for c in cols}
    too_many: set[str] = set()
    for f in files:
        for batch in pq.ParquetFile(f).iter_batches(columns=cols, batch_size=65536):
            for c in cols:
                if c in too_many:
                    continue
                vc = pc.value_counts(batch.column(c))
                bucket = counts[c][split_of[f]]
                for v, n in zip(vc.field("values").to_pylist(), vc.field("counts").to_pylist()):
                    bucket["<null>" if v is None else v] += n
                if len(bucket) > max_distinct:
                    too_many.add(c)

    for c in cols:
        if c in too_many:
            rep(f"- **`{c}`**: more than {max_distinct:,} distinct values — not an identifier column, skipped")
            continue
        splits = sorted(counts[c])
        total: Counter = Counter()
        for s in splits:
            total.update(counts[c][s])
        df = pd.DataFrame({"value": list(total)})
        df["format"] = df["value"].map(classify_id)
        df["n_total"] = df["value"].map(total)
        for s in splits:
            df[f"n_{s}"] = df["value"].map(counts[c][s]).fillna(0).astype(int)
        df = df.sort_values("n_total", ascending=False)
        path = write_result(df, f"schema/{src.key}__{c}__values.csv")
        summary.id_columns[c] = f"{len(df)} distinct (full scan), {dominant_format(df['value'])}"
        rep(f"- **`{c}`** (full scan): {len(df)} distinct values → `{path.relative_to(REPO_ROOT).as_posix()}`")
        for fmt, n, ex in format_breakdown(df["value"]):
            rep(f"  - {fmt}: {n} — e.g. {', '.join(f'`{x}`' for x in ex)}")
        rep(f"  - top 10: {', '.join(f'`{v}`={n:,}' for v, n in total.most_common(10))}")
        rep(f"  - bottom 5: {', '.join(f'`{v}`={n:,}' for v, n in total.most_common()[-5:])}")

    # Script profile per identifier value: needed to resolve languages that FLORES
    # lists under more than one script. Only for columns that look like language ids.
    values = {c: set().union(*counts[c].values()) for c in cols if c not in too_many}
    lang_cols = [c for c, vals in values.items()
                 if len(vals) >= 2
                 and (re.search(r"lang|iso|locale|script|dialect|code", c, re.I)
                      or sum(classify_id(v) in CODE_LIKE for v in vals) >= 0.8 * len(vals))]
    text_cols = [c for c in schema.names
                 if pa.types.is_string(schema.field(c).type) or pa.types.is_large_string(schema.field(c).type)]
    text_cols = [c for c in text_cols if c not in cols and _mean_len(sample_rows, c) > 40]
    if not lang_cols or not text_cols:
        rep(f"- script profile skipped (language-id columns: {lang_cols or 'none'}; "
            f"long top-level text columns: {text_cols or 'none'})")
        return
    rep(f"- script profile: up to {script_samples} rows per value of {lang_cols}, "
        f"letters from {text_cols} (first 1000 chars each)")
    for c in lang_cols:
        prof, n_seen = script_profiles(files, c, text_cols, values[c], script_samples)
        rows = []
        for v in sorted(prof, key=lambda v: -sum(prof[v].values())):
            tot = sum(prof[v].values()) or 1
            top = prof[v].most_common(3)
            rows.append({
                "value": v, "n_rows_sampled": n_seen[v], "n_letters": tot,
                "script_1": top[0][0] if top else "", "share_1": round(top[0][1] / tot, 3) if top else 0,
                "script_2": top[1][0] if len(top) > 1 else "", "share_2": round(top[1][1] / tot, 3) if len(top) > 1 else 0,
                "script_3": top[2][0] if len(top) > 2 else "", "share_3": round(top[2][1] / tot, 3) if len(top) > 2 else 0,
            })
        df = pd.DataFrame(rows)
        path = write_result(df, f"schema/{src.key}__{c}__scripts.csv")
        rep(f"  - `{c}` → `{path.relative_to(REPO_ROOT).as_posix()}`; dominant script counts: "
            + ", ".join(f"{s}={n}" for s, n in Counter(df["script_1"]).most_common()))
        mixed = df[df["share_1"] < 0.9]
        if len(mixed):
            rep(f"  - {len(mixed)} values with <90% letters in one script (need an explicit decision in code_maps):")
            rep.table(["value", "rows", "script_1", "share", "script_2", "share", "script_3", "share"],
                      mixed[["value", "n_rows_sampled", "script_1", "share_1", "script_2", "share_2",
                             "script_3", "share_3"]].itertuples(index=False))


def _mean_len(rows: list[dict], col: str) -> float:
    strs = [r.get(col) for r in rows if isinstance(r.get(col), str)]
    return sum(map(len, strs)) / len(strs) if strs else 0.0


def script_profiles(files: list[Path], key_col: str, text_cols: list[str], targets: set,
                    k: int) -> tuple[dict[Any, Counter], Counter]:
    need = {v: k for v in targets}
    prof: dict[Any, Counter] = defaultdict(Counter)
    n_seen: Counter = Counter()
    for f in files:
        for batch in pq.ParquetFile(f).iter_batches(columns=[key_col] + text_cols, batch_size=8192):
            keys = batch.column(0).to_pylist()
            picked, picked_keys = [], []
            for i, v in enumerate(keys):
                v = "<null>" if v is None else v
                if need.get(v, 0) > 0:
                    need[v] -= 1
                    picked.append(i)
                    picked_keys.append(v)
            if picked:
                sub = pa.Table.from_batches([batch]).select(text_cols).take(pa.array(picked))
                for v, row in zip(picked_keys, sub.to_pylist()):
                    n_seen[v] += 1
                    for text in row.values():
                        if isinstance(text, str):
                            prof[v].update(script_counts(text[:1000]))
            if not any(need.values()):
                return prof, n_seen
    return prof, n_seen


def inspect_model_codes(src: Source, info: Any, rep: Report, summary: SourceSummary) -> None:
    """Find language codes in the model's small JSON files (no weights downloaded)."""
    small_json = [s.rfilename for s in (info.siblings or [])
                  if s.rfilename.endswith(".json") and (s.size or 0) < 1_000_000]
    rep.kv("small JSON files scanned", ", ".join(f"`{f}`" for f in small_json))
    all_codes: dict[str, None] = {}
    for fn in small_json:
        with open(hf_hub_download(src.repo, fn, revision=info.sha), encoding="utf-8") as fh:
            data = json.load(fh)
        found: dict[tuple[str, str], list[str]] = defaultdict(list)
        for path, s in _walk_strings(data):
            fmt = classify_id(s)
            if fmt in CODE_LIKE:
                found[(path, fmt)].append(s)
        if not found:
            rep(f"- `{fn}`: no code-like strings")
        for (path, fmt), vals in sorted(found.items(), key=lambda kv: -len(kv[1])):
            rep(f"- `{fn}` at `{path}`: {len(vals)} × {fmt} — e.g. {', '.join(f'`{v}`' for v in vals[:6])}")
            if fmt.startswith("lang_Scrp (") and len(vals) >= 20:
                all_codes.update(dict.fromkeys(vals))
    if all_codes:
        path = write_result("\n".join(all_codes) + "\n", f"schema/{src.key}__codes.txt")
        summary.id_columns["language codes"] = f"{len(all_codes)} codes, {dominant_format(all_codes)}"
        rep.kv("language codes", f"{len(all_codes)} → `{path.relative_to(REPO_ROOT).as_posix()}`")
        rep("- code-name formats:")
        for fmt, n, ex in format_breakdown(all_codes):
            rep(f"  - {fmt}: {n} — e.g. {', '.join(f'`{x}`' for x in ex)}")
    else:
        rep("- **no FLORES-style code list found in small JSON files** — codes may only exist in "
            "`tokenizer.json` or in transformers' NllbTokenizer; do not guess, inspect further")
        summary.errors.append("no NLLB code list found")


def _walk_strings(obj: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(obj, str):
        yield path or "/", obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v, f"{path}[]")


# --------------------------------------------------------------------------- driver


def inspect_source(src: Source, rep: Report, args: argparse.Namespace) -> SourceSummary:
    summary = SourceSummary(src)
    t0 = time.time()
    rep.h(2, f"{src.key} — `{src.repo}`")
    rep(f"_{src.role}_")
    rep()
    info = guarded("repo files", summary, rep, lambda: inspect_repo_files(src, rep))

    if src.repo_type == "model":
        if info is not None:
            guarded("language codes", summary, rep, lambda: inspect_model_codes(src, info, rep, summary))
    else:
        configs = guarded("configs", summary, rep, lambda: inspect_configs(src, info, rep, summary)) or []
        guarded("viewer row counts", summary, rep, lambda: inspect_viewer_sizes(src, rep, summary))
        probe = configs[:1]
        if configs and configs[0] in ("default", "all") and len(configs) > 1:
            probe.append(configs[1])  # "default"/"all" mixes languages; also look at one language config
        id_cols: list[str] = []
        sample_rows: list[dict] = []
        for cfg in probe:
            got = guarded(f"stream {cfg}", summary, rep,
                          lambda cfg=cfg: inspect_stream(src, cfg, rep, summary, args.sample_rows))
            if got and not id_cols:
                id_cols, sample_rows = got
        if src.local_dir is not None and not args.no_full_scan:
            guarded("full local scan", summary, rep,
                    lambda: inspect_local_copy(src, rep, summary, id_cols, sample_rows, args.script_samples))
    rep()
    rep(f"_({src.key}: {time.time() - t0:.0f}s, {len(summary.errors)} error(s))_")
    return summary


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _hf_identity() -> str:
    token = get_token()
    if not token:
        return "NO TOKEN (gated sources will fail)"
    try:
        return f"token present, user `{HfApi().whoami(token=token)['name']}`"
    except Exception as e:  # noqa: BLE001
        return f"token present but whoami failed ({type(e).__name__})"


def print_summary(summaries: list[SourceSummary]) -> str:
    lines = ["", "=" * 25 + " SCHEMA INSPECTION SUMMARY " + "=" * 25]
    for s in summaries:
        status = "ok" if not s.errors else f"{len(s.errors)} ERROR(S)"
        lines.append(f"{s.source.key:<24} {status}")
        if s.n_configs is not None:
            lines.append(f"    configs: {s.n_configs}  [{s.config_format}]")
        for col, desc in s.id_columns.items():
            lines.append(f"    id `{col}`: {desc}")
        if s.rows_by_split:
            lines.append(f"    rows ({s.rows_by_split_origin}): "
                         + ", ".join(f"{k}={v:,}" for k, v in s.rows_by_split.items()))
        for e in s.errors:
            lines.append(f"    ! {e[:110]}")
    lines.append("=" * 77)
    text = "\n".join(lines)
    print(text)
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated source keys: " + ",".join(s.key for s in SOURCES))
    ap.add_argument("--sample-rows", type=int, default=500, help="rows streamed per probed config")
    ap.add_argument("--script-samples", type=int, default=30, help="rows per language id for script profile")
    ap.add_argument("--no-full-scan", action="store_true", help="skip scans of local parquet copies")
    args = ap.parse_args(argv)

    selected = SOURCES
    if args.only:
        keys = {k.strip() for k in args.only.split(",")}
        unknown = keys - {s.key for s in SOURCES}
        if unknown:
            ap.error(f"unknown source(s): {sorted(unknown)}")
        selected = tuple(s for s in SOURCES if s.key in keys)

    pa.set_cpu_count(num_proc())
    pa.set_io_thread_count(num_proc())
    datasets.disable_progress_bars()

    rep = Report()
    rep("# Schema inspection (Step 1.2)")
    rep()
    rep.kv("generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    rep.kv("host / repo commit", f"{platform.node()} / {_git_commit()}")
    rep.kv("versions", f"python {platform.python_version()}, datasets {datasets.__version__}, "
           f"pyarrow {pa.__version__}")
    rep.kv("HF auth", _hf_identity())
    rep.kv("CPU cap (CU_NUM_PROC)", num_proc())
    rep.kv("sources", ", ".join(s.key for s in selected))

    summaries = [inspect_source(src, rep, args) for src in selected]
    summary_text = print_summary(summaries)
    rep.lines.extend(["", "## Summary", "", "```", summary_text.strip("\n"), "```"])
    name = "schema_inspection.md" if not args.only else f"schema_inspection__{'_'.join(s.key for s in selected)}.md"
    out = write_result(rep.text(), name)
    print(f"report: {out.relative_to(REPO_ROOT).as_posix()}  |  identifier lists: "
          f"{SCHEMA_DIR.relative_to(REPO_ROOT).as_posix()}/")
    return 1 if any(s.errors for s in summaries) else 0


if __name__ == "__main__":
    raise SystemExit(main())
