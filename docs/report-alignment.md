# Alignment to the revised project report

The [28-page revised report](../output/pdf/ForearmSense_AI_AECD_PBL_REVISED_UNO.pdf), in the original academic template, defines the scope. The [editable manuscript](ForearmSense_AI_AECD_PBL_REVISED_UNO.md) and [hardware mapping](fixed-hardware-project-map.md) explain it. Original report files in Downloads are preserved.

## Runtime contract

`project.json` is shared by the backend and frontend. It contains the confirmed Uno/BioAmp/MPU-6050/gripper inventory, unknown ADC configuration, unavailable physical measurements, planned capabilities and seven contiguous phases of the 35-second task. The API serves it at `/api/project`; `/api/project/report` serves the PDF.

The default dashboard view displays this scope. Simulation tabs retain the seeded analytical laboratory. Trial responses/exports carry synthetic provenance and the model-versus-hardware distinction. No live connection, recording or replay control is presented as functional. The report already marks these capabilities as planned; this alignment does not invent a firmware contract or change that status.

## Directory traceability

| Area | Role under the report |
| --- | --- |
| `backend/app/`, `frontend/src/` | Implemented educational simulator and report-aligned project overview; physical acquisition remains planned |
| `backend/tests/`, `frontend/tests/` | Software and numerical checks; never physical calibration evidence |
| `scripts/` | Launch and reproduce educational synthetic/engineering experiments |
| `circuits/` | Original theoretical AFE and SPICE studies; not BioAmp schematics or physical wiring |
| `datasets/synthetic/` | Generated datasets; not participant recordings |
| `results/` | Preserved historical generated metrics, plots, model artifacts and verification outputs |
| `docs/` | Revised manuscript, design mapping, implementation documentation and dated verification history |
| `output/pdf/` | Revised academic report, retaining the original template |
| `tmp/` | Ignored local report generators, downloaded fonts and page previews; not a submission deliverable |
| `.venv/`, `.tools/`, `frontend/node_modules/`, build/cache/log files | Development infrastructure; ignored or generated, not report evidence |
| `recordings/` | Ignored reserved location for future private sensor sessions; no recorder is implemented |

Saved historical figures can show the earlier dashboard. Their old labels do not establish current hardware capabilities; they remain archived evidence rather than being overwritten to resemble new measurements.

## Measurements and educational assumptions

- Available hardware has one EMG channel and six-axis inertial sensing; no working optical sensor or force transducer.
- Uno revision, ADC reference/resolution, module gain/bandpass and sample rate remain unverified. Unknown physical measurements are null in the contract.
- Custom INA826/OPA2376 gain, 12-bit/3.3 V conversion, 2/4/8 kHz sampling, generated PPG and synthetic gesture benchmarks are educational model assumptions.
- Approximately 250 Hz legacy raw output cannot preserve a 450 Hz EMG band. The simulator's spectral and decimation routines do not establish physical bandwidth.
- Task timing, activation consistency and low-frequency movement analysis are the planned live outcomes. No medical score, calibrated force, pulse measurement, absolute heading or physiological fatigue diagnosis is established.

## Next work requiring actual hardware evidence

Inspect the board revision, module configuration and existing sketch; capture the real serial format. Then implement validated ingestion, calibration, the task workflow, safe session persistence and replay. Do not guess firmware fields, wiring, rate or calibration from contradictory historical guides. The simulation remains usable without hardware.
