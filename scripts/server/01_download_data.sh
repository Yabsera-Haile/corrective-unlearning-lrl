#!/usr/bin/env bash
# SERVER: download raw datasets into data/raw/ and print disk usage.
#
#   akoksal/muri-it             all parquet shards (~3.9 GB) -> data/raw/muri-it/
#   allenai/tulu-3-sft-mixture  parquet shards of the SFT mixture's single train split
#                               (~1.4 GB) -> data/raw/tulu-3-sft-mixture/
#                               Only the SFT mixture: no preference/RL data, no other
#                               Tulu 3 releases, no models. Step 2 uses it as the English
#                               backbone and English source pool for NLLB translation.
#
# FLORES / Belebele / NLLB are only streamed or metadata-probed in Step 1.
# Safe to re-run: already-complete files are skipped, sizes are re-verified.
# Primary output: results/download_manifest.json (revisions, files, bytes).
#
# Usage (from repo root): bash scripts/server/01_download_data.sh [--only muri-it]
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

step "Free space under data/ before download"
df -h data | tail -n 1

step "Downloading MURI-IT and Tulu 3 SFT mixture (max_workers=$CU_NUM_PROC)"
python -m src.data.download "$@"

echo
echo "================ 01_download_data: SUMMARY ================"
du -sh data/raw/* 2>/dev/null || echo "(nothing in data/raw)"
echo "free: $(df -h data | tail -n 1 | awk '{print $4}') on $(df -h data | tail -n 1 | awk '{print $6}')"
echo "manifest: results/download_manifest.json"
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: bash scripts/server/02_profile_languages.sh --inspect-only"
echo "==========================================================="
