# Expanded scenarios and circuit engineering

All outputs here are synthetic signals or model calculations. The revised project report is still unavailable. New engineering assumptions are explicit and do not establish a safe wearable circuit.

## Reproduce

From the project root in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_spice.py
.\.venv\Scripts\python.exe scripts\engineering_experiment.py
```

The preparation script downloads the official portable Windows ngspice-41 Fusion360 update and public TI model archives. It does not modify PATH or install system services. The current stable download links returned HTTP 404 during implementation, so version 41 is deliberately used and recorded. Originals, adapted model hashes and source URLs are recorded in `circuits/models/sources.json`. Downloaded binaries/libraries are ignored by Git; their notices remain intact. On another platform, install ngspice separately or set `NGSPICE_EXE`; its code-model initialization must work on that installation.

The experiment writes `results/engineering/{summary,analog,scenarios}.json`, two scenario CSVs, five engineering plots and `results/spice/` netlists, numerical AC/transient/noise/DC arrays, logs and `verification.json`. Earlier milestone CSVs and figures are preserved.

## Motion scenarios

`motion_scenario` selects the original Gesture trajectory, Stationary, Repetitive, Tremor or Sudden motion. The original Gesture default and seed remain unchanged. `motion_scale` scales trajectory amplitude and dynamic acceleration; `tremor_hz` controls a small 3–12 Hz rotation. Sudden motion uses a short Gaussian rotation pulse and an explicit acceleration impulse. Bias, white noise and drift remain in all scenarios, including stationary.

The tremor estimate is the strongest 3–12 Hz gyro-Y spectral peak for the selected Tremor scenario; it is not a diagnostic detector. Frequency resolution is 1/trial duration. The generated default tremor example produces 6.0 Hz. A six-axis IMU still cannot provide absolute yaw. Euler-angle derivatives approximate gyro axes; full rigid-body cross-axis kinematics are not modeled. Sudden linear acceleration corrupts accelerometer-derived pitch/roll, so the complementary filter is not ground-truth orientation.

## PPG scenarios and quality gate

`ppg_scenario` selects Clean, Motion artifact, Low perfusion or Dropout. Adjustable noise and motion amplitudes use arbitrary units. Motion adds 1.7/3.2 Hz interference; low perfusion reduces pulse amplitude tenfold; dropout removes the pulse over the middle 30% of the trial while retaining baseline and noise. The response preserves clean pulse reference, raw signal, detected peaks and dropout mask.

Quality is a **synthetic oracle**: known injected noise/artifact power is compared to known pulse power. This is not a clinical signal-quality algorithm and could not be computed this way from unknown sensor data. Heart rate is withheld unless the injected-component SNR is at least 10 dB, no dropout is present, duration is at least 4 seconds and at least three peaks are detected. Conservative fixed peak prominence also withholds weak pulses. Peak marks may still be shown on poor data; they are not accepted physiological beats.

In the saved 10-second, 90 bpm examples, Clean estimates 90.226 bpm; Motion artifact, Low perfusion and Dropout return null. The default 2-second trial now deliberately withholds HR. Select 5 or 10 seconds to obtain a clean-signal estimate. No SpO₂ is produced.

## Candidate circuit topology

The primary waveform chain retains its previous ideal Butterworth transfer functions and ZOH discretization, so the original seed-42 EMG remains reproducible. A separate, component-defined candidate realizes the same continuous-time HP/LP responses using three unity-buffer Sallen-Key sections. These are calculated component values, not rounded preferred-series BOM selections.

For each section, the buffer output follows node b. HP: input → C1 → node a → C2 → node b; R1 connects a to buffer output; R2 connects b to ground (AC reference). LP: input → R1 → a → R2 → b; C1 connects a to output; C2 connects b to ground. A real single-supply circuit needs correct 1.65 V biasing and reference buffering; the SPICE filter test is an AC-ground, ideal-buffer candidate.

Define P = R1 R2 C1 C2. Both denominators are P s² + D s + 1. HP has D = R1(C1+C2), numerator P s²; LP has D = C2(R1+R2), numerator 1. Natural frequency is 1/(2π√P), Q = √P/D. HP Q = 1/√2. The two LP Q values are 1/√(2+√2) and 1/√(2−√2). Their product reproduces the fourth-order Butterworth low-pass. These relationships are used for both numerical analysis and generated netlists, and tested against the original transfer functions.

## Noise estimate

The budget integrates uncorrelated white-noise PSD from 20 to 450 Hz. Source transfer weights include their actual position in the chain. Sallen-Key resistor noise and buffer voltage/current noise are derived from the two-node admittance matrix, including buffer feedback. Johnson noise uses 4 k T R (or current form 4 k T/R). Post feedback resistor noise uses Rf parallel Rg and noise gain. Electrode resistance is an assumed real resistance per leg, not a measured impedance.

The [TI INA826 datasheet](https://www.ti.com/lit/ds/symlink/ina826.pdf) specifies separate typical input-stage and output-stage noise densities. Input-referred voltage density is sqrt(eNI² + (eNO/G)²), using 18 and 110 nV/√Hz. Input current noise is 100 fA/√Hz. The external gain resistor is included separately. The [TI OPAx376 datasheet](https://www.ti.com/lit/ds/symlink/opa2376.pdf) gives typical 7.5 nV/√Hz voltage and 2 fA/√Hz current densities. These typical point specifications are extrapolated as white sources in the analysis, not guaranteed at every frequency or at 3.3 V.

Default calculated output RMS is 294.170 µV; dividing by nominal gain gives 0.588448 µV. This nominal-gain referral is not an inverse-filter correction near the notch/cutoffs. Sources combine by quadrature, not arithmetic summation. Noise is **not injected into waveform samples**; the generator's existing `noise_mv` is a separate illustrative contamination control.

This is a band-limited estimate, not a complete physical noise budget: 1/f, reference/supply, PCB, capacitor dielectric and physical notch-circuit noise are excluded. Quantization and out-of-band noise aliasing are also separate. The notch is noiseless in the analytical budget because no physical notch topology has been selected.

The temperature control changes Johnson-noise temperature; semiconductor noise densities are held at their typical point values rather than claiming a validated temperature dependence.

## Component tolerances

200 seeded independent uniform draws vary each R and C separately. Defaults are R ±1%, C ±5%. INA RG and both post-gain resistors are included; the 49.4 kΩ internal INA resistance is held ideal. Both natural frequencies and Q vary, so mismatch is not reduced to a single cutoff shift. The notch is omitted from this sweep because its physical components are unspecified.

Default sampled nominal-gain range is 487.415–511.784×. The response stores 5th/95th percentiles and per-stage frequency/Q ranges. These are finite Monte Carlo summaries, not worst-case guarantees or production yields. Zero-tolerance behavior and reproducibility are tested. Internal device errors, parasitics, temperature coefficients, finite bandwidth and stability under real loads remain outside the sweep.

## Actual SPICE evidence

The official [ngspice download page](https://ngspice.sourceforge.io/download.html) links the portable version-41 update used here. `POST /api/analog/spice` generates fixed netlists from bounded configuration and executes the local solver with a timeout and a single-run lock. Output files are removed before each run to prevent accepting stale numerical files. A successful process exit is insufficient: numerical checks decide acceptance.

- **Ideal-buffer R/C circuit:** actual AC response matches the analytical component equations within 1.45×10⁻⁷ dB over 401 points. A separate `.tran` run produces the 1 mV pulse response. A `.noise` run compares filter-resistor noise with the independently assembled analytical budget. This is genuine circuit-level SPICE with ideal buffer sources, not manufacturer-model full-chain validation.
- **OPA2376:** the TI macro-model gives approximately 50.001× at 100 Hz for requested gain 50×, with a separate DC input sweep and 10 kΩ load to the reference. Raw output range and linear-region error are retained in `verification.json`. This checks one operating condition, not every load or temperature.
- **INA826:** the public TI PSpice model fails the expected gain-10 check under this ngspice compatibility run (about 0.000938× at 100 Hz), with convergence warnings. It is explicitly rejected. This is a model/solver compatibility result, not evidence that the real INA826 behaves this way. Its common-mode envelope and complete low-voltage operation remain unverified. Reproduce in the vendor-supported TINA-TI/PSpice environment before making a device claim.

Overall SPICE status is therefore **partial**. The dashboard displays the failed device check; tests verify that a zero exit code cannot silently promote it to a passed result. The INA file receives only documented diode AREA syntax and whitespace/encoding adaptations; original archives and notices are retained. No fitted or substituted device model is presented as TI's model.

Acceptance uses a coarse ±5% gain gate and, for OPA, ≤20 mV maximum DC error where the ideal output lies between 0.2 and 3.1 V. The default OPA sweep has about 17.10 mV maximum error in that region and output extremes about 0.0184/3.2848 V. These are macro-model outputs and test thresholds, not precision specifications. The filter-resistor noise comparison is 56.8303 µV analytical versus 56.8303 µV SPICE RMS over the same 20–450 Hz band (relative difference about 5.36×10⁻⁷).

## ML scope

Existing training still uses Gesture/scale=1 trials. New independent motion scenarios are not quietly added to the gesture labels or claimed as validated classes. Inference on these scenarios returns a training-domain warning. Current ML benchmark files remain benchmarks of the original programmed gesture scenarios.
