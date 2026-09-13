# SRE and Reliability — Middle

## Instrument boundaries with RED and USE

At every service boundary, instrument **operation, outcome, duration, and correlation ID**. Two standard metric shapes cover most needs:

| Framework | Applies to | Metrics |
|---|---|---|
| **RED** | Services (things that receive requests) | **R**ate (requests/sec), **E**rrors (failed requests/sec), **D**uration (latency distribution) |
| **USE** | Resources (things that get consumed) | **U**tilization (% busy), **S**aturation (queue depth, work waiting), **E**rrors (resource-level errors) |

A queue worker needs both: RED for the jobs it processes (rate, error rate, processing duration) and USE for the queue itself (how full it is, how saturated the worker pool is).

## Propagate trace context across every boundary

A trace is only useful if its context (trace ID, span ID) survives every hop — HTTP calls, message queues, background jobs. A request that crosses an async boundary without propagated context produces two disconnected traces instead of one complete picture. Use structured logs that can **join** on trace ID, request ID, tenant ID, and deployment version — but keep those join fields bounded. A field like `user_email` or a raw request body as a log label creates unbounded cardinality that can break a metrics backend (each unique value becomes a new time series).

## Use error-budget burn to decide, not just observe

An **error budget** is `1 - SLO`: if your SLO is 99.9% success, your budget is 0.1% failure, spendable on releases, risky changes, or absorbing real incidents. Error-budget burn *rate* — not just remaining budget — drives decisions:

- **Fast burn** (budget would be exhausted in hours): stop releases, treat as an active incident.
- **Slow burn** (budget would be exhausted in weeks): investigate and fix, but don't necessarily freeze releases.

## Design for overload before it happens

- **Graceful degradation** — serve a reduced but functional experience (cached data, a simpler response) instead of failing outright when a dependency is unhealthy.
- **Load shedding** — reject the least valuable requests first (health checks over user requests; free tier over paid, if that's a legitimate business call) once a resource is saturated, so the system stays up for the requests that matter most.
- **Retry budgets** — cap total retries as a percentage of traffic, not per-request, so retries can't multiply a slowdown into an overload (see [Debug-Thinking — Middle](../../engineering-thinking/08-debug-thinking/middle.md) for the retry-storm failure pattern this prevents).
- **Dependency timeouts** — every outbound call needs a timeout shorter than the caller's own SLO budget; an unbounded call to a slow dependency propagates the slowness upward.

## Reduce toil, not just work

**Toil** is operational work that is manual, repetitive, automatable, tactical (no lasting value), and scales linearly with service growth. Restarting a stuck process by hand every week is toil; designing the fix that makes it stop getting stuck is not. When automating toil away, the automation must still **expose failure and ownership** — a script that silently retries and hides a growing problem just moves the toil into a harder-to-see place.

## Diagnostic endpoints and sampling

- **Diagnostic endpoints** (health checks, debug dashboards, internal state dumps) should expose safe, authenticated state — never secrets, never an unbounded dump of internal data.
- **Sampling is a fidelity decision.** Head sampling (decide to keep a trace before you know the outcome) controls cost predictably but can discard exactly the slow or failed traces you'd want later. Tail sampling (decide after the outcome is known) can preferentially retain failed or slow traces — at higher buffering cost. Document what your sampling strategy *cannot* prove, so nobody trusts a sampled signal for a question it wasn't designed to answer.

## Test yourself

1. Which RED and USE metrics fit a queue worker specifically?
2. How does trace context survive crossing an asynchronous (queue, background job) boundary?
3. What cardinality mistake in a log or metric label can break a metrics backend?
4. When is the extra buffering cost of tail sampling worth it over head sampling?
5. Why must toil-reducing automation still expose failure, not just hide it?

Continue to [`senior.md`](senior.md).
