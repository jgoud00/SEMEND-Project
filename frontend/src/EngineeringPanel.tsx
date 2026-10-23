import { useState } from 'react'
import { CircuitBoard } from 'lucide-react'
import { type Analysis } from './api'

type SpiceCheck = { status: string; reason?: string; max_magnitude_error_db?: number; noise_relative_error?: number; ina_gain_100hz?: number; post_gain_100hz?: number; ina_valid?: boolean; post_valid?: boolean }
type SpiceReport = { status: string; reason?: string; checks?: Record<string, SpiceCheck>; limitations?: string }

export function EngineeringPanel({ data }: { data: Analysis }) {
  const [report, setReport] = useState<SpiceReport | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { noise_budget: noise, tolerances: tolerance } = data.analog
  async function runSpice() {
    setBusy(true)
    setError('')
    try {
      const response = await fetch('/api/analog/spice', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data.config) })
      if (!response.ok) throw new Error(`SPICE request failed (${response.status})`)
      setReport(await response.json())
    } catch (e) { setError(e instanceof Error ? e.message : 'SPICE request failed') }
    finally { setBusy(false) }
  }
  return <section className="panel details"><div className="panel-heading"><div><CircuitBoard size={17} /><h2>Circuit engineering</h2></div><span className="tag">ANALYTICAL ESTIMATES</span></div>
    <h3>20–450 Hz noise estimate</h3><p>Output RMS {(noise.output_rms_v*1e6).toFixed(2)} µV · nominal-gain referred {(noise.nominal_gain_referred_rms_v*1e6).toFixed(3)} µV. INA white noise at configured gain: {noise.ina_white_rti_nv_sqrt_hz.toFixed(2)} nV/√Hz.</p>
    <p>{noise.exclusions}</p><div className="table-wrap"><table><thead><tr><th>Noise source</th><th>Output RMS / µV</th></tr></thead><tbody>{noise.contributions.map(v => <tr key={v.source}><td>{v.source}</td><td>{(v.output_rms_v*1e6).toFixed(3)}</td></tr>)}</tbody></table></div>
    <h3>Component tolerance sweep</h3><p>{tolerance.trials} seeded draws · R ±{tolerance.resistor_tolerance_pct}% · C ±{tolerance.capacitor_tolerance_pct}% · gain range {tolerance.total_gain_min_max.map(n => n.toFixed(2)).join(' – ')}×. Notch omitted from this sweep.</p>
    <div className="table-wrap"><table><thead><tr><th>Stage</th><th>Natural frequency range / Hz</th><th>Q range</th></tr></thead><tbody>{Object.entries(tolerance.stages).map(([name, p]) => <tr key={name}><td>{name}</td><td>{p.frequency_hz_min_max.map(n => n.toFixed(2)).join(' – ')}</td><td>{p.q_min_max.map(n => n.toFixed(3)).join(' – ')}</td></tr>)}</tbody></table></div><p>{tolerance.limitations}</p>
    <h3>SPICE verification</h3><p>Run the candidate R/C filter circuit and separate TI amplifier checks with the local solver. Results below are from the last requested SPICE run; they are not recomputed by other controls.</p><button className="button" disabled={busy} onClick={() => void runSpice()}><CircuitBoard size={16} />{busy ? 'Running SPICE…' : 'Run SPICE verification'}</button>
    {error && <p role="alert">{error}</p>}{report && <div data-testid="spice-report"><p>SPICE status: <strong>{report.status}</strong> {report.reason}</p>{report.checks && Object.entries(report.checks).map(([name, check]) => <p key={name}>{name}: {check.status}. {check.reason}{check.max_magnitude_error_db !== undefined && ` Maximum AC magnitude error ${check.max_magnitude_error_db.toExponential(2)} dB.`}{check.ina_gain_100hz !== undefined && ` INA gain ${check.ina_gain_100hz.toPrecision(4)}× (${check.ina_valid ? 'accepted' : 'rejected'}); OPA gain ${check.post_gain_100hz?.toPrecision(4)}× (${check.post_valid ? 'accepted' : 'rejected'}).`}</p>)}<p>{report.limitations}</p></div>}
  </section>
}
