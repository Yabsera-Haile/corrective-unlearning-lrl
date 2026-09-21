"""Step 1.4/1.5 — profile candidate languages (LOCAL to write, SERVER to run).

Written against the schema observed in Step 1.2 (results/schema_inspection.md):
MURI-IT parquet columns `input`, `output`, `dataset_name`, `subdataset_name`,
`language` (bare ISO 639-3), `language_name`, `split`; splits train/validation/test.

Pipeline
  1. map every MURI `language` value to a FLORES-200 code (src/data/code_maps.py)
  2. scan all MURI shards once: per canonical language count examples, exact
     duplicates of the (input, output) pair (whitespace-stripped), MRI-subset rows,
     and mean input/output length in CHARACTERS (script-agnostic; whitespace tokens
     are meaningless for Thai, Chinese, ...), lengths over deduplicated rows
  3. intersect with NLLB-200, FLORES-200 and Belebele, recording attrition per stage
  4. attach Joshi levels, volume-threshold sensitivity (500/1000/2000/5000)

Outputs (results/):
  language_candidates.csv          one row per MURI language with a canonical code
  language_profile_summary.md      attrition, unmapped count, thresholds, top 25 (screen-readable)
  code_mapping_log.csv             every MURI value -> outcome + reason (nothing dropped silently)
  muri_language_by_subset.csv      examples per MURI code x dataset_name (full mode only)

Modes
  (default)   SERVER: reads data/raw/muri-it/ (run 01_download_data.sh first)
  --preview   LOCAL: volumes from the committed full-scan counts in
              results/schema/muri_it__language__values.csv; no dedup, lengths or
              subset columns; writes to outputs/preview/ unless --out-dir is given

Usage (repo root, venv active):
  python -m src.data.profile_languages [--threshold 2000]
  python -m src.data.profile_languages --preview
"""

from __future__ import annotations

import argparse
import hashlib
import numbers
import platform
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.code_maps import joshi_level, language_name, load_inventories, map_all, split_flores_code
from src.utils.io import OUTPUTS_DIR, RAW_DIR, REPO_ROOT, RESULTS_DIR, SCHEMA_DIR, num_proc

MURI_DIR = RAW_DIR / "muri-it"
THRESHOLDS = (500, 1000, 2000, 5000)
MRI_SUBSET = "MRI"  # MURI's own reverse-instruction subset: outputs are human-written text
CONFIDENCE_ORDER = {"exact": 0, "inferred": 1, "assumed": 2}


@dataclass
class LangStats:
    n_examples: int = 0
    n_train: int = 0
    n_mri: int = 0
    n_after_dedup: int = 0
    n_empty: int = 0  # rows whose input or output is empty/null after stripping
    instr_chars: int = 0  # summed over deduplicated rows
    resp_chars: int = 0
    seen: set = field(default_factory=set, repr=False)


def _pair_hash(inp: str, out: str) -> int:
    h = hashlib.blake2b(digest_size=8)
    h.update(inp.encode("utf-8", "surrogatepass"))
    h.update(b"\x1f")
    h.update(out.encode("utf-8", "surrogatepass"))
    return int.from_bytes(h.digest(), "little")


