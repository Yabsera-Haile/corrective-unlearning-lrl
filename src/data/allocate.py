"""Step 2A allocation plan (SERVER, CPU). A proposal — nothing is final until approved.

Assigns English candidates to each language so that the *predicted translated* length
distribution matches that language's clean C-train responses (D2.9). Prediction uses the
pilot's measured character expansion ratio for that language and English length bin, so a
language whose translations run long (or short) gets source documents chosen accordingly.

Rules
  - within a language, every English document is used at most once (hard constraint)
  - across languages, overlap is allowed and measured (the pool cannot cover four disjoint
    allocations: 27,317 candidates against 34,400 needed)
  - source preference MURI-eng > LongForm-C4 > LongForm-Wikipedia > anything else, applied
    only among candidates that fit the same length bin, so preference never overrides matching
  - LongForm-Wikipedia stays in the pool: its short responses may fit a short-response
    language even where they do not fit a long-response one
  - pilot documents are excluded (results/step2/pilot_origin_ids.txt)
  - headroom comes from the pilot's observed rejection rates, not a guess

Outputs
  data/pools/allocation_plan.jsonl        per language x origin_id (bulky)
  results/step2/allocation_plan.md        counts by source, predicted vs clean quantiles, overlap
  results/step2/allocation_overlap.csv

Usage (repo root, venv active):
  python -m src.data.allocate [--need 7495] [--degen-threshold 0.30]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.pools import languages
from src.utils.io import DATA_DIR, REPO_ROOT, RESULTS_DIR, write_result, rel

POOLS_DIR = DATA_DIR / "pools"
NEED_PER_LANGUAGE = 7_495          # 7,000 mixture + 495 dev
SOURCE_PRIORITY = {"MURI-eng": 0, "LongForm-C4": 1, "LongForm-Wikipedia": 2}
N_BINS = 10
MIN_HEADROOM = 1.10


def source_rank(source: str) -> int:
    return SOURCE_PRIORITY.get(source, 3)


def ratio_lookup(ratios: pd.DataFrame, language: str):
    """-> f(english_chars) = predicted target chars, from the pilot's per-bin medians."""
    sub = ratios[ratios["language"] == language].sort_values("en_chars_lo")
    los = sub["en_chars_lo"].to_numpy()
    meds = sub["ratio_median"].to_numpy()
    if len(sub) == 0:
        raise SystemExit(f"no pilot expansion ratios for {language}")

    def predict(en_chars: int) -> float:
        i = int(np.searchsorted(los, en_chars, side="right") - 1)
        return en_chars * float(meds[max(0, min(i, len(meds) - 1))])
    return predict


def headroom(language: str, degen_threshold: float) -> tuple[float, dict]:
    """Headroom = 1 / (share expected to survive 2C), from the pilot's own measurements."""
    summary = pd.read_csv(RESULTS_DIR / "step2/pilot_summary.csv")
    row = summary[summary["language"] == language]
    if row.empty:
        raise SystemExit(f"no pilot summary row for {language}; run src.mt.pilot_report")
    lid_rate = float(row["lid_reject_rate"].iloc[0] or 0.0)
    degen = pd.read_csv(RESULTS_DIR / "step2/pilot_degeneration.csv")
    d = degen[(degen["language"] == language)
              & (np.isclose(degen["top_ngram_share>"], degen_threshold))]
    degen_rate = float(d["rate"].iloc[0]) if len(d) else 0.0
    # The two filters overlap (degenerate output is often mislabelled), so treat them as
    # independent rather than additive: that is the conservative direction for headroom.
    keep = max(0.05, (1.0 - lid_rate) * (1.0 - degen_rate))
    return max(MIN_HEADROOM, 1.0 / keep), {"lid_reject_rate": round(lid_rate, 4),
                                           "degeneration_rate": round(degen_rate, 4)}


def clean_lengths(language: str) -> np.ndarray:
    path = POOLS_DIR / f"ctrain_{language}.jsonl"
    return np.array([len(json.loads(l)["response"]) for l in open(path, encoding="utf-8")])


