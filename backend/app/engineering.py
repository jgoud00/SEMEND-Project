"""Candidate Sallen-Key components, band-limited noise, and component sweeps.

Ideal buffers and a noiseless behavioral notch; not a complete physical design.
"""
import numpy as np
from scipy import signal

from .schemas import SimulationConfig

KB = 1.380649e-23


def components(c: SimulationConfig):
    hp_q = 1/np.sqrt(2)
    hp_r1 = 1/(2*np.pi*c.highpass_hz*100e-9*2*hp_q)
    result = [{"name": "HP", "kind": "highpass", "r1_ohm": hp_r1, "r2_ohm": 4*hp_q**2*hp_r1, "c1_f": 100e-9, "c2_f": 100e-9}]
    for i, q in enumerate([1/np.sqrt(2+np.sqrt(2)), 1/np.sqrt(2-np.sqrt(2))]):
        c2 = 10e-9
        c1 = 4*q*q*c2
        r = 1/(2*np.pi*c.lowpass_hz*np.sqrt(c1*c2))
        result.append({"name": f"LP{i+1}", "kind": "lowpass", "r1_ohm": r, "r2_ohm": r, "c1_f": c1, "c2_f": c2})
    return result


def transfer(stage):
    r1, r2, c1, c2 = [stage[k] for k in ["r1_ohm", "r2_ohm", "c1_f", "c2_f"]]
    product = r1*r2*c1*c2
    damping = r1*(c1+c2) if stage["kind"] == "highpass" else c2*(r1+r2)
    return ([product, 0, 0] if stage["kind"] == "highpass" else [1]), [product, damping, 1]


def stage_properties(stage):
    _, a = transfer(stage)
    return {"natural_frequency_hz": 1/(2*np.pi*np.sqrt(a[0])), "q": np.sqrt(a[0])/a[1]}


def filter_noise(stage, f, temperature_k):
    """MNA with unity follower: noise at each R and op-amp input, output PSD."""
    r1, r2, c1, c2 = [stage[k] for k in ["r1_ohm", "r2_ohm", "c1_f", "c2_f"]]
    s = 2j*np.pi*f
    g1, g2 = 1/r1, 1/r2
    m = np.zeros((len(f), 2, 2), complex)
    if stage["kind"] == "lowpass":
        m[:, 0, 0], m[:, 0, 1] = g1+g2+s*c1, -g2-s*c1
        m[:, 1, 0], m[:, 1, 1] = -g2, g2+s*c2
        sources = [np.array([1, 0]), np.array([1, -1])]
        feedback = s*c1
    else:
        m[:, 0, 0], m[:, 0, 1] = s*(c1+c2)+g1, -s*c2-g1
        m[:, 1, 0], m[:, 1, 1] = -s*c2, s*c2+g2
        sources = [np.array([1, 0]), np.array([0, 1])]
        feedback = np.full(len(f), g1)
    inv = np.linalg.inv(m)
    thermal = sum(4*KB*temperature_k*g*np.abs(inv[:, 1, :] @ source)**2 for g, source in zip([g1, g2], sources))
    voltage = (7.5e-9)**2*np.abs(1+inv[:, 1, 0]*feedback)**2
    current = (2e-15)**2*np.abs(inv[:, 1, 1])**2
    return {"resistors": thermal, "buffer_voltage": voltage, "buffer_current": current}


