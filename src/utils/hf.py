"""Hub download helpers.

The link from this server to huggingface.co is slow and occasionally drops a transfer
mid-stream ("error decoding response body", seen while fetching GlotLID's 1.7 GB model).
Every download goes through `download_with_retry`, which retries and, on the last attempt,
turns off the Xet transfer backend, which is where that error comes from.
"""

from __future__ import annotations

import os
import time
from typing import Callable

RETRIES = 3
BACKOFF_SECONDS = 5


def _attempt(fn: Callable, disable_xet: bool):
    previous = os.environ.get("HF_HUB_DISABLE_XET")
    if disable_xet:
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    try:
        return fn()
    finally:
        if disable_xet:
            if previous is None:
                os.environ.pop("HF_HUB_DISABLE_XET", None)
            else:
                os.environ["HF_HUB_DISABLE_XET"] = previous


def download_with_retry(repo_id: str, filename: str | None = None, *, repo_type: str = "model",
                        retries: int = RETRIES, **kwargs) -> str:
    """hf_hub_download (one file) or snapshot_download (whole repo) with retries."""
    from huggingface_hub import hf_hub_download, snapshot_download

    def once():
        if filename is None:
            return snapshot_download(repo_id=repo_id, repo_type=repo_type, **kwargs)
        return hf_hub_download(repo_id=repo_id, filename=filename, repo_type=repo_type, **kwargs)

    last = None
    for attempt in range(1, retries + 1):
        disable_xet = attempt == retries  # last try without Xet
        try:
            t0 = time.time()
            path = _attempt(once, disable_xet)
            if attempt > 1:
                print(f"    downloaded {repo_id}{'/' + filename if filename else ''} on attempt "
                      f"{attempt}{' (Xet disabled)' if disable_xet else ''} in {time.time() - t0:.0f}s",
                      flush=True)
            return path
        except Exception as e:  # noqa: BLE001 — network failures are expected here
            last = e
            print(f"    download attempt {attempt}/{retries} for {repo_id} failed: "
                  f"{type(e).__name__}: {str(e)[:120]}", flush=True)
            if attempt < retries:
                time.sleep(BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"could not download {repo_id}{'/' + filename if filename else ''} "
                       f"after {retries} attempts") from last
