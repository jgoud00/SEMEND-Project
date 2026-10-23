import project from '../../project.json'

export function ProjectOverview() {
  return <div className="project-overview">
    <section className="panel details"><h2>Available-hardware project</h2>
      <p>{project.scope}. The current application implements the report's educational simulation laboratory. Live sensor acquisition, session recording and replay are planned.</p>
      <a className="button" href="/api/project/report" target="_blank" rel="noreferrer">Open revised project report</a>
      <h3>Confirmed inventory</h3>
      <div className="table-wrap"><table><thead><tr><th>Hardware</th><th>Role</th><th>Verification status</th></tr></thead><tbody>{project.hardware.map(item => <tr key={item.name}><th>{item.name}</th><td>{item.role}</td><td>{item.status}</td></tr>)}</tbody></table></div>
    </section>
    <section className="panel details"><h2>Implementation status</h2>
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
