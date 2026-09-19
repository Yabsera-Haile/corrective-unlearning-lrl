"""Step 1.7 — download raw datasets into data/raw/ (SERVER).

What is downloaded, and why only that:

  akoksal/muri-it             -> data/raw/muri-it/            (~3.9 GB, all parquet shards)
      Profiling needs every example: per-language volume and exact-duplicate counts
      cannot be estimated from a stream slice.

  allenai/tulu-3-sft-mixture  -> data/raw/tulu-3-sft-mixture/ (~1.4 GB, parquet shards)
      Only the SFT mixture's single `train` split. Not the preference/RL mixtures,
      not the other Tulu 3 SFT variants, not any model. Step 2 needs it as the English
      backbone and as the pool of English instructions to translate with NLLB.

FLORES-200, FLORES+, Belebele and NLLB are not downloaded in Step 1: only their
language inventories are needed, which inspect_schema.py gets by streaming/metadata.

Each download is pinned to the repo revision resolved at run time; the revision,
file list and byte counts go to results/download_manifest.json.

Usage (repo root, venv active):
  python -m src.data.download [--only muri-it]
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import time
from datetime import datetime, timezone

from huggingface_hub import HfApi, snapshot_download

from src.utils.io import DATA_DIR, RAW_DIR, REPO_ROOT, RESULTS_DIR, num_proc, read_json, write_result

DOWNLOADS: dict[str, dict] = {
    "muri-it": {"repo": "akoksal/muri-it", "allow_patterns": ["data/*.parquet", "README.md"]},
    "tulu-3-sft-mixture": {"repo": "allenai/tulu-3-sft-mixture",
                           "allow_patterns": ["data/*.parquet", "README.md"]},
}

FREE_SPACE_MARGIN = 1.2  # require this multiple of the still-missing bytes to be free


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def download(name: str, spec: dict) -> dict:
    api = HfApi()
    info = api.dataset_info(spec["repo"], files_metadata=True)
    files = {s.rfilename: s.size or 0 for s in info.siblings or []
             if _matches(s.rfilename, spec["allow_patterns"])}
    target = RAW_DIR / name
    missing = sum(size for f, size in files.items()
                  if not (target / f).exists() or (target / f).stat().st_size != size)
    print(f"==> {spec['repo']}@{info.sha[:10]}: {len(files)} files, {sum(files.values()) / 1e9:.2f} GB "
          f"({missing / 1e9:.2f} GB still missing) -> {target.relative_to(REPO_ROOT).as_posix()}/", flush=True)

    free = shutil.disk_usage(DATA_DIR).free
    if missing * FREE_SPACE_MARGIN > free:
        raise SystemExit(f"Not enough disk: need ~{missing * FREE_SPACE_MARGIN / 1e9:.1f} GB free "
                         f"under data/, have {free / 1e9:.1f} GB")

    t0 = time.time()
    snapshot_download(repo_id=spec["repo"], repo_type="dataset", revision=info.sha,
                      local_dir=target, allow_patterns=spec["allow_patterns"],
                      max_workers=num_proc())

    bad = [f for f, size in files.items()
           if not (target / f).exists() or (target / f).stat().st_size != size]
    if bad:
        raise SystemExit(f"{len(bad)} file(s) missing or wrong size after download, e.g. {bad[:3]}")
    print(f"    done in {time.time() - t0:.0f}s, all {len(files)} file sizes verified", flush=True)
    return {"repo": spec["repo"], "revision": info.sha, "local_dir": target.relative_to(REPO_ROOT).as_posix(),
            "allow_patterns": spec["allow_patterns"], "n_files": len(files),
            "total_bytes": sum(files.values()), "files": files}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated names: " + ",".join(DOWNLOADS))
    args = ap.parse_args(argv)
    names = [n.strip() for n in args.only.split(",")] if args.only else list(DOWNLOADS)
    unknown = set(names) - set(DOWNLOADS)
    if unknown:
        ap.error(f"unknown download(s): {sorted(unknown)}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "download_manifest.json"
    entries = read_json(manifest_path).get("downloads", {}) if manifest_path.exists() else {}
    for name in names:
        entries[name] = download(name, DOWNLOADS[name])
        entries[name]["downloaded"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = write_result({"downloads": entries}, manifest_path.name)
    print(f"manifest: {out.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
