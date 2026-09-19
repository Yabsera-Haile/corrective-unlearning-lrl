# corrective-unlearning-lrl

Corrective unlearning of machine-translation-contaminated low-resource-language data.

## Two-machine workflow (read this first)

| Machine | Hardware | Access | Used for |
|---|---|---|---|
| **LOCAL** | Windows/Linux PC, RTX 2070 (4 GB) | Direct; has Claude Code | Writing code, light CPU work, inspecting small results |
| **SERVER** | 3× RTX A5000 (24 GB), driver 535.309.01, CUDA 12.2, open internet incl. HuggingFace | **AnyDesk only.** No SSH, no scp/rsync, no remote file copy | Downloads, profiling, training, evaluation |

**The only channel between the machines is git (GitHub):**

```
code:     LOCAL  --git push-->  GitHub  --git pull-->  SERVER
results:  SERVER --git push-->  GitHub  --git pull-->  LOCAL
```

Rules that follow from this:

- Never write a step or script that assumes SSH, `rsync`, `scp`, or a shared filesystem.
- Anything that must come back to LOCAL is written to **`results/`** and committed from the SERVER.
  Keep each file there small (target **< 1 MB**): CSV, JSON, YAML, Markdown tables.
  `src/utils/io.py::write_result` warns when a file exceeds this.
- Large artifacts (raw datasets, HF cache, checkpoints, generations, logs) stay on the machine
  that produced them, in the gitignored `data/`, `outputs/`, `logs/`. They never go through git.
- Server-side console output returns by copy-paste from the AnyDesk window, so every server
  script ends with a summary that fits on one terminal screen.

Every step in the project spec is labelled **LOCAL** or **SERVER**.

## Layout

```
configs/languages.yaml     selected languages (populated at end of Step 1)
src/data/                  dataset inspection, profiling, language-code normalisation
src/utils/io.py            paths + read/write helpers (write_result -> results/)
scripts/server/            bash scripts run on SERVER from the AnyDesk terminal
results/                   SMALL committed outputs — the SERVER -> LOCAL return channel
data/ outputs/ logs/       gitignored; created by 00_setup_env.sh
```

## Server scripts convention

Every `scripts/server/NN_name.sh`:

1. Is run from the repo root as `bash scripts/server/NN_name.sh`.
2. Sources `scripts/server/_common.sh` (strict mode, `cd` to repo root, `HF_HOME=data/hf_cache`,
   venv activation, log mirroring to `logs/`).
3. Echoes each action (`==> ...`) before doing it.
4. Writes its primary output to `results/`, bulky output to `data/` or `outputs/`.
5. Ends with a short `SUMMARY` block that fits in one terminal screen.

## First-time server setup (SERVER, via AnyDesk)

```bash
git clone https://github.com/<you>/corrective-unlearning-lrl.git
cd corrective-unlearning-lrl
bash scripts/server/00_setup_env.sh          # PYTHON_BIN=python3.11 to pick a specific interpreter
git add results/server_env.txt && git commit -m "server env" && git push
```

For private repos, the server needs a GitHub credential (a fine-grained personal access token
with Contents read/write on this repo is enough).

## Routine loop

```bash
# SERVER
git pull
bash scripts/server/NN_name.sh
git add results/ && git commit -m "results: NN_name" && git push

# LOCAL
git pull            # results/ now has the new outputs
```

## Environment

Step 1 is CPU-only; `requirements.txt` deliberately excludes torch/transformers.
They are added (pinned for CUDA 12.2) when a GPU step needs them.
