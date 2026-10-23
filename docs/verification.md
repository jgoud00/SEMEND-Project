# Verification record

Current scope: Uno/BioAmp/MPU-6050 inventory with educational simulation implemented; live acquisition, recording and replay planned. The dated records below describe software/simulation checks at their respective milestones, not physical hardware validation. See [report alignment](report-alignment.md).


## Report alignment - 2026-10-23

Aligned the default dashboard, shared project contract, API health/project metadata, trial exports and documentation with the revised report: Arduino Uno, one BioAmp EXG Pill, MPU-6050 and gripper. The original 28-page PDF and pixel-identical cover remain preserved. Live acquisition, recording, replay and calibration remain planned/unverified.

**62 backend tests passed**, including the shared inventory/unknown-measurement contract, contiguous 35-second protocol, simulation provenance and report serving/missing-file behavior. **Production build and ESLint passed.** Six of seven browser cases passed in the final full run; the remaining scenario case used the old pulse-tile selector. After updating it to `SIMULATED PULSE`, that case passed in a targeted rerun, including PPG dropout, tolerance updates and actual SPICE. Thus all seven browser cases have passed against the final application; they were not one uninterrupted seven-pass run. The first run was also interrupted by the final HTML edit causing a development reload.

The report overview mobile-width and source-boundary checks passed. A SHA-256 comparison preserved all 42 existing files under datasets/ and results/ byte-for-byte. Browser artifacts remain isolated from those saved results. Local Markdown links and diff whitespace checks passed. Existing Starlette test-client deprecation and Vite bundle-size advisories remain; no physical hardware testing was performed.


## Ponytail optimization — 2026-10-23

Profiling the default trial identified state-space conditioning as the largest cost and the 200-draw tolerance sweep as the next substantial engineering cost. Conditioning retains its existing numerics. The tolerance sweep now evaluates component draws in NumPy batches while preserving the original seeded draw order. Training and prediction share an EMG/IMU feature-trial path; prediction no longer constructs unused PPG, spectra, decimation and engineering reports. Training reads window timestamps once instead of constructing a pandas row for each exported probability record. No dependencies, model settings or API response fields changed.

Local warm-call timings on this Windows workstation, median of five repetitions; full-analysis/preparation measurements alternate execution order. These measure Python computation, excluding HTTP serialization, browser rendering and model probability evaluation. They are local observations, not latency guarantees.

| Computation | Before | After | Speedup |
| --- | ---: | ---: | ---: |
| Default 200-draw tolerance sweep | 0.3440 s | 0.0295 s | 11.66× |
| Default full analysis | 1.6732 s | 1.4191 s | 1.18× |
| Prediction input preparation | 1.6732 s | 1.3171 s | 1.27× |

Three separate 200-draw sweeps (default, zero tolerances and upper parameter bounds) matched the original seeded gain/stage ranges exactly and response percentiles within `1e-12` absolute/relative tolerance. An independent seed-7, five-trial dataset comparison matched all 95 rows and 25 columns exactly. **60 backend tests passed**, including new scalar-reference comparisons, exact compact/full feature equivalence at 2/4/8 kHz, an API check rejecting unused analysis work, and OOF timestamp/label/trial alignment. The Starlette test-client deprecation warning remains. The local API was restarted and its health check passed.

**Six Chromium browser tests passed** against the updated backend, including real benchmark training, prediction, all controls and actual SPICE. A final SHA-256 check preserved all 42 saved dataset/result files with no additions. Frontend source was unchanged. The conditioning algorithm remains the main compute bottleneck; no hardware validation or INA826 compatibility repair was attempted.

## Audit fixes — 2026-10-23

All five audit findings are fixed: test artifact isolation, report-derived benchmark provenance, complete-run ML publication, parsed transient acceptance and locked model selection during requests.

**53 backend tests passed** (`.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q backend/tests`), including real training and prepared ngspice integration. New fault tests cover model-write/publication failures and malformed transient text, wrong column counts, NaNs, duplicate/reversed time and truncated duration. A seed-7, 60-trial report verifies the exported chart title. After the final exception-handling adjustment, all three artifact/report tests passed again.

**Six Chromium browser tests passed**, including returned seed/trial provenance, a delayed prediction with disabled model selection, real grouped training and real SPICE. Production TypeScript/Vite build and ESLint pass. Existing Starlette deprecation, Vite bundle-size and browser test-duration advisories remain.

