"""Seeded illustrative signals; every EMG amplitude is in volts."""
import numpy as np
from scipy import signal

from .schemas import SimulationConfig


def emg(c: SimulationConfig):
    rng = np.random.default_rng(c.seed)
    fs = c.sample_rate_hz
    t = np.arange(round(c.duration_s * fs)) / fs
    carrier = signal.sosfilt(signal.butter(4, [20, 450], fs=fs, btype="bandpass", output="sos"), rng.normal(size=len(t)))
    # Keep the clean signal within the stated 5 mVpp full-scale assumption.
    carrier /= max(np.max(np.abs(carrier)), 1e-12)
    envelope = 0.2 + 0.8 * np.sin(np.pi * 0.8 * t) ** 4
    activation = 0.025 if c.gesture == "Rest" else c.intensity
    if c.fatigue:
        fatigued = signal.sosfilt(signal.butter(2, 100, fs=fs, output="sos"), carrier)
        blend = c.fatigue * t / c.duration_s
        carrier = (1 - blend) * carrier + blend * fatigued
    clean = 0.0025 * activation * envelope * carrier
    white = rng.normal(0, c.noise_mv / 1000, len(t))
    colored = signal.lfilter([1], [1, -0.95], rng.normal(size=len(t)))
    colored *= c.noise_mv / 2000 / max(np.std(colored), 1e-12)
    motion = c.motion_mv / 1000 * np.sin(2 * np.pi * 3 * t) * np.sin(np.pi * t / c.duration_s) ** 2
    raw = clean + white + colored + motion + c.mains_mv / 1000 * np.sin(2 * np.pi * 50 * t) + c.offset_mv / 1000
    return t, clean, raw


def imu(c: SimulationConfig):
    rng = np.random.default_rng(c.seed + 1)
    fs = 200
    t = np.arange(round(c.duration_s * fs)) / fs
    amplitude = {"Rest": 0, "Grip": 2, "Wrist flexion": 25, "Wrist extension": -25, "Forearm rotation": 12}[c.gesture]
    pitch = amplitude * np.sin(2 * np.pi * 0.8 * t)
    roll = (30 if c.gesture == "Forearm rotation" else 3) * np.sin(2 * np.pi * 0.6 * t)
    dynamic_acceleration = np.zeros((len(t), 3))
    if c.motion_scenario == "Stationary":
        pitch, roll = np.zeros(len(t)), np.zeros(len(t))
    elif c.motion_scenario == "Repetitive":
        pitch, roll = 25*np.sin(2*np.pi*1.2*t), 10*np.sin(2*np.pi*0.6*t)
    elif c.motion_scenario == "Tremor":
        pitch, roll = 2*np.sin(2*np.pi*c.tremor_hz*t), np.sin(2*np.pi*c.tremor_hz*t)
    elif c.motion_scenario == "Sudden motion":
        pulse = np.exp(-0.5*((t-c.duration_s/2)/0.05)**2)
        pitch, roll = 20*pulse, 8*pulse
        dynamic_acceleration[:, 0] = 3*pulse
    pitch, roll = pitch*c.motion_scale, roll*c.motion_scale
    dynamic_acceleration *= c.motion_scale
    p, r = np.deg2rad(pitch), np.deg2rad(roll)
    acceleration = np.column_stack((-9.80665 * np.sin(p), 9.80665 * np.sin(r) * np.cos(p), 9.80665 * np.cos(r) * np.cos(p)))
    acceleration += rng.normal(0, 0.025, acceleration.shape)
    acceleration += dynamic_acceleration
    gyro = np.column_stack((np.gradient(roll, 1 / fs), np.gradient(pitch, 1 / fs), np.zeros(len(t))))
    gyro += 0.1 + rng.normal(0, 0.12, gyro.shape)
    gyro += t[:, None] * 0.01
    acc_pitch = np.rad2deg(np.arctan2(-acceleration[:, 0], np.hypot(acceleration[:, 1], acceleration[:, 2])))
    acc_roll = np.rad2deg(np.arctan2(acceleration[:, 1], acceleration[:, 2]))
    estimated = np.zeros((len(t), 2))
    estimated[0] = [acc_pitch[0], acc_roll[0]]
    alpha = 0.98
    for i in range(1, len(t)):
        estimated[i] = alpha * (estimated[i-1] + gyro[i, [1, 0]] / fs) + (1-alpha) * np.array([acc_pitch[i], acc_roll[i]])
    f, power = signal.periodogram(gyro[:, 1], fs)
    band = (f >= 3) & (f <= 12)
    tremor_peak = float(f[band][np.argmax(power[band])]) if c.motion_scenario == "Tremor" and c.motion_scale > 0 else None
    return {"sample_rate_hz": fs, "scenario": c.motion_scenario, "time_s": t.tolist(), "acceleration_m_s2": acceleration.tolist(), "angular_velocity_deg_s": gyro.tolist(), "pitch_deg": estimated[:, 0].tolist(), "roll_deg": estimated[:, 1].tolist(), "gyro_rms_deg_s": float(np.sqrt(np.mean(gyro**2))), "estimated_tremor_hz": tremor_peak, "orientation_warning": "Dynamic acceleration biases accelerometer-derived orientation; no absolute yaw.", "yaw": None}


def ppg(c: SimulationConfig):
    rng = np.random.default_rng(c.seed + 2)
    fs = 100
    t = np.arange(round(c.duration_s * fs)) / fs
    phase = t * c.heart_rate_bpm / 60
    wave = np.sin(2*np.pi*phase) + 0.25*np.sin(4*np.pi*phase - 0.6)
    clean = (1 + 0.1*np.sin(2*np.pi*0.1*t)) * wave
    amplitude = 0.1 if c.ppg_scenario == "Low perfusion" else 1
    noise = rng.normal(0, c.ppg_noise_au, len(t))
    artifact = c.ppg_motion_au*(np.sin(2*np.pi*1.7*t) + 0.5*np.sin(2*np.pi*3.2*t)) if c.ppg_scenario == "Motion artifact" else np.zeros(len(t))
    observed_pulse = amplitude*clean
    dropout = (t >= c.duration_s*0.35) & (t < c.duration_s*0.65) if c.ppg_scenario == "Dropout" else np.zeros(len(t), dtype=bool)
    observed_pulse[dropout] = 0
    raw = observed_pulse + 0.15*np.sin(2*np.pi*0.2*t) + noise + artifact
    # Synthetic oracle quality uses known injected components, not a clinical SQI.
    corruption = noise + artifact
    snr = float(10*np.log10(max(np.mean(observed_pulse**2), 1e-20)/max(np.mean(corruption**2), 1e-20)))
    usable = snr >= 10 and not np.any(dropout)
    peaks, _ = signal.find_peaks(raw, distance=int(fs*60/200), prominence=0.7)
    enough = len(peaks) >= 3 and c.duration_s >= 4
    bpm = float(60*fs/np.median(np.diff(peaks))) if usable and enough else None
    reason = "usable illustrative signal" if usable and enough else "insufficient duration or peaks" if usable else "corrupted or incomplete synthetic signal"
    return {"sample_rate_hz": fs, "scenario": c.ppg_scenario, "time_s": t.tolist(), "amplitude_au": raw.tolist(), "clean_amplitude_au": clean.tolist(), "dropout_mask": dropout.tolist(), "peak_indices": peaks.tolist(), "estimated_bpm": bpm, "quality": reason, "quality_snr_db": snr, "quality_method": "synthetic oracle: known injected components, threshold 10 dB; not a validated clinical SQI", "spo2": None}
