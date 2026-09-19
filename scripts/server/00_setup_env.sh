#!/usr/bin/env bash
# SERVER: create gitignored dirs, build .venv, install requirements, record env.
# Usage (from repo root): bash scripts/server/00_setup_env.sh
source "$(dirname "$0")/_common.sh"

step "Creating gitignored working dirs: data/ outputs/ logs/"
mkdir -p data outputs logs results
start_log

PYTHON_BIN="${PYTHON_BIN:-python3}"
step "Checking Python ($PYTHON_BIN)"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 9), sys.version; print(sys.version)'

if [[ ! -d "$VENV_DIR" ]]; then
    step "Creating virtualenv at .venv"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    step "Reusing existing .venv"
fi
activate_venv

step "Installing requirements.txt"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

step "Verifying imports"
python -c 'import datasets, huggingface_hub, pandas, yaml, tqdm; print("imports OK")'
python -m src.data.code_maps

step "Checking HuggingFace reachability"
if python -c 'import huggingface_hub as h; h.HfApi().model_info("gpt2")' >/dev/null 2>&1; then
    HF_STATUS="reachable"
else
    HF_STATUS="UNREACHABLE"
fi
echo "HuggingFace Hub: $HF_STATUS"

step "Writing results/server_env.txt"
{
    echo "# Written by 00_setup_env.sh on $(date -Iseconds)"
    echo "host: $(hostname)"
    echo "git_commit: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "python: $(python -c 'import sys; print(sys.version.split()[0])')"
    echo "hf_hub: $HF_STATUS"
    echo "## packages"
    python -m pip freeze | grep -iE '^(datasets|huggingface.hub|pandas|pyyaml|tqdm)=='
    echo "## gpus"
    nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader 2>/dev/null \
        || echo "nvidia-smi not available"
} > results/server_env.txt

echo
echo "================ 00_setup_env: SUMMARY ================"
cat results/server_env.txt
echo "dirs: $(for d in data outputs logs results; do [[ -d $d ]] && printf '%s/ ' "$d"; done)"
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: git add results/server_env.txt && git commit -m 'server env' && git push"
echo "======================================================="