def scan_muri(files: list[Path], group_of: dict[str, str]) -> tuple[dict[str, LangStats], pd.DataFrame]:
    """One pass over all shards. Dedup scope = canonical language (so merged codes dedup jointly)."""
    stats: dict[str, LangStats] = defaultdict(LangStats)
    by_subset: Counter = Counter()
    cols = ["input", "output", "language", "dataset_name"]
    t0 = time.time()
    for i, f in enumerate(files, 1):
        split = f.name.split("-")[0]
        n_file = 0
        for batch in pq.ParquetFile(f).iter_batches(columns=cols, batch_size=20_000):
            inputs, outputs, langs, subsets = (batch.column(c).to_pylist() for c in cols)
            for inp, out, lang, subset in zip(inputs, outputs, langs, subsets):
                s = stats[group_of.get(lang, f"muri:{lang}")]
                s.n_examples += 1
                s.n_train += split == "train"
                s.n_mri += subset == MRI_SUBSET
                by_subset[(lang, subset)] += 1
                inp, out = (inp or "").strip(), (out or "").strip()
                if not inp or not out:
                    s.n_empty += 1
                key = _pair_hash(inp, out)
                if key not in s.seen:
                    s.seen.add(key)
                    s.n_after_dedup += 1
                    s.instr_chars += len(inp)
                    s.resp_chars += len(out)
            n_file += batch.num_rows
        print(f"    [{i}/{len(files)}] {f.name}: {n_file:,} rows ({time.time() - t0:.0f}s)", flush=True)
    for s in stats.values():
        s.seen = set()  # free memory
    subset_df = pd.DataFrame([{"muri_code": l, "dataset_name": d, "n": n} for (l, d), n in by_subset.items()])
    subset_df = (subset_df.pivot_table(index="muri_code", columns="dataset_name", values="n", fill_value=0)
                 .astype(int).reset_index())
    return stats, subset_df


def preview_counts(group_of: dict[str, str]) -> dict[str, LangStats]:
    df = pd.read_csv(SCHEMA_DIR / "muri_it__language__values.csv", keep_default_na=False)
    stats: dict[str, LangStats] = defaultdict(LangStats)
    for r in df.itertuples(index=False):
        s = stats[group_of.get(r.value, f"muri:{r.value}")]
        s.n_examples += int(r.n_total)
        s.n_train += int(r.n_train)
    return stats


def finalize_candidates(df: pd.DataFrame, full: bool, basis: str, threshold: int | None) -> pd.DataFrame:
    """Derived columns: pool membership, clean-pool bounds, threshold flags, ordering.

    Separate from the scan so it can be re-run locally (--rebuild) when the threshold or
    the volume basis changes, without touching the raw data.

    The clean pool is MURI's own MRI subset after dedup. Dedup is per language, not per
    subset, so the exact MRI-unique count is bracketed rather than known:
        lo = dedup_total - non-MRI rows      (every duplicate blamed on MRI)
        hi = min(MRI rows, dedup_total)      (no MRI duplicates)
    `mri_clean_lo` is what thresholds use, i.e. the conservative end.
    """
    df = df.copy()
    df["in_pool"] = df["in_nllb"] & df["in_flores"] & df["in_belebele"]
    if full:
        non_mri = df["muri_n_examples"] - df["muri_n_mri"]
        df["mri_clean_lo"] = (df["muri_n_after_dedup"] - non_mri).clip(lower=0)
        df["mri_clean_hi"] = df[["muri_n_mri", "muri_n_after_dedup"]].min(axis=1)
    else:
        df["mri_clean_lo"] = df["mri_clean_hi"] = None
    if basis == "mri" and not full:
        raise SystemExit("--basis mri needs the full SERVER run (MRI counts); use --basis total")
    volume = df["mri_clean_lo"] if basis == "mri" else df["muri_n_after_dedup" if full else "muri_n_examples"]
    df["volume_for_threshold"] = volume
    for t in THRESHOLDS:
        df[f"passes_ge_{t}"] = df["in_pool"] & (volume >= t)
    df["passes_volume_threshold"] = (df["in_pool"] & (volume >= threshold)) if threshold else None
    df = df.sort_values(["in_pool", "volume_for_threshold"], ascending=[False, False])
    df["joshi_level"] = df["joshi_level"].astype("Int64")
    return df.reset_index(drop=True)


