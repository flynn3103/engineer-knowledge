# Graceful Degradation — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you compose fallbacks across modules while preserving contracts, freshness limits, and testability?

---

## Make fallback a contract

Expose a dependency through an interface that can return a normal value, a bounded stale value, or an explicit unavailable result. Callers should not infer a fallback from `null`. Include freshness and source metadata where it affects user decisions.

## Choose deliberately

| Fallback | Good for | Do not use for |
|---|---|---|
| Cached value | Catalog, profile display | Authorization decisions |
| Default value | Recommendations, layout | Prices or balances |
| Async queue | Noncritical notifications | Immediate confirmation |
| Explicit unavailable | Required but nonfatal option | Concealing failed transactions |

## Scenario

Product pages combine catalog, price, inventory, and recommendations. Recommendations may use a 15-minute cached default. Price must come from the authoritative service or show unavailable; stale price could mislead a purchase. Put timeouts and circuit breakers in the dependency adapter, then integration-test the page with each dependency unavailable.

## Avoid silent normality

Fallback must emit a metric and structured reason. Set a maximum stale age and make the normal path periodically recover; otherwise an outdated cache can become invisible technical debt.

## Apply it

1. Define an interface result for normal, stale, and unavailable data.
2. Set a freshness bound for one cache-backed feature.
3. Write integration tests for each dependency outcome.

## Verify your work

- Callers can distinguish stale from authoritative results.
- A failure cannot bypass a correctness-critical decision.
- Dashboards show fallback rate and stale-age distribution.

## Review questions

- Why should fallback state be explicit in an interface?
- Which data must never be served stale?
- How can a cache fallback become a hidden outage?
