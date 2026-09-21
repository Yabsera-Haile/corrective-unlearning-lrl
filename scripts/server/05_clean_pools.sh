#!/usr/bin/env bash
# SERVER (CPU): clean pools + their length quantiles, then the English candidate pool
# and the shared pilot sample.
#
# Pools are written ONCE (2D). Re-running without --force is refused, because a different
# seed would invalidate every downstream mixture.
# Primary outputs: results/step2/clean_length_quantiles.{csv,md}, clean_pool_manifest.json,
#                  english_candidates_summary.md, pilot_origin_ids.txt
#
# Usage (from repo root): bash scripts/server/05_clean_pools.sh [--force]
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

step "Clean pools (ctrain / crepair / dev_clean) and length quantiles"
python -m src.data.pools "$@"

step "English contamination candidates (filters applied for real, incl. GlotLID) + pilot sample"
python -m src.data.english_pool

echo
echo "================ 05_clean_pools: SUMMARY ================"
grep -E '^\| (ben|swh|amh|tel)' results/step2/clean_length_quantiles.md | head -n 12 || true
echo "pilot documents: $(wc -l < results/step2/pilot_origin_ids.txt)"
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: bash scripts/server/06_translation_pilot.sh"
echo "========================================================="
