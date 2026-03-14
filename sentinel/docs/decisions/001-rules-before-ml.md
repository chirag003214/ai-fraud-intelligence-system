# ADR 001: Rules Before ML

## Status: Accepted

## Context
We need to decide the order of evaluation for fraud detection components.

## Decision
Hard rules run BEFORE the ML model:
1. Rules are deterministic, sub-millisecond, and catch known attack patterns.
2. The ML model handles novel patterns the rules don't cover.
3. If a rule fires, we still run the ML model for confidence scoring
   but the decision is already BLOCK.

## Consequences
- Known fraud patterns are caught regardless of model quality.
- Rules can be updated without retraining the model.
- The pipeline is more resilient to model degradation.
