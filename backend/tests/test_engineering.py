import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
import numpy as np
import pytest
from scipy import signal

from app import analog, engineering, simulation, spice
from app.main import app
from app.schemas import SimulationConfig

client = TestClient(app)


@pytest.mark.parametrize("settings", [{}, {"seed": 7, "resistor_tolerance_pct": 0, "capacitor_tolerance_pct": 0},
                                      {"seed": 123, "highpass_hz": 100, "lowpass_hz": 700, "post_gain": 100,
                                       "resistor_tolerance_pct": 5, "capacitor_tolerance_pct": 10}])
def test_batched_tolerances_match_scalar_circuit_draws(settings):
    c = SimulationConfig(**settings)
    trials = 17
    result = engineering.tolerances(c, trials)
    rng = np.random.default_rng(c.seed)
    rt, ct = c.resistor_tolerance_pct/100, c.capacitor_tolerance_pct/100
    gains, magnitudes = [], []
    properties = {s["name"]: {"frequency_hz": [], "q": []} for s in engineering.components(c)}
    for _ in range(trials):
        gain = (1+49400/(5490*rng.uniform(1-rt, 1+rt)))*(1+(c.post_gain-1)*rng.uniform(1-rt, 1+rt)/rng.uniform(1-rt, 1+rt))
        gains.append(gain)
        h = np.full(len(result["frequency_hz"]), gain, complex)
        for stage in engineering.components(c):
            for key in ["r1_ohm", "r2_ohm", "c1_f", "c2_f"]:
                spread = rt if key.startswith("r") else ct
                stage[key] *= rng.uniform(1-spread, 1+spread)
            h *= signal.freqs(*engineering.transfer(stage), worN=2*np.pi*np.array(result["frequency_hz"]))[1]
            p = engineering.stage_properties(stage)
            properties[stage["name"]]["frequency_hz"].append(p["natural_frequency_hz"])
            properties[stage["name"]]["q"].append(p["q"])
        magnitudes.append(20*np.log10(np.maximum(np.abs(h), 1e-15)))
    assert result["total_gain_min_max"] == [min(gains), max(gains)]
    for percentile in [5, 95]:
        np.testing.assert_allclose(result[f"magnitude_p{percentile:02d}_db"], np.percentile(magnitudes, percentile, axis=0), rtol=1e-12, atol=1e-12)
    for name, values in properties.items():
        for key, values in values.items():
            assert result["stages"][name][key+"_min_max"] == [min(values), max(values)]


@pytest.mark.parametrize("scenario", ["Stationary", "Repetitive", "Tremor", "Sudden motion"])
def test_motion_scenarios(scenario):
    c = SimulationConfig(duration_s=5, motion_scenario=scenario)
    a = simulation.imu(c)
    assert a == simulation.imu(c)
    assert len(a["time_s"]) == 1000
    assert np.isfinite(a["acceleration_m_s2"]).all()
    assert a["yaw"] is None
    if scenario == "Stationary":
        assert a["gyro_rms_deg_s"] < 1
        assert max(abs(np.array(a["pitch_deg"]))) < 1
    elif scenario == "Tremor":
        assert a["estimated_tremor_hz"] == pytest.approx(6, abs=0.2)
    elif scenario == "Sudden motion":
        assert np.max(np.abs(a["angular_velocity_deg_s"])) > 100
        assert abs(np.array(a["pitch_deg"])[500]-20) > 0.1  # Dynamic acceleration perturbs orientation.
    else:
        assert a["gyro_rms_deg_s"] > 20


@pytest.mark.parametrize("scenario", ["Clean", "Motion artifact", "Low perfusion", "Dropout"])
def test_ppg_quality_gates_and_seed(scenario):
    c = SimulationConfig(duration_s=10, heart_rate_bpm=90, ppg_scenario=scenario, ppg_motion_au=1)
    p = simulation.ppg(c)
    assert p == simulation.ppg(c)
    assert len(p["amplitude_au"]) == 1000
    assert p["spo2"] is None
    assert "synthetic oracle" in p["quality_method"]
    if scenario == "Clean":
        assert p["estimated_bpm"] == pytest.approx(90, abs=2)
    else:
        assert p["estimated_bpm"] is None
    if scenario == "Dropout":
        assert sum(p["dropout_mask"]) == 300
    assert simulation.ppg(SimulationConfig(duration_s=2))["estimated_bpm"] is None


