# Health Monitoring — Senior

<!-- level-focus -->
At senior level, focus on this question:

> What invariant must your health-check design guarantee so that a single flaky dependency degrades traffic gracefully instead of triggering a synchronized failure across every replica — and what evidence would prove that invariant holds under a real dependency outage, not just in the design doc?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Anchor the Design to Invariants, Not to Endpoints

A middle-level health-check design is organized around individual endpoints: `/healthz` is shallow, `/readyz` covers the named hard dependencies. That's correct as far as it goes, but at senior level the organizing question changes: **which invariant does the health-check architecture actually guarantee, across every replica and every failure mode it will ever encounter?** An invariant is a property that must hold regardless of which dependency fails or how many replicas exist — not "readyz checks the database" but "no single shared dependency's failure can simultaneously remove more capacity than the failure itself would have removed."

Three invariants worth naming explicitly for a health-check system:

| Invariant | What it rules out |
|---|---|
| A "ready" instance can actually serve a request correctly | A gray failure where the check passes but real requests fail anyway |
| No two replicas' readiness decisions are perfectly correlated on a single shared dependency's blip | The cascading, self-inflicted outage from Core Concept 3 of the middle-level guide, at fleet scale |
| A restart triggered by liveness can plausibly fix the problem it responds to | A restart loop that repeatedly kills healthy processes because a downstream outage was mistakenly wired into liveness |

An endpoint-level design is *done* when `/healthz` and `/readyz` exist and return the right status codes in isolation. An invariant-level design is *done* when each of these properties has a *mechanism* enforcing it — jitter, caching, circuit-breaker-informed readiness, a restart policy that only fires on conditions a restart can fix — not just a description of the intent.

## Core Concept 2 — Failure Mode: Gray Failure

A **gray failure** is the health-check analogue of a bug that only shows up in production: the check reports healthy, but real traffic fails anyway. It's the hardest category because every individual signal looks fine in isolation:

- A readiness check pings the database with `SELECT 1` and gets a fast response, but the actual query paths the service uses hit a different, degraded table or a replica lagging far enough behind that reads return stale data — the check measures connectivity, not correctness.
- A shallow liveness check proves the HTTP server thread responds, while a background worker thread inside the same process has deadlocked and stopped processing the actual work the service exists to do — the process is "alive" by the check's definition and useless by every other definition.
- A readiness check succeeds because a dependency call is served from a stale in-memory cache the health-check code doesn't realize is stale, while requests using the same cache return wrong answers.

The senior-level response to a gray failure isn't "add more checks" reflexively — more checks that still test the wrong thing produce more false confidence, not more truth. The response is asking what the check is actually a proxy for, and whether real request outcomes (error rates, correctness) are ever reconciled against what the check reports.

## Core Concept 3 — Failure Mode: Correlated Failure and Restart Storms

Two related but distinct failure modes deserve separate names, because they call for different fixes:

- **Correlated readiness failure** (the middle-level cascading scenario, at architecture scale): every replica's readiness check fails within the same probe cycle because they all synchronously depend on the same shared resource with no decorrelation. The fix lives in the readiness design — jitter, cached results, or replacing synchronous per-probe checks with a background poller.
- **Restart storm from liveness misuse**: a deep dependency check leaks into the liveness endpoint. The dependency goes down; every replica's liveness probe fails; the orchestrator restarts every replica; the new replicas boot, immediately re-check the same still-down dependency, and fail liveness again — producing `CrashLoopBackOff` (or the equivalent) across the entire fleet, while the actual root cause was never in any of the restarted processes at all.

```mermaid
sequenceDiagram
    participant Kubelet as Orchestrator
    participant R1 as Replica (liveness checks DB)
    participant DB as Downstream Database
    Note over DB: DB goes down
    Kubelet->>R1: liveness probe
    R1->>DB: dependency check (fails)
    R1-->>Kubelet: liveness = fail
    Kubelet->>R1: restart container
    Note over R1: New container boots,<br/>immediately checks DB again
    R1->>DB: dependency check (still fails)
    R1-->>Kubelet: liveness = fail
    Note over Kubelet,R1: Restart loop continues;<br/>DB outage is never touched by any restart
```

