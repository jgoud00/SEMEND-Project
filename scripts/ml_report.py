"""Plot already-computed benchmark results, without rerunning training."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.artifacts import current_ml_run  # noqa: E402


def main():
    directory = current_ml_run()
    report = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
    records = report["records"]
    names = list(dict.fromkeys(r["model"] for r in records))
    fig, ax = plt.subplots(figsize=(12, 5), layout="constrained")
    for j, modality in enumerate(["EMG", "IMU", "Fusion"]):
        values = [next(r["f1_macro"] for r in records if r["model"] == name and r["modality"] == modality) for name in names]
        ax.bar(np.arange(len(names)) + (j-1)*0.25, values, width=0.25, label=modality)
    ax.set(xticks=np.arange(len(names)), xticklabels=names, ylim=(0, 1.05), ylabel="Out-of-fold macro-F1", title=f"SYNTHETIC benchmark — {report['trials']} trials, {len(report['folds'])} grouped folds, seed {report['seed']}")
    ax.legend()
    fig.savefig(directory / "model-comparison.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), layout="constrained")
    for ax, name in zip(axes.flat, names):
        record = next(r for r in records if r["model"] == name and r["modality"] == "Fusion")
        matrix = np.array(record["confusion_matrix"])
        ax.imshow(matrix, cmap="Blues")
        ax.set(title=name, xticks=range(5), yticks=range(5), xticklabels=report["labels"], yticklabels=report["labels"], xlabel="Predicted", ylabel="True")
        ax.tick_params(axis="x", labelrotation=40, labelsize=7)
        ax.tick_params(axis="y", labelsize=7)
        for (i, j), value in np.ndenumerate(matrix):
            ax.text(j, i, str(value), ha="center", va="center", color="white" if value > matrix.max()/2 else "black")
    axes.flat[-1].axis("off")
    fig.suptitle("SYNTHETIC fusion confusion matrices — held-out windows grouped by trial")
    fig.savefig(directory / "confusion-matrices.png", dpi=160)
    plt.close(fig)
    lines = ["# Synthetic gesture benchmark", "", f"Seed {report['seed']} · {report['trials']} trials · {report['windows']} windows. No human validation.", "", "| Model | Modality | Accuracy | Balanced accuracy | Macro-F1 | Brier |", "| --- | --- | --- | --- | --- | --- |"]
    for r in records:
        lines.append(f"| {r['model']} | {r['modality']} | {r['accuracy']:.4f} | {r['balanced_accuracy']:.4f} | {r['f1_macro']:.4f} | {r['brier_multiclass']:.4f} |")
    lines += ["", report["cv"], "", report["limitations"], "", "Full precision/recall, trial-bootstrap CIs, class order, fold membership and confusion matrices are in metrics.json. Per-window held-out probabilities are in out-of-fold-predictions.csv."]
    (directory / "benchmark-report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Wrote benchmark figures and report to {directory}")


if __name__ == "__main__":
    main()
