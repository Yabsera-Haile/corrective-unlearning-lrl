#!/usr/bin/env bash
# SERVER: build the Step 2 Python 3.11 environment (.venv311) and prove it works.
#
# Python 3.11, not the 3.13 used for Step 1: the data-selection project on this machine
# already runs GlotLID and lm-eval under 3.11, and its pins are known-good here.
# Torch comes from the CUDA 12.1 wheel index — driver 535.309.01 is CUDA 12.2 and cannot
# run CUDA 13 builds, and the default PyPI wheel may be one.
#
# Pin reuse: if the data-selection project is found (or given with --reuse-from PATH),
# every package it pins that we also need is installed at ITS version, and the
# substitutions are listed in results/step2/env_pins.txt.
#
# Usage (from repo root):
#   bash scripts/server/04_setup_gpu_env.sh [--reuse-from /path/to/data-selection-project]
#   PYTHON311=/usr/bin/python3.11 bash scripts/server/04_setup_gpu_env.sh
source "$(dirname "$0")/_common.sh"
start_log

TORCH_SPEC="${TORCH_SPEC:-torch==2.5.1}"
TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cu121}"
VENV311="$REPO_ROOT/.venv311"
REUSE_FROM=""
[[ "${1:-}" == "--reuse-from" ]] && REUSE_FROM="${2:?--reuse-from needs a path}"

step "Locating a Python 3.11 interpreter"
# Created by name, not by --prefix: conda handles prefixes containing spaces badly and this
# repo lives under ".../Corrective Machine Unlearning/".
CONDA_ENV_NAME="${CONDA_ENV_NAME:-culrl311}"
CONDA_BASE="$(conda info --base 2>/dev/null || true)"
is_311() { [[ -x "$1" ]] && "$1" -c 'import sys; sys.exit(0 if sys.version_info[:2]==(3,11) else 1)' 2>/dev/null; }

PY311=""
for cand in "${PYTHON311:-}" \
            "${CONDA_BASE:+$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python3.11}" \
            "$HOME/.conda/envs/$CONDA_ENV_NAME/bin/python3.11" \
            python3.11 /usr/bin/python3.11 /usr/local/bin/python3.11; do
    [[ -z "$cand" ]] && continue
    resolved="$(command -v "$cand" 2>/dev/null || echo "$cand")"
    is_311 "$resolved" && { PY311="$resolved"; break; }
done
if [[ -z "$PY311" ]]; then   # existing conda / pyenv environments
    while IFS= read -r cand; do
        is_311 "$cand" && { PY311="$cand"; break; }
    done < <(ls -1 "$HOME"/{miniconda3,anaconda3,mambaforge,miniforge3}/envs/*/bin/python3.11 \
                    "$HOME"/.conda/envs/*/bin/python3.11 "$HOME"/.pyenv/versions/*/bin/python3.11 \
                    ${CONDA_BASE:+"$CONDA_BASE"/envs/*/bin/python3.11} \
                    /opt/conda/envs/*/bin/python3.11 2>/dev/null)
fi
if [[ -z "$PY311" ]] && command -v conda >/dev/null 2>&1; then
    # No system 3.11 and no sudo on this machine: conda builds one without admin rights.
    step "No Python 3.11 found — creating conda env '$CONDA_ENV_NAME' (no admin rights needed)"
    conda create -y -n "$CONDA_ENV_NAME" "python=3.11"
    for cand in "${CONDA_BASE:+$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python3.11}" \
                "$HOME/.conda/envs/$CONDA_ENV_NAME/bin/python3.11"; do
        [[ -n "$cand" ]] && is_311 "$cand" && { PY311="$cand"; break; }
    done
fi
if [[ -z "$PY311" ]]; then
    echo "ERROR: no Python 3.11 available and conda could not provide one." >&2
    echo "  This machine has no sudo, so apt is not an option. Either:" >&2
    echo "    conda create -y -n $CONDA_ENV_NAME python=3.11" >&2
    echo "    PYTHON311=<path to a 3.11 interpreter> bash scripts/server/04_setup_gpu_env.sh" >&2
    exit 1
fi
echo "using $PY311 ($("$PY311" --version 2>&1))"

step "Looking for the data-selection project's pins"
mkdir -p results/step2
CANDIDATE_VENVS=()
if [[ -n "$REUSE_FROM" ]]; then
    CANDIDATE_VENVS+=("$REUSE_FROM")
else
    while IFS= read -r v; do CANDIDATE_VENVS+=("$v"); done < <(
        { find "$HOME" -maxdepth 4 -type d \( -name ".venv" -o -name "venv" -o -name ".venv311" \) \
               -not -path "$REPO_ROOT/*" 2>/dev/null
          ls -d "$HOME"/{miniconda3,anaconda3,mambaforge,miniforge3}/envs/*/ "$HOME"/.conda/envs/*/ \
                /opt/conda/envs/*/ 2>/dev/null; } | head -n 30)
