"""Trial-grouped synthetic benchmark. Never load untrusted model files."""
import json
import os
import shutil
import threading
import uuid

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from . import analog, dsp, simulation
from .schemas import SimulationConfig
from .artifacts import output_root

LABELS = sorted(["Rest", "Grip", "Wrist flexion", "Wrist extension", "Forearm rotation"])
EMG = list(dsp.features(np.zeros(800), 4000))
IMU = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z", "pitch", "roll"]
MODALITIES = {"EMG": EMG, "IMU": IMU, "Fusion": EMG + IMU}
MODEL_NAMES = ["Logistic Regression", "SVM", "Decision Tree", "Random Forest", "Gradient Boosting"]
LOCK = threading.Lock()
MODELS = {}
METRICS = None


def trial_features(result):
    fs = result["config"]["sample_rate_hz"]
    x = np.asarray(result["emg"]["input_referred_v"])
    imu = result["imu"]
    acceleration = np.asarray(imu["acceleration_m_s2"])
    gyro = np.asarray(imu["angular_velocity_deg_s"])
    rows = []
    for i in range(0, len(x)-round(fs*0.2)+1, round(fs*0.1)):
        begin = round(i/fs*200)
        end = begin + 40
        row = dsp.features(x[i:i+round(fs*0.2)], fs)
        for axis, name in enumerate(["x", "y", "z"]):
            row[f"acc_{name}"] = float(np.mean(acceleration[begin:end, axis]))
            row[f"gyro_{name}"] = float(np.sqrt(np.mean(gyro[begin:end, axis]**2)))
        row["pitch"] = float(np.mean(imu["pitch_deg"][begin:end]))
        row["roll"] = float(np.mean(imu["roll_deg"][begin:end]))
        row["window_start_s"] = i/fs
        rows.append(row)
    return rows


def feature_trial(c):
    _, _, raw = simulation.emg(c)
    chain = analog.condition(raw, c)
    referred = (chain["adc_v"]-analog.VREF)/(analog.INA_GAIN*c.post_gain)
    return {"config": c.model_dump(), "emg": {"input_referred_v": referred, "clipped_samples": chain["clipped_samples"]}, "imu": simulation.imu(c)}


def dataset(seed=1000, trials_per_class=6):
    rng = np.random.default_rng(seed)
    rows = []
    for label in LABELS:
        for trial in range(trials_per_class):
            trial_seed = int(rng.integers(0, 2**31))
            c = SimulationConfig(seed=trial_seed, gesture=label, intensity=float(rng.uniform(0.3, 1)), noise_mv=float(rng.uniform(0.02, 0.15)), mains_mv=float(rng.uniform(0, 0.5)))
            result = feature_trial(c)
            for row in trial_features(result):
                rows.append({**row, "trial_id": f"{label}-{trial}", "label": label, "seed": trial_seed, "sample_rate_hz": 4000, "duration_s": 2, "noise_mv": c.noise_mv, "mains_mv": c.mains_mv, "source": "synthetic", "clipped_samples": result["emg"]["clipped_samples"]})
    return pd.DataFrame(rows)


def grouped_splits(y, groups, seed, folds=3):
    splits = list(StratifiedGroupKFold(folds, shuffle=True, random_state=seed).split(np.zeros(len(y)), y, groups))
    for train, test in splits:
        assert set(groups[train]).isdisjoint(groups[test]), "Trial leakage"
    return splits


def estimator(name, seed, y, groups):
    if name == "SVM":
        return CalibratedClassifierCV(make_pipeline(StandardScaler(), SVC(random_state=seed)), cv=grouped_splits(y, groups, seed, 2))
    if name == "Logistic Regression":
        model = LogisticRegression(max_iter=1500, random_state=seed)
    elif name == "Decision Tree":
        model = DecisionTreeClassifier(max_depth=6, random_state=seed)
    elif name == "Random Forest":
        model = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=seed, n_jobs=1)
    else:
        model = GradientBoostingClassifier(n_estimators=40, max_depth=2, random_state=seed)
    return make_pipeline(StandardScaler(), model)


