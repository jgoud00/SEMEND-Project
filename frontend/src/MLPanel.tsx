import { useEffect, useState } from 'react'
import { BrainCircuit, Play } from 'lucide-react'
import { type Config } from './api'

type ModelMetric = { model: string; modality: string; accuracy: number; balanced_accuracy: number; f1_macro: number; precision_macro: number; recall_macro: number; brier_multiclass: number; accuracy_ci95_trial_bootstrap: number[]; confusion_matrix: number[][] }
type Benchmark = { source: string; seed: number; trials: number; windows: number; labels: string[]; records: ModelMetric[]; limitations: string }
type Prediction = { model: string; scenario: string; seed: number; predicted_gesture: string; class_probabilities: Record<string, number>; domain_warning: string | null }
const names = ['Logistic Regression', 'SVM', 'Decision Tree', 'Random Forest', 'Gradient Boosting']

export function MLPanel({ config }: { config: Config }) {
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null)
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [model, setModel] = useState('Random Forest')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    void fetch('/api/ml/metrics').then(async r => { if (r.ok && active) setBenchmark(await r.json()) }).catch(() => {})
    return () => { active = false }
  }, [])
  async function run(mode: 'train' | 'predict') {
    setBusy(mode)
    setError('')
    try {
      const r = await fetch(`/api/ml/${mode}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(mode === 'train' ? { seed: 1000, trials_per_class: 6 } : { config, model }) })
      if (!r.ok) throw new Error(`ML request failed (${r.status}). Train in this server session before prediction.`)
      if (mode === 'train') { setBenchmark(await r.json()); setPrediction(null) }
      else setPrediction(await r.json())
    } catch (e) { setError(e instanceof Error ? e.message : 'ML request failed') }
    finally { setBusy('') }
  }
  const selected = benchmark?.records.find(r => r.model === model && r.modality === 'Fusion')
  return <section className="panel ml-panel">
    <div className="panel-heading"><div><BrainCircuit size={18} /><h2>Gesture recognition benchmark</h2></div><span className="tag">SYNTHETIC DATA</span></div>
    <div className="ml-body"><p>Educational synthetic benchmark, not live grip or health prediction. Five classifiers · EMG, IMU and fusion · 3-fold trial-grouped validation. Overlapping windows stay in the same fold. Training runs locally and can take a few minutes.</p>
      <div className="ml-actions"><label className="field">Model<select aria-label="Model" disabled={!!busy} value={model} onChange={e => { setModel(e.target.value); setPrediction(null) }}>{names.map(n => <option key={n}>{n}</option>)}</select></label><button className="button" disabled={!!busy} onClick={() => void run('train')}><BrainCircuit size={15} />{busy === 'train' ? 'Training…' : 'Train benchmarks'}</button><button className="button" disabled={!benchmark || !!busy} onClick={() => void run('predict')}><Play size={15} />{busy === 'predict' ? 'Predicting…' : 'Predict trial'}</button></div>
      {error && <div className="error" role="alert">{error}</div>}
      {!benchmark ? <p>No benchmarks in this server session. Train to calculate synthetic benchmark results. No prefilled accuracy is shown.</p> : <>
        <p>{benchmark.trials} independent trials · {benchmark.windows} overlapping windows · seed {benchmark.seed}</p>
        <div className="table-wrap"><table><thead><tr><th>Model</th><th>Modality</th><th>Accuracy</th><th>Macro-F1</th></tr></thead><tbody>{benchmark.records.map(r => <tr key={r.model+r.modality}><td>{r.model}</td><td>{r.modality}</td><td>{(r.accuracy*100).toFixed(1)}%</td><td><div className="metric-bar"><span style={{ width: `${r.f1_macro*100}%` }} /></div>{r.f1_macro.toFixed(3)}</td></tr>)}</tbody></table></div>
        {selected && <><h3>{model} · fusion evaluation</h3><p>Balanced accuracy {selected.balanced_accuracy.toFixed(3)} · Precision {selected.precision_macro.toFixed(3)} · Recall {selected.recall_macro.toFixed(3)} · Brier {selected.brier_multiclass.toFixed(3)}</p><p>Accuracy 95% trial-bootstrap CI: {selected.accuracy_ci95_trial_bootstrap.map(n => `${(n*100).toFixed(1)}%`).join(' – ')}</p><h3>Confusion matrix</h3><p>Rows: true class. Columns: predicted class. Counts are windows.</p><div className="table-wrap"><table className="confusion"><thead><tr><th>True / predicted</th>{benchmark.labels.map(l => <th key={l}>{l}</th>)}</tr></thead><tbody>{selected.confusion_matrix.map((row, i) => <tr key={benchmark.labels[i]}><th>{benchmark.labels[i]}</th>{row.map((count, j) => <td style={{ background: `rgba(102,228,192,${count/Math.max(1, ...row)*0.2})` }} key={j}>{count}</td>)}</tr>)}</tbody></table></div></>}
        <p>{benchmark.limitations}</p>
      </>}
      {prediction && <div className="prediction"><h3>Predicted: {prediction.predicted_gesture}</h3><p>{prediction.domain_warning} Scenario: {prediction.scenario} · seed {prediction.seed}. Mean probabilities across windows; no human validation.</p>{Object.entries(prediction.class_probabilities).map(([label, p]) => <div className="probability" key={label}><span>{label}</span><div className="metric-bar"><span style={{ width: `${p*100}%` }} /></div><strong>{(p*100).toFixed(1)}%</strong></div>)}</div>}
    </div>
  </section>
}
