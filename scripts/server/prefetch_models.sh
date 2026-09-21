#!/usr/bin/env bash
# SERVER: download every model Step 2 needs, with retries, into data/hf_cache.
#
# The hub link here runs at roughly 0.5 MB/s, and the four models total ~17.7 GB:
#   google/madlad400-3b-mt            11.8 GB (fp32 only; no bf16 release exists)
#   facebook/nllb-200-distilled-600M   2.4 GB
#   sentence-transformers/LaBSE        1.8 GB
#   cis-lmu/glotlid                    1.7 GB
# So this is the long pole. run_step2_bundle.sh starts it in the background after the
# environment is built, so it overlaps with the CPU stages.
#
# Safe to run twice: anything already cached is skipped, and a partial file resumes.
#
# Usage: nohup bash scripts/server/prefetch_models.sh > logs/prefetch_models.out 2>&1 &
source "$(dirname "$0")/_common.sh"
activate_venv
start_log

step "Prefetching Step 2 models into data/hf_cache (HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-0})"
python - <<'PY'
import time
from src.utils.hf import download_with_retry

JOBS = [
    ("cis-lmu/glotlid", "model.bin", None),
    ("sentence-transformers/LaBSE", None, ["*.json", "*.txt", "*.bin", "*.safetensors", "*.model", "1_Pooling/*"]),
    ("facebook/nllb-200-distilled-600M", None, ["*.json", "*.model", "*.bin", "*.safetensors"]),
    ("google/madlad400-3b-mt", None, ["*.json", "*.model", "*.safetensors"]),
]
for repo, filename, patterns in JOBS:
    t0 = time.time()
    print(f"==> {repo}", flush=True)
    kwargs = {"allow_patterns": patterns} if patterns else {}
    path = download_with_retry(repo, filename, **kwargs)
    print(f"    done in {time.time() - t0:.0f}s -> {path}", flush=True)
PY

echo
echo "================ prefetch_models: SUMMARY ================"
du -sh data/hf_cache 2>/dev/null || true
echo "log:  ${LOG_FILE#$REPO_ROOT/}"
echo "=========================================================="
