# Hardware roadmap

The [revised report](../output/pdf/ForearmSense_AI_AECD_PBL_REVISED_UNO.pdf) and [fixed-hardware mapping](fixed-hardware-project-map.md) define the project: **Arduino Uno + one BioAmp EXG Pill + MPU-6050 + hand gripper**. No new MCU, amplifier or optical sensor is required.

1. Identify Uno revision, actual firmware, ADC reference/resolution, BioAmp configuration and MPU ranges/rate. Inspect the existing serial contract and record representative packets; preserve working wiring.
2. Verify actual sample timing and UART capacity. The approximately 250 Hz legacy EMG output cannot preserve a 20-450 Hz spectrum. Start with envelope/activity and verified low-frequency motion.
3. Implement read-only serial ingestion with malformed-packet rejection, unavailable fields, explicit source labels and disconnect/gap/reset handling.
4. Add baseline/reference calibration, the 35-second protocol, raw session recording and timestamp-based replay. Keep recordings local and excluded from Git by default.
5. Assess repeatability with calibration on designated data and evaluation on held-out holds. Use independent labels and session/participant holdouts before real-data ML claims.

Live acquisition, recording and replay remain planned. Exact wiring is not prescribed without verified module labels and existing configuration. Body-connected operation requires separate review of the existing hardware; successful software tests do not establish electrical safety.

The custom INA826/OPA2376/SPICE work remains an [educational engineering study](engineering-analysis.md), not a requirement to replace the BioAmp. No working optical sensor, calibrated grip-force channel, magnetometer or absolute yaw is confirmed. Measured HR, SpO2, blood flow and force remain unavailable.
