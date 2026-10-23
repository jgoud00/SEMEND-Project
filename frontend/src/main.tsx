import { StrictMode, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Activity, ArrowDownToLine, ArrowUpRight, AudioLines, CircuitBoard, FlaskConical, HeartPulse, Layers3, Move3D, Pause, Play, Radio, RotateCcw, Settings2, ShieldCheck } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { type Analysis, type Config, defaults, download, simulate } from './api'
import './style.css'
import { MLPanel } from './MLPanel'
import { EngineeringPanel } from './EngineeringPanel'
import { ProjectOverview } from './ProjectOverview'

type Row = Record<string, number | null>
const colors = ['#66e4c0', '#76a8fb', '#f3be75']
function Plot({ data, series, x = 't', unit = '', height = 215 }: { data: Row[]; series: { key: string; name: string; color?: string; points?: boolean }[]; x?: string; unit?: string; height?: number }) {
  return <div style={{ height }} role="img" aria-label={`${series.map(s => s.name).join(', ')} chart; vertical unit ${unit}`}>
    <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 10, right: 12, bottom: 2, left: -12 }}>
      <CartesianGrid stroke="#253033" strokeDasharray="3 5" vertical={false} />
      <XAxis type="number" domain={['dataMin', 'dataMax']} dataKey={x} tickFormatter={v => Math.abs(v) < 1 ? Number(v).toFixed(2) : Number(v).toFixed(0)} minTickGap={45} stroke="#718184" tickLine={false} axisLine={false} fontSize={10} />
      <YAxis width={58} tickFormatter={v => Number(v).toPrecision(2)} stroke="#718184" tickLine={false} axisLine={false} fontSize={10} />
      <Tooltip contentStyle={{ background: '#142023', border: '1px solid #354347', borderRadius: 8, fontSize: 12 }} labelFormatter={v => `${Number(v).toFixed(3)}`} formatter={(v, name) => [`${Number(v).toPrecision(4)} ${unit}`, name]} />
      {series.map((s, i) => <Line key={s.key} type="linear" dataKey={s.key} name={s.name} stroke={s.color ?? colors[i]} strokeWidth={s.points ? 0 : 1.2} dot={s.points ? { r: 3, fill: s.color ?? colors[i] } : false} isAnimationActive={false} />)}
    </LineChart></ResponsiveContainer>
  </div>
}

function Range({ label, value, min, max, step = 1, unit, onChange }: { label: string; value: number; min: number; max: number; step?: number; unit: string; onChange: (n: number) => void }) {
  return <label className="range"><span>{label}<strong>{value}{unit}</strong></span><input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(Number(e.target.value))} /></label>
}

