# Engineering case study: Signal Timing Analyzers

## 1. The task and operating context

Check periodic signals used to confirm normal operation of a marine control and monitoring module, and make timing deviations and selected noise/glitch conditions visible during Type Approval testing.

The operating context is marine module testing associated with DNV-CG-0339 and LR-TS-01. The specific product, employer, test laboratory, acceptance limits and private recordings are not disclosed.

## 2. The problem before the tool

Raw digital transitions do not directly answer whether a periodic health signal remained normal. Short glitches and noisy edges can also create misleading decoded bits or frequency estimates. An operator needs a repeatable way to inspect the timing, identify exceptions, and distinguish raw events from tolerated or repaired interpretations.

## 3. The intervention

Use C++ low-level analyzers where direct access to sampled transitions is needed, and a Python high-level analyzer for grouped SPI-derived bit frames. Keep frequency expectations, edge selection and glitch-width settings visible. Include timing and correction metadata in analyzer output so a repaired interpretation is not mistaken for the original waveform.

### Input → decision → output

1. **Input:** Captured transitions.
2. **Processing:** Edge / glitch checks.
3. **Interpretation:** Frequency / frame checks.
4. **Output:** Annotated exports.

This workflow is illustrated in the README and is mapped to actual source entry points in [architecture](architecture.md).

## 4. Work enabled by the implementation

- Inspect expected-clock frequency and timing deviations at the captured-signal level.
- Decode SSI-related CLK/DATA behavior with selectable sampling edges and a configurable short-pulse threshold.
- Review grouped patterns and reported correction reasons instead of manually counting every transition.

The author confirms use for periodic normal-operation checks and the addition of filtering for some glitch/noise data. This supports analysis of performance logs; the repository does not claim that filtering establishes electrical immunity or proves compliance with every acceptance criterion.

## 5. Technical choices and tradeoffs

### Two levels of analysis

LLA code can examine sampled edges directly, while the HLA can reason about already decoded frames. These are complementary integration points, not duplicate implementations.

### Expose tolerances

The expected frequency and glitch threshold are test parameters. Their defaults are examples from this codebase, not requirements taken from a class rule.

### Preserve diagnostic meaning

Tolerance and correction logic should explain what was accepted and why. A clean-looking interpreted frame is not a replacement for the raw capture.

## 6. Engineering contribution

Decode clock/SSI transitions and expose configurable timing and glitch filtering. The linked architecture document identifies implementation entry points; validation records distinguish source inspection, executable checks and hardware-dependent behavior.

## 7. Evidence and scope

Python HLA syntax was parsed. Source paths, current defaults and exported result fields were inspected. No hardware-equivalence or filtering-performance claim is made.

- Signal patterns and default thresholds are application-specific examples.
- C++ plugins share a CMake target name and must be configured in separate build directories.
- SDK build, electrical sampling accuracy, false-positive/false-negative rates and captured-waveform replay remain unverified here.

## 8. Next measurable milestone

- [ ] Create public fixtures for nominal, missing-edge, extra-edge and invalid-pattern cases.
- [ ] Measure detection behavior against manually labeled synthetic waveforms.
- [ ] Document threshold selection separately from the applicable test acceptance criteria.

## Before and after the intervention

| Before | Implementation | Work enabled and evidence |
|---|---|---|
| Periodic health signals needed timing inspection and noise interpretation. | Decode clock/SSI transitions and expose configurable timing and glitch filtering. | The tools supported checking periodic normal-operation signals in the marine test workflow. |
