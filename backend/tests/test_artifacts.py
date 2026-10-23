import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from app import ml
from app.artifacts import current_ml_run, output_root


@pytest.mark.parametrize("failure", ["model", "publish"])
def test_failed_save_preserves_complete_previous_run(monkeypatch, failure):
    frame = pd.DataFrame({"seed": [7]})
    base = output_root() / "results/ml"
    base.mkdir(parents=True)
    legacy = base / "metrics.json"
    legacy.write_text('{"seed": 1}', encoding="utf-8")
    assert current_ml_run() == base
    ml.save_run(frame, [{"p": 1}], {}, {"seed": 7})
    previous = current_ml_run()
    snapshot = {p.name: p.read_bytes() for p in previous.iterdir()}
    pointer = (base / "current.json").read_bytes()

    def fail(*args, **kwargs):
        raise OSError("injected write failure")

    if failure == "model":
        monkeypatch.setattr(ml.joblib, "dump", fail)
    else:
        monkeypatch.setattr(ml.os, "replace", fail)
    with pytest.raises(OSError, match="injected"):
        ml.save_run(pd.DataFrame({"seed": [8]}), [], {}, {"seed": 8})
    assert current_ml_run() == previous
    assert (base / "current.json").read_bytes() == pointer
    assert {p.name: p.read_bytes() for p in previous.iterdir()} == snapshot
    assert list((base / "runs").iterdir()) == [previous]
    assert legacy.read_text(encoding="utf-8") == '{"seed": 1}'


def test_report_uses_saved_provenance(monkeypatch):
    spec = importlib.util.spec_from_file_location("ml_report", Path(__file__).resolve().parents[2] / "scripts/ml_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    directory = current_ml_run()
    directory.mkdir(parents=True)
    records = [{"model": name, "modality": modality, "accuracy": 1, "balanced_accuracy": 1,
                "f1_macro": 1, "brier_multiclass": 0, "confusion_matrix": [[1]*5]*5}
               for name in ml.MODEL_NAMES for modality in ml.MODALITIES]
    report = {"seed": 7, "trials": 60, "windows": 1140, "folds": [{}, {}, {}],
              "records": records, "labels": ml.LABELS, "cv": "grouped", "limitations": "synthetic"}
    (directory / "metrics.json").write_text(json.dumps(report), encoding="utf-8")
    titles = []
    original = module.plt.Figure.savefig

    def capture(fig, *args, **kwargs):
        titles.extend(ax.get_title() for ax in fig.axes)
        return original(fig, *args, **kwargs)

    monkeypatch.setattr(module.plt.Figure, "savefig", capture)
    module.main()
    assert "SYNTHETIC benchmark — 60 trials, 3 grouped folds, seed 7" in titles
    assert "Seed 7 · 60 trials" in (directory / "benchmark-report.md").read_text(encoding="utf-8")
    assert (directory / "model-comparison.png").is_file()
