export const defaults = {
  seed: 42, duration_s: 2, sample_rate_hz: 4000, gesture: 'Grip',
  intensity: 0.65, mains_mv: 0.25, noise_mv: 0.05, offset_mv: 0,
  motion_mv: 0.15, fatigue: 0, post_gain: 50, highpass_hz: 20,
  lowpass_hz: 450, notch: true, heart_rate_bpm: 72,
  motion_scenario: 'Gesture', tremor_hz: 6, motion_scale: 1,
  ppg_scenario: 'Clean', ppg_noise_au: 0.035, ppg_motion_au: 0.5,
  resistor_tolerance_pct: 1, capacitor_tolerance_pct: 5,
  electrode_resistance_ohm: 10000, temperature_c: 25,
}
export type Config = typeof defaults
export type Analysis = {
  config: Config
  provenance: { source: string; seed: number; samples: number }
  emg: { time_s: number[]; clean_v: number[]; raw_v: number[]; input_referred_v: number[]; ina_v: number[]; filtered_v: number[]; adc_input_v: number[]; adc_v: number[]; adc_codes: number[]; clipped_samples: number; ina_clipped_samples: number }
  dsp: { frequency_hz: number[]; amplitude_v: number[]; psd_frequency_hz: number[]; psd_v2_hz: number[]; features: Record<string, number>; windows: { time_s: number; rms_v: number }[]; decimation: { fir_taps: number; passband_ripple_db: number; stopband_attenuation_db: number } }
  analog: { method: string; ina_gain: number; total_gain: number; frequency_hz: number[]; magnitude_db: number[]; phase_deg: number[]; lp_checks: { frequency_hz: number; attenuation_db: number; alias_hz: number }[]; adc_step_v: number; nyquist_hz: number;
    noise_budget: { output_rms_v: number; nominal_gain_referred_rms_v: number; ina_white_rti_nv_sqrt_hz: number; exclusions: string; contributions: {source: string; output_rms_v: number}[] };
    tolerances: { trials: number; resistor_tolerance_pct: number; capacitor_tolerance_pct: number; total_gain_min_max: number[]; stages: Record<string, { frequency_hz_min_max: number[]; q_min_max: number[] }>; limitations: string }
  }
  imu: { time_s: number[]; acceleration_m_s2: number[][]; angular_velocity_deg_s: number[][]; pitch_deg: number[]; roll_deg: number[]; gyro_rms_deg_s: number; estimated_tremor_hz: number | null; orientation_warning: string }
  ppg: { time_s: number[]; amplitude_au: number[]; peak_indices: number[]; estimated_bpm: number | null; quality: string; quality_snr_db: number }
  warnings: string[]
}

export async function simulate(config: Config, signal: AbortSignal): Promise<Analysis> {
  const response = await fetch('/api/simulation/multimodal', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config), signal })
  if (!response.ok) throw new Error(`Simulation failed (${response.status}). Check configuration and backend.`)
  return response.json()
}

export function download(data: Analysis) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `forearmsense-synthetic-seed-${data.config.seed}.json`
  a.click()
  URL.revokeObjectURL(url)
}
