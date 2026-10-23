# Architecture

The browser sends a bounded configuration through Vite's same-origin proxy to FastAPI. `schemas.py` validates at that trust boundary. `simulation.py` owns deterministic seeded EMG, IMU and PPG synthesis. `analog.py` conditions the EMG with continuous-time ideal filter transfer functions sampled as state-space systems. `dsp.py` analyzes the quantized, input-referred signal. `main.py` assembles numerical arrays, sample counts, provenance and warnings.

`frontend/src/api.ts` defines the frontend contract, performs requests and downloads the exact completed response. `main.tsx` owns configuration and trial state; `MLPanel.tsx` handles training, model choice, prediction and benchmark displays. AbortController and generation checks reject stale responses after pause, reset and parameter changes. Each running update advances the seed. State lives in memory; no database or cloud services are involved.

Both servers bind to 127.0.0.1. Requests are capped at 10 s and sample rates 2/4/8 kHz. A common trial duration and t = 0 align independently synthesized modalities: EMG configurable, IMU 200 Hz, PPG 100 Hz. No interpolation or claim of physical coupling is made.

`ml.py` builds independent trials and aligns 200 ms EMG/IMU feature windows by time. It uses training-only preprocessing, outer trial-grouped folds, nested grouped SVM calibration and trial-bootstrap accuracy intervals. A nonblocking training lock prevents concurrent API fits. Completed models and metrics replace the in-memory snapshot only after training/artifact writing succeeds. Predictions average fusion-model window probabilities. Saved joblib files are generated locally and never automatically loaded; train in the current session. Use a single Uvicorn worker for this local application.

Scope touched: new Python application, schemas, tests, frontend types/network/chart/state layers, dependency manifests and locks, launcher, experiment/training/report scripts, sample artifacts and documentation. The directory was empty; no existing files or callers were replaced. No cloud credentials or user data are present.

Live display is repeatable batches over REST. A WebSocket is unnecessary for this milestone. Errors are visible and stop the running loop, while the previous completed trial remains available with its original configuration in exports.

The engineering expansion adds `engineering.py` for candidate R/C topology, source-weighted in-band noise and deterministic tolerance sweeps; these results are included in analog analysis and exports but are not injected into signal waveforms. `spice.py` independently generates fixed numerical netlists and runs a local solver with timeout/locking and explicit numerical acceptance gates. `EngineeringPanel.tsx` renders estimates and separate SPICE results. The new scenarios use the existing bounded configuration. New motion modes are not silently included in ML training; inference flags that distribution shift.

Browser QA runs its own backend/frontend on 18000/15173 with a test-specific proxy target. Normal app ports remain 8000/5173. This prevents false failures or successes from reusing an old running backend. The launcher still refuses occupied normal ports.
