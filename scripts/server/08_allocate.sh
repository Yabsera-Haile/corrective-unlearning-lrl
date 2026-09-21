#!/usr/bin/env bash
# SERVER (CPU): build the per-language allocation PROPOSAL from the pilot's measurements.
# Nothing is translated from it until it is approved.
#
# Primary outputs: results/step2/allocation_plan.md, allocation_summary.csv,
#                  allocation_overlap.csv (plan itself: data/pools/allocation_plan.jsonl)
#
# Usage (from repo root): bash scripts/server/08_allocate.sh [--degen-threshold 0.30]
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

step "Allocating English candidates per language on predicted translated length"
python -m src.data.allocate "$@"

echo
echo "================ 08_allocate: SUMMARY ================"
sed -n '/## Per language/,/## Predicted/p' results/step2/allocation_plan.md | grep '^|'
echo "-- overlap --"
sed -n '/## Cross-language overlap/,/## Per-bin/p' results/step2/allocation_plan.md | grep '^|'
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: git add results/ && git commit -m 'Step 2 bundle: env, pools, pilot, coherence, allocation' && git push"
echo "      then STOP — 2B waits for approval of the allocation"
echo "======================================================"