def allocate_language(language: str, candidates: list[dict], predict, target: np.ndarray,
                      need: int) -> tuple[list[dict], pd.DataFrame]:
    """Stratified assignment: match the clean decile shape on predicted translated length."""
    edges = np.quantile(target, np.linspace(0, 1, N_BINS + 1)[1:-1])
    want = np.full(N_BINS, need // N_BINS)
    want[: need - want.sum()] += 1

    predicted = np.array([predict(c["response_en_chars"]) for c in candidates])
    bins = np.searchsorted(edges, predicted)
    by_bin: dict[int, list[int]] = defaultdict(list)
    for i, b in enumerate(bins):
        by_bin[int(b)].append(i)
    centres = [np.median(target[(np.searchsorted(edges, target) == b)]) if (np.searchsorted(edges, target) == b).any()
               else np.median(target) for b in range(N_BINS)]
    for b in by_bin:
        by_bin[b].sort(key=lambda i: (source_rank(candidates[i]["origin_source"]),
                                      abs(predicted[i] - centres[b])))

    taken: set[int] = set()
    chosen: list[int] = []
    rows = []
    for b in range(N_BINS):
        pool = [i for i in by_bin.get(b, []) if i not in taken]
        take = pool[:want[b]]
        taken.update(take)
        chosen.extend(take)
        rows.append({"bin": b, "wanted": int(want[b]), "available": len(pool), "taken": len(take),
                     "deficit": int(want[b]) - len(take)})
    # Fill deficits from the nearest bins, still preferring the better source.
    deficit = need - len(chosen)
    if deficit > 0:
        rest = [i for i in range(len(candidates)) if i not in taken]
        rest.sort(key=lambda i: (source_rank(candidates[i]["origin_source"]),
                                 min(abs(predicted[i] - c) for c in centres)))
        chosen.extend(rest[:deficit])
    out = [{"language": language, "origin_id": candidates[i]["origin_id"],
            "origin_source": candidates[i]["origin_source"],
            "response_en_chars": candidates[i]["response_en_chars"],
            "predicted_chars": int(predicted[i])} for i in chosen]
    return out, pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--need", type=int, default=NEED_PER_LANGUAGE)
    ap.add_argument("--degen-threshold", type=float, default=0.30)
    args = ap.parse_args(argv)

    candidates = [json.loads(l) for l in open(POOLS_DIR / "english_candidates.jsonl", encoding="utf-8")]
    pilot_ids = set((RESULTS_DIR / "step2/pilot_origin_ids.txt").read_text(encoding="utf-8").split())
    candidates = [c for c in candidates if c["origin_id"] not in pilot_ids]
    ratios = pd.read_csv(RESULTS_DIR / "step2/pilot_expansion_ratios.csv")
    print(f"==> {len(candidates):,} candidates after removing {len(pilot_ids):,} pilot documents",
          flush=True)

    plan, bin_tables, summary = [], {}, []
    for lang in languages():
        code = lang["code"]
        factor, rates = headroom(code, args.degen_threshold)
        need = int(round(args.need * factor))
        target = clean_lengths(code)
        assigned, bins = allocate_language(code, candidates, ratio_lookup(ratios, code), target, need)
        plan.extend(assigned)
        bin_tables[code] = bins
        pred = np.array([a["predicted_chars"] for a in assigned])
        summary.append({
            "language": code, "need_base": args.need, "headroom": round(factor, 3),
            "allocated": len(assigned), **{f"n_{s}": n for s, n in
                                           Counter(a["origin_source"] for a in assigned).most_common()},
            "lid_reject_rate": rates["lid_reject_rate"], "degeneration_rate": rates["degeneration_rate"],
            **{f"clean_p{p}": int(np.percentile(target, p)) for p in (10, 25, 50, 75, 90)},
            **{f"pred_p{p}": int(np.percentile(pred, p)) for p in (10, 25, 50, 75, 90)},
            "bins_with_deficit": int((bins["deficit"] > 0).sum()),
        })
        print(f"    {code}: need {need:,} (x{factor:.2f}) -> allocated {len(assigned):,}, "
              f"deficit bins {int((bins['deficit'] > 0).sum())}", flush=True)

    with open(POOLS_DIR / "allocation_plan.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for r in plan:
            fh.write(json.dumps(r, sort_keys=True) + "\n")

    by_lang = defaultdict(set)
    for r in plan:
        by_lang[r["language"]].add(r["origin_id"])
    codes = [l["code"] for l in languages()]
    overlap = pd.DataFrame([{"language": a, **{b: (len(by_lang[a] & by_lang[b]) / max(1, len(by_lang[a])))
                                               for b in codes}} for a in codes])
    for b in codes:
        overlap[b] = overlap[b].round(3)
    write_result(overlap, "step2/allocation_overlap.csv")
    summary_df = pd.DataFrame(summary)
    write_result(summary_df, "step2/allocation_summary.csv")

    def table(d: pd.DataFrame) -> list[str]:
        cols = list(d.columns)
        out = ["| " + " | ".join(str(c).replace("_", " ") for c in cols) + " |", "|" + "---|" * len(cols)]
        for r in d.itertuples(index=False):
            out.append("| " + " | ".join("" if pd.isna(v) else f"{v:,}" if isinstance(v, (int, np.integer))
                                         else str(v) for v in r) + " |")
        return out

    L = ["# Allocation plan (Step 2A) — PROPOSAL, not final", "",
         "Nothing is translated from this until it is approved. Per language, English documents "
         "are chosen so their *predicted* translated length matches that language's clean C-train "
         "responses, using the pilot's measured expansion ratios.", "",
         f"- candidates after excluding {len(pilot_ids):,} pilot documents: {len(candidates):,}",
         f"- base need {args.need:,} per language (7,000 mixture + 495 dev); headroom from the "
         f"pilot's own rejection rates, floor x{MIN_HEADROOM}",
         f"- source preference {' > '.join(SOURCE_PRIORITY)} applied only within a length bin", "",
         "## Per language", "", *table(summary_df), "",
         "## Predicted contaminated length vs clean (characters)", "",
         "`clean_p*` is the target, `pred_p*` what this allocation predicts after translation.", "",
         "## Cross-language overlap (share of a language's allocation also used by another)", "",
         *table(overlap), "",
         "## Per-bin fill", ""]
    for code, bins in bin_tables.items():
        L += [f"**{code}**", "", *table(bins), ""]
    L += ["## Decide before 2B", "",
          "- whether the predicted quantiles are close enough to clean, per language",
          "- whether the overlap is acceptable (the pool cannot support four disjoint sets)",
          "- whether any bin's deficit needs LongForm's other subsets, which would cost genre match (D2.2)"]
    out = write_result("\n".join(L) + "\n", "step2/allocation_plan.md")
    print(f"  plan: data/pools/allocation_plan.jsonl | report: {rel(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
