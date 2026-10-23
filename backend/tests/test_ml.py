import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import analog, dsp, ml, simulation
from app.artifacts import current_ml_run
from app.main import app, run
from app.schemas import SimulationConfig

client = TestClient(app)


@pytest.mark.parametrize("settings", [{}, {"sample_rate_hz": 2000, "duration_s": 1, "notch": False},
                                      {"sample_rate_hz": 8000, "seed": 7, "motion_scenario": "Tremor", "offset_mv": 50}])
def test_feature_trial_matches_full_analysis(settings):
    c = SimulationConfig(**settings)
    full, compact = run(c), ml.feature_trial(c)
    assert compact["config"] == full["config"]
    assert compact["emg"]["clipped_samples"] == full["emg"]["clipped_samples"]
    np.testing.assert_array_equal(compact["emg"]["input_referred_v"], full["emg"]["input_referred_v"])
    assert ml.trial_features(compact) == ml.trial_features(full)


def test_prediction_skips_unused_analysis(monkeypatch):
    class Model:
        def predict_proba(self, x):
            return np.full((len(x), len(ml.LABELS)), 1/len(ml.LABELS))

    def unused(*args):
        pytest.fail("Inference must not generate display-only analyses")

    monkeypatch.setattr(ml, "MODELS", {"Random Forest": Model()})
    monkeypatch.setattr(analog, "analyze", unused)
    monkeypatch.setattr(dsp, "analyze", unused)
    monkeypatch.setattr(simulation, "ppg", unused)
    response = client.post("/api/ml/predict", json={})
    assert response.status_code == 200
    assert response.json()["windows"] == 19


def test_grouped_splits_and_known_metrics():
    y = np.repeat(ml.LABELS, 12)
    groups = np.array([f"{label}-{i//3}" for label in ml.LABELS for i in range(12)])
    for a, b in ml.grouped_splits(y, groups, 1000):
        assert set(groups[a]).isdisjoint(groups[b])
    perfect = (y[:, None] == np.array(ml.LABELS)[None, :]).astype(float)
    metrics = ml.metrics(y, perfect, groups, 1000)
    assert metrics["accuracy"] == 1
    assert metrics["f1_macro"] == 1
    assert metrics["brier_multiclass"] == 0
    assert metrics["accuracy_ci95_trial_bootstrap"] == [1, 1]


def test_no_untrained_predictions():
    old_models, old_metrics = ml.MODELS, ml.METRICS
    try:
        ml.MODELS, ml.METRICS = {}, None
        assert client.get("/api/ml/metrics").status_code == 409
        assert client.post("/api/ml/predict", json={}).status_code == 409
    finally:
        ml.MODELS, ml.METRICS = old_models, old_metrics
    assert client.post("/api/ml/train", json={"trials_per_class": 1}).status_code == 422
    assert client.post("/api/ml/predict", json={"model": "unknown"}).status_code == 422


def test_full_training_and_inference():
    response = client.post("/api/ml/train", json={"seed": 1000, "trials_per_class": 6})
    assert response.status_code == 200
    report = response.json()
    assert report["trials"] == 30
    assert report["windows"] == 570
    assert len(report["records"]) == 15
    for fold in report["folds"]:
        assert set(fold["train_trials"]).isdisjoint(fold["test_trials"])
    for metric in report["records"]:
        assert 0 <= metric["accuracy"] <= 1
        assert 0 <= metric["brier_multiclass"] <= 2
        assert np.asarray(metric["confusion_matrix"]).sum() == 570
    result = run(SimulationConfig())
    assert ml.predict(result, "Random Forest")["domain_warning"] is None
    expanded = run(SimulationConfig(motion_scenario="Tremor"))
    assert "outside" in ml.predict(expanded, "Random Forest")["domain_warning"]
    rows = ml.trial_features(result)
    assert len(rows) == 19
    assert len([k for k in rows[0] if k != "window_start_s"]) == 15
    for model in ml.MODEL_NAMES:
        p = ml.predict(result, model)
        assert sum(p["class_probabilities"].values()) == pytest.approx(1)
        assert p["predicted_gesture"] in ml.LABELS
    first = client.post("/api/ml/predict", json={}).json()
    assert first == client.post("/api/ml/predict", json={}).json()
    assert client.get("/api/ml/metrics").json() == report
    frame = pd.read_csv(current_ml_run() / "gesture-windows.csv")
    oof = pd.read_csv(current_ml_run() / "out-of-fold-predictions.csv")
    columns = ["trial_id", "label", "window_start_s"]
    pd.testing.assert_frame_equal(oof[columns], pd.concat([frame[columns]]*15, ignore_index=True))
    a = ml.estimator("Logistic Regression", 1000, frame.label.to_numpy(), frame.trial_id.to_numpy())
    b = ml.estimator("Logistic Regression", 1000, frame.label.to_numpy(), frame.trial_id.to_numpy())
    x = frame[ml.MODALITIES["Fusion"]].to_numpy()
    assert np.array_equal(a.fit(x, frame.label).predict(x), b.fit(x, frame.label).predict(x))
