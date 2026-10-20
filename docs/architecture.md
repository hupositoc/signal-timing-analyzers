# Architecture and source walkthrough

## System boundary

Use C++ low-level analyzers where direct access to sampled transitions is needed, and a Python high-level analyzer for grouped SPI-derived bit frames. Keep frequency expectations, edge selection and glitch-width settings visible. Include timing and correction metadata in analyzer output so a repaired interpretation is not mistaken for the original waveform.

```mermaid
flowchart LR
    A["Captured transitions"] --> B["Edge / glitch checks"]
    B --> C["Frequency / frame checks"]
    C --> D["Annotated exports"]
```

This is a source-derived conceptual diagram, not a captured execution trace. The text equivalent is Captured transitions → Edge / glitch checks → Frequency / frame checks → Annotated exports.

## Source responsibilities

| Source entry point | Responsibility |
|---|---|
| [`SimpleSerialAnalyzer::WorkerThread`](../clock-lla/src/SimpleSerialAnalyzer.cpp#L35) | Converts sampled edge intervals into clock-analysis output. |
| [`mExpectedFrequencyHz`](../clock-lla/src/SimpleSerialAnalyzerSettings.cpp#L6) | Exposes expected frequency; the current code default is 300 Hz. |
| [`SimpleSerialAnalyzer::WorkerThread`](../ssi-lla/src/SimpleSerialAnalyzer.cpp#L49) | Processes CLK/DATA edges and short clock pulses. |
| [`mGlitchPulseWidthLimitNs`](../ssi-lla/src/SimpleSerialAnalyzerSettings.cpp#L8) | Configurable pulse-width threshold; current default 500 ns. |
| [`try_remove_glitch_bits`](../hla/HighLevelAnalyzer.py#L218) | Attempts explicitly reported extra-bit recovery. |
| [`try_correct_bit_value_jitter_by_hamming`](../hla/HighLevelAnalyzer.py#L829) | Checks tolerated bit differences against configured patterns. |

## Design decisions

### Two levels of analysis

LLA code can examine sampled edges directly, while the HLA can reason about already decoded frames. These are complementary integration points, not duplicate implementations.

### Expose tolerances

The expected frequency and glitch threshold are test parameters. Their defaults are examples from this codebase, not requirements taken from a class rule.

### Preserve diagnostic meaning

Tolerance and correction logic should explain what was accepted and why. A clean-looking interpreted frame is not a replacement for the raw capture.

## Input/output contract to preserve

The input configuration must be recoverable alongside the output. Defaults should be treated as this implementation’s starting values, not an external standard. An integration test must check the real host/runtime because an isolated function test cannot establish timing, UI, hardware or external-service behavior.

When modifying the code, identify which responsibility changes: input acquisition, interpretation, persistent state or output presentation. Keep the public behavior and its test evidence together. Avoid silently converting a missing input or failed integration into a successful result.

## Known boundaries

- Signal patterns and default thresholds are application-specific examples.
- C++ plugins share a CMake target name and must be configured in separate build directories.
- SDK build, electrical sampling accuracy, false-positive/false-negative rates and captured-waveform replay remain unverified here.
