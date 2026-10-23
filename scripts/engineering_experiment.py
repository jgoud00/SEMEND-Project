"""Generate scenario, noise, tolerance and actual SPICE evidence from project code."""
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app import analog, simulation, spice  # noqa: E402
from app.schemas import SimulationConfig  # noqa: E402


def main():
    target = ROOT / "results/engineering"
    figures = ROOT / "results/figures"
    target.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    motions, pulses = {}, {}
    fig, axes = plt.subplots(5, 1, figsize=(12, 10), layout="constrained")
    imu_rows = []
    for ax, scenario in zip(axes, ["Gesture", "Stationary", "Repetitive", "Tremor", "Sudden motion"]):
        c = SimulationConfig(duration_s=5, motion_scenario=scenario)
        p = simulation.imu(c)
        motions[scenario] = {"config": c.model_dump(), "result": p}
        ax.plot(p["time_s"], np.array(p["angular_velocity_deg_s"])[:, 1], lw=0.8)
        ax.set(ylabel="Y gyro / °/s", title=scenario)
        for i, t in enumerate(p["time_s"]):
            imu_rows.append([scenario, t, *p["acceleration_m_s2"][i], *p["angular_velocity_deg_s"][i], p["pitch_deg"][i], p["roll_deg"][i]])
    axes[-1].set_xlabel("Time / s")
    fig.suptitle("SYNTHETIC motion scenarios — seed 42, not diagnostic measurements")
    fig.savefig(figures / "motion-scenarios.png", dpi=160)
    plt.close(fig)
    with (target / "motion-scenarios.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "time_s", "ax_m_s2", "ay_m_s2", "az_m_s2", "gx_deg_s", "gy_deg_s", "gz_deg_s", "pitch_deg", "roll_deg"])
        w.writerows(imu_rows)
    fig, axes = plt.subplots(4, 1, figsize=(12, 9), layout="constrained")
    ppg_rows = []
    for ax, scenario in zip(axes, ["Clean", "Motion artifact", "Low perfusion", "Dropout"]):
        c = SimulationConfig(duration_s=10, ppg_scenario=scenario, ppg_motion_au=1, heart_rate_bpm=90)
        p = simulation.ppg(c)
        pulses[scenario] = {"config": c.model_dump(), "result": p}
        ax.plot(p["time_s"], p["amplitude_au"], lw=0.8)
        peaks = p["peak_indices"]
        ax.scatter(np.array(p["time_s"])[peaks], np.array(p["amplitude_au"])[peaks], s=8, color="tab:orange")
        ax.set(ylabel="Pulse / a.u.", title=f"{scenario} | HR: {p['estimated_bpm'] if p['estimated_bpm'] is not None else 'withheld'} | {p['quality']}")
        for i, t in enumerate(p["time_s"]):
            ppg_rows.append([scenario, t, p["amplitude_au"][i], i in peaks, p["dropout_mask"][i]])
    axes[-1].set_xlabel("Time / s")
    fig.suptitle("SYNTHETIC PPG quality scenarios — injected-component oracle, no clinical SQI")
    fig.savefig(figures / "ppg-scenarios.png", dpi=160)
    plt.close(fig)
    with (target / "ppg-scenarios.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "time_s", "amplitude_au", "detected_peak", "dropout"])
        w.writerows(ppg_rows)
    (target / "scenarios.json").write_text(json.dumps({"source": "synthetic", "motions": motions, "pulses": pulses}, indent=2), encoding="utf-8")
    c = SimulationConfig()
    analysis = analog.analyze(c)
    (target / "analog.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    budget = analysis["noise_budget"]
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    parts = budget["contributions"]
    ax.barh([v["source"] for v in parts], [v["output_rms_v"]*1e6 for v in parts])
    ax.set(xlabel="Output RMS noise / µV (20–450 Hz)", title="Analytical white-noise contributions — quadrature sum, not waveform noise")
    fig.savefig(figures / "noise-budget.png", dpi=160)
    plt.close(fig)
    tol = analysis["tolerances"]
    f = np.array(tol["frequency_hz"])
    nominal = analog.response(c.model_copy(update={"notch": False}), f)*analysis["total_gain"]
    fig, ax = plt.subplots(figsize=(12, 5), layout="constrained")
    ax.fill_between(f, tol["magnitude_p05_db"], tol["magnitude_p95_db"], alpha=0.3, label="5th–95th percentile, 200 seeded component draws")
    ax.semilogx(f, 20*np.log10(np.abs(nominal)), label="Nominal")
    ax.set(xlabel="Frequency / Hz", ylabel="Gain / dB", title="Candidate Sallen-Key R ±1%, C ±5% — ideal buffers; notch omitted")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.savefig(figures / "component-tolerances.png", dpi=160)
    plt.close(fig)
    report = spice.run(c)
    if report.get("checks", {}).get("ideal", {}).get("status") == "passed":
        ac = np.loadtxt(ROOT / "results/spice/ideal-ac.txt", skiprows=1)
        transient = np.loadtxt(ROOT / "results/spice/ideal-transient.txt", skiprows=1)
        fig, axes = plt.subplots(2, 1, figsize=(12, 7), layout="constrained")
        axes[0].semilogx(ac[:, 0], 20*np.log10(np.hypot(ac[:, 1], ac[:, 2])))
        axes[0].set(xlabel="Frequency / Hz", ylabel="Gain / dB", title="Actual ngspice ideal-buffer circuit AC result (no notch)")
        axes[1].plot(transient[:, 0], transient[:, 2])
        axes[1].set(xlabel="Time / s", ylabel="Output / V", title="Actual ngspice transient for a 1 mV, 50 ms input pulse")
        fig.savefig(figures / "spice-verification.png", dpi=160)
        plt.close(fig)
    summary = {"noise_output_rms_uv": budget["output_rms_v"]*1e6, "noise_nominal_gain_referred_rms_uv": budget["nominal_gain_referred_rms_v"]*1e6, "tolerance_gain_min_max": tol["total_gain_min_max"], "tremor_estimated_hz": motions["Tremor"]["result"]["estimated_tremor_hz"], "ppg_hr_bpm": {name: p["result"]["estimated_bpm"] for name, p in pulses.items()}, "spice": report}
    (target / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
