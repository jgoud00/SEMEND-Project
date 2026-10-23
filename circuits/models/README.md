# Local manufacturer models

## Revised report scope

These TI models support the original educational custom-AFE analysis. They are not BioAmp manufacturer models and do not specify the fixed Uno/BioAmp hardware. No additional amplifier purchase is required.

See [report alignment](../../docs/report-alignment.md) for status and hardware boundaries.

Run `scripts/prepare_spice.py` from the project root. It retrieves public TI archives from `https://www.ti.com/lit/zip/sbomc48` (INA826) and `https://www.ti.com/lit/zip/sbom309` (OPAx376), preserves originals and copyright notices, and records source/model SHA-256 hashes in `sources.json`.

Binary archives and model libraries are ignored by Git. The original licenses/notices govern their use; this repository does not relicense TI's files. Copies installed locally are for the requested simulation. Adaptations normalize encoding/line endings and INA diode AREA syntax. They are documented and hashed, not concealed as untouched vendor files.

OPA2376 passes the isolated gain check in the current ngspice run. INA826 does not; use a supported TI simulator to resolve compatibility. See `docs/engineering-analysis.md` and the actual solver logs under `results/spice/`.
