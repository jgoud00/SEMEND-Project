"""Run from the project root with .venv/Scripts/python scripts/experiment.py."""
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import run  # noqa: E402
from app.schemas import SimulationConfig  # noqa: E402


def main():
    result = run(SimulationConfig())
    for directory in ["results/figures", "results/metrics", "datasets/synthetic"]:
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    (ROOT / "results/metrics/trial-seed42.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    emg = result["emg"]
    with (ROOT / "datasets/synthetic/emg-seed42.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        keys = ["time_s", "clean_v", "raw_v", "ina_v", "filtered_v", "adc_input_v", "adc_v", "adc_codes", "input_referred_v"]
        writer.writerow(keys)
        writer.writerows(zip(*(emg[k] for k in keys)))
    for name, keys in [("imu", ["time_s", "pitch_deg", "roll_deg"]), ("ppg", ["time_s", "amplitude_au"])]:
        with (ROOT / f"datasets/synthetic/{name}-seed42.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            writer.writerows(zip(*(result[name][k] for k in keys)))
    fig, axes = plt.subplots(5, 1, figsize=(12, 10), layout="constrained")
    for ax, key, label in zip(axes, ["clean_v", "raw_v", "ina_v", "filtered_v", "adc_v"], ["Clean EMG / V", "Electrode / V", "INA output / V", "Filtered AC / V", "ADC / V"]):
        ax.plot(emg["time_s"], emg[key], lw=0.5)
        ax.set_ylabel(label)
        ax.grid(alpha=0.2)
    axes[-1].set_xlabel("Time / s")
    fig.suptitle("ForearmSense AI — SYNTHETIC analytical trial, seed 42")
    fig.savefig(ROOT / "results/figures/signal-chain.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout="constrained")
    a, d = result["analog"], result["dsp"]
    axes[0, 0].semilogx(a["frequency_hz"], a["magnitude_db"])
    axes[0, 0].set(xlabel="Frequency / Hz", ylabel="Chain magnitude / dB")
    axes[0, 1].semilogx(a["frequency_hz"], a["phase_deg"])
    axes[0, 1].set(xlabel="Frequency / Hz", ylabel="Unwrapped phase / degrees")
    axes[1, 0].plot(d["frequency_hz"], d["amplitude_v"])
    axes[1, 0].set(xlabel="Frequency / Hz", ylabel="FFT amplitude / V", xlim=(0, 700))
    axes[1, 1].semilogy(d["psd_frequency_hz"], np.maximum(d["psd_v2_hz"], 1e-20))
    axes[1, 1].set(xlabel="Frequency / Hz", ylabel="Welch PSD / V²/Hz", xlim=(0, 700))
    for ax in axes.flat:
        ax.grid(alpha=0.2)
    fig.suptitle("SYNTHETIC — continuous-time analog response and sampled DSP")
    fig.savefig(ROOT / "results/figures/frequency-analysis.png", dpi=160)
    plt.close(fig)
    summary = {"source": "synthetic", "seed": 42, "samples": result["provenance"]["samples"], "features": d["features"], "ina_clipped_samples": emg["ina_clipped_samples"], "clipped_samples": emg["clipped_samples"], "lp_checks": a["lp_checks"]}
    (ROOT / "results/metrics/summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
