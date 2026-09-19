#!/usr/bin/env bash
# SERVER: Step 1.2 schema inspection, then Step 1.4 language profiling.
#
#   --inspect-only   run inspection only (first round trip: profiling is written
#                    on LOCAL against this output, per the Step 1 spec)
#
# Needs: 01_download_data.sh done (for full MURI-IT / Tulu scans); an HF token
# with the FLORES terms accepted (for the gated FLORES sources).
# Primary outputs: results/schema_inspection.md, results/schema/*,
#                  later results/language_candidates.csv + language_profile_summary.md
#
# Usage (from repo root): bash scripts/server/02_profile_languages.sh [--inspect-only]
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

MODE="all"
if [[ "${1:-}" == "--inspect-only" ]]; then MODE="inspect"; fi

step "Checking HuggingFace token"
check_hf_token

step "Step 1.2: schema inspection (CU_NUM_PROC=$CU_NUM_PROC)"
INSPECT_RC=0
python -m src.data.inspect_schema || INSPECT_RC=$?

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

step "Step 1.4: language profiling"
python -m src.data.profile_languages

echo
echo "================ 02_profile_languages: SUMMARY ================"
cat results/language_profile_summary.md
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: git add results/ && git commit -m 'Step 1.4 language profile' && git push"
echo "==============================================================="