def noise_budget(c: SimulationConfig):
    f = np.geomspace(20, 450, 2048)
    stages = components(c)
    responses = [signal.freqs(*transfer(stage), worN=2*np.pi*f)[1] for stage in stages]
    notch = np.ones(len(f), complex)
    if c.notch:
        w = 2*np.pi*50
        notch = signal.freqs([1, 0, w*w], [1, w/30, w*w], worN=2*np.pi*f)[1]
    gain = 1+49400/5490
    total_gain = gain*c.post_gain
    downstream = [notch*responses[1]*responses[2], responses[2], np.ones(len(f))]
    full = responses[0]*downstream[0]*total_gain
    temp = c.temperature_c+273.15
    rs = c.electrode_resistance_ohm
    psds = {
        "INA input voltage": (18e-9)**2*np.abs(full)**2,
        "INA output voltage": (110e-9/gain)**2*np.abs(full)**2,
        "INA input current (two electrodes)": 2*(100e-15*rs)**2*np.abs(full)**2,
        "Electrode resistance (two electrodes)": 2*4*KB*temp*rs*np.abs(full)**2,
        "External INA gain resistor": 4*KB*temp*5490*((gain-1)/gain)**2*np.abs(full)**2,
    }
    for stage, after in zip(stages, downstream):
        for source, power in filter_noise(stage, f, temp).items():
            psds[f"{stage['name']} {source}"] = power*np.abs(after*c.post_gain)**2
    rf, rg = (c.post_gain-1)*1000, 1000
    equivalent = rf*rg/(rf+rg)
    psds["Post op-amp voltage"] = np.full(len(f), (7.5e-9*c.post_gain)**2)
    psds["Post feedback resistors"] = np.full(len(f), 4*KB*temp*equivalent*c.post_gain**2)
    psds["Post inverting-input current"] = np.full(len(f), (2e-15*rf)**2)
    contributions = [{"source": name, "output_rms_v": float(np.sqrt(np.trapezoid(p, f))), "nominal_gain_referred_rms_v": float(np.sqrt(np.trapezoid(p, f))/total_gain)} for name, p in psds.items()]
    total = np.sum(list(psds.values()), axis=0)
    return {"method": "uncorrelated white sources integrated over 20–450 Hz; ideal unity Sallen-Key buffers", "band_hz": [20, 450], "temperature_c": c.temperature_c, "electrode_resistance_ohm_per_leg": rs, "ina_white_rti_nv_sqrt_hz": float(np.hypot(18, 110/gain)), "contributions": contributions, "output_rms_v": float(np.sqrt(np.trapezoid(total, f))), "nominal_gain_referred_rms_v": float(np.sqrt(np.trapezoid(total, f))/total_gain), "frequency_hz": f[::8].tolist(), "output_density_v_sqrt_hz": np.sqrt(total[::8]).tolist(), "exclusions": "No 1/f, reference/supply, capacitor dielectric, PCB, notch-circuit noise or ADC alias noise. Densities are typical datasheet values, not guaranteed at 3.3 V. Not injected into waveforms; quantization remains separate."}


def tolerances(c: SimulationConfig, trials=200):
    rng = np.random.default_rng(c.seed)
    f = np.geomspace(5, 4000, 256)
    nominal = components(c)
    properties = {}
    rt, ct = c.resistor_tolerance_pct/100, c.capacitor_tolerance_pct/100
    # Keep each trial's original draw order while evaluating all responses together.
    spread = np.array([rt]*3 + [rt, rt, ct, ct]*len(nominal))
    draws = rng.uniform(1-spread, 1+spread, size=(trials, len(spread)))
    gains = (1+49400/(5490*draws[:, 0]))*(1+(c.post_gain-1)*draws[:, 1]/draws[:, 2])
    h = np.broadcast_to(gains[:, None], (trials, len(f))).astype(complex)
    s = 2j*np.pi*f
    for i, stage in enumerate(nominal):
        varied = dict(stage)
        for j, k in enumerate(["r1_ohm", "r2_ohm", "c1_f", "c2_f"]):
            varied[k] = stage[k]*draws[:, 3+4*i+j, None]
        b, a = transfer(varied)
        numerator = (b[0]*s)*s if stage["kind"] == "highpass" else 1
        h *= numerator/((a[0]*s+a[1])*s+1)
        p = stage_properties(varied)
        properties[stage["name"]] = {"frequency_hz": p["natural_frequency_hz"], "q": p["q"]}
    magnitudes = 20*np.log10(np.maximum(np.abs(h), 1e-15))
    return {"method": f"{trials} seeded independent uniform R/C component draws; ideal buffers; notch omitted to isolate component effects", "seed": c.seed, "trials": trials, "resistor_tolerance_pct": c.resistor_tolerance_pct, "capacitor_tolerance_pct": c.capacitor_tolerance_pct, "total_gain_min_max": [float(gains.min()), float(gains.max())], "stages": {name: {k+"_min_max": [float(v.min()), float(v.max())] for k, v in values.items()} for name, values in properties.items()}, "frequency_hz": f.tolist(), "magnitude_p05_db": np.percentile(magnitudes, 5, axis=0).tolist(), "magnitude_p95_db": np.percentile(magnitudes, 95, axis=0).tolist(), "limitations": "Percentiles are sampling summaries, not worst-case guarantees. No internal gain errors, parasitics or finite op-amp response. Q changes with component mismatch."}
