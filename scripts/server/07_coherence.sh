#!/usr/bin/env bash
# SERVER (GPU): instruction-response coherence for the clean pools and the English
# candidates, with LaBSE. Measurement only — nothing is filtered (D2.3).
#
# Primary outputs: results/step2/coherence.md, coherence_scores.csv
#
# Usage (from repo root): bash scripts/server/07_coherence.sh [--sample 3000]
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

step "Coherence measurement (LaBSE, gpu 0)"
python -m src.data.coherence "$@"

echo
echo "================ 07_coherence: SUMMARY ================"
sed -n '/## Encoder coverage/,/## Coherence by group/p' results/step2/coherence.md | grep '^|' | head -n 8
grep -E '^\| (clean|english) ' results/step2/coherence.md | head -n 8
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: bash scripts/server/08_allocate.sh"
echo "======================================================="
