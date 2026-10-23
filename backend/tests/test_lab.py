import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy import signal

from app import analog, dsp, simulation
from app.main import app
from app.schemas import SimulationConfig

client = TestClient(app)


def test_generator_units_seed_count_and_noise():
    c = SimulationConfig(noise_mv=0, mains_mv=0, motion_mv=0)
    t, clean, raw = simulation.emg(c)
    assert len(t) == 8000
    assert np.diff(t) == pytest.approx(np.full(7999, 1/4000))
    assert np.max(clean) - np.min(clean) <= 0.005
    assert np.array_equal(clean, raw)
    assert np.array_equal(raw, simulation.emg(c)[2])
    assert not np.array_equal(raw, simulation.emg(c.model_copy(update={"seed": 43}))[2])
    mains = simulation.emg(c.model_copy(update={"mains_mv": 1}))[2] - raw
    assert np.sqrt(np.mean(mains**2)) == pytest.approx(0.001/np.sqrt(2))
    white = simulation.emg(c.model_copy(update={"noise_mv": 0.1}))[2] - raw
    assert np.std(white) > 8e-5
    offset = simulation.emg(c.model_copy(update={"offset_mv": 50}))[2] - raw
    assert offset == pytest.approx(np.full(len(t), 0.05))


def test_analog_gain_cutoffs_and_aliasing():
    c = SimulationConfig(notch=False)
    assert analog.INA_GAIN == pytest.approx(9.99818, rel=1e-6)
    for cutoff, order, kind in [(20, 2, "highpass"), (450, 4, "lowpass")]:
        b, a = signal.butter(order, 2*np.pi*cutoff, btype=kind, analog=True)
        _, h = signal.freqs(b, a, [2*np.pi*cutoff])
        assert 20*np.log10(abs(h[0])) == pytest.approx(-3.0103, abs=1e-4)
        assert np.all(np.real(np.roots(a)) < 0)
    checks = analog.analyze(c)["lp_checks"]
    assert checks[4]["alias_hz"] == 450
    assert checks[4]["attenuation_db"] > 70
    assert checks[1]["attenuation_db"] < 6  # 450 Hz LP is insufficient for 1 kHz decimation.
    assert abs(analog.response(SimulationConfig(), [50])[0]) < 1e-10


def test_adc_clipping_and_quantization():
    c = SimulationConfig()
    chain = analog.condition(np.full(8000, 0.5), c)
    assert chain["ina_clipped_samples"] == 8000
    assert chain["clipped_samples"] > 0
    assert np.min(chain["adc_codes"]) >= 0
    assert np.max(chain["adc_codes"]) <= 4095
    assert np.max(np.abs(chain["adc_v"] - chain["adc_input_v"])) <= 3.3/4095/2 + 1e-12


def test_fft_features_and_psd():
    fs = 4000
    t = np.arange(8000)/fs
    x = 0.001*np.sin(2*np.pi*125*t)
    result = dsp.analyze(x, fs)
    f = result["features"]
    assert f["rms_v"] == pytest.approx(0.001/np.sqrt(2))
    peak = np.argmax(result["amplitude_v"])
    assert result["frequency_hz"][peak] == 125
    assert result["amplitude_v"][peak] == pytest.approx(0.001, rel=1e-3)
    assert f["median_frequency_hz"] == pytest.approx(125)
    assert len(result["windows"]) == 19
    assert np.trapezoid(result["psd_v2_hz"], result["psd_frequency_hz"]) == pytest.approx(np.mean(x*x), rel=0.01)
    assert dsp.features(np.zeros(800), fs)["mean_frequency_hz"] == 0


@pytest.mark.parametrize("fs", [2000, 4000, 8000])
def test_api_valid_response(fs):
    response = client.post("/api/simulation/emg", json={"sample_rate_hz": fs})
    assert response.status_code == 200
    d = response.json()
    assert d["provenance"]["source"] == "synthetic"
    assert len(d["emg"]["raw_v"]) == 2*fs
    assert np.isfinite(d["emg"]["input_referred_v"]).all()
    assert len(d["dsp"]["amplitude_v"]) == fs+1
    assert len(d["imu"]["time_s"]) == 400
    assert len(d["ppg"]["time_s"]) == 200
    assert d["imu"]["yaw"] is None
    assert d["ppg"]["spo2"] is None


@pytest.mark.parametrize("body", [{"duration_s": -1}, {"sample_rate_hz": 999}, {"intensity": 2}, {"post_gain": 0}, {"seed": -1}, {"seed": 1.5}, {"gesture": "unknown"}, {"unexpected": 1}, {"offset_mv": 51}, {"lowpass_hz": 9999}])
def test_invalid_requests(body):
    assert client.post("/api/simulation/emg", json=body).status_code == 422


def test_other_endpoints_and_pulse():
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/config").json()["defaults"]["seed"] == 42
    for path in ["simulation/multimodal", "simulation/imu", "simulation/ppg", "analog/analyze", "dsp/analyze"]:
        assert client.post(f"/api/{path}", json={}).status_code == 200
    p = simulation.ppg(SimulationConfig(duration_s=10, heart_rate_bpm=90))
    assert p["estimated_bpm"] == pytest.approx(90, abs=2)


def test_orientation_stationary_and_reproducible():
    c = SimulationConfig(gesture="Rest")
    a = simulation.imu(c)
    assert a == simulation.imu(c)
    assert max(abs(np.array(a["pitch_deg"]))) < 1
    assert np.median(np.array(a["acceleration_m_s2"])[:, 2]) == pytest.approx(9.8, abs=0.1)


@pytest.mark.parametrize("fs", [2000, 4000, 8000])
def test_decimator_rejects_alias_tone_and_preserves_passband(fs):
    t = np.arange(fs*2)/fs
    x = np.sin(2*np.pi*125*t) + np.sin(2*np.pi*700*t)
    d = dsp.decimate(x, fs)
    assert d["sample_rate_hz"] == 1000
    assert len(d["signal_v"]) == 2000
    assert d["passband_ripple_db"] < 0.1
    assert d["stopband_attenuation_db"] >= 60
    middle = np.array(d["signal_v"])[250:-250]
    f = dsp.spectrum(middle, 1000)
    frequencies, amplitudes = np.array(f["frequency_hz"]), np.array(f["amplitude_v"])
    assert np.max(amplitudes[abs(frequencies-300) < 2]) < 0.001
    assert np.max(amplitudes[abs(frequencies-125) < 2]) > 0.8