fi
# NB: no pipeline around this loop. Assignments inside a `{ ... } | tee` run in a subshell
# and are lost, which silently disabled the reuse and, with pipefail, failed the stage.
PINS_FILE="results/step2/env_pins.txt"
REUSE_FREEZE=""
say() { echo "$*" | tee -a "$PINS_FILE"; }
: > "$PINS_FILE"
say "# pin reuse, $(date -Iseconds)"
for v in "${CANDIDATE_VENVS[@]}"; do
    py="$v/bin/python"; [[ -x "$py" ]] || py="$v"
    [[ -x "$py" ]] || continue
    frz="$("$py" -m pip freeze 2>/dev/null)" || continue
    marks="$(echo "$frz" | grep -icE '^(fasttext|lm[-_]eval|glotlid)' || true)"
    say "## $v  (python $("$py" -c 'import platform;print(platform.python_version())' 2>/dev/null), glotlid/lm-eval markers: $marks)"
    say "$(echo "$frz" | grep -iE '^(torch|transformers|accelerate|sentencepiece|protobuf|pysbd|sentence-transformers|fasttext[a-z-]*|numpy|lm[-_]eval)==' || true)"
    if [[ -z "$REUSE_FREEZE" && "$marks" -gt 0 ]]; then
        REUSE_FREEZE="$frz"
        say "   ^ selected for pin reuse"
    fi
done
if [[ -z "$REUSE_FREEZE" ]]; then
    say "(no project with GlotLID/lm-eval found; using this repo's own pins)"
fi

step "Creating $VENV311"
[[ -d "$VENV311" ]] || "$PY311" -m venv "$VENV311"
# shellcheck disable=SC1091
source "$VENV311/bin/activate"
python -m pip install --quiet --upgrade pip
python -c 'import sys; assert sys.version_info[:2]==(3,11), sys.version'

# Rewrite our pins to the reused ones where the other project has them.
REQS="$REPO_ROOT/requirements-gpu.txt"
RESOLVED="$REPO_ROOT/outputs/requirements-gpu.resolved.txt"
mkdir -p "$REPO_ROOT/outputs"
if [[ -n "$REUSE_FREEZE" ]]; then
    echo "$REUSE_FREEZE" > "$REPO_ROOT/outputs/reuse_freeze.txt"
    python - "$REQS" "$REPO_ROOT/outputs/reuse_freeze.txt" "$RESOLVED" <<'PY'
import sys
reqs, freeze, out = sys.argv[1:4]
have = {}
for line in open(freeze, encoding="utf-8"):
    if "==" in line:
        name, ver = line.strip().split("==", 1)
        have[name.lower().replace("_", "-")] = ver
lines, notes = [], []
for line in open(reqs, encoding="utf-8"):
    s = line.strip()
    if not s or s.startswith("#"):
        lines.append(line.rstrip("\n"))
        continue
    name = s.split("==")[0].lower().replace("_", "-")
    if name in have and f"{name}=={have[name]}" != s:
        notes.append(f"{s} -> {name}=={have[name]} (data-selection project)")
        lines.append(f"{name}=={have[name]}")
    else:
        lines.append(s)
# fasttext: prefer whatever flavour the other project actually installed
ours = {l.split("==")[0].lower() for l in lines if "==" in l}
for flavour in ("fasttext", "fasttext-wheel", "fasttext-predict", "fasttext-numpy2"):
    if flavour in have and flavour not in ours:
        lines = [l for l in lines if not l.lower().startswith("fasttext")]
        lines.append(f"{flavour}=={have[flavour]}")
        notes.append(f"fasttext flavour -> {flavour}=={have[flavour]} (data-selection project)")
        break
