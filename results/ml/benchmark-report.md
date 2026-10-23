# Synthetic gesture benchmark

Seed 1000 · 30 trials · 570 windows. No human validation.

| Model | Modality | Accuracy | Balanced accuracy | Macro-F1 | Brier |
| --- | --- | --- | --- | --- | --- |
| Logistic Regression | EMG | 0.3561 | 0.3561 | 0.3364 | 0.6664 |
| SVM | EMG | 0.4000 | 0.4000 | 0.3644 | 0.6921 |
| Decision Tree | EMG | 0.3140 | 0.3140 | 0.3241 | 0.8161 |
| Random Forest | EMG | 0.3509 | 0.3509 | 0.3532 | 0.6999 |
| Gradient Boosting | EMG | 0.3649 | 0.3649 | 0.3641 | 0.6982 |
| Logistic Regression | IMU | 0.7982 | 0.7982 | 0.7982 | 0.3187 |
| SVM | IMU | 0.7175 | 0.7175 | 0.7175 | 0.3871 |
| Decision Tree | IMU | 0.8825 | 0.8825 | 0.8808 | 0.1517 |
| Random Forest | IMU | 0.9895 | 0.9895 | 0.9895 | 0.0675 |
| Gradient Boosting | IMU | 0.9895 | 0.9895 | 0.9895 | 0.0552 |
| Logistic Regression | Fusion | 0.8211 | 0.8211 | 0.8210 | 0.2314 |
| SVM | Fusion | 0.8070 | 0.8070 | 0.8053 | 0.2641 |
| Decision Tree | Fusion | 0.8772 | 0.8772 | 0.8710 | 0.1487 |
| Random Forest | Fusion | 0.9053 | 0.9053 | 0.9050 | 0.1579 |
| Gradient Boosting | Fusion | 0.9877 | 0.9877 | 0.9877 | 0.0621 |

3-fold stratified trial-grouped; SVM uses nested grouped calibration

Scores evaluate programmed scenarios only. CIs use 500 trial bootstrap resamples of OOF accuracy, not model refits; no independent model-selection holdout.

Full precision/recall, trial-bootstrap CIs, class order, fold membership and confusion matrices are in metrics.json. Per-window held-out probabilities are in out-of-fold-predictions.csv.
