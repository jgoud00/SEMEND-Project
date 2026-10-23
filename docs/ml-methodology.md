# Synthetic gesture methodology

## Revised report scope

These are educational synthetic gesture benchmarks retained under the revised report. They are not live grip-quality, force or health predictors. Session recording and real-data evaluation are planned. New-person claims require participant holdouts; session grouping alone is insufficient. Operator triggers and generated optical values are not clinical labels or predictors.

See [report alignment](report-alignment.md) for status and hardware boundaries.

`backend/app/ml.py` generates independent trials for Rest, Grip, Wrist flexion, Wrist extension and Forearm rotation. Default seed 1000 generates 6 trials/class (30 total) of 2 seconds at 4 kHz; there are 19 windows/trial (570 total), each 200 ms with 50% overlap. Intensity, noise and mains vary by trial using a seeded RNG. Trial IDs, sample rates, seeds, labels, noise, interference, duration, clipping metadata and window start times are saved with features.

Seven EMG features are aligned with eight IMU features: mean X/Y/Z acceleration, RMS X/Y/Z angular velocity, mean pitch and mean roll. EMG-only, IMU-only and fusion comparisons use the same held-out trials. The non-rest EMG scenarios deliberately share statistical distributions; no perfect EMG separation is manufactured. IMU rotation trajectories are programmed differently, so high IMU/fusion scores do not establish human generalization.

## Models and splits

Logistic Regression, SVM, Decision Tree, Random Forest and Gradient Boosting use fixed random states. StandardScaler is fitted within each training pipeline. Outer evaluation uses three-fold StratifiedGroupKFold with trial IDs as groups. Every split asserts disjoint trial sets. All windows are held out exactly once. SVM probability calibration uses a second, two-fold group-respecting split inside the outer training data, with scaling inside those calibration folds. Other classifiers use native probabilities; a Brier score quantifies them but does not certify calibration.

Final fusion models are fitted to all generated trials after evaluation for demonstration inference. Predictions average window probabilities over a fresh generated trial. Models are saved as local joblib artifacts, but the server never automatically loads them or accepts uploaded pickle files. Train in the current server process before predicting. CLI artifact generation does not hydrate a separate running server.

## Metrics and artifacts

All reported metrics use outer out-of-fold predictions: accuracy, balanced accuracy, macro precision/recall/F1, class-ordered confusion matrices and multiclass Brier score. The Brier convention is mean(sum over classes((probability minus one-hot truth) squared)), range 0–2. Class order is sorted and stored in the report. Confusion counts are windows, not independent subjects or trials.

Accuracy intervals use 500 bootstrap resamples of independent trial accuracies, not overlapping windows. Trials have equal window counts. These intervals quantify variability conditional on fixed fits and omit retraining variability. Other metrics do not currently have confidence intervals.

Each new training run saves `metrics.json`, `out-of-fold-predictions.csv`, `gesture-windows.csv` and `fusion-models.joblib` together under `results/ml/runs/run-<id>/`. Only after every write succeeds does an atomic replacement of `results/ml/current.json` publish the run. Failed saves leave the previous pointer and in-memory models intact; previous runs are retained. An interruption before publication may leave an unpublished run directory. Legacy `results/ml/metrics.json` and `datasets/synthetic/gesture-windows.csv` are preserved. The report writer follows the pointer, falling back to the legacy metrics when no pointer exists. Python dependency versions are locked in `backend/requirements-lock.txt`.

Run `scripts/train.py`, then `scripts/ml_report.py` to generate comparison/confusion plots and a Markdown report alongside the selected run's metrics. Plot and dashboard provenance comes from that report's seed and trial count. The browser uses the same training path via `/api/ml/train`, model selection, prediction probabilities and metrics. It does not show prefilled scores.

## Limits

Expanded Stationary/Repetitive/Tremor/Sudden motion scenarios and non-default motion scales are outside the original Gesture/scale=1 training distribution. Inference returns and displays a domain warning for them. The current benchmark is not relabeled as a benchmark of these new scenarios; no new class-level performance is fabricated.

All results are **synthetic-data benchmarks**. Selecting a model by comparing the same folds is optimistic; use independent held-out trials or nested model selection before making claims about a selected model. Current generators share fixed programmed motion trajectories and omit subject anatomy, electrode placement, session drift and sensor calibration. There is no human dataset, subject/session separation or clinical validation. A correct software pipeline is not evidence of a correct wearable classifier.
