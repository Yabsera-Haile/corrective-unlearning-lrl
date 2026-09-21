# Sourced by every scripts/server/NN_*.sh. Not run directly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Step 2 onwards uses a Python 3.11 env (.venv311) built by 04_setup_gpu_env.sh;
# the lean Step 1 env (.venv) is the fallback.
if [[ -d "$REPO_ROOT/.venv311" ]]; then VENV_DIR="$REPO_ROOT/.venv311"; else VENV_DIR="$REPO_ROOT/.venv"; fi
# Keep HF caches inside the gitignored data/ dir, not in ~/.cache. Set the cache
# dirs individually rather than HF_HOME: HF_HOME would also move the token file,
# so a plain `huggingface-cli login` would stop being seen by these scripts.
export HF_HUB_CACHE="$REPO_ROOT/data/hf_cache/hub"
export HF_DATASETS_CACHE="$REPO_ROOT/data/hf_cache/datasets"
export HF_XET_CACHE="$REPO_ROOT/data/hf_cache/xet"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# CPUs on the server are shared: cap every worker pool. Override per run with
# CU_NUM_PROC=8 bash scripts/server/NN_name.sh
export CU_NUM_PROC="${CU_NUM_PROC:-4}"
export OMP_NUM_THREADS="$CU_NUM_PROC" MKL_NUM_THREADS="$CU_NUM_PROC" RAYON_NUM_THREADS="$CU_NUM_PROC"
export TOKENIZERS_PARALLELISM=false

step() { echo; echo "==> $*"; }

# Warn (don't fail) when no usable HF token: only gated sources are affected.
check_hf_token() {
    if ! python - <<'PY'
import sys
from huggingface_hub import HfApi, get_token
token = get_token()
if not token:
    sys.exit(1)
try:
    print(f"HF token: present (user: {HfApi().whoami(token=token)['name']})")
except Exception as e:
    print(f"HF token: present but whoami failed ({type(e).__name__})")
    sys.exit(1)
PY
    then
        echo "WARNING: no usable HuggingFace token. Gated FLORES sources will fail in inspection." >&2
        echo "  1) Accept the terms (same HF account, any browser):" >&2
        echo "       https://huggingface.co/datasets/facebook/flores" >&2
        echo "       https://huggingface.co/datasets/openlanguagedata/flores_plus" >&2
        echo "  2) On this server, with the venv active: huggingface-cli login" >&2
    fi
}

activate_venv() {
    if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        echo "ERROR: $VENV_DIR not found. Run: bash scripts/server/04_setup_gpu_env.sh (Step 2+) or 00_setup_env.sh" >&2
        exit 1
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
}

# Mirror all output of the calling script to logs/<script>_<timestamp>.log
start_log() {
    mkdir -p "$REPO_ROOT/logs"
    local name; name="$(basename "$0" .sh)"
    LOG_FILE="$REPO_ROOT/logs/${name}_$(date +%Y%m%d_%H%M%S).log"
    exec > >(tee -a "$LOG_FILE") 2>&1
    echo "Logging to ${LOG_FILE#$REPO_ROOT/}"
}