def metrics(y, probabilities, groups, seed):
    prediction = np.asarray(LABELS)[np.argmax(probabilities, axis=1)]
    p, r, f, _ = precision_recall_fscore_support(y, prediction, average="macro", zero_division=0)
    truth = np.asarray(y)[:, None] == np.asarray(LABELS)[None, :]
    # Cluster bootstrap: resample trials, never individual overlapping windows.
    unique = np.unique(groups)
    trial_correct = np.array([np.mean(prediction[groups == group] == y[groups == group]) for group in unique])
    rng = np.random.default_rng(seed)
    draws = rng.choice(trial_correct, size=(500, len(unique)), replace=True).mean(axis=1)
    return {"accuracy": float(accuracy_score(y, prediction)), "balanced_accuracy": float(balanced_accuracy_score(y, prediction)), "precision_macro": float(p), "recall_macro": float(r), "f1_macro": float(f), "brier_multiclass": float(np.mean(np.sum((probabilities-truth)**2, axis=1))), "confusion_matrix": confusion_matrix(y, prediction, labels=LABELS).tolist(), "accuracy_ci95_trial_bootstrap": np.quantile(draws, [0.025, 0.975]).tolist()}


def train(seed=1000, trials_per_class=6):
    global METRICS, MODELS
    frame = dataset(seed, trials_per_class)
    y, groups = frame.label.to_numpy(), frame.trial_id.to_numpy()
    starts = frame.window_start_s.to_numpy()
    splits = grouped_splits(y, groups, seed)
    records, fitted, predictions = [], {}, []
    fold_membership = [{"train_trials": sorted(set(groups[a])), "test_trials": sorted(set(groups[b]))} for a, b in splits]
    for modality, columns in MODALITIES.items():
        x = frame[columns].to_numpy()
        for name in MODEL_NAMES:
            probabilities = np.zeros((len(y), len(LABELS)))
            for train_indices, test_indices in splits:
                model = estimator(name, seed, y[train_indices], groups[train_indices])
                model.fit(x[train_indices], y[train_indices])
                assert list(model.classes_) == LABELS
                probabilities[test_indices] = model.predict_proba(x[test_indices])
            records.append({"model": name, "modality": modality, **metrics(y, probabilities, groups, seed)})
            for i in range(len(y)):
                predictions.append({"model": name, "modality": modality, "trial_id": groups[i], "label": y[i], "window_start_s": float(starts[i]), **{f"p_{label}": float(probabilities[i, j]) for j, label in enumerate(LABELS)}})
            if modality == "Fusion":
                model = estimator(name, seed, y, groups)
                model.fit(x, y)
                fitted[name] = model
    report = {"source": "synthetic-data benchmark; no human validation", "seed": seed, "trials": len(np.unique(groups)), "windows": len(frame), "labels": LABELS, "features": MODALITIES, "cv": "3-fold stratified trial-grouped; SVM uses nested grouped calibration", "folds": fold_membership, "records": records, "limitations": "Scores evaluate programmed scenarios only. CIs use 500 trial bootstrap resamples of OOF accuracy, not model refits; no independent model-selection holdout."}
    save_run(frame, predictions, fitted, report)
    MODELS, METRICS = fitted, report
    return report


def save_run(frame, predictions, fitted, report):
    base = output_root() / "results/ml"
    directory = base / "runs" / f"run-{uuid.uuid4().hex}"
    directory.mkdir(parents=True)
    pointer = base / f".{directory.name}.json"
    try:
        frame.to_csv(directory / "gesture-windows.csv", index=False)
        pd.DataFrame(predictions).to_csv(directory / "out-of-fold-predictions.csv", index=False)
        joblib.dump({"models": fitted, "columns": MODALITIES["Fusion"], "labels": LABELS, "seed": report["seed"]}, directory / "fusion-models.joblib")
        (directory / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        pointer.write_text(json.dumps({"run": directory.name}), encoding="utf-8")
        os.replace(pointer, base / "current.json")
    except Exception:
        pointer.unlink(missing_ok=True)
        shutil.rmtree(directory)
        raise


def predict(result, name):
    rows = trial_features(result)
    x = pd.DataFrame(rows)[MODALITIES["Fusion"]].to_numpy()
    probabilities = MODELS[name].predict_proba(x).mean(axis=0)
    return {"source": "synthetic model inference; not validated on human gestures", "scenario": result["config"]["gesture"], "seed": result["config"]["seed"], "model": name, "predicted_gesture": LABELS[int(np.argmax(probabilities))], "class_probabilities": dict(zip(LABELS, probabilities.tolist())), "aggregation": "mean window probabilities", "windows": len(rows), "domain_warning": "Expanded motion scenarios/scales are outside the Gesture/scale=1 training distribution." if result["config"].get("motion_scenario", "Gesture") != "Gesture" or result["config"].get("motion_scale", 1) != 1 else None}
