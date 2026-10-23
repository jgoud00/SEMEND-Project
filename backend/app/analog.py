"""Continuous-time transfer functions, sampled using a zero-order hold.

This is not a manufacturer-model or transistor-level SPICE simulation.
"""
import numpy as np
from scipy import signal

from .schemas import SimulationConfig
from .engineering import components, noise_budget, tolerances

INA_GAIN = 1 + 49400 / 5490
VREF = 1.65
SUPPLY = 3.3
HEADROOM = 0.1  # Conservative illustrative output margin, not a device guarantee.


def stages(c: SimulationConfig):
    result = [signal.butter(2, 2*np.pi*c.highpass_hz, btype="highpass", analog=True)]
    if c.notch:
        w = 2*np.pi*50
        result.append((np.array([1, 0, w*w]), np.array([1, w/30, w*w])))
    result.append(signal.butter(4, 2*np.pi*c.lowpass_hz, analog=True))
    return result


def response(c: SimulationConfig, frequencies):
    h = np.ones(len(frequencies), dtype=complex)
    for b, a in stages(c):
        _, part = signal.freqs(b, a, worN=2*np.pi*np.asarray(frequencies))
        h *= part
    return h


def condition(raw, c: SimulationConfig):
    ina_ideal = VREF + INA_GAIN * raw
    ina = np.clip(ina_ideal, HEADROOM, SUPPLY - HEADROOM)
    y = ina - VREF
    # State-space discretization avoids badly conditioned fourth-order polynomials.
    for b, a in stages(c):
        ss = signal.tf2ss(b, a)
        ad, bd, cd, dd, _ = signal.cont2discrete(ss, 1/c.sample_rate_hz, method="zoh")
        _, out, _ = signal.dlsim((ad, bd, cd, dd, 1/c.sample_rate_hz), y)
        y = out[:, 0]
    filtered = y * c.post_gain
    ideal = VREF + filtered
    adc_input = np.clip(ideal, HEADROOM, SUPPLY - HEADROOM)
    codes = np.rint(adc_input / SUPPLY * 4095).astype(int)
    adc_v = codes * SUPPLY / 4095
    return {"ina_v": ina, "filtered_v": filtered, "adc_input_v": adc_input, "adc_v": adc_v, "adc_codes": codes, "ina_clipped_samples": int(np.count_nonzero(ina_ideal != ina)), "clipped_samples": int(np.count_nonzero(ideal != adc_input))}


def analyze(c: SimulationConfig):
    f = np.geomspace(1, 10000, 350)
    h = response(c, f)
    checks = np.array([450, 500, 1000, 2000, 3550, 4000])
    # LP-only attenuation is separate from the notch/HP response.
    b, a = signal.butter(4, 2*np.pi*c.lowpass_hz, analog=True)
    _, lp = signal.freqs(b, a, worN=2*np.pi*checks)
    result = {"method": "analytical continuous-time transfer functions; ZOH sampled input", "ina_gain": INA_GAIN, "gain_resistor_ohm": 5490, "post_gain": c.post_gain, "total_gain": INA_GAIN*c.post_gain, "supply_v": SUPPLY, "reference_v": VREF, "assumed_headroom_v": HEADROOM, "adc_bits": 12, "adc_step_v": SUPPLY/4095, "nyquist_hz": c.sample_rate_hz/2, "frequency_hz": f.tolist(), "magnitude_db": (20*np.log10(np.maximum(np.abs(h)*INA_GAIN*c.post_gain, 1e-12))).tolist(), "phase_deg": np.rad2deg(np.unwrap(np.angle(h))).tolist(), "lp_checks": [{"frequency_hz": float(freq), "attenuation_db": float(-20*np.log10(abs(value))), "alias_hz": float(abs((freq+c.sample_rate_hz/2) % c.sample_rate_hz-c.sample_rate_hz/2))} for freq, value in zip(checks, lp)], "input_common_mode": "Not device-validated: gain-dependent internal-node limits require TI Figure 60 / VCM-vs-output verification.", "noise": "Full resistor/current/1-f noise budget deferred; generator noise is configurable, not a device noise specification."}

    result.update({"components": components(c), "noise_budget": noise_budget(c), "tolerances": tolerances(c)})
    result["noise"] = result["noise_budget"]["exclusions"]
    return result
