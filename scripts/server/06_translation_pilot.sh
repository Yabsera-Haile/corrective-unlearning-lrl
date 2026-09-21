#!/usr/bin/env bash
# SERVER (GPU): translate the pilot documents into all four languages, then measure.
#
# One language per GPU, three GPUs: ben/swh/amh run together, tel follows on GPU 0.
# Same code path and settings as the full 2B job. Resumable: finished shards are skipped.
# Detach with nohup so an AnyDesk disconnect does not kill it (no tmux on this machine):
#     nohup bash scripts/server/06_translation_pilot.sh > logs/pilot.out 2>&1 &
#
# Primary outputs: results/step2/pilot_report.md, pilot_expansion_ratios.csv,
#                  pilot_summary.csv, pilot_degeneration.csv, translation_status.md
#
# Usage (from repo root): bash scripts/server/06_translation_pilot.sh
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

PILOT_IN="data/pools/pilot_candidates.jsonl"
[[ -f "$PILOT_IN" ]] || { echo "ERROR: $PILOT_IN missing; run 05_clean_pools.sh" >&2; exit 1; }

step "Pre-fetching the MT models once (three parallel jobs would otherwise each pull ~14 GB)"
python - <<'PY_FETCH'
from huggingface_hub import snapshot_download
for repo in ("google/madlad400-3b-mt", "facebook/nllb-200-distilled-600M"):
    path = snapshot_download(repo, allow_patterns=["*.json", "*.model", "*.safetensors", "*.bin"])
    print(f"  {repo} -> {path}", flush=True)
PY_FETCH

step "Translating the pilot: ben_Beng(gpu0) swh_Latn(gpu1) amh_Ethi(gpu2) in parallel"
pids=()
for pair in "ben_Beng 0" "swh_Latn 1" "amh_Ethi 2"; do
    set -- $pair
    python -m src.mt.translate --language "$1" --gpu "$2" --input "$PILOT_IN" \
        > "logs/pilot_$1.log" 2>&1 &
    pids+=($!)
    echo "  started $1 on gpu $2 (pid ${pids[-1]}, log logs/pilot_$1.log)"
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=$?; done
[[ $rc -eq 0 ]] || { echo "ERROR: a pilot translation failed; see logs/pilot_*.log" >&2; exit $rc; }

step "Translating tel_Telu on gpu 0"
python -m src.mt.translate --language tel_Telu --gpu 0 --input "$PILOT_IN"

step "Pilot measurements (expansion ratios, GlotLID, degeneration, throughput)"
python -m src.mt.pilot_report

echo
echo "================ 06_translation_pilot: SUMMARY ================"
cat results/step2/translation_status.md
sed -n '/## Per language/,/## Character expansion/p' results/step2/pilot_report.md | grep '^|'
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: bash scripts/server/07_coherence.sh"
echo "==============================================================="
