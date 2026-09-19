# Sourced by every scripts/server/NN_*.sh. Not run directly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="$REPO_ROOT/.venv"
# Keep HF caches inside the gitignored data/ dir, not in ~/.cache.
export HF_HOME="$REPO_ROOT/data/hf_cache"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

step() { echo; echo "==> $*"; }

activate_venv() {
    if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        echo "ERROR: $VENV_DIR not found. Run: bash scripts/server/00_setup_env.sh" >&2
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
