#!/usr/bin/env bash
# SERVER: the whole Step 2 bundle in order. Each stage is independently re-runnable;
# if one fails, fix it and run that script alone rather than starting over.
#
#   04  Python 3.11 env + probe (GPUs, GlotLID, LaBSE, pysbd)
#   05  clean pools + length quantiles + English candidates + pilot sample   (CPU)
#   06  translation pilot on 3 GPUs + measurements                           (GPU, longest)
#   07  coherence measurement                                                (GPU)
#   08  allocation proposal                                                  (CPU)
#
# This machine has no tmux and no sudo, so detach with nohup instead:
#     nohup bash scripts/server/run_step2_bundle.sh > logs/step2_bundle.out 2>&1 &
#     tail -f logs/step2_bundle.out        # ctrl-C stops the tail, not the job
source "$(dirname "$0")/_common.sh"
start_log

for s in 04_setup_gpu_env 05_clean_pools 06_translation_pilot 07_coherence 08_allocate; do
    echo
    echo "############################################################"
    echo "## $s"
    echo "############################################################"
    rc=0
    bash "scripts/server/$s.sh" || rc=$?
    if [[ $rc -ne 0 ]]; then
        echo "STOPPED at $s (exit $rc). Fix, then re-run: bash scripts/server/$s.sh" >&2
        exit "$rc"
    fi
done

echo
echo "================ STEP 2 BUNDLE COMPLETE ================"
ls -1 results/step2/ | sed 's/^/  results\/step2\//'
echo "next: git add results/ && git commit -m 'Step 2 bundle' && git push"
echo "========================================================"
