# Analytical analog design

The sections below describe the initial waveform model. The follow-up [engineering analysis](engineering-analysis.md) adds an equivalent component-defined Sallen-Key candidate, band-limited white-noise estimates, component tolerance sweeps and actual SPICE checks. The primary dashboard waveform model itself remains analytical. OPA2376 isolated checks pass; INA826 compatibility does not, so full-chain manufacturer-model validation is still unresolved.

## Reference and traceability

The revised technical report was not available in the supplied attachment or empty project directory. Initial design assumptions therefore come from the user's brief. Formula verification used Texas Instruments' official [INA826 datasheet, SBOS562G](https://www.ti.com/lit/ds/symlink/ina826.pdf) and [OPA2376 datasheet, SBOS406G](https://www.ti.com/lit/ds/symlink/opa2376.pdf), consulted 2026-10-23.

`backend/app/analog.py` implements the following equations. Generator voltages are differential EMG inputs; an input common-mode waveform is not synthesized. The model **assumes valid common mode** and ideal input protection. It does not claim to verify the INA826's operating envelope, resistor network, supply, load or patient safety.

## Amplifiers

INA826 gain: G = 1 + 49,400 Ω / RG. With RG = 5,490 Ω, G ≈ 9.99818. First-stage ideal output is 1.65 V + G × differential input. The first stage clips before high-pass filtering; downstream DC rejection cannot recover an upstream saturated signal.

The OPA2376 stage is modeled as ideal non-inverting gain 50, referenced to 1.65 V: Vout = 1.65 + 50 × Vac. A physical implementation would require Rf/Rg = 49 (for example 49 kΩ / 1 kΩ), correct biasing and finite-bandwidth stability analysis. These component choices are not a verified schematic. Total nominal gain is ≈499.909. A 5 mVpp input centered at 0 produces ≈2.50 Vpp before frequency attenuation, within a nominal 0.1–3.2 V assumed output range around 1.65 V.

Supply = 3.3 V. An illustrative 0.1 V output rail margin is used for both stages, **not a datasheet guarantee across loads/temperatures**. TI's INA826 input common-mode constraints depend on internal first-stage outputs and differential gain (see datasheet sections 8.3.3–8.3.4 and Figure 60). A simple check that pins lie inside supply rails is insufficient, particularly for the ±50 mV offset scenario. This envelope remains unverified and is explicitly disclosed in API warnings.

## Filters

Second-order Butterworth high-pass:

Hhp(s) = s² / (s² + √2 ωh s + ωh²), ωh = 2π × 20 rad/s.

Optional notch, Q = 30:

Hn(s) = (s² + ωn²) / (s² + (ωn/Q)s + ωn²), ωn = 2π × 50 rad/s.

Fourth-order Butterworth low-pass is generated with SciPy's continuous-time Butterworth design, cutoff 2π × 450 rad/s. Magnitude at cutoff is −3.0103 dB. Its two normalized denominator factors have s coefficients approximately 0.765367 and 1.847759 (Q ≈ 1.30656 and 0.541196). The follow-up engineering model selects an equivalent Sallen-Key R/C candidate and generates ideal-buffer SPICE netlists; the waveform path remains this ideal transfer function, not a complete physical schematic.

The frequency plot is the product of these continuous-time transfer functions and the two scalar gains. The optional notch removes genuine EMG content near 50 Hz as well as mains contamination. It is not a signal-preserving artifact remover.

Time-domain filtering converts each continuous system to a state-space discrete realization via zero-order hold at the configured input rate. This is a sampled-input approximation; it does not model a continuous source above Nyquist. Initial states are zero, so startup transients are retained. It must not be mistaken for transistor-level or manufacturer-model SPICE.

## ADC and aliasing

Codes = round(clipped voltage / 3.3 × 4095). Codes span 0…4095. Reconstructed voltage = codes × 3.3/4095. This endpoint-inclusive convention has a step of about 0.806 mV; an ideal code-bin convention often quotes 3.3/4096 instead. Quantization error is bounded by half a step away from clipping. ADC input is modeled with the amplifier margin; clipping events are counted separately at INA and post-gain stages.

`results/metrics/summary.json` records executed LP-only attenuation checks at 450/500/1000/2000/3550/4000 Hz. At 4 kHz sampling, 3550 Hz aliases to 450 Hz and 4000 Hz to DC. The analytic filter attenuates these frequencies but cannot prove physical anti-alias protection without a continuous input and component model. Attenuation at 500 Hz is only about 5.22 dB; do not decimate directly to 1 kHz based on this filter alone.

## Noise, tolerances and remaining engineering

Device noise is not synthesized into the waveform. A separate 20–450 Hz white-noise budget now includes INA input/output voltage and current noise, external RG, two electrode resistances, filter resistor/buffer noise, and post-amplifier voltage/current/feedback-resistor noise. INA input referral combines the 18 nV/√Hz input term and 110 nV/√Hz output term divided by gain. Sources are weighted by downstream transfer functions and summed in quadrature. Full 1/f, reference/supply, physical notch, capacitor/PCB and out-of-band alias noise remain excluded. The generator's `noise_mv` stays a separate illustrative contamination control.

Candidate component tolerances now vary each R/C independently, including Q changes, with explicit seed and distributions. Actual ideal-buffer SPICE AC/transient/resistor-noise results and an OPA macro-model gain/DC sweep are generated. INA model compatibility, full operating envelope, finite-bandwidth behavior of the complete chain, protection/reference design and physical calibration remain unverified. See the follow-up document and saved solver logs for the precise evidence boundary.
