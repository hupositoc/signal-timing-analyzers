# Engineering decision record

## Context

Short transitions can be either interference or a meaningful device event.

## Decision

Make filtering parameters and timing interpretation visible in the analysis workflow.

## Consequences and evidence

A filtered output depends on the selected threshold; retain raw captures when interpreting suspected glitches.

See [architecture](architecture.md), [validation](validation.md) and the [case study](case-study.md) for implementation details and limits.