Pytest redirects ML/SPICE writes into each test's temporary directory and restores ML process state. Playwright directs backend artifacts, screenshots and downloads into `frontend/test-results/`; its JSON report is `frontend/playwright-report/browser-tests.json`. Tests no longer update the saved experiment reports in `results/metrics/`. A SHA-256 snapshot of all 42 pre-existing files under `datasets/` and `results/` was unchanged after verification, with no added experiment files.

New ML runs live together under `results/ml/runs/run-<id>/`, selected by atomically replaced `results/ml/current.json`. The report writer follows that pointer and supports legacy metrics; existing experiment files remain preserved. See [ML methodology](ml-methodology.md) for publication and interruption behavior. The local API and production preview were restarted; HTTP health and frontend checks passed.

INA826 compatibility remains rejected, so SPICE remains partial where that model fails. These checks do not establish physical hardware or human validation. Earlier records below describe their respective milestones and output paths.

## Current engineering expansion — 2026-10-23

**44 backend tests passed**, including the original signal/DSP/ML checks and 19 new scenario/engineering checks. Added coverage verifies seeded stationary/repetitive/tremor/sudden motion, PPG quality/short-trial gating, component-equivalent transfer functions, quadrature noise summation, zero-tolerance behavior, Q variation, input validation, unavailable solver behavior and actual prepared SPICE integration. Vendor-model preprocessing has a narrow syntax-preservation test. ML inference now tests its expanded-scenario domain warning.

**Five Chromium browser tests passed** on isolated backend/frontend ports 18000/15173. The fifth test changes motion/PPG scenarios and R tolerances through real API requests, observes withheld HR and runs the actual SPICE endpoint. The previous four acquisition/export/mobile/ML tests also pass. An earlier attempt reused old running servers on 8000/5173 and failed against their outdated schema; QA now refuses to reuse servers. Current XML/JSON test reports are in `results/metrics/`.

The new experiment generates scenario CSV/JSON, noise/tolerance calculations and actual SPICE numerical outputs. Default 200-draw gain range: 487.415–511.784×. Band-limited white-noise estimate: 294.170 µV output RMS, 0.588448 µV nominal-gain referred. Generated 6 Hz tremor estimates 6.0 Hz; the 90 bpm clean PPG example estimates 90.226 bpm, with degraded scenarios withholding HR. Quality uses known injected components, not a clinical SQI; default 2-second trials now withhold HR.

Actual ngspice-41 candidate R/C AC response matches the component equations within 1.45×10⁻⁷ dB. Resistor-noise agreement is independently checked below 1% relative error; pulse transient output is saved. Isolated TI OPA2376 gain/DC checks pass. **TI INA826 compatibility fails the expected-gain check**, despite solver exit zero, so overall status is explicitly **partial**. Raw logs, netlists, model source hashes and rejection details are retained. No failed model result is presented as hardware behavior or full device-chain validation.

See [engineering analysis](engineering-analysis.md) for reproduction, equations, assumptions and remaining omissions. The initial record below is preserved as history; the statement that no solver was available describes that earlier milestone only.

Current production TypeScript/Vite build and ESLint pass. The project launcher was used to replace the identified older project servers, and a live request through port 5173 returned the new Tremor/Dropout schema, 6.0 Hz estimate, null HR and 200-draw circuit analysis. The updated app is served at `http://127.0.0.1:5173`. New scenario/tolerance plots and the engineering dashboard screenshot were inspected; test/result artifacts passed final consistency checks. The initial Vite bundle-size advisory and Starlette test-client warning remain.

## Initial milestone record

Verified locally on Windows with Python 3.12.10 and Node.js 24.11.1 on 2026-10-23. Installed versions are in `backend/requirements-lock.txt` and `frontend/package-lock.json`. The starting directory was empty. No revised report was supplied; only the implementation prompt was attached.

## Executed numerical and API checks

Command from `backend`: `..\.venv\Scripts\python.exe -m pytest -q --junitxml=../results/metrics/backend-tests.xml`.

**25 tests passed.** Coverage includes seeded signal count/rate/voltage/reproducibility, mains amplitude, noise and offset behavior, analytical gain/cutoffs/stability, notch rejection, alias frequencies, stage clipping, ADC quantization bounds, known-tone FFT amplitude/frequency, integrated PSD power, zero-signal features, window count, all acquisition rates, nullable unvalidated quantities, valid/invalid API inputs, pulse estimation, stationary orientation and verified decimation with alias-tone rejection. ML checks include known perfect-prediction metrics, trial-disjoint folds, all 15 model/modality evaluations, probability sums, reproducible Logistic Regression fits, feature dimensions, untrained errors and API inference.

