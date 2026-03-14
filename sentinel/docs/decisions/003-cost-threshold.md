# ADR 003: Cost-Aware Threshold

## Status: Accepted

## Context
The default 0.5 classification threshold doesn't account for the asymmetric
costs of false positives vs. false negatives in fraud detection.

## Decision
Use a Bayes-optimal threshold derived from the cost matrix:

```
t* = FP_cost / (FP_cost + FN_cost)
```

With our defaults (FP=$5 analyst time, FN=$850 fraud loss):
```
t* = 5 / (5 + 850) = 0.0059
```

This is clamped to [0.1, 0.9] to avoid extreme values from uncalibrated models.

## Consequences
- The system is biased toward catching fraud (lower threshold → more blocks).
- False positives increase but at $5/ea vs $850/ea for false negatives.
- The threshold is included in every prediction response for transparency.
- Can be tuned via environment variables without code changes.
