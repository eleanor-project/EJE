# Review: Ops Center Hardening Changes

## Summary
The recent hardening patch improves cache freshness, error-rate visibility, and secure defaults. Overall direction is solid, but a few areas would benefit from follow-up to avoid operational surprises in production deployments.

## Strengths
- TTL + config fingerprinting in `DecisionCache` reduces stale responses after deployments.
- Aggregator now surfaces critic failure rate, helping operators spot degraded coverage.
- FastAPI defaults tighten auth and CORS expectations for safer deployments.

## Recommendations
1. **Guard cache in multi-threaded servers**  
   `DecisionCache` maintains access order and counters without locking; Uvicorn/Gunicorn workers sharing the engine could interleave reads/writes, corrupting `_access_order`, or miscounting hits. Wrap `get`/`put` with a `threading.Lock` or move to `functools.lru_cache`-style primitives to keep cache state consistent under concurrency.【F:src/ejc/utils/caching.py†L35-L148】

2. **Normalize block thresholds**  
   The aggregator treats `BLOCK`/`DENY` scores as raw `confidence * weight` sums, so adding more critics can exceed `block_threshold` even if each signal is weak. Consider dividing by total applied weight (or using average confidence) before comparing to the threshold to keep semantics stable as critics scale.【F:src/ejc/core/aggregator.py†L65-L140】

3. **Avoid persisting error-only decisions**  
   When all critics error, the engine still stores precedents and audit records for the `ERROR` decision bundle. That can pollute precedent retrieval and dashboards with unusable entries. Skip precedent/audit writes when `overall_verdict` is `ERROR`, or flag them distinctly so retrieval can ignore them by default.【F:src/ejc/core/ethical_reasoning_engine.py†L258-L289】【F:src/ejc/core/aggregator.py†L92-L140】

4. **Refresh cache fingerprint on config reloads**  
   The config fingerprint is captured once at engine init; if runtime hot-reloads mutate `self.config`, the cache continues serving entries tied to the old fingerprint. Add a hook to recompute `cache_fingerprint` (and clear the cache) whenever configs are reloaded to ensure fresh evaluations after live changes.【F:src/ejc/core/ethical_reasoning_engine.py†L40-L85】【F:src/ejc/utils/caching.py†L41-L74】

5. **Expose cache stats in health endpoints**  
   The API now surfaces critic error rates but omits cache observability. Returning cache hit rate and size via the health endpoint would help operators validate that TTL/config fingerprinting works and spot eviction-related performance regressions.【F:src/ejc/core/ethical_reasoning_engine.py†L293-L321】【F:src/ejc/utils/caching.py†L132-L148】
