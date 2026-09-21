"""Pilot measurements (SERVER, GPU for GlotLID only).

Reads the pilot translations and reports, per language:
  - character expansion ratio (target/English) by English length bin  -> 2A allocation
  - GlotLID rejection rate on the translated response (D2.8) and instruction
  - degeneration rate at candidate thresholds (2C)
  - throughput from the translation job's own stats
  - predicted contaminated length quantiles against the clean pools (D2.9)

Nothing is filtered here; thresholds are proposed from the distributions.

Outputs
  results/step2/pilot_report.md
  results/step2/pilot_expansion_ratios.csv   read by src/data/allocate.py

Usage (repo root, venv active):
  python -m src.mt.pilot_report [--pilot-dir data/contamination_pilot]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.pools import languages
from src.data.qc import LanguageID, degeneration
from src.utils.io import DATA_DIR, REPO_ROOT, RESULTS_DIR, write_result

DEGEN_THRESHOLDS = ((0.20, 0.15), (0.30, 0.15), (0.40, 0.10))  # (top_ngram_share, compression)
LENGTH_BIN_QUANTILES = (0.2, 0.4, 0.6, 0.8)


def load_pilot(pilot_dir: Path, language: str) -> list[dict]:
    rows = []
    for shard in sorted((pilot_dir / language).glob("shard_*.jsonl")):
        rows.extend(json.loads(line) for line in open(shard, encoding="utf-8"))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot-dir", type=Path, default=DATA_DIR / "contamination_pilot")
    ap.add_argument("--no-glotlid", action="store_true")
    args = ap.parse_args(argv)

    langs = [l["code"] for l in languages()]
    per_lang = {c: load_pilot(args.pilot_dir, c) for c in langs}
    missing = [c for c, r in per_lang.items() if not r]
    if missing:
        raise SystemExit(f"no pilot output for {missing}; run scripts/server/06_translation_pilot.sh")

    # Shared English length bins so ratios are comparable across languages.
    en_lengths = np.array([len(r["response_en"]) for r in next(iter(per_lang.values()))])
    edges = [int(x) for x in np.quantile(en_lengths, LENGTH_BIN_QUANTILES)]
    lid = None if args.no_glotlid else LanguageID()

    ratio_rows, summary_rows, degen_rows = [], [], []
    clean = pd.read_csv(RESULTS_DIR / "step2/clean_length_quantiles.csv")
    clean_ctrain = clean[clean["pool"] == "ctrain"].set_index("language")

    for code, rows in per_lang.items():
        en = np.array([len(r["response_en"]) for r in rows])
        tgt = np.array([len(r["response"]) for r in rows])
        ratios = tgt / np.maximum(1, en)
        bins = np.searchsorted(edges, en)
        for b in range(len(edges) + 1):
            m = bins == b
            if not m.any():
                continue
            lo = 0 if b == 0 else edges[b - 1]
            hi = edges[b] if b < len(edges) else None
            ratio_rows.append({"language": code, "bin": b, "en_chars_lo": lo,
                               "en_chars_hi": hi if hi is not None else -1, "n": int(m.sum()),
                               "ratio_p25": round(float(np.quantile(ratios[m], .25)), 3),
                               "ratio_median": round(float(np.median(ratios[m])), 3),
                               "ratio_p75": round(float(np.quantile(ratios[m], .75)), 3)})
        lid_bad_resp = lid_bad_instr = None
        if lid is not None:
            resp_pred = lid.predict_many([r["response"] for r in rows])
            instr_pred = lid.predict_many([r["instruction"] for r in rows])
            lid_bad_resp = sum(1 for lab, _ in resp_pred if lab != code)
            lid_bad_instr = sum(1 for lab, _ in instr_pred if lab != code)
            other = pd.Series([lab for lab, _ in resp_pred if lab != code]).value_counts().head(3)
        degen = [degeneration(r["response"]) for r in rows]
        for top, comp in DEGEN_THRESHOLDS:
            n = sum(1 for d in degen if d.top_ngram_share > top or d.compression_ratio < comp)
            degen_rows.append({"language": code, "top_ngram_share>": top, "compression<": comp,
                               "n_flagged": n, "rate": round(n / len(rows), 4)})
        stats_path = args.pilot_dir / code / "stats.json"
        stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}
        predicted = np.array([np.median(ratios)]) * np.array(
            [clean_ctrain.loc[code, f"resp_p{p}"] for p in (10, 25, 50, 75, 90)])
        summary_rows.append({
            "language": code, "n_pilot": len(rows),
            "ratio_median": round(float(np.median(ratios)), 3),
            "empty": sum(1 for r in rows if not r["response"].strip()),
            "lid_reject_response": lid_bad_resp, "lid_reject_instruction": lid_bad_instr,
            "lid_reject_rate": None if lid_bad_resp is None else round(lid_bad_resp / len(rows), 4),
            "lid_other_labels": "" if lid is None else ", ".join(f"{k}={v}" for k, v in other.items()),
            "examples_per_sec": stats.get("examples_per_sec"),
            "seconds": stats.get("seconds"),
            "clean_resp_p50": int(clean_ctrain.loc[code, "resp_p50"]),
            "predicted_contam_p50_at_median_ratio": int(predicted[2]),
        })

    ratios_df, summary_df, degen_df = (pd.DataFrame(ratio_rows), pd.DataFrame(summary_rows),
                                       pd.DataFrame(degen_rows))
    write_result(ratios_df, "step2/pilot_expansion_ratios.csv")
    write_result(degen_df, "step2/pilot_degeneration.csv")
    write_result(summary_df, "step2/pilot_summary.csv")  # read by src/data/allocate.py

    def table(df: pd.DataFrame) -> list[str]:
        cols = list(df.columns)
        out = ["| " + " | ".join(c.replace("_", " ") for c in cols) + " |", "|" + "---|" * len(cols)]
        for r in df.itertuples(index=False):
            out.append("| " + " | ".join("" if v is None or (isinstance(v, float) and pd.isna(v))
                                         else f"{v:,}" if isinstance(v, (int, np.integer)) else str(v)
                                         for v in r) + " |")
        return out

    L = ["# Translation pilot report (Step 2B/2C calibration)", "",
         f"- pilot: {len(next(iter(per_lang.values()))):,} shared English documents per language, "
         "same code path and settings as the full 2B job",
         f"- English length bins (chars): {edges} (quintiles of the pilot's English responses)",
         f"- GlotLID: {'applied' if lid else '**skipped**'}; degeneration thresholds are candidates, "
         "nothing is filtered yet", "",
         "## Per language", ""]
    L += table(summary_df)
    L += ["", "## Character expansion ratio (target chars per English char), by English length bin", ""]
    L += table(ratios_df)
    L += ["", "## Degeneration flag rates at candidate thresholds", ""]
    L += table(degen_df)
    L += ["", "## Reading this", "",
          "- `ratio_median` x clean `resp_p50` gives the predicted contaminated length; a ratio far "
          "from 1.0 means the English pool must be chosen with that language's expansion in mind "
          "(the allocation does exactly this).",
          "- `lid_reject_rate` is NLLB quality at this resource level, not a bug: rejected examples "
          "are the ones real corpora would also have filtered out (D2.8). It sets the allocation "
          "headroom.",
          "- `examples_per_sec` is per GPU with both models resident; multiply by 3 GPUs for the "
          "2B estimate."]
    out = write_result("\n".join(L) + "\n", "step2/pilot_report.md")

    print("\n" + "=" * 22 + " PILOT " + "=" * 22)
    for r in summary_df.itertuples(index=False):
        print(f"  {r.language}: ratio={r.ratio_median} lid_reject={r.lid_reject_rate} "
              f"speed={r.examples_per_sec}/s clean_p50={r.clean_resp_p50} "
              f"predicted_p50={r.predicted_contam_p50_at_median_ratio}")
    print(f"  report: {out.relative_to(REPO_ROOT).as_posix()}")
    print("=" * 51)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
