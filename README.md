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
2. Sources `scripts/server/_common.sh` (strict mode, `cd` to repo root, HF caches under
   `data/hf_cache/`, CPU cap `CU_NUM_PROC` (default 4), venv activation, log mirroring to `logs/`).
3. Echoes each action (`==> ...`) before doing it.
4. Writes its primary output to `results/`, bulky output to `data/` or `outputs/`.
5. Ends with a short `SUMMARY` block that fits in one terminal screen.

## Working rules

- **Write code on LOCAL, run data work on SERVER.** Datasets are never downloaded on LOCAL.
- **Import-test every server module on LOCAL before pushing**, even when it can't run there:
  `python -c "import src.data.<module>"` from the repo root, using the pinned venv
  (LOCAL keeps it outside OneDrive at `~/.venvs/cu-lrl`).
- **Streaming loads and explicit worker caps.** The server's GPUs are dedicated but its CPUs
  are shared; every pool uses `src.utils.io.num_proc()` / `CU_NUM_PROC`.
- **Inspect, don't guess.** When a dataset's structure or language-code format is uncertain,
  inspect it on the server and read the report before writing logic against it.

## Step 1 — language selection (current)

Sources: MURI-IT (`akoksal/muri-it`), NLLB-200 (`facebook/nllb-200-distilled-600M`, codes only),
FLORES-200 (`facebook/flores`, gated), FLORES+ (`openlanguagedata/flores_plus`, gated),
Belebele (`facebook/belebele`), Tülu 3 SFT (`allenai/tulu-3-sft-mixture`, for Step 2).

**One-time:** accept the terms for both FLORES datasets on huggingface.co (any browser, same
account), then on the server run `source .venv/bin/activate && huggingface-cli login`.

```bash
# SERVER — round trip 1: download + schema inspection (1.2)
git pull
bash scripts/server/01_download_data.sh                # ~5.3 GB into data/raw/
bash scripts/server/02_profile_languages.sh --inspect-only
git add results/ && git commit -m "Step 1.2 schema inspection" && git push

# LOCAL — code_maps.py (1.3) and profile_languages.py (1.4) are written against
#         results/schema_inspection.md and results/schema/*

# SERVER — round trip 2: profiling (1.4/1.5)
git pull && bash scripts/server/02_profile_languages.sh
git add results/ && git commit -m "Step 1.4 language profile" && git push
```

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
