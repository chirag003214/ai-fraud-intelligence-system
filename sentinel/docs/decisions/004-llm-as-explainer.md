# ADR 004: LLM as Explainer

## Status: Accepted

## Context
Fraud analysts need human-readable explanations of why a transaction was flagged.

## Decision
Use Llama 3-8B (via HuggingFace Inference API) as a post-hoc explainer:
1. The LLM generates a one-sentence narrative AFTER the decision is made.
2. It never influences the classification — it is explanation-only.
3. Explanation is computed asynchronously in a Celery background task.
4. If the LLM fails, the prediction is unaffected.

## Consequences
- Prediction latency is not impacted by LLM response time.
- Explanations may take 2-10s to appear after the prediction.
- Frontend polls GET /v1/explain/{txn_id} until explanation_ready=True.
- LLM cost is bounded (one call per prediction, max 60 tokens).
