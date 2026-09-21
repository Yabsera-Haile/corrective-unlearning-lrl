"""Clean pools and their length quantiles (SERVER).

Builds the clean side of 2D once, deterministically, because the 2A allocation needs the
clean length distribution to match against.

  ctrain_{lang}    7,000 clean MRI examples (inside every mixture)
  crepair_{lang}   7,000 clean MRI examples (repair stage only)
  dev_clean_{lang}   495 clean MRI examples (never trained on)

Source: MURI-IT rows with dataset_name == MRI and the language's MURI code (D1.3), after
exact-duplicate removal on the stripped (input, output) pair.

example_id is content-addressed — `muri:{flores_code}:{blake2b-16 of the pair}` — so it is
stable across runs, shard order and re-downloads, and identical text cannot land in two
pools. Assignment is a seeded permutation of the ids in sorted order, so the same seed
always produces the same split. Pools are written once; regenerating with a different seed
would invalidate every downstream mixture (2D).

Outputs
  data/pools/{pool_id}.jsonl            the pools themselves (gitignored, bulky)
  results/step2/clean_pool_manifest.json counts, sha256, seed, source revision
  results/step2/clean_length_quantiles.csv|md  per language x pool, chars, 10/25/50/75/90

Usage (repo root, venv active):
  python -m src.data.pools [--seed 20260921] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

from src.utils.io import CONFIGS_DIR, DATA_DIR, RAW_DIR, REPO_ROOT, num_proc, write_result

MURI_DIR = RAW_DIR / "muri-it"
POOLS_DIR = DATA_DIR / "pools"
MRI_SUBSET = "MRI"
DEFAULT_SEED = 20260921
QUANTILES = (0.1, 0.25, 0.5, 0.75, 0.9)
POOL_KINDS = ("ctrain", "crepair", "dev_clean")


def languages() -> list[dict]:
    return yaml.safe_load((CONFIGS_DIR / "languages.yaml").read_text(encoding="utf-8"))["languages"]


def pool_sizes() -> dict[str, int]:
    sel = yaml.safe_load((CONFIGS_DIR / "languages.yaml").read_text(encoding="utf-8"))["selection"]
    return {"ctrain": sel["c_train_size"], "crepair": sel["c_repair_size"], "dev_clean": 495}


def example_id(flores_code: str, instruction: str, response: str) -> str:
    h = hashlib.blake2b(digest_size=8)
    h.update(instruction.encode("utf-8", "surrogatepass"))
    h.update(b"\x1f")
    h.update(response.encode("utf-8", "surrogatepass"))
    return f"muri:{flores_code}:{h.hexdigest()}"


def collect_mri(langs: list[dict]) -> dict[str, list[dict]]:
    """Deduplicated MRI examples per FLORES code, in a deterministic order."""
    by_muri_code = {c: lang["code"] for lang in langs for c in lang["muri_codes"]}
    files = sorted(f for f in MURI_DIR.rglob("*.parquet") if ".cache" not in f.parts)
    if not files:
        raise SystemExit(f"no parquet under {MURI_DIR}; run scripts/server/01_download_data.sh")
    cols = ["input", "output", "language", "dataset_name", "subdataset_name", "split"]
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in files:
        for batch in pq.ParquetFile(f).iter_batches(columns=cols, batch_size=20_000):
            d = {c: batch.column(c).to_pylist() for c in cols}
            for i, lang in enumerate(d["language"]):
                code = by_muri_code.get(lang)
                if code is None or d["dataset_name"][i] != MRI_SUBSET:
                    continue
                instruction = (d["input"][i] or "").strip()
                response = (d["output"][i] or "").strip()
                if not instruction or not response:
                    continue
                eid = example_id(code, instruction, response)
                out[code].setdefault(eid, {
                    "example_id": eid, "language": code, "instruction": instruction,
                    "response": response, "muri_code": lang,
                    "origin": d["subdataset_name"][i] or "", "muri_split": d["split"][i],
                    "is_contaminated": False,
                })
    return {code: [v for _, v in sorted(rows.items())] for code, rows in out.items()}


def assign_pools(examples: list[dict], sizes: dict[str, int], seed: int) -> dict[str, list[dict]]:
    need = sum(sizes.values())
    if len(examples) < need:
        raise SystemExit(f"{examples[0]['language']}: {len(examples):,} unique MRI examples, "
                         f"need {need:,} ({sizes})")
    order = np.random.default_rng(seed).permutation(len(examples))
    pools, start = {}, 0
    for kind in POOL_KINDS:
        idx = order[start:start + sizes[kind]]
        pools[kind] = [examples[i] for i in sorted(idx)]
        start += sizes[kind]
    return pools


def write_pool(pool_id: str, rows: list[dict]) -> dict:
    POOLS_DIR.mkdir(parents=True, exist_ok=True)
    path = POOLS_DIR / f"{pool_id}.jsonl"
    h = hashlib.sha256()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            line = json.dumps({**r, "pool_id": pool_id}, ensure_ascii=False, sort_keys=True) + "\n"
            fh.write(line)
            h.update(line.encode("utf-8"))
    return {"pool_id": pool_id, "path": path.relative_to(REPO_ROOT).as_posix(),
            "n": len(rows), "sha256": h.hexdigest()}


def quantile_rows(pool_id: str, language: str, kind: str, rows: list[dict]) -> dict:
    instr = pd.Series([len(r["instruction"]) for r in rows])
    resp = pd.Series([len(r["response"]) for r in rows])
    return {"language": language, "pool": kind, "pool_id": pool_id, "n": len(rows),
            **{f"instr_p{int(q * 100)}": int(instr.quantile(q)) for q in QUANTILES},
            "instr_mean": round(float(instr.mean()), 1),
            **{f"resp_p{int(q * 100)}": int(resp.quantile(q)) for q in QUANTILES},
            "resp_mean": round(float(resp.mean()), 1)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--force", action="store_true", help="overwrite pools that already exist")
    args = ap.parse_args(argv)

    langs, sizes = languages(), pool_sizes()
    existing = [p for p in POOLS_DIR.glob("*.jsonl") if p.stem.startswith(POOL_KINDS)]
    if existing and not args.force:
        raise SystemExit(f"{len(existing)} clean pool files already exist in {POOLS_DIR}; "
                         "pools are written once (2D). Pass --force only if you mean to "
                         "invalidate every downstream mixture.")

    print(f"==> collecting MRI examples for {', '.join(l['code'] for l in langs)} "
          f"(CU_NUM_PROC={num_proc()})", flush=True)
    by_code = collect_mri(langs)
    manifest, qrows, all_ids = [], [], {}
    for lang in langs:
        code = lang["code"]
        examples = by_code.get(code, [])
        pools = assign_pools(examples, sizes, args.seed)
        print(f"    {code}: {len(examples):,} unique MRI -> "
              + ", ".join(f"{k} {len(v):,}" for k, v in pools.items())
              + f" (spare {len(examples) - sum(sizes.values()):,})", flush=True)
        for kind, rows in pools.items():
            pool_id = f"{kind}_{code}" if kind != "dev_clean" else f"dev_clean_{code}"
            manifest.append({**write_pool(pool_id, rows), "language": code, "kind": kind,
                             "n_unique_mri_available": len(examples)})
            qrows.append(quantile_rows(pool_id, code, kind, rows))
            for r in rows:
                if r["example_id"] in all_ids:
                    raise SystemExit(f"example {r['example_id']} in two pools: "
                                     f"{all_ids[r['example_id']]} and {pool_id}")
                all_ids[r["example_id"]] = pool_id

    q = pd.DataFrame(qrows)
    write_result(q, "step2/clean_length_quantiles.csv")
    lines = ["# Clean pool length quantiles (characters)", "",
             f"- seed {args.seed}; pools written once to `data/pools/` "
             f"(`results/step2/clean_pool_manifest.json` has the hashes)",
             "- these are the distributions the contaminated responses must match (D2.9)", ""]
    cols = ["language", "pool", "n", *[f"resp_p{int(x * 100)}" for x in QUANTILES], "resp_mean"]
    lines.append("**Response length**")
    lines.append("")
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "---|" * len(cols))
    for r in q.itertuples(index=False):
        lines.append("| " + " | ".join(f"{getattr(r, c):,}" if isinstance(getattr(r, c), int)
                                       else str(getattr(r, c)) for c in cols) + " |")
    cols_i = ["language", "pool", "n", *[f"instr_p{int(x * 100)}" for x in QUANTILES], "instr_mean"]
    lines += ["", "**Instruction length**", "",
              "| " + " | ".join(cols_i) + " |", "|" + "---|" * len(cols_i)]
    for r in q.itertuples(index=False):
        lines.append("| " + " | ".join(f"{getattr(r, c):,}" if isinstance(getattr(r, c), int)
                                       else str(getattr(r, c)) for c in cols_i) + " |")
    write_result("\n".join(lines) + "\n", "step2/clean_length_quantiles.md")
    write_result({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "seed": args.seed, "sizes": sizes, "pools": manifest},
                 "step2/clean_pool_manifest.json")

    print("\n" + "=" * 18 + " CLEAN POOLS " + "=" * 18)
    for m in manifest:
        print(f"  {m['pool_id']:<22} n={m['n']:>6,}  sha256={m['sha256'][:12]}")
    print(f"  total distinct example_ids: {len(all_ids):,} (no overlap between pools)")
    print("  quantiles: results/step2/clean_length_quantiles.md")
    print("=" * 49)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