def test_candidate_transfer_noise_and_tolerance():
    c = SimulationConfig(notch=False)
    f = np.geomspace(1, 10000, 500)
    candidate = np.ones(len(f), complex)
    for stage in engineering.components(c):
        candidate *= signal.freqs(*engineering.transfer(stage), worN=2*np.pi*f)[1]
    assert candidate == pytest.approx(analog.response(c, f), rel=1e-10)
    noise = engineering.noise_budget(c)
    gain = (1+49400/5490)*c.post_gain
    assert noise["ina_white_rti_nv_sqrt_hz"] == pytest.approx(np.hypot(18, 110/(1+49400/5490)))
    assert noise["output_rms_v"]**2 == pytest.approx(sum(p["output_rms_v"]**2 for p in noise["contributions"]))
    assert noise["nominal_gain_referred_rms_v"] == pytest.approx(noise["output_rms_v"]/gain)
    assert noise["output_rms_v"] > engineering.noise_budget(c.model_copy(update={"electrode_resistance_ohm": 0}))["output_rms_v"]
    zero = engineering.tolerances(c.model_copy(update={"resistor_tolerance_pct": 0, "capacitor_tolerance_pct": 0}), trials=10)
    assert zero["total_gain_min_max"] == pytest.approx([gain, gain])
    assert zero["magnitude_p05_db"] == pytest.approx(zero["magnitude_p95_db"])
    varied = engineering.tolerances(c, trials=30)
    assert varied == engineering.tolerances(c, trials=30)
    assert varied["stages"]["HP"]["q_min_max"][0] < 1/np.sqrt(2) < varied["stages"]["HP"]["q_min_max"][1]


@pytest.mark.parametrize("body", [{"tremor_hz": 30}, {"motion_scenario": "unknown"}, {"ppg_noise_au": -1}, {"ppg_scenario": "real"}, {"resistor_tolerance_pct": 99}, {"electrode_resistance_ohm": -1}, {"temperature_c": 500}])
def test_engineering_invalid_requests(body):
    assert client.post("/api/simulation/multimodal", json=body).status_code == 422


def test_engineering_api_and_unavailable_solver(monkeypatch):
    response = client.post("/api/analog/analyze", json={})
    assert response.status_code == 200
    assert len(response.json()["components"]) == 3
    monkeypatch.setattr(spice, "solver", lambda: None)
    assert client.post("/api/analog/spice", json={}).json()["status"] == "unavailable"


def test_actual_spice_checks_when_prepared():
    if spice.solver() is None:
        pytest.skip("Run scripts/prepare_spice.py for optional solver integration")
    report = spice.run(SimulationConfig())
    assert report["checks"]["ideal"]["status"] == "passed"
    assert report["checks"]["ideal"]["noise_relative_error"] < 0.01
    if "post_valid" in report["checks"]["devices"]:
        assert report["checks"]["devices"]["post_valid"]
        if not report["checks"]["devices"]["ina_valid"]:
            assert report["status"] == "partial"


def test_vendor_model_preparation_is_narrow():
    spec = importlib.util.spec_from_file_location("prepare_spice", Path(__file__).resolve().parents[2]/"scripts/prepare_spice.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = "* vendor copyright\r\nD1 a b DBE {AREA}\r\n.Model DBE D ( IS=1e-18)\r\n"
    adapted = module.adapt_model(original, "INA826")
    assert "* vendor copyright" in adapted
    assert "D1 a b DBE area={AREA}" in adapted
    assert ".Model DBE D( IS=1e-18)" in adapted


@pytest.mark.parametrize("transient", [
    "not numerical data\n",
    "0 0\n0.15 0\n",
    "0 0 0\n0.075 nan 0\n0.15 0 0\n",
    "0 0 0\n0.075 0 0\n0.075 0 0\n0.15 0 0\n",
    "0 0 0\n0.1 0 0\n0.075 0 0\n0.15 0 0\n",
    "0 0 0\n0.05 0 0\n0.1 0 0\n",
])
def test_spice_rejects_corrupt_transient(monkeypatch, transient):
    from types import SimpleNamespace

    monkeypatch.setattr(spice, "solver", lambda: Path(__file__))
    monkeypatch.setattr(spice, "netlists", lambda c: {"ideal": "test netlist"})

    def fake_solver(*args, cwd, **kwargs):
        (cwd / "ideal.log").write_text("completed", encoding="ascii")
        for name in ["ideal-ac.txt", "ideal-noise.txt"]:
            (cwd / name).write_text("header\n1 1 0\n2 1 0\n", encoding="ascii")
        (cwd / "ideal-transient.txt").write_text("time input output\n" + transient, encoding="ascii")
        return SimpleNamespace(returncode=0, stdout=b"test solver")

    monkeypatch.setattr(spice.subprocess, "run", fake_solver)
    report = spice.run(SimulationConfig())
    assert report["status"] == "failed"
    assert report["checks"]["ideal"]["status"] == "failed"
    assert "reason" in report["checks"]["ideal"]
