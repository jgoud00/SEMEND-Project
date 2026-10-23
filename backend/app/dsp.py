import numpy as np
from scipy import signal
from functools import lru_cache


@lru_cache(maxsize=3)
def decimator(fs):
    # 400 Hz passband, 500 Hz stopband; design margin above the 60 dB requirement.
    count, beta = signal.kaiserord(65, 100/(fs/2))
    count += 1 - count % 2
    taps = signal.firwin(count, 450, fs=fs, window=("kaiser", beta))
    f, h = signal.freqz(taps, worN=65536, fs=fs)
    gain_db = 20*np.log10(np.maximum(np.abs(h), 1e-15))
    ripple = float(np.ptp(gain_db[f <= 400]))
    attenuation = float(-np.max(gain_db[f >= 500]))
    assert ripple <= 0.1 and attenuation >= 60, "Decimation response fails specification"
    return taps, ripple, attenuation


def decimate(x, fs):
    taps, ripple, attenuation = decimator(fs)
    y = signal.resample_poly(x, 1, fs//1000, window=taps)
    return {"sample_rate_hz": 1000, "signal_v": y.tolist(), "fir_taps": len(taps), "passband_edge_hz": 400, "stopband_edge_hz": 500, "passband_ripple_db": ripple, "stopband_attenuation_db": attenuation, "boundary": "zero extension, delay-compensated offline resampling; edge transients retained"}


def spectrum(x, fs):
    n = len(x)
    window = np.hanning(n)
    amplitude = 2*np.abs(np.fft.rfft((x - np.mean(x))*window))/np.sum(window)
    amplitude[0] /= 2
    if n % 2 == 0:
        amplitude[-1] /= 2
    f = np.fft.rfftfreq(n, 1/fs)
    pf, power = signal.welch(x, fs, nperseg=min(n, 1024))
    return {"frequency_hz": f.tolist(), "amplitude_v": amplitude.tolist(), "psd_frequency_hz": pf.tolist(), "psd_v2_hz": power.tolist()}


def features(x, fs):
    f, power = signal.welch(x, fs, nperseg=min(256, len(x)))
    total = power.sum()
    differences = np.diff(x)
    threshold = 1e-5
    return {"rms_v": float(np.sqrt(np.mean(x*x))), "mav_v": float(np.mean(np.abs(x))), "waveform_length_v": float(np.abs(differences).sum()), "zero_crossings": int(np.sum((x[:-1]*x[1:] < 0) & (np.abs(differences) > threshold))), "slope_sign_changes": int(np.sum((differences[:-1]*differences[1:] < 0) & (np.abs(differences[:-1]) > threshold) & (np.abs(differences[1:]) > threshold))), "mean_frequency_hz": float(np.dot(f, power)/total) if total > 0 else 0.0, "median_frequency_hz": float(f[np.searchsorted(np.cumsum(power), total/2)]) if total > 0 else 0.0}


def analyze(x, fs):
    size, hop = round(0.2*fs), round(0.1*fs)
    windows = [{"time_s": (i+size/2)/fs, **features(x[i:i+size], fs)} for i in range(0, len(x)-size+1, hop)]
    return {**spectrum(x, fs), "features": features(x, fs), "windows": windows, "window_ms": 200, "overlap": 0.5, "decimation": decimate(x, fs)}