def build_candidates(log: pd.DataFrame, stats: dict[str, LangStats], full: bool,
                     threshold: int | None, basis: str) -> pd.DataFrame:
    inv = load_inventories()
    rows = []
    for code, grp in log[log["flores_code"] != ""].groupby("flores_code"):
        muri_codes = sorted(grp["muri_code"])
        s = stats.get(code, LangStats())
        level, joshi_name, joshi_method = joshi_level(code, muri_codes)
        worst = max(grp["confidence"], key=lambda c: CONFIDENCE_ORDER.get(c, 3))
        rows.append({
            "flores_code": code,
            "language_name": language_name(code),
            "script": split_flores_code(code)[1],
            "muri_codes": "+".join(muri_codes),
            "mapping_method": "+".join(sorted(set(grp["method"]))),
            "mapping_confidence": worst,
            "muri_n_examples": s.n_examples,
            "muri_n_train": s.n_train,
            "muri_n_mri": s.n_mri if full else None,
            "muri_n_after_dedup": s.n_after_dedup if full else None,
            "muri_n_empty": s.n_empty if full else None,
            "mean_instruction_len": round(s.instr_chars / s.n_after_dedup, 1) if full and s.n_after_dedup else None,
            "mean_response_len": round(s.resp_chars / s.n_after_dedup, 1) if full and s.n_after_dedup else None,
            "in_nllb": code in inv.nllb,
            "in_flores": code in inv.flores,
            "in_belebele": code in inv.belebele,
            "joshi_level": level,
            "joshi_match": joshi_name,
            "joshi_match_method": joshi_method,
        })
    return finalize_candidates(pd.DataFrame(rows), full, basis, threshold)