The restart storm is strictly worse than doing nothing: it adds boot-time load (connection storms, cache-warming queries) on top of an already-struggling dependency, and it burns the orchestrator's restart budget on a condition no restart can ever resolve. This is why the invariant in Core Concept 1's table — *a restart triggered by liveness can plausibly fix the problem it responds to* — has to be checked explicitly for every check that lives inside a liveness handler, not assumed.

## Core Concept 4 — Recovery Design: What Each Probe Is Allowed to Trigger

The recovery mechanism a probe triggers has to match what that probe can actually diagnose:

- Liveness can only diagnose "is this process itself broken." Its only sane recovery action is restart, and it must never be wired to anything a restart cannot fix — which rules out any external dependency check.
- Readiness can only diagnose "can this instance serve traffic right now." Its recovery action — removal from the load-balancer pool — is reversible and cheap, which is exactly why readiness is allowed to be more speculative and more dependency-aware than liveness: getting it wrong costs a temporarily smaller traffic pool, not a restart storm.
- A circuit breaker tracking real request failures (not a synthetic probe at all) can diagnose "this dependency is failing for actual traffic," and its recovery action is failing fast for the specific request path affected, without touching the instance's overall readiness status.

Letting a circuit breaker's open/closed state inform readiness — rather than running a separate synthetic ping — has a real advantage: it reflects what's *actually happening to real requests*, which directly addresses the gray-failure risk from Core Concept 2. A synthetic `SELECT 1` can succeed while the actual query patterns used by real traffic fail; a circuit breaker tripped by real failures cannot have that gap, because it's built from the same requests it's protecting.

## Core Concept 5 — Evidence Over Assumption

A health-check architecture validated only by reading the code is validated against what the author *intended* it to do, not what it actually does under a real dependency failure. Validate it with:

- **Fault injection**, not just unit tests against mocks. Kill the actual dependency (or a realistic proxy of it — a network partition, an artificially slow response) in a staging environment and observe: do replicas fail within the same probe cycle, or spread out? Does a liveness probe ever fail as a side effect?
- **Correlating probe status with real request outcomes.** If readiness says healthy but the real error rate for that instance is elevated, that's a live gray failure, not a hypothetical one — and it means the check is measuring the wrong thing.
- **Reconciliation against past incidents.** Every health-check-adjacent incident (a restart storm, an instance serving errors while marked ready, a total outage from a partial dependency blip) should map to either confirming an existing safeguard worked as designed, or exposing a gap that needs to close. A health-check design with zero incidents traced back to it either belongs to a very young system or hasn't been tested against reality.

Treat every claim about the health-check design — "readiness can't correlate across replicas," "liveness never depends on anything external" — as something with a confidence level: verified under fault injection, verified by code review only, or asserted and never checked. Prioritize checking the asserted ones first.

## Core Concept 6 — Cross-Component Scenario: Redesigning a Payment Service's Health Checks

A payment service runs behind a load balancer with several replicas, backed by a Postgres primary, a Redis cache, and an internal fraud-scoring service called on every request. Two plausible designs:

| Design | Behavior | Trade-off |
|---|---|---|
| **A: Synchronous per-probe dependency check with jitter** — each replica's `/readyz` pings Postgres directly, with a randomized offset per replica | Simple to reason about; each replica's readiness reflects its own direct observation | A synthetic ping only proves connectivity, not correctness — it can miss the gray-failure cases in Core Concept 2, and under sustained load the probes themselves add extra connection pressure onto an already-struggling database |
| **B: Circuit-breaker-informed readiness** — readiness reflects whether the circuit breaker wrapping real Postgres calls is open or closed, with no separate synthetic check | Reflects actual request outcomes, closing the gray-failure gap; adds no extra load on the dependency beyond what real traffic already generates | Readiness reacts only after real requests start failing, so there's a short lag versus a proactive ping; requires the service to already have well-tuned circuit-breaker thresholds, which is its own piece of engineering |

