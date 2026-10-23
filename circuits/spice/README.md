# Generated circuit checks

## Revised report scope

These netlists belong to the educational custom-AFE study retained in the revised report. They are not a verified BioAmp schematic, wiring plan or physical prototype measurement.

See [report alignment](../../docs/report-alignment.md) for status and hardware boundaries.

The actual executed netlists and numerical files are in `results/spice/`. Run `scripts/engineering_experiment.py`, or the dashboard's **Run SPICE verification** control. The generator is `backend/app/spice.py`.

- `ideal.cir`: actual Sallen-Key resistor/capacitor network with ideal unity buffers, scalar INA/post gains, AC, transient and resistor-noise analyses. No notch or device rail behavior.
- `devices.cir`: separate TI INA826 and OPA2376 macro-model gain checks plus OPA DC sweep, 3.3 V supply and 1.65 V reference.
- `verification.json`: requested configuration, solver banner, acceptance checks and limits. The current result is partial because the INA model fails the numerical gate.

These netlists are ngspice-oriented. Ideal E-source/R/C sections are portable in principle, but the `.control`/`wrdata` commands are ngspice-specific; LTspice equivalence is not claimed. Do not connect this simulated circuit to a person.
