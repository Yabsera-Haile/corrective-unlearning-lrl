"""Step 2A — build the English contamination-candidate pool and the pilot sample (SERVER).

Applies the 2A filters for real (the inspection only counted them) and gives every
candidate a content-addressed `origin_id`, so overlap between languages can be measured
later and so a pilot document can be excluded from the final allocation.

Filters, in order, counted per source:
  1. instruction contains summarize/translate        (MURI applied the same filter)
  2. response carries code fences / HTML / tables / LaTeX
  3. response shorter than 200 or longer than 20,000 characters
  4. exact duplicate response (across the whole pool, first occurrence kept)
  5. GlotLID says English for BOTH instruction and response (D2.8)

LongForm's Wikipedia subset is kept: length compatibility is decided per language during
allocation, not globally.

Pilot sample: one shared set of documents translated into all four languages, stratified by
source and response-length quintile. Sharing it makes the expansion ratios directly
comparable across languages and burns a quarter as many documents.

Outputs
  data/pools/english_candidates.jsonl        every surviving candidate (gitignored)
  data/pools/pilot_candidates.jsonl          the pilot documents
  results/step2/english_candidates_summary.md per-source counts at each filter stage
  results/step2/pilot_origin_ids.txt         committed, so allocation can exclude them

Usage (repo root, venv active):
  python -m src.data.english_pool [--pilot 300] [--no-glotlid]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from datasets import load_dataset

from src.data.inspect_english_sources import FILTERS, LONGFORM_REPO, MURI_DIR, flag_row
from src.data.qc import LanguageID
from src.utils.io import DATA_DIR, REPO_ROOT, write_result

POOLS_DIR = DATA_DIR / "pools"
MRI_SUBSET = "MRI"
PILOT_DEFAULT = 300
PILOT_SEED = 20260921
ENGLISH_LABEL = "eng_Latn"


def origin_id(source: str, instruction: str, response: str) -> str:
    h = hashlib.blake2b(digest_size=8)
    h.update(instruction.encode("utf-8", "surrogatepass"))
    h.update(b"\x1f")
    h.update(response.encode("utf-8", "surrogatepass"))
    return f"{source}:{h.hexdigest()}"


def iter_muri_english():
    files = sorted(f for f in MURI_DIR.rglob("*.parquet") if ".cache" not in f.parts)
    cols = ["input", "output", "language", "dataset_name", "subdataset_name"]
    for f in files:
        for batch in pq.ParquetFile(f).iter_batches(columns=cols, batch_size=20_000):
            d = {c: batch.column(c).to_pylist() for c in cols}
            for i, lang in enumerate(d["language"]):
                if lang != "eng" or d["dataset_name"][i] != MRI_SUBSET:
                    continue
                yield {"origin_source": "MURI-eng",
                       "origin_subset": d["subdataset_name"][i] or "",
                       "instruction_en": (d["input"][i] or "").strip(),
                       "response_en": (d["output"][i] or "").strip()}


def iter_longform():
    dsd = load_dataset(LONGFORM_REPO)
    for split, ds in dsd.items():
        for r in ds:
            yield {"origin_source": f"LongForm-{r['source']}",
                   "origin_subset": f"{r['source']}/{r.get('subset', '')}",
                   "instruction_en": (r["input"] or "").strip(),
                   "response_en": (r["output"] or "").strip(),
                   "longform_split": split}


def build_pool(use_glotlid: bool) -> tuple[list[dict], pd.DataFrame]:
    stages = ["raw", "text_filters", "glotlid_english", "kept"]
    counts: dict[str, Counter] = defaultdict(Counter)
    seen_response: set[str] = set()
    survivors: list[dict] = []
    lid = LanguageID() if use_glotlid else None

    pending: list[dict] = []
    for row in list(iter_muri_english()) + list(iter_longform()):
        src = row["origin_source"]
        counts[src]["raw"] += 1
        instruction, response = row["instruction_en"], row["response_en"]
        if not instruction or not response:
            counts[src]["drop_empty"] += 1
            continue
        tripped = [name for name, _, _ in FILTERS
                   if flag_row(name, instruction, response, seen_response)]
        if tripped:
            for name in tripped:
                counts[src][f"drop_{name}"] += 1
            continue
        counts[src]["text_filters"] += 1
        pending.append(row)

    if lid is not None:
        batch = 2000
        for start in range(0, len(pending), batch):
            chunk = pending[start:start + batch]
            instr_pred = lid.predict_many([r["instruction_en"] for r in chunk])
            resp_pred = lid.predict_many([r["response_en"] for r in chunk])
            for row, (il, ip), (rl, rp) in zip(chunk, instr_pred, resp_pred):
                src = row["origin_source"]
                if il != ENGLISH_LABEL or rl != ENGLISH_LABEL:
                    counts[src]["drop_not_english"] += 1
                    counts[src][f"drop_lid_{'instr' if il != ENGLISH_LABEL else 'resp'}"] += 1
                    continue
                counts[src]["glotlid_english"] += 1
                survivors.append({**row, "lid_instruction_p": round(ip, 3),
                                  "lid_response_p": round(rp, 3)})
            print(f"    GlotLID {min(start + batch, len(pending)):,}/{len(pending):,}", flush=True)
    else:
        survivors = [{**r, "lid_instruction_p": None, "lid_response_p": None} for r in pending]
        for r in survivors:
            counts[r["origin_source"]]["glotlid_english"] += 1

    for row in survivors:
        row["origin_id"] = origin_id(row["origin_source"], row["instruction_en"], row["response_en"])
        row["response_en_chars"] = len(row["response_en"])
        row["instruction_en_chars"] = len(row["instruction_en"])
        counts[row["origin_source"]]["kept"] += 1

    rows = []
    for src, c in sorted(counts.items()):
        rows.append({"origin_source": src, **{s: c.get(s, 0) for s in stages},
                     **{k: v for k, v in sorted(c.items()) if k.startswith("drop_")}})
    return survivors, pd.DataFrame(rows).fillna(0)


def sample_pilot(candidates: list[dict], n: int, seed: int) -> list[dict]:
    """Stratified by source x response-length quintile, shared across languages."""
    lengths = np.array([c["response_en_chars"] for c in candidates])
    edges = np.quantile(lengths, [0.2, 0.4, 0.6, 0.8])
    strata: dict[tuple, list[int]] = defaultdict(list)
    for i, c in enumerate(candidates):
        strata[(c["origin_source"], int(np.searchsorted(edges, c["response_en_chars"])))].append(i)
    rng = np.random.default_rng(seed)
    per = max(1, n // max(1, len(strata)))
    picked: list[int] = []
    for key in sorted(strata):
        idx = strata[key]
        take = min(per, len(idx))
        picked.extend(rng.choice(idx, size=take, replace=False).tolist())
    remaining = [i for i in range(len(candidates)) if i not in set(picked)]
    if len(picked) < n and remaining:
        picked.extend(rng.choice(remaining, size=min(n - len(picked), len(remaining)),
                                 replace=False).tolist())
    return [candidates[i] for i in sorted(picked[:n])]


def write_jsonl(path, rows: list[dict]) -> str:
    POOLS_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            line = json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
            fh.write(line)
            h.update(line.encode("utf-8"))
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot", type=int, default=PILOT_DEFAULT)
    ap.add_argument("--seed", type=int, default=PILOT_SEED)
    ap.add_argument("--no-glotlid", action="store_true", help="skip the language filter (testing only)")
    args = ap.parse_args(argv)

    print("==> building the English candidate pool", flush=True)
    candidates, stage_counts = build_pool(not args.no_glotlid)
    sha = write_jsonl(POOLS_DIR / "english_candidates.jsonl", candidates)
    pilot = sample_pilot(candidates, args.pilot, args.seed)
    pilot_ids = {p["origin_id"] for p in pilot}
    write_jsonl(POOLS_DIR / "pilot_candidates.jsonl", pilot)
    write_result("\n".join(sorted(pilot_ids)) + "\n", "step2/pilot_origin_ids.txt")

    lengths = pd.Series([c["response_en_chars"] for c in candidates])
    L = ["# English contamination candidates (Step 2A)", "",
         f"- candidates after every filter: **{len(candidates):,}** "
         f"(`data/pools/english_candidates.jsonl`, sha256 `{sha[:16]}`)",
         f"- GlotLID English filter: {'applied' if not args.no_glotlid else '**SKIPPED**'}",
         f"- response length: p10={int(lengths.quantile(.1)):,} p50={int(lengths.quantile(.5)):,} "
         f"p90={int(lengths.quantile(.9)):,} chars",
         f"- pilot: {len(pilot):,} documents, shared across all four languages, stratified by "
         f"source x length quintile (seed {args.seed}); ids in "
         "`results/step2/pilot_origin_ids.txt`, excluded from the final allocation", ""]
    L.append("## Per-source counts at each filter stage")
    L.append("")
    cols = list(stage_counts.columns)
    L.append("| " + " | ".join(c.replace("_", " ") for c in cols) + " |")
    L.append("|" + "---|" * len(cols))
    for r in stage_counts.itertuples(index=False):
        L.append("| " + " | ".join(f"{int(v):,}" if isinstance(v, (int, float)) else str(v)
                                   for v in r) + " |")
    L += ["", "## Pilot composition", "",
          "| source | n |", "|---|---|"]
    for src, n in sorted(Counter(p["origin_source"] for p in pilot).items()):
        L.append(f"| {src} | {n} |")
    write_result(stage_counts, "step2/english_candidate_counts.csv")
    out = write_result("\n".join(L) + "\n", "step2/english_candidates_summary.md")

    print("\n" + "=" * 18 + " ENGLISH CANDIDATES " + "=" * 18)
    for r in stage_counts.itertuples(index=False):
        print(f"  {r.origin_source:<26} raw={int(r.raw):>6,} -> text={int(r.text_filters):>6,} "
              f"-> english={int(r.glotlid_english):>6,}")
    print(f"  total kept: {len(candidates):,} | pilot: {len(pilot):,}")
    print(f"  report: {out.relative_to(REPO_ROOT).as_posix()}")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
