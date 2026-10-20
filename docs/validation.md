# Validation and evidence record

## Evidence vocabulary

| Label | Meaning |
|---|---|
| Source inspected | A mechanism exists in the cited implementation; this alone is not proof of successful execution. |
| Locally executed | A named check was run in the current preparation environment, with its scope stated. |
| Author-reported use | Historical operating context supplied by the author; private reports are not published. |
| Pending | A check has not been reproduced and is not presented as a result. |

## Current record

Python HLA syntax was parsed. Source paths, current defaults and exported result fields were inspected. No hardware-equivalence or filtering-performance claim is made.

**Historical/context statement:** The author confirms use for periodic normal-operation checks and the addition of filtering for some glitch/noise data. This supports analysis of performance logs; the repository does not claim that filtering establishes electrical immunity or proves compliance with every acceptance criterion.

## Integration verification checklist

- [ ] Record exact runtime, dependency versions, input/configuration and date.
- [ ] Run a nominal case with a predictable expected output.
- [ ] Exercise an invalid input or interruption and inspect the failure state.
- [ ] Retain a shareable output and the procedure that produced it.
- [ ] Compare the result with the original task, rather than only checking that the program launched.

## Claims deliberately kept separate

- Signal patterns and default thresholds are application-specific examples.
- C++ plugins share a CMake target name and must be configured in separate build directories.
- SDK build, electrical sampling accuracy, false-positive/false-negative rates and captured-waveform replay remain unverified here.

An expected output, architecture drawing or sample configuration is not a measured result. This document is the place to add test logs when integration work is actually completed.
