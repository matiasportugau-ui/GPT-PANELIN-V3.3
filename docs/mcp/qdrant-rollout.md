# Qdrant rollout guide for `quotation_store`

This document defines when to keep the default `FileStore` and when to enable `QdrantStore` for quotation memory.

## Feature flags

Set these in environment variables (or default them in `mcp/config/mcp_server_config.json`):

- `ENABLE_QDRANT_MEMORY`: turns on Qdrant as preferred backend.
- `ENABLE_VECTOR_RETRIEVAL`: enables similar-quotation retrieval responses.

## Cost and latency breakpoints

Use these thresholds as rollout guardrails:

| Workload profile | Recommended backend | Why |
| --- | --- | --- |
| **< 1,000 quotations/month** and **< 3 concurrent users** | `FileStore` | Near-zero infra cost, predictable local writes, no network dependency. |
| **1,000–10,000 quotations/month** or **3–15 concurrent users** | `FileStore` initially, then pilot `QdrantStore` | File search remains acceptable, but retrieval latency can start increasing with larger history. |
| **> 10,000 quotations/month** or **> 15 concurrent users** | `QdrantStore` | Vector index keeps retrieval bounded and supports better semantic matching quality. |
| **P95 retrieval SLA < 150 ms** over WAN | `QdrantStore` | Remote vector DB can outperform file scans when tuned and colocated. |
| **Budget constraint < $10/month** and low request volume | `FileStore` | Avoid managed vector DB spending until usage justifies it. |

### Rule of thumb

Enable Qdrant when **either**:

1. Similarity retrieval requests exceed **100/day**, or
2. Local file retrieval P95 exceeds **250 ms** for a week, or
3. Memory dataset exceeds **~50 MB** serialized JSON.

If none of the above are true, keep `FileStore`.

## Startup degradation behavior

When `ENABLE_QDRANT_MEMORY=true`:

1. Server attempts a Qdrant health check (`GET /collections`).
2. If it fails, server automatically falls back to `FileStore`.
3. A structured warning is emitted:

```json
{
  "event": "memory_backend_degraded",
  "requested_backend": "qdrant",
  "active_backend": "file",
  "reason": "...connection error..."
}
```

This ensures `quotation_store` callers receive the same response shape regardless of backend.
