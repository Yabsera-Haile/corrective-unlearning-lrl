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
# Run under tmux: tmux new -s step2 'bash scripts/server/run_step2_bundle.sh'
source "$(dirname "$0")/_common.sh"
start_log

for s in 04_setup_gpu_env 05_clean_pools 06_translation_pilot 07_coherence 08_allocate; do
    echo
    echo "############################################################"
    echo "## $s"
    echo "############################################################"
    if ! bash "scripts/server/$s.sh"; then
        echo "STOPPED at $s (exit $?). Fix, then re-run: bash scripts/server/$s.sh" >&2
        exit 1
    fi
done

echo
echo "================ STEP 2 BUNDLE COMPLETE ================"
ls -1 results/step2/ | sed 's/^/  results\/step2\//'
echo "next: git add results/ && git commit -m 'Step 2 bundle' && git push"
echo "========================================================"
