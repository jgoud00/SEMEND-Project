import project from '../../project.json'
import { Activity, ArrowUpRight, Cable, CircuitBoard, Move3D, ShieldCheck } from 'lucide-react'

export function ProjectOverview() {
  return <div className="project-overview">
    <section className="project-intro">
      <div className="intro-copy"><span className="scope-label"><Activity size={16} /> Grip activity & stability</span><h2>A closer look at<br />every contraction.</h2><p>Explore the relationship between muscle activity and movement. One workspace for the hardware plan, signal experiments and synthetic benchmarks.</p><a className="button report-link" href="/api/project/report" target="_blank" rel="noreferrer">Open revised project report<ArrowUpRight size={16} /></a><span className="intro-footnote"><ShieldCheck size={14} /> Educational prototype · Human validation not established</span></div>
      <div className="signal-map" role="group" aria-label="Planned acquisition path: electrodes through BioAmp EXG Pill to Arduino Uno, with MPU-6050 motion input">
        <div className="map-heading"><span>Planned acquisition path</span><span className="tag">Hardware concept</span></div>
        <div className="map-source"><Activity size={26} /><div><strong>Surface electrodes</strong><span>Muscle electrical activity</span></div></div>
        <div className="map-connection"><span>Analog EMG</span></div>
        <div className="map-node"><CircuitBoard size={22} /><div><strong>BioAmp EXG Pill</strong><span>Signal conditioning</span></div></div>
        <div className="map-connection"><span>Analog input</span></div>
        <div className="map-node map-processor"><Cable size={22} /><div><strong>Arduino Uno</strong><span>Acquisition & serial transport</span></div><span className="map-port">USB</span></div>
        <div className="map-motion"><Move3D size={17} /><span>MPU-6050 <small>Motion input via I²C</small></span></div>
        <p>Live acquisition is planned. The laboratory currently uses generated signals.</p>
      </div>
    </section>
    <section className="panel details inventory-panel"><div className="overview-heading"><div><span className="section-context">Hardware foundation</span><h2>Available-hardware project</h2></div><span className="tag">{project.hardware.length} components</span></div>
      <p>{project.scope}. The current application implements the report's educational simulation laboratory. Live sensor acquisition, session recording and replay are planned.</p>
      <h3>Confirmed inventory</h3>
      <div className="table-wrap"><table><thead><tr><th>Hardware</th><th>Role</th><th>Verification status</th></tr></thead><tbody>{project.hardware.map(item => <tr key={item.name}><th>{item.name}</th><td>{item.role}</td><td>{item.status}</td></tr>)}</tbody></table></div>
    </section>
    <section className="panel details status-panel"><span className="section-context">Development progress</span><h2>Implementation status</h2>
      <div className="table-wrap"><table><thead><tr><th>Capability</th><th>Status</th></tr></thead><tbody>{Object.entries(project.capabilities).map(([name, status]) => <tr key={name}><th>{name.replaceAll('_', ' ')}</th><td>{status}</td></tr>)}</tbody></table></div>
      <p>No live measurements are available. No working optical sensor or force sensor is part of the confirmed setup. Measured heart rate, SpO₂, blood flow, grip force and absolute yaw remain unavailable.</p>
      <p>{project.acquisition.note}</p>
    </section>
    <section className="panel details"><h2>35-second grip task</h2><p>Planned comfortable-hold protocol. The first hold may establish a declared reference; holds two and three provide within-session comparisons. This table is a protocol reference, not a running acquisition or a recorded session.</p>
      <ol className="task-protocol">{project.task_protocol.map(phase => <li key={phase.start_s}><strong>{phase.start_s}–{phase.end_s} s</strong><span>{phase.phase}</span></li>)}</ol>
    </section>
    <section className="panel details"><h2>Educational simulation boundary</h2><p>{project.educational_model}</p><p>Use the laboratory tabs for generated signals, analytical circuits and synthetic ML benchmarks. All rates, voltages and performance values there describe the model. They do not establish the physical Uno/BioAmp configuration or human performance.</p></section>
  </div>
}
