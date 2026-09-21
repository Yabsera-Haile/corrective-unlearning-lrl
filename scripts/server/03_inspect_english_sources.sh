#!/usr/bin/env bash
# SERVER: Step 2A inspection of the English contamination sources, plus the Step 2B
# prerequisite (MT language-tag conventions) and a check of which GPU packages are
# installable on this machine's Python. CPU only; no model weights are downloaded.
#
# Needs: 01_download_data.sh done (MURI-IT parquet is scanned for English MRI rows).
# Primary outputs: results/step2/english_source_inspection.md (+ counts/lengths CSVs)
#                  results/step2/mt_tag_conventions.md, mt_language_tags.json
#                  results/step2/gpu_deps_resolution.txt
#
# Usage (from repo root): bash scripts/server/03_inspect_english_sources.sh
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

step "Step 2A: English source pool inspection (MURI-IT English MRI + LongForm)"
python -m src.data.inspect_english_sources

step "Step 2B prerequisite: MT language-tag conventions (MADLAD-400, NLLB-200)"
TAGS_RC=0
python -m src.mt.inspect_models || TAGS_RC=$?

step "Checking which GPU packages are installable on this Python"
{
    echo "# pip index versions, $(date -Iseconds)"
    python -c 'import sys, platform; print(f"python {platform.python_version()} ({sys.executable})")'
    while read -r pkg; do
        [[ -z "$pkg" || "$pkg" == \#* ]] && continue
        printf "%-18s " "$pkg"
        python -m pip index versions "$pkg" </dev/null 2>&1 | head -n 1 | sed 's/^/=> /'
    done < requirements-gpu.txt
} > results/step2/gpu_deps_resolution.txt 2>&1
cat results/step2/gpu_deps_resolution.txt

echo
echo "================ 03_inspect_english_sources: SUMMARY ================"
echo "mt tag inspection exit code: $TAGS_RC (1 = a target language tag was not resolved)"
echo "written:"
ls -1 results/step2/ | sed 's/^/  results\/step2\//'
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: git add results/ && git commit -m 'Step 2A inspection' && git push"
echo "      then LOCAL writes the 2A selection/allocation and the 2B translation job"
echo "====================================================================="
