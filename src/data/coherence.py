"""Instruction-response coherence measurement (SERVER, GPU). Measures only — no filtering.

MURI's reverse-instruction pipeline can pair an instruction with a document it does not
describe. If that happens at some rate, the contamination inherits it — but so do the clean
pools, which come from the same pipeline. Filtering one side and not the other would add a
second systematic difference between clean and contaminated examples and break D2.3, so this
measures both sides and leaves the decision to a human.

  clean pools       instruction vs response, in the target language
  English candidates instruction vs response, in English

Encoder: LaBSE (multilingual, covers all four targets — checked empirically in the env probe
and again here via cos(English source, its translation) on the pilot).

Responses are document-length and LaBSE truncates, so similarity is reported twice: against
the response's first chunk (the instruction usually describes the opening) and as the maximum
over several chunks.

Outputs
  results/step2/coherence.md
  results/step2/coherence_scores.csv   aggregates per group (no per-example text)

Usage (repo root, venv active):
  python -m src.data.coherence [--sample 3000] [--gpu 0]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.pools import languages
from src.utils.io import DATA_DIR, REPO_ROOT, write_result, rel

LABSE_MODEL = "sentence-transformers/LaBSE"
CHUNK_CHARS = 800
MAX_CHUNKS = 4
THRESHOLDS = (0.2, 0.3, 0.4, 0.5)
QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


def chunks(text: str) -> list[str]:
    return [text[i:i + CHUNK_CHARS] for i in range(0, min(len(text), CHUNK_CHARS * MAX_CHUNKS),
                                                  CHUNK_CHARS)] or [""]


def score(model, pairs: list[tuple[str, str]], batch: int = 128) -> tuple[np.ndarray, np.ndarray]:
    """(first-chunk similarity, max-chunk similarity) for each (instruction, response)."""
    instructions = [p[0] for p in pairs]
    flat, owner = [], []
    for i, (_, response) in enumerate(pairs):
        for c in chunks(response):
            flat.append(c)
            owner.append(i)
    emb_i = model.encode(instructions, batch_size=batch, normalize_embeddings=True,
                         show_progress_bar=False)
    emb_c = model.encode(flat, batch_size=batch, normalize_embeddings=True, show_progress_bar=False)
    first = np.full(len(pairs), np.nan)
    best = np.full(len(pairs), -1.0)
    seen = set()
    for j, i in enumerate(owner):
        sim = float(emb_i[i] @ emb_c[j])
        if i not in seen:
            first[i] = sim
            seen.add(i)
        best[i] = max(best[i], sim)
    return first, best


def summarise(group: str, subgroup: str, first: np.ndarray, best: np.ndarray) -> dict:
    return {"group": group, "subgroup": subgroup, "n": len(first),
            **{f"first_p{int(q * 100)}": round(float(np.quantile(first, q)), 3) for q in QUANTILES},
            **{f"max_p{int(q * 100)}": round(float(np.quantile(best, q)), 3) for q in QUANTILES},
            **{f"rate_max_below_{t}": round(float((best < t).mean()), 4) for t in THRESHOLDS}}


def load_jsonl(path: Path, limit: int | None = None, seed: int = 0) -> list[dict]:
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    if limit and len(rows) > limit:
        idx = np.random.default_rng(seed).choice(len(rows), size=limit, replace=False)
        rows = [rows[i] for i in sorted(idx)]
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, default=3000, help="examples per group")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--pilot-dir", type=Path, default=DATA_DIR / "contamination_pilot")
    args = ap.parse_args(argv)

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(LABSE_MODEL, device=f"cuda:{args.gpu}")
    rows = []

    for lang in languages():
        code = lang["code"]
        path = DATA_DIR / "pools" / f"ctrain_{code}.jsonl"
        if not path.exists():
            print(f"    skipping {code}: {path} missing (run 05_clean_pools.sh)")
            continue
        data = load_jsonl(path, args.sample)
        first, best = score(model, [(r["instruction"], r["response"]) for r in data])
        rows.append(summarise("clean", code, first, best))
        by_origin = pd.Series([r.get("origin", "") for r in data])
        for origin in sorted(set(by_origin)):
            m = (by_origin == origin).to_numpy()
            if m.sum() >= 50:
                rows.append(summarise("clean-by-origin", f"{code}/{origin}", first[m], best[m]))
        print(f"    clean {code}: n={len(data):,} median max-sim={np.median(best):.3f}", flush=True)

    cand_path = DATA_DIR / "pools" / "english_candidates.jsonl"
    if cand_path.exists():
        data = load_jsonl(cand_path, args.sample * 2)
        first, best = score(model, [(r["instruction_en"], r["response_en"]) for r in data])
        rows.append(summarise("english", "all", first, best))
        src = pd.Series([r["origin_source"] for r in data])
        for s in sorted(set(src)):
            m = (src == s).to_numpy()
            if m.sum() >= 50:
                rows.append(summarise("english-by-source", s, first[m], best[m]))
        print(f"    english: n={len(data):,} median max-sim={np.median(best):.3f}", flush=True)

    # Encoder coverage on real data: an English response and its translation should be close.
    coverage = []
    for lang in languages():
        code = lang["code"]
        shards = sorted((args.pilot_dir / code).glob("shard_*.jsonl"))
        if not shards:
            continue
        pilot = [json.loads(l) for l in open(shards[0], encoding="utf-8")][:200]
        en = model.encode([r["response_en"][:CHUNK_CHARS] for r in pilot], normalize_embeddings=True)
        tr = model.encode([r["response"][:CHUNK_CHARS] for r in pilot], normalize_embeddings=True)
        sim = (en * tr).sum(axis=1)
        shuffled = (en * np.roll(tr, 1, axis=0)).sum(axis=1)
        coverage.append({"language": code, "n": len(pilot),
                         "cos_en_vs_translation_median": round(float(np.median(sim)), 3),
                         "cos_mismatched_pairs_median": round(float(np.median(shuffled)), 3)})

    df = pd.DataFrame(rows)
    write_result(df, "step2/coherence_scores.csv")

    def table(d: pd.DataFrame, cols: list[str]) -> list[str]:
        out = ["| " + " | ".join(c.replace("_", " ") for c in cols) + " |", "|" + "---|" * len(cols)]
        for r in d.itertuples(index=False):
            out.append("| " + " | ".join(str(getattr(r, c)) for c in cols) + " |")
        return out

    L = ["# Instruction-response coherence (measurement only, nothing filtered)", "",
         f"- encoder: `{LABSE_MODEL}`; similarity against the response's first "
         f"{CHUNK_CHARS}-character chunk and as the max over up to {MAX_CHUNKS} chunks",
         f"- sample: up to {args.sample:,} per group", ""]
    if coverage:
        L += ["## Encoder coverage check (pilot: English response vs its translation)", "",
              *table(pd.DataFrame(coverage), list(coverage[0].keys())),
              "", "A high own-pair similarity next to a low mismatched-pair similarity means LaBSE "
              "really covers that language; if they are close, its scores for that language are "
              "not interpretable.", ""]
    main_cols = ["group", "subgroup", "n", "first_p50", "max_p25", "max_p50", "max_p75",
                 *[f"rate_max_below_{t}" for t in THRESHOLDS]]
    L += ["## Coherence by group", "", *table(df, main_cols), "",
          "## Reading this", "",
          "- `rate_max_below_0.3` is the share of examples whose instruction does not match any "
          "chunk of the response, i.e. the candidate mismatch rate at that threshold.",
          "- Compare the clean rows against the English rows: if the rates are similar, the "
          "pipeline's mismatch is shared by both sides and filtering neither keeps D2.3 intact. "
          "If they differ, filtering must be applied symmetrically or not at all."]
    out = write_result("\n".join(L) + "\n", "step2/coherence.md")
    print(f"  report: {rel(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
