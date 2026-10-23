# Hardware roadmap

No human-connected experiment is authorized or implemented. A simulation cannot establish electrical safety, calibration or medical-device compliance.

1. Obtain the revised report. Review the implemented Sallen-Key candidate and tolerance assumptions, then complete protection, bias/reference and preferred-series component selection.
2. Check INA826 common-mode/differential/output operating envelope at 3.3 V for every offset scenario. Verify OPA2376 headroom, gain-bandwidth, noise and stability under the actual load.
3. Resolve the downloaded INA826 model's failed gain check in a vendor-supported simulator. The local ngspice candidate filter AC/transient/resistor-noise checks and OPA gain/DC checks are implemented; source hashes and logs are preserved. This partial verification does not establish the full device chain.
4. Verify the circuit on an isolated bench with a signal generator and dummy electrode impedance only. Test startup recovery, offsets, clipping, anti-alias rejection and ADC/reference accuracy. No person should be connected.
5. Only under qualified supervision and an approved electrical-safety/ethics plan should a separate future project consider human recordings, battery isolation, leakage limits, electrode procedures and applicable standards.
6. Validate sensor calibration, sample clocks, synchronization and actual gesture labels. Measure subject/session-generalization; compare real observations to simulation assumptions.

EMG amplitude alone is not grip force. A six-axis IMU cannot provide drift-free absolute yaw. Single-channel synthetic PPG cannot provide validated SpO₂. No current module makes those claims.
