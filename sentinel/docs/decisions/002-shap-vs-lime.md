# ADR 002: SHAP vs LIME

## Status: Accepted

## Context
We need model-agnostic explanations for fraud predictions.

## Decision
Use SHAP (TreeExplainer) instead of LIME:
1. TreeExplainer is exact for tree-based models (XGBoost) — O(TLD) vs O(n*K) for LIME.
2. SHAP values sum to the model output (additive), making them interpretable.
3. LIME requires sampling perturbations, which is slower and non-deterministic.

## Consequences
- Explanations are exact and reproducible.
- Computation is fast enough for async background processing.
- Requires tree-based model — if we switch to a neural model, we'd use KernelSHAP.