One dependency warning remains: the installed Starlette test client deprecates its httpx integration in favor of httpx2. Tests execute successfully; no warning was hidden.

## Frontend checks

Commands from `frontend`: `npm.cmd run lint`, `npm.cmd run build`, `npm.cmd run test:e2e` after `npx.cmd playwright install chromium`.

TypeScript production build and ESLint pass. Vite emits a bundle-size advisory (approximately 619 kB uncompressed JS, largely charting/React); this is not a build failure. npm installation reported zero dependency vulnerabilities at install time. No ongoing security guarantee is implied.

The Chromium browser suite uses the real FastAPI server and Vite proxy. It checks actual rendered raw/filtered paths, exact seed/sample count and calculated RMS, start/advance/pause/reset behavior, JSON download, acquisition configuration reaching the API, analog/multimodal tabs, narrow viewport width and visible backend-failure handling. The ML test runs real training, selects a model, renders confusion metrics and obtains five prediction probabilities.

**All four browser tests passed in the final run (32.9 s).** `scripts/start.ps1 -Production` also built and launched both servers successfully. Live HTTP checks returned backend status `ok`, frontend HTTP 200 and a proxied EMG response with 8,000 synthetic samples. Manual terminal launch commands are documented as an alternative. Desktop, mobile and ML screenshots were generated; the desktop/mobile and ML screenshots were visually inspected.

An initial ML browser run exposed an ambiguous select label. The model selector now has an explicit accessible name. The suite was rerun after the fix. ESLint excludes disposable browser-result directories so concurrent browser cleanup cannot race its scan. Final browser result is stored in `results/metrics/browser-tests.json`.

The session's interactive browser connector exposed no browser surfaces, so browser verification uses the repository's Playwright Chromium suite. Desktop/mobile screenshots were opened and visually inspected as local images. This does not claim interactive testing on every browser or a physical mobile device.

## Generated numerical evidence

`scripts/experiment.py` produced full JSON, CSV and PNG outputs. Seed 42, duration 2 s, 4 kHz: 8,000 EMG samples; input-referred RMS 0.000226251 V; mean frequency 211.736 Hz; median frequency 203.125 Hz; zero first-stage and post-stage clipping events.

The default decimator has 161 taps, measured passband ripple 0.008335 dB through 400 Hz, and measured stopband attenuation 64.56095 dB from 500 Hz on a 65,536-bin grid. A 700 Hz tone is rejected before it could alias to 300 Hz at 1 kHz. Output has 2,000 samples for a 2 s trial. Edge transients remain explicitly disclosed.

`results/ml/metrics.json` and `benchmark-report.md` contain executed seed-1000 results: 30 trials, 570 windows, 15 comparisons. Example out-of-fold accuracy: EMG-only Random Forest 0.350877, fusion Random Forest 0.905263, fusion Gradient Boosting 0.987719. These are programmed synthetic scenarios, not human performance. Same-fold model comparison is not an independent model-selection holdout. CIs resample trials, conditional on the fixed fits.

## Artifacts and review

- `results/metrics/backend-tests.xml`, `browser-tests.json`: executed test reports.
- `results/metrics/trial-seed42.json`, `summary.json`: full trial and numerical summary.
- `datasets/synthetic/`: generated signals, orientation/pulse examples and ML feature dataset.
- `results/ml/`: saved models, grouped metrics, per-window OOF probabilities and benchmark report.
- `results/figures/`: signal-chain, frequency, model-comparison, confusion and dashboard screenshots.

## Verification limits and next work

No physical sensors or people were tested. No ngspice executable was available; no transistor-level/manufacturer-model SPICE results are claimed. The common-mode envelope, protection network, finite op-amp bandwidth/slew, component topology/tolerances and full noise budget remain unverified. No clinical, medical certification, force, absolute-yaw or SpO₂ claims are made.

Expanded tremor/sudden-motion IMU scenarios, PPG motion/quality controls, LMS, FIR/IIR comparison and pole-zero/step plots remain subsequent phases. The present motion generator has stationary/grip/wrist/rotation scenarios with bias/noise/drift; PPG has adjustable rate, harmonics, amplitude variation, baseline drift, peaks and noise. The dashboard's signal-range indicator only reports modeled clipping. UI smoke tests do not establish complete accessibility compliance or cross-browser coverage.
