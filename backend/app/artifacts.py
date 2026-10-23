"""Artifact location shared by the API and offline report writer."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def output_root():
    return Path(os.environ.get("FOREARMSENSE_OUTPUT_ROOT", ROOT)).resolve()


def current_ml_run():
    directory = output_root() / "results/ml"
    pointer = directory / "current.json"
    if not pointer.exists():
        return directory  # Legacy experiments remain readable and untouched.
    name = json.loads(pointer.read_text(encoding="utf-8"))["run"]
    if not isinstance(name, str) or not name.startswith("run-") or Path(name).name != name:
        raise ValueError("Invalid ML run pointer")
    return directory / "runs" / name
