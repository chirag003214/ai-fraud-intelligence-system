# Sentinel API Reference

## Authentication

All endpoints (except `/v1/health` and `/docs`) require authentication.

**Option 1: API Key**
```
x-api-key: your-api-key
```

**Option 2: JWT Bearer Token**
```
Authorization: Bearer <jwt-token>
```

Get a JWT by exchanging your API key:
```bash
curl -X POST http://localhost:8000/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "<your-API_KEY-from-.env>"}'
```

---

## Endpoints

### POST /v1/predict

Evaluate a single transaction for fraud risk.

**Request:**
```json
{
  "customer_id": "CUST_001",
  "ip_address": "192.168.1.1",
  "type": "TRANSFER",
  "amount": 95000,
  "oldbalanceOrg": 95000,
  "newbalanceOrig": 0
}
```

**Response:**
```json
{
  "transaction_id": "uuid-here",
  "action": "BLOCK",
  "risk_score": "CRITICAL",
  "confidence": 0.94,
  "decision_threshold": 0.1,
  "reasons": ["Phantom Drain", "ML Score 0.94 ≥ threshold 0.10"],
  "velocity_1h": 1,
  "model_version": "latest",
  "ab_variant": "champion"
}
```

### POST /v1/predict/batch

Queue a batch of transactions for processing.

### GET /v1/explain/{txn_id}

Retrieve SHAP and LLM explanation for a transaction.

### GET /v1/history

Fetch recent transactions for the audit log.

### GET /v1/health

System health check.

### GET /v1/metrics

Prometheus-compatible metrics.

### GET /v1/drift

Real PSI drift report.

### WS /ws/alerts

WebSocket endpoint for real-time BLOCK alerts.

### POST /v1/auth/token

Exchange API key for JWT token.