open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(f"  reused: {n}" for n in notes) or "  (no overlapping pins to reuse)")
PY
    if grep -q '^torch==' "$REPO_ROOT/outputs/reuse_freeze.txt"; then
        TORCH_SPEC="$(grep -m1 '^torch==' "$REPO_ROOT/outputs/reuse_freeze.txt")"
        echo "  reused: $TORCH_SPEC (data-selection project)"
    fi
else
    cp "$REQS" "$RESOLVED"
fi

step "Installing torch from the CUDA 12.1 index: $TORCH_SPEC"
python -m pip install --quiet --index-url "$TORCH_INDEX" "$TORCH_SPEC"

# One resolver pass over BOTH files: installing them separately lets pip quietly upgrade a
# Step 1 pin (a reused transformers is newer than ours and wants a newer huggingface_hub),
# leaving an environment that no longer matches requirements.txt.
step "Installing requirements.txt + $(basename "$RESOLVED") in a single resolver pass"
if ! python -m pip install --quiet -r "$REPO_ROOT/requirements.txt" -r "$RESOLVED"; then
    # The only real conflict: huggingface_hub==0.33.0 vs the reused transformers==4.57.6,
    # which needs hub >=0.34,<1.0. Move that one pin into transformers' range and keep every
    # other Step 1 pin (datasets 3.6.0, pandas 2.2.3, pyarrow 20.0.0) exactly as tested.
    # (An earlier version relaxed four pins and then ran an UNPINNED install of all four,
    # which pulled pandas 3.x, pyarrow 25 and datasets 5 — never tested with this code.)
    echo "  pins conflict; moving huggingface_hub into transformers' range, all other pins kept" \
        | tee -a "$PINS_FILE"
    grep -vE '^huggingface_hub==' "$REPO_ROOT/requirements.txt" \
        > "$REPO_ROOT/outputs/requirements-step1.relaxed.txt"
    python -m pip install --quiet -r "$REPO_ROOT/outputs/requirements-step1.relaxed.txt" -r "$RESOLVED" \
        "huggingface_hub>=0.34,<1.0"
fi

# Fail loudly if the tested library versions did not survive resolution, rather than
# discovering a pandas major-version change three stages later.
python - <<'PY'
import datasets, pandas, pyarrow, huggingface_hub
want = {"datasets": ("3.6.0", datasets.__version__), "pandas": ("2.2.3", pandas.__version__),
        "pyarrow": ("20.0.0", pyarrow.__version__)}
bad = {k: v for k, v in want.items() if v[0] != v[1]}
print(f"  resolved: datasets {datasets.__version__}, pandas {pandas.__version__}, "
      f"pyarrow {pyarrow.__version__}, huggingface_hub {huggingface_hub.__version__}")
if bad:
    raise SystemExit("  ERROR: tested pins not honoured: "
                     + ", ".join(f"{k} want {w} got {g}" for k, (w, g) in bad.items()))
PY

step "Probing: versions, a real matmul on every GPU, GlotLID, LaBSE, pysbd"
PROBE_RC=0
python -m src.utils.env_probe || PROBE_RC=$?

step "Recording the installed environment"
{
    echo "# .venv311 as installed, $(date -Iseconds)"
    python -c 'import platform,sys;print(f"python {platform.python_version()} ({sys.executable})")'
    python -m pip freeze | grep -iE '^(torch|transformers|accelerate|sentencepiece|protobuf|pysbd|sentence-transformers|fasttext[a-z-]*|numpy|datasets|pandas|pyarrow|huggingface)' || true
} >> results/step2/env_pins.txt

echo
echo "================ 04_setup_gpu_env: SUMMARY ================"
echo "probe exit code: $PROBE_RC (0 = gpu+glotlid+labse+pysbd all usable)"
sed -n '/## Verdict/,$p' results/step2/env_probe.md | grep '^- ' || true
echo "venv: .venv311 ($(python -c 'import platform;print(platform.python_version())'))"
echo "pins: results/step2/env_pins.txt   probe: results/step2/env_probe.md"
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "next: bash scripts/server/05_clean_pools.sh"
echo "==========================================================="
exit $PROBE_RC
