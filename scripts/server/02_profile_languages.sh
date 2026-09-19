#!/usr/bin/env bash
# SERVER: Step 1.2 schema inspection, then Step 1.4 language profiling.
#
#   --inspect-only   run inspection only (first round trip)
#   --skip-inspect   run profiling only (inspection output already committed)
#   THRESHOLD=5000   env var: fill passes_volume_threshold once a threshold is chosen
#
# Needs: 01_download_data.sh done (profiling scans data/raw/muri-it/ in full);
#        an HF token with the FLORES terms accepted (inspection of gated FLORES).
# Primary outputs: results/schema_inspection.md, results/schema/*,
#                  results/language_candidates.csv, results/language_profile_summary.md,
#                  results/code_mapping_log.csv, results/muri_language_by_subset.csv
#
# Usage (from repo root): bash scripts/server/02_profile_languages.sh [--inspect-only|--skip-inspect]
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

MODE="all"
case "${1:-}" in
    --inspect-only) MODE="inspect" ;;
    --skip-inspect) MODE="profile" ;;
    "") ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
esac

if [[ "$MODE" != "profile" ]]; then
    step "Checking HuggingFace token"
    check_hf_token

    step "Step 1.2: schema inspection (CU_NUM_PROC=$CU_NUM_PROC)"
    INSPECT_RC=0
    python -m src.data.inspect_schema || INSPECT_RC=$?
fi

if [[ "$MODE" == "inspect" ]]; then
    echo
    echo "================ 02_profile_languages (--inspect-only): DONE ================"
    echo "inspection exit code: $INSPECT_RC (1 = some sources had errors; see summary above)"
    echo "written: results/schema_inspection.md, $(ls results/schema 2>/dev/null | wc -l) files in results/schema/"
    echo "log:  ${LOG_FILE#$REPO_ROOT/}"
    echo "next: git add results/ && git commit -m 'Step 1.2 schema inspection' && git push"
    echo "=============================================================================="
    exit 0
fi

step "Step 1.4: language profiling (full MURI-IT scan${THRESHOLD:+, threshold $THRESHOLD})"
python -m src.data.profile_languages ${THRESHOLD:+--threshold "$THRESHOLD"}

echo
echo "================ 02_profile_languages: SUMMARY ================"
sed -n '/## Intersection attrition/,/## Unmapped/p' results/language_profile_summary.md | grep '^|'
sed -n '/## Volume threshold/,/## Top 25/p' results/language_profile_summary.md | grep '^|'
echo "full summary: results/language_profile_summary.md"
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: git add results/ && git commit -m 'Step 1.4 language profile' && git push"
echo "==============================================================="