function App() {
  const [config, setConfig] = useState<Config>({ ...defaults })
  const [data, setData] = useState<Analysis | null>(null)
  const [running, setRunning] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('Project overview')
  const [reset, setReset] = useState(0)
  const trial = useRef(0)
  const generation = useRef(0)
  const completedConfig = useRef('')
  function change<K extends keyof Config>(key: K, value: Config[K]) { setConfig(c => ({ ...c, [key]: value })) }

  useEffect(() => {
    const key = JSON.stringify(config) + reset
    if (!running && completedConfig.current === key) { setLoading(false); return }
    const controller = new AbortController()
    const current = ++generation.current
    let timer: ReturnType<typeof setTimeout>
    async function update() {
      setLoading(true)
      try {
        const result = await simulate({ ...config, seed: config.seed + trial.current }, controller.signal)
        if (current !== generation.current) return
        setData(result)
        completedConfig.current = key
        setError('')
        if (running) { trial.current += 1; timer = setTimeout(update, config.duration_s * 1000) }
      } catch (e) {
        if (!controller.signal.aborted) { setError(e instanceof Error ? e.message : 'Backend unavailable'); setRunning(false) }
      } finally { if (current === generation.current && !controller.signal.aborted) setLoading(false) }
    }
    void update()
    return () => { controller.abort(); clearTimeout(timer); generation.current += 1 }
  }, [config, running, reset])

  function resetSimulation() { trial.current = 0; setRunning(false); setConfig({ ...defaults }); setReset(n => n + 1) }
  const clips = data ? data.emg.clipped_samples + data.emg.ina_clipped_samples : 0
  const waveform = data?.emg.time_s.slice(0, Math.round(data.config.sample_rate_hz * 0.25)).map((t, i) => ({ t, raw: data.emg.raw_v[i] * 1000, filtered: data.emg.input_referred_v[i] * 1000 })) ?? []
  const fft = data?.dsp.frequency_hz.map((t, i) => ({ t, fft: data.dsp.amplitude_v[i] * 1000 })).filter(v => v.t <= 700) ?? []
  const psd = data?.dsp.psd_frequency_hz.map((t, i) => ({ t, psd: 10 * Math.log10(Math.max(data.dsp.psd_v2_hz[i], 1e-20)) })).filter(v => v.t <= 700) ?? []
  const bode = data?.analog.frequency_hz.map((t, i) => ({ t, gain: data.analog.magnitude_db[i] })).filter(v => v.t <= 2000) ?? []
  const inertial = data?.imu.time_s.map((t, i) => ({ t, x: data.imu.acceleration_m_s2[i][0], y: data.imu.acceleration_m_s2[i][1], z: data.imu.acceleration_m_s2[i][2], gx: data.imu.angular_velocity_deg_s[i][0], gy: data.imu.angular_velocity_deg_s[i][1], gz: data.imu.angular_velocity_deg_s[i][2], pitch: data.imu.pitch_deg[i], roll: data.imu.roll_deg[i] })) ?? []
  const pulse = data?.ppg.time_s.map((t, i) => ({ t, pulse: data.ppg.amplitude_au[i], peak: data.ppg.peak_indices.includes(i) ? data.ppg.amplitude_au[i] : null })) ?? []
  const multi = tab === 'Motion & pulse'
  const circuit = tab === 'Analog circuit'
  const features = data?.dsp.features

  return <div className="app">
    <aside className="sidebar">
      <a href="#main" className="skip">Skip to laboratory</a>
      <div className="brand"><div className="brand-icon"><AudioLines size={24} /></div><div>ForearmSense<span>AI SIGNAL LABORATORY</span></div></div>
      <div className="workspace"><span className="led" /><span>Local workspace</span><span className="version">v0.1</span></div>
      <p className="nav-label">WORKSPACE</p>
      <nav>{[{ label: 'Project overview', icon: ShieldCheck }, { label: 'EMG laboratory', icon: Activity }, { label: 'Analog circuit', icon: CircuitBoard }, { label: 'Motion & pulse', icon: Move3D }, { label: 'Machine learning', icon: Layers3 }, { label: 'Experiment details', icon: FlaskConical }].map(({ label, icon: Icon }) => <button className={tab === label ? 'nav-item active' : 'nav-item'} onClick={() => setTab(label)} key={label}><Icon size={18} />{label}{tab === label && <span className="nav-dot" />}</button>)}</nav>
      <div className="pipeline"><p className="nav-label">EDUCATIONAL MODEL</p>{['Synthetic electrodes', 'Analog conditioning', 'Simulated 12-bit ADC', 'Digital signal analysis'].map((name, i) => <div key={name}><span>{String(i + 1).padStart(2, '0')}</span>{name}</div>)}</div>
      <div className="sidebar-note"><ShieldCheck size={19} /><strong>Built for exploration</strong><p>Synthetic signals. Transparent models. Reproducible experiments.</p><span>AECD · 25EC1302E</span></div>
      <div className="university"><div>KL</div><span>KL University<small>Hyderabad · Engineering laboratory</small></span></div>
    </aside>
    <div className="content">
      <header className="topbar"><span>Workspace <span className="slash">/</span> <strong>{tab}</strong></span><div><span className="synthetic"><span /> {tab === 'Project overview' ? 'PROJECT SCOPE' : 'SIMULATED DATA'}</span><span className="local"><Radio size={13} /> Local engine</span></div></header>
      <main id="main">
        <div className="page-title"><div><div className="eyebrow">MULTIMODAL BIOMEDICAL SIGNAL LABORATORY</div><h1>{tab === 'EMG laboratory' ? 'See the signal. Understand the muscle.' : tab}</h1><p>{tab === 'Project overview' ? 'Arduino Uno / BioAmp EXG Pill / MPU-6050 / Hand gripper' : 'Educational simulation: generated signals, theoretical circuits and synthetic benchmarks.'}</p></div><button className="button export" disabled={!data || loading || tab === 'Project overview'} onClick={() => data && download(data)}><ArrowDownToLine size={16} />Export trial</button></div>
        <div className="notice"><FlaskConical size={16} /><span>This is a simulation environment. All signals are generated; no real physiological measurements.</span><span className="notice-tag">RESEARCH PROTOTYPE</span></div>
        {tab === 'Project overview' ? <ProjectOverview /> : <><section className="stats" aria-label="Educational simulation overview">
          <div className="stat"><div><span>EMG ACTIVITY</span><Activity size={17} /></div><strong>{features ? (features.rms_v * 1000).toFixed(3) : '—'}<small>mV RMS</small></strong><p>Simulated ADC · input-referred</p></div>
          <div className="stat"><div><span>MOVEMENT</span><Move3D size={17} /></div><strong>{data ? data.imu.gyro_rms_deg_s.toFixed(1) : '—'}<small>°/s RMS</small></strong><p>Six-axis synthetic IMU</p></div>
          <div className="stat"><div><span>SIMULATED PULSE</span><HeartPulse size={17} /></div><strong>{data?.ppg.estimated_bpm?.toFixed(0) ?? '—'}<small>bpm</small></strong><p>Simulated PPG · unvalidated</p></div>
          <div className={`stat ${clips ? 'warning-stat' : ''}`}><div><span>ACQUISITION</span><Layers3 size={17} /></div><strong>{data ? clips ? 'Clipping' : 'In range' : '—'}<small>{data ? `${data.config.sample_rate_hz / 1000} kHz` : ''}</small></strong><p>{clips ? `${clips} clipping events across stages` : 'Model: 12-bit ADC / 3.3 V'}</p></div>
        </section>
        <div className="laboratory">
          <div className="plots">
            {circuit && data && <EngineeringPanel data={data} />}
            {multi && data && <section className="panel details"><h2>Scenario quality</h2><p>Educational motion/PPG models only. No working pulse sensor is in the available hardware; measured HR and oxygen saturation are unavailable.</p><p>Motion: {data.config.motion_scenario}. Estimated tremor peak: {data.imu.estimated_tremor_hz?.toFixed(2) ?? 'unavailable'} Hz. {data.imu.orientation_warning}</p><p>PPG: {data.config.ppg_scenario} · {data.ppg.quality} · injected-component SNR {data.ppg.quality_snr_db.toFixed(1)} dB (synthetic oracle, not a clinical quality score). Heart rate is withheld for poor quality or trials shorter than 4 seconds.</p></section>}
            {tab === 'Machine learning' && <MLPanel config={data?.config ?? config} />}
            {error && <div className="error" role="alert">{error}. Start the backend on 127.0.0.1:8000, then press Start simulation.</div>}
            <section className="panel waveform-panel"><div className="panel-heading"><div><span className="section-number">01</span><h2>{multi ? 'Motion telemetry' : circuit ? 'Analog frequency response' : 'EMG signal acquisition'}</h2></div><span className={`status ${running ? 'live' : ''}`}><span />{loading ? 'COMPUTING' : running ? 'RUNNING' : 'PAUSED'}</span></div>
              <div className="chart-toolbar"><div className="legend"><span><i />{multi ? 'Acceleration X' : circuit ? 'Chain magnitude' : 'Filtered EMG'}</span>{!circuit && <span><i className="blue" />{multi ? 'Acceleration Y' : 'Raw electrode'}</span>}</div><span>{multi ? 'm/s² · seconds' : circuit ? 'dB · Hz' : 'mV · first 250 ms'}</span></div>
              {!data ? <div className="empty">{error ? 'Waiting for the local backend' : 'Generating the first trial…'}</div> : <Plot data={multi ? inertial : circuit ? bode : waveform} series={multi ? [{ key: 'x', name: 'X' }, { key: 'y', name: 'Y' }, { key: 'z', name: 'Z' }] : circuit ? [{ key: 'gain', name: 'Gain' }] : [{ key: 'filtered', name: 'Filtered input-referred' }, { key: 'raw', name: 'Raw electrode' }]} unit={multi ? 'm/s²' : circuit ? 'dB' : 'mV'} height={255} />}
              <div className="chart-footer"><span><span className="led" /> {data ? `${data.provenance.samples.toLocaleString()} EMG samples · ${data.config.duration_s}s trial` : 'Waiting for data'}</span><span data-testid="seed">SEED {data?.config.seed ?? '—'} <span className="slash">/</span> {data?.config.gesture ?? config.gesture}</span></div>
            </section>
            <div className="chart-pair">
              <section className="panel"><div className="panel-heading"><div><span className="section-number">02</span><h2>{multi ? 'Optical pulse' : circuit ? 'ADC output' : 'Frequency spectrum'}</h2></div><span className="tag">{multi ? 'PPG' : circuit ? '12 BIT' : 'FFT'}</span></div><p className="chart-caption">{multi ? 'Synthetic amplitude · arbitrary units' : circuit ? 'Biased and quantized · volts' : 'Hann window · amplitude in mV'}</p><Plot data={multi ? pulse : circuit ? (data?.emg.time_s.slice(0, data.config.sample_rate_hz/4).map((t, i) => ({ t, adc: data.emg.adc_v[i] })) ?? []) : fft} series={multi ? [{ key: 'pulse', name: 'Pulse' }, { key: 'peak', name: 'Detected peak', color: '#f3be75', points: true }] : [{ key: circuit ? 'adc' : 'fft', name: circuit ? 'ADC' : 'Amplitude' }]} unit={multi ? 'a.u.' : circuit ? 'V' : 'mV'} /></section>
              <section className="panel"><div className="panel-heading"><div><span className="section-number">03</span><h2>{multi ? 'Orientation estimate' : circuit ? 'Phase response' : 'Muscle activation envelope'}</h2></div><span className="tag">{multi ? 'IMU' : circuit ? 'DEG' : 'RMS'}</span></div><p className="chart-caption">{multi ? 'Complementary filter · pitch and roll in degrees' : circuit ? 'Unwrapped phase · degrees vs Hz' : '200 ms windows · 50% overlap · mV'}</p><Plot data={multi ? inertial : circuit ? (data?.analog.frequency_hz.map((t, i) => ({ t, phase: data.analog.phase_deg[i] })).filter(v => v.t <= 2000) ?? []) : (data?.dsp.windows.map(w => ({ t: w.time_s, rms: w.rms_v * 1000 })) ?? [])} series={multi ? [{ key: 'pitch', name: 'Pitch' }, { key: 'roll', name: 'Roll' }] : [{ key: circuit ? 'phase' : 'rms', name: circuit ? 'Phase' : 'RMS', color: '#76a8fb' }]} unit={multi || circuit ? '°' : 'mV'} /></section>
            </div>
            {tab === 'EMG laboratory' && <section className="panel"><div className="panel-heading"><div><span className="section-number">04</span><h2>Power spectral density</h2></div><span className="tag">WELCH</span></div><p className="chart-caption">Input-referred power · dB(V²/Hz)</p><Plot data={psd} series={[{ key: 'psd', name: 'PSD', color: '#c6a0f6' }]} unit="dB(V²/Hz)" height={160} /></section>}
            {multi && <section className="panel"><div className="panel-heading"><div><Move3D size={16} /><h2>Angular velocity</h2></div><span className="tag">GYROSCOPE</span></div><p className="chart-caption">Three-axis synthetic angular velocity · degrees / second</p><Plot data={inertial} series={[{ key: 'gx', name: 'X' }, { key: 'gy', name: 'Y' }, { key: 'gz', name: 'Z' }]} unit="°/s" /></section>}
            {tab === 'Experiment details' && data && <section className="panel details"><h2>Verified anti-aliased downsampling</h2><p>{data.config.sample_rate_hz.toLocaleString()} → 1,000 Hz · {data.dsp.decimation.fir_taps} FIR taps · passband ripple {data.dsp.decimation.passband_ripple_db.toFixed(4)} dB · stopband attenuation {data.dsp.decimation.stopband_attenuation_db.toFixed(2)} dB. Passband ends at 400 Hz; stopband begins at 500 Hz. Full offline, delay-compensated output is included in exports.</p></section>}
            <section className="panel features"><div className="panel-heading"><div><Settings2 size={16} /><h2>{circuit ? 'Anti-aliasing checks' : 'Extracted features'}</h2></div><span className="tag">{circuit ? 'LP ONLY' : 'CURRENT TRIAL'}</span></div>{circuit ? <div className="table-wrap"><table><thead><tr><th>Frequency</th><th>Attenuation</th><th>Alias at ADC rate</th></tr></thead><tbody>{data?.analog.lp_checks.map(v => <tr key={v.frequency_hz}><td>{v.frequency_hz} Hz</td><td>{v.attenuation_db.toFixed(2)} dB</td><td>{v.alias_hz} Hz</td></tr>)}</tbody></table></div> : <div className="feature-grid">{[['Mean absolute value', features ? `${(features.mav_v * 1000).toFixed(3)} mV` : '—'], ['Waveform length', features ? `${(features.waveform_length_v * 1000).toFixed(2)} mV` : '—'], ['Mean frequency', features ? `${features.mean_frequency_hz.toFixed(1)} Hz` : '—'], ['Median frequency', features ? `${features.median_frequency_hz.toFixed(1)} Hz` : '—']].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>}</section>
            {tab === 'Experiment details' && <section className="panel details"><h2>Reproducible by design</h2><p>EMG / IMU / PPG share a trial origin at t = 0 with rates {data?.config.sample_rate_hz ?? 4000} / 200 / 100 Hz. Each running update is a new seeded trial, not a continuous hardware stream. Export preserves every sample and configuration.</p><p>Gesture selection controls the synthetic scenario. Machine learning provides separately trained predictions and trial-grouped synthetic benchmarks.</p>{data?.warnings.map(w => <p key={w}>{w}</p>)}<p>Revised report scope: Uno + BioAmp + MPU-6050. Custom-AFE/SPICE results are educational; live acquisition and recording are planned. No measured force, absolute yaw, oxygen saturation or clinical claims.</p></section>}
          </div>
          <aside className="controls panel"><div className="panel-heading"><div><Settings2 size={17} /><h2>Simulation controls</h2></div></div><div className="controls-body">
            <p className="control-subtitle">Configure your experiment</p>
            <label className="field">Gesture scenario<select value={config.gesture} onChange={e => change('gesture', e.target.value)}>{['Rest', 'Grip', 'Wrist flexion', 'Wrist extension', 'Forearm rotation'].map(s => <option key={s}>{s}</option>)}</select></label>
            <Range label="Contraction intensity" value={config.intensity} min={0} max={1} step={0.05} unit="" onChange={v => change('intensity', v)} />
            <Range label="Mains interference" value={config.mains_mv} min={0} max={2} step={0.05} unit=" mV" onChange={v => change('mains_mv', v)} />
            <div className="control-divider" /><p className="control-group">THEORETICAL CUSTOM AFE</p>
            <div className="fixed-value"><span>INA826 first-stage gain</span><strong>10×</strong></div>
            <Range label="Post-amplifier gain" value={config.post_gain} min={1} max={100} unit="×" onChange={v => change('post_gain', v)} />
            <Range label="High-pass cutoff" value={config.highpass_hz} min={5} max={100} unit=" Hz" onChange={v => change('highpass_hz', v)} />
            <Range label="Low-pass cutoff" value={config.lowpass_hz} min={150} max={700} step={10} unit=" Hz" onChange={v => change('lowpass_hz', v)} />
            <label className="switch-row"><span>50 Hz notch filter<small>Q = 30 · optional rejection</small></span><input type="checkbox" role="switch" checked={config.notch} onChange={e => change('notch', e.target.checked)} /><span className="switch-track" /></label>
            <div className="control-divider" /><p className="control-group">SIMULATED ACQUISITION</p>
            <label className="field">Sampling rate<select value={config.sample_rate_hz} onChange={e => change('sample_rate_hz', Number(e.target.value))}>{[2000, 4000, 8000].map(n => <option value={n} key={n}>{n.toLocaleString()} Hz</option>)}</select></label>
            <label className="field">Trial duration<select value={config.duration_s} onChange={e => change('duration_s', Number(e.target.value))}>{[2, 5, 10].map(n => <option value={n} key={n}>{n} seconds</option>)}</select></label>
            <details><summary>Signal conditions</summary><Range label="Electrode offset" value={config.offset_mv} min={-50} max={50} unit=" mV" onChange={v => change('offset_mv', v)} /><Range label="Noise" value={config.noise_mv} min={0} max={0.5} step={0.01} unit=" mV" onChange={v => change('noise_mv', v)} /><Range label="Fatigue blend" value={config.fatigue} min={0} max={1} step={0.05} unit="" onChange={v => change('fatigue', v)} /><Range label="Pulse rate" value={config.heart_rate_bpm} min={40} max={180} unit=" bpm" onChange={v => change('heart_rate_bpm', v)} /></details>
            <details><summary>Motion & pulse settings</summary>
              <label className="field">Motion scenario<select aria-label="Motion scenario" value={config.motion_scenario} onChange={e => change('motion_scenario', e.target.value)}>{['Gesture', 'Stationary', 'Repetitive', 'Tremor', 'Sudden motion'].map(s => <option key={s}>{s}</option>)}</select></label>
              <Range label="Tremor frequency" value={config.tremor_hz} min={3} max={12} step={0.5} unit=" Hz" onChange={v => change('tremor_hz', v)} />
              <Range label="Motion scale" value={config.motion_scale} min={0} max={2} step={0.1} unit="×" onChange={v => change('motion_scale', v)} />
              <label className="field">PPG scenario<select aria-label="PPG scenario" value={config.ppg_scenario} onChange={e => change('ppg_scenario', e.target.value)}>{['Clean', 'Motion artifact', 'Low perfusion', 'Dropout'].map(s => <option key={s}>{s}</option>)}</select></label>
              <Range label="PPG noise" value={config.ppg_noise_au} min={0} max={0.5} step={0.005} unit=" a.u." onChange={v => change('ppg_noise_au', v)} />
              <Range label="PPG motion artifact" value={config.ppg_motion_au} min={0} max={2} step={0.1} unit=" a.u." onChange={v => change('ppg_motion_au', v)} />
            </details>
            <details><summary>Circuit assumptions</summary><Range label="Resistor tolerance" value={config.resistor_tolerance_pct} min={0} max={5} step={0.5} unit="%" onChange={v => change('resistor_tolerance_pct', v)} /><Range label="Capacitor tolerance" value={config.capacitor_tolerance_pct} min={0} max={10} step={0.5} unit="%" onChange={v => change('capacitor_tolerance_pct', v)} /><Range label="Electrode resistance per leg" value={config.electrode_resistance_ohm} min={0} max={100000} step={1000} unit=" Ω" onChange={v => change('electrode_resistance_ohm', v)} /><Range label="Circuit temperature" value={config.temperature_c} min={0} max={50} unit=" °C" onChange={v => change('temperature_c', v)} /></details>
            <button className="button primary" onClick={() => setRunning(r => !r)}>{running ? <Pause size={16} /> : <Play size={16} />}{running ? 'Pause simulation' : 'Start simulation'}</button><button className="button reset" onClick={resetSimulation}><RotateCcw size={14} />Reset experiment</button>
            <p className="controls-note">Changes recompute a trial. Start advances seeds; pause holds the current trial.</p>
          </div></aside>
        </div>
        </>}<footer><span><span className="led" /> Analytical model · local computation</span><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">Explore the API <ArrowUpRight size={13} /></a></footer>
      </main>
    </div>
  </div>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
