"""Small I/O helpers.

Anything written under results/ is committed and travels SERVER -> GitHub -> LOCAL,
so writes there go through `write_result`, which warns when a file exceeds the
~1 MB budget.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
SCHEMA_DIR = RESULTS_DIR / "schema"
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUTS_DIR = REPO_ROOT / "outputs"
LOGS_DIR = REPO_ROOT / "logs"
CONFIGS_DIR = REPO_ROOT / "configs"

RESULT_SIZE_BUDGET = 1_000_000  # bytes


def num_proc() -> int:
    """CPU worker cap. The server's CPUs are shared: never assume more than this.

    Set via CU_NUM_PROC (scripts/server/_common.sh defaults it to 4).
    """
    return max(1, int(os.environ.get("CU_NUM_PROC", "4")))


def ensure_dirs() -> None:
    for d in (RESULTS_DIR, DATA_DIR, OUTPUTS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def read_yaml(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_yaml(obj: Any, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)
    return path


def read_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(obj: Any, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def write_result(obj: Any, name: str) -> Path:
    """Write a small committed output to results/<name>.

    Format is chosen by extension: .json, .yaml/.yml, .csv (pandas DataFrame),
    or .md/.txt (str).
    """
    path = RESULTS_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".json":
        write_json(obj, path)
    elif suffix in (".yaml", ".yml"):
        write_yaml(obj, path)
    elif suffix == ".csv":
        obj.to_csv(path, index=False)
    elif suffix in (".md", ".txt"):
        path.write_text(obj, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported results extension: {suffix}")

    size = path.stat().st_size
    if size > RESULT_SIZE_BUDGET:
        print(
            f"WARNING: {path.relative_to(REPO_ROOT)} is {size / 1e6:.2f} MB "
            f"(> {RESULT_SIZE_BUDGET / 1e6:.0f} MB budget for results/). "
            "Consider writing the full version to data/ or outputs/ instead.",
            file=sys.stderr,
        )
    return path