Design A is easier to build first and catches "database is completely unreachable" cleanly, but it cannot catch "database is reachable but returning wrong or stale data for the queries that matter," and it adds connection load exactly when the database can least afford it. Design B closes the gray-failure gap and adds no extra dependency load, but only works if the circuit breaker's failure threshold and recovery window are already well-tuned — a poorly tuned breaker either flaps readiness on transient blips or takes too long to notice a real outage. The senior-level resolution is usually a hybrid: circuit-breaker-informed readiness as the primary signal (because it reflects real traffic), with a synthetic ping as a fallback only during the narrow startup window before the breaker has seen enough real traffic to have a meaningful state.

## Core Concept 7 — Questions That Expose Weak Assumptions

- "If our shared database's latency spikes for five seconds, do all replicas become not-ready within the same probe cycle?" — an untested "no" is usually a hopeful guess, not a verified property.
- "Does anything inside our liveness handler ever call outside the process?" — a single overlooked call turns liveness into a second, undocumented readiness check with restart as its only response.
- "If readiness says healthy but real requests are failing right now, how would we find out?" — an honest "we wouldn't" means detection needs direct investment, not just another synthetic check.
- "What does a restart triggered by our liveness probe actually fix?" — if the honest answer is "nothing, for at least one of our checks," that check needs to move to readiness or be removed.
- "Has this design ever been tested against a real dependency outage, or only against mocks?" — a design untested under fault injection is a hypothesis, not a verified invariant.

## Core Concept 8 — Evolution

A health-check architecture needs explicit triggers for revisiting it, not a one-time design pass: a new dependency added to the request path, a change in which queries are "hard" for a given instance, an incident where readiness or liveness behaved unexpectedly, or a circuit breaker's thresholds proving miscalibrated under real load. Treat each of these as a scheduled re-evaluation point — and treat an incident where a check misbehaved as the highest-value input to the next revision, because it's the one piece of evidence that's actually about your system rather than a general principle borrowed from somewhere else.

## Common Mistakes

- **Adding more synthetic checks in response to a gray failure**, instead of asking what the check should have measured in the first place.
- **Assuming jitter or caching alone eliminates correlated failure** without ever testing it against a real, simulated dependency outage.
- **Wiring any external check into liveness "just to be safe,"** which converts a downstream outage into a fleet-wide restart storm.
- **Treating a circuit-breaker-informed readiness design as strictly superior** without accounting for its dependency on already-well-tuned failure thresholds — a poorly tuned breaker is worse than a simple synthetic ping.
- **Never reconciling probe status against real request error rates**, which is the only way to actually catch a gray failure rather than assume the checks are correct.

## Apply it

1. Take a service you know with at least one shared, heavily-used dependency, and write down which of the three invariants from Core Concept 1's table you can currently point to a real enforcement mechanism for — versus which are just assumed.
2. Design a fault-injection test that kills (or heavily degrades) that shared dependency in a staging environment, and predict, in writing, whether replicas will fail within the same probe cycle before you run it.
3. Identify one place in your system where a synthetic health check could pass while real requests fail (a gray-failure candidate), and describe what evidence would reveal that gap in production.
4. Compare a synchronous-ping design against a circuit-breaker-informed design for one specific dependency, using Core Concept 6's table as a template, and state which you'd choose and why.
5. Run the five weak-assumption questions from Core Concept 7 against your system and identify which one exposes the shakiest assumption.

## Verify your work

- Your fault-injection test's actual result either confirms or contradicts your written prediction — and if it contradicts it, you can name the specific mechanism (or missing mechanism) responsible.
- You can point to a concrete enforcement mechanism — not just a description — for at least one of the three invariants from Core Concept 1.
- Your identified gray-failure candidate names a specific scenario where the check and reality diverge, not a generic "checks could be wrong somewhere."
- Your synchronous-ping-versus-circuit-breaker comparison names a real trade-off specific to your dependency, not a restatement of the general pattern.
- At least one weak-assumption question surfaces a genuine, previously untested gap in your own system.

## Review questions

- Why does anchoring a health-check design to invariants change what counts as "the design is complete"?
- What makes a gray failure harder to catch than a check that simply fails outright?
- Why can wiring an external dependency check into a liveness probe produce a worse outcome than having no liveness probe at all?
- What evidence turns a claim like "our readiness checks won't fail in a correlated way" from an assumption into something you can actually trust?