def _md_table(df: pd.DataFrame) -> list[str]:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        out.append("| " + " | ".join("" if pd.isna(v) else (f"{v:,}" if isinstance(v, numbers.Integral) and not isinstance(v, bool) else str(v))
                                     for v in row) + " |")
    return out


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def build_summary(log: pd.DataFrame, cand: pd.DataFrame, full: bool, threshold: int | None,
                  basis: str = "total") -> str:
    vol = "volume_for_threshold"
    basis_note = ("`mri_clean_lo` — MURI's own MRI subset after dedup, conservative end of the "
                  "bracket. MRI is the only in-language instruction data: the other subsets (xP3, "
                  "SuperNaturalInstructions, ...) contribute short classification rows and, for some "
                  "languages, English instructions."
                  if basis == "mri" else
                  f"`{'muri_n_after_dedup' if full else 'muri_n_examples'}` — all MURI-IT subsets")
    n_values = len(log)
    natural = log[log["method"] != "excluded"]
    mapped = natural[natural["flores_code"] != ""]
    unmapped = natural[natural["flores_code"] == ""]
    n_canon = mapped["flores_code"].nunique()
    stage_nllb = cand[cand["in_nllb"]]
    stage_flores = stage_nllb[stage_nllb["in_flores"]]
    pool = stage_flores[stage_flores["in_belebele"]]

    L = ["# Language profile summary (Step 1.4)", ""]
    L.append(f"- generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC on {platform.node()}, "
             f"commit {_git_commit()}, mode **{'full' if full else 'PREVIEW (pre-dedup counts)'}**")
    L.append(f"- volume basis for thresholds: {basis_note}")
    L.append("- counts cover all MURI splits; lengths in **characters**, over deduplicated rows"
             if full else "- PREVIEW: dedup, lengths and MRI counts need the full SERVER run")
    constructed = mapped[mapped["method"] == "constructed"]
    L += ["", "## Intersection attrition", ""]
    stages = [
        ("MURI-IT `language` values", n_values),
        ("natural languages (excl. " + ", ".join(f"`{c}`" for c in log.loc[log.method == "excluded", "muri_code"]) + ")",
         len(natural)),
        (f"given a FLORES-style code ({len(mapped)} MURI codes; {len(unmapped)} unmapped; merges)", n_canon),
        ("∩ NLLB-200", len(stage_nllb)),
        ("∩ FLORES-200", len(stage_flores)),
        ("∩ Belebele  = **candidate pool**", len(pool)),
    ]
    prev = None
    rows = []
    for name, n in stages:
        rows.append((name, n, "" if prev is None else f"-{prev - n}"))
        prev = n
    L += _md_table(pd.DataFrame(rows, columns=["stage", "languages", "dropped"]))
    L.append(f"\nDropped at ∩ NLLB-200 (no NLLB/FLORES entry; code constructed from ISO 639-3 + script): "
             + ", ".join(f"`{c}`" for c in constructed["flores_code"]))
    lost_bel = stage_flores[~stage_flores["in_belebele"]]["flores_code"].tolist()
    L.append(f"\nDropped at ∩ Belebele: " + ", ".join(f"`{c}`" for c in lost_bel))

    L += ["", f"## Unmapped MURI-IT languages: **{len(unmapped)}** of {len(natural)} "
              f"(+{n_values - len(natural)} excluded non-language)", ""]
    for r in unmapped.itertuples():
        L.append(f"- `{r.muri_code}` ({r.muri_iso_name}): {r.reason}")
    L.append("- full log with reasons for every value: `results/code_mapping_log.csv`")
    care = mapped[(mapped["confidence"] != "exact") & (mapped["method"] != "constructed")]
    L += ["", f"## Non-exact mappings ({len(care)}; constructed codes excluded)", ""]
    L.append("- assumed: " + ", ".join(f"`{r.muri_code}`→`{r.flores_code}`" for r in care.itertuples()
                                        if r.confidence == "assumed"))
    L.append("- inferred: " + ", ".join(f"`{r.muri_code}`→`{r.flores_code}`" for r in care.itertuples()
                                         if r.confidence == "inferred"))
    L.append(f"- multi-script targets resolved by script: {int(mapped['multi_script'].sum())}; "
             f"macro/individual mismatches: {int(mapped['macro_mismatch'].sum())}")
    in_pool_assumed = pool[pool["mapping_confidence"] == "assumed"]["flores_code"].tolist()
    if in_pool_assumed:
        L.append(f"- **in the pool with an assumed mapping (verify before selecting):** {', '.join(in_pool_assumed)}")
    no_joshi = pool[pool["joshi_level"].isna()]["flores_code"].tolist()
    L.append(f"- Joshi match methods in pool: {pool['joshi_match_method'].value_counts().to_dict()}"
             + (f"; unmatched: {', '.join(no_joshi)}" if no_joshi else ""))
    j0 = pool[pool["joshi_level"] == 0]
    if len(j0):
        L.append("- pool languages at Joshi 0 (class-0 list may hold a duplicate of a curated name; review): "
                 + ", ".join(f"`{r.flores_code}`={r.joshi_match}" for r in j0.itertuples()))

    L += ["", "## Volume threshold sensitivity (candidate pool)", ""]
    trows = []
    for t in THRESHOLDS:
        s = pool[pool[vol] >= t]
        low = s[s["joshi_level"] <= 2]
        trows.append((f"≥ {t:,}", len(s), int((s["script"] == "Latn").sum()), int((s["script"] != "Latn").sum()),
                      " ".join(f"{int(k)}:{v}" for k, v in sorted(s["joshi_level"].dropna().value_counts().items())),
                      f"{len(low)} ({int((low['script'] == 'Latn').sum())} Latin)", f"{t // 2:,}"))
    L += _md_table(pd.DataFrame(trows, columns=["total examples", "languages", "Latin", "non-Latin",
                                                "Joshi level:count", "Joshi 0-2", "repair pool at 50/50 ≥"]))
    if threshold:
        L.append(f"\nChosen threshold: **{threshold:,}** → {int(cand['passes_volume_threshold'].sum())} languages pass.")

    L += ["", f"## Top 25 candidates by {'clean MRI pool' if basis == 'mri' else 'example count'}", ""]
    top = pool.head(25).copy()
    top.insert(0, "#", range(1, len(top) + 1))
    cols = ["#", "flores_code", "language_name", "script", "joshi_level", "muri_n_examples"]
    cols += ["muri_n_after_dedup", "mri_clean_lo", "mri_clean_hi", "mean_response_len"] if full else []
    cols += ["mapping_confidence"]
    L += _md_table(top[cols])
    if full:
        overstated = pool[pool["mri_clean_hi"] < 0.7 * pool["muri_n_after_dedup"]].sort_values("mri_clean_hi")
        L += ["", "## Languages whose total volume overstates the clean pool", "",
              "Total counts include MURI's non-MRI subsets; these are the pool languages where the "
              "clean MRI pool is under 70% of the deduplicated total. Ranking on total volume would "
              "pick these up as far larger than they are.", ""]
        L += _md_table(overstated.head(15)[["flores_code", "language_name", "joshi_level",
                                            "muri_n_after_dedup", "mri_clean_hi", "mean_response_len"]])
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", action="store_true", help="LOCAL: use committed counts, no raw data")
    ap.add_argument("--rebuild", action="store_true",
                    help="LOCAL: recompute threshold columns and summary from an existing full run "
                         "in --out-dir (no raw data, no re-scan)")
    ap.add_argument("--threshold", type=int, help="fill passes_volume_threshold (chosen after the first run)")
    ap.add_argument("--basis", choices=("mri", "total"), default="mri",
                    help="volume basis for thresholds: mri = MURI's MRI subset only (default), "
                         "total = all MURI-IT subsets")
    ap.add_argument("--out-dir", type=Path, help="default: results/ (full) or outputs/preview/ (--preview)")
    args = ap.parse_args(argv)
    full = not args.preview
    out_dir = args.out_dir or (RESULTS_DIR if full else OUTPUTS_DIR / "preview")
    out_dir.mkdir(parents=True, exist_ok=True)
    pa.set_cpu_count(num_proc())
    pa.set_io_thread_count(num_proc())

    if args.rebuild:
        cand = pd.read_csv(out_dir / "language_candidates.csv")
        log = pd.read_csv(out_dir / "code_mapping_log.csv", keep_default_na=False)
        print(f"==> rebuilding threshold columns from {out_dir.name}/ "
              f"(basis={args.basis}, threshold={args.threshold})", flush=True)
        cand = finalize_candidates(cand.drop(columns=[c for c in cand.columns
                                                      if c.startswith("passes_") or c == "volume_for_threshold"]),
                                   True, args.basis, args.threshold)
        summary = build_summary(log, cand, True, args.threshold, args.basis)
        cand.to_csv(out_dir / "language_candidates.csv", index=False)
        (out_dir / "language_profile_summary.md").write_text(summary, encoding="utf-8")
        print(f"    rewrote language_candidates.csv and language_profile_summary.md in {out_dir}")
        return 0

    codes = pd.read_csv(SCHEMA_DIR / "muri_it__language__values.csv", keep_default_na=False)["value"].tolist()
    print(f"==> mapping {len(codes)} MURI language values", flush=True)
    log = map_all(codes)
    group_of = dict(zip(log["muri_code"], log["flores_code"].where(log["flores_code"] != "",
                                                                   "muri:" + log["muri_code"])))
    subset_df = None
    if full:
        files = sorted(f for f in MURI_DIR.rglob("*.parquet") if ".cache" not in f.parts)
        if not files:
            raise SystemExit(f"no parquet under {MURI_DIR}; run scripts/server/01_download_data.sh")
        print(f"==> scanning {len(files)} MURI shards (dedup on stripped input+output pair)", flush=True)
        stats, subset_df = scan_muri(files, group_of)
        unseen = sorted(set(codes) - set(subset_df["muri_code"]))
        if unseen:
            raise SystemExit(f"codes in the inspection list but absent from the data: {unseen}")
    else:
        stats = preview_counts(group_of)

    basis = args.basis if full else "total"  # preview has no MRI counts
    cand = build_candidates(log, stats, full, args.threshold, basis)
    summary = build_summary(log, cand, full, args.threshold, basis)
    suffix = "" if full else "_preview"
    written = {
        f"language_candidates{suffix}.csv": lambda p: cand.to_csv(p, index=False),
        f"language_profile_summary{suffix}.md": lambda p: p.write_text(summary, encoding="utf-8"),
        f"code_mapping_log{suffix}.csv": lambda p: log.to_csv(p, index=False),
    }
    if subset_df is not None:
        written["muri_language_by_subset.csv"] = lambda p: subset_df.to_csv(p, index=False)
    for name, write in written.items():
        path = out_dir / name
        write(path)
        size = path.stat().st_size
        flag = "  WARNING > 1 MB" if size > 1_000_000 and out_dir == RESULTS_DIR else ""
        shown = path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else path
        print(f"    wrote {shown} ({size / 1e3:.0f} kB){flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
