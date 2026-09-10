# Debug-Thinking — Senior

**Your question:** How do I diagnose a failure that no single component caused, under incomplete information, while a live incident is still running?

At middle level, the bug lives somewhere specific — you just have to find the right boundary. At senior level, some failures are **emergent**: no single service is broken, but the interaction between several correctly-behaving components produces a failure none of them would produce alone. You also don't get to bisect calmly — during a live incident, you're forming hypotheses against a clock, with partial telemetry, while other people are asking for a status update.

## Separate mitigation from root-cause diagnosis

The single highest-leverage move at senior level: **stop the bleeding before you understand it.** Rolling back a deploy, failing over to a backup, or disabling a feature flag doesn't require knowing *why* something broke — only that a specific recent change is a plausible trigger and reverting it is safe.

- **Mitigate first, explain later.** If a rollback is cheap and reversible, do it as soon as you have a plausible (not proven) trigger. Root-cause diagnosis can continue after user impact stops, with far less time pressure and a much lower cost of being wrong.
- **Don't let "we don't fully understand it yet" block mitigation.** You do not need a confirmed hypothesis to roll back the last deploy — you need only a plausible one and a cheap, reversible mitigation.
- **Don't let mitigation substitute for diagnosis.** A rollback that makes the symptom go away is not the same as knowing the cause. If you don't investigate afterward, the same bug ships again under a different trigger.

## Diagnose emergent failure by modeling interaction, not components

An emergent failure requires looking at the *relationship* between components, not each one in isolation:

- **Retry storms:** service A times out calling service B, retries; multiplied across many clients, the retries themselves overwhelm B, which was only slow, not down — the retries turn a slowdown into an outage. No single retry is wrong; the aggregate behavior is.
- **Cascading failure:** service B's real slowdown exhausts service A's connection pool waiting on B; A now can't serve its *unrelated* callers either, because its resource (connections) was shared across all traffic, not because A itself has a bug.
- **Resource exhaustion under a specific load shape:** a system handles average load fine but a specific concurrency pattern (many requests arriving in the same instant, not just "a lot of load") exhausts a shared resource (thread pool, lock, connection limit) that average-load testing never exercised.

**How to model it:** draw the actual resource-sharing graph — which components share a connection pool, a thread pool, a rate limit, a downstream dependency — not just the logical call graph. Emergent failures usually live in a *shared resource* the architecture diagram doesn't show, because architecture diagrams show intended calls, not contention.

## Separate correlation from causation

"It broke right after the deploy" is a correlation, not yet a causation claim. Before treating it as the root cause:

1. **Name the mechanism.** How, specifically, could this change cause this symptom? If you can't state a causal path (what line of code, what changed behavior, what new interaction), you have a coincidence candidate, not a hypothesis.
2. **Check for confounders.** Did anything else change at the same time — a config change, a traffic pattern shift, a dependency's own deploy, a scheduled job? Two things co-occurring near an incident doesn't rule out a third, unnoticed cause driving both.
3. **Look for a dose-response relationship.** If the suspected cause is real, does more of it produce more of the symptom (more traffic to the new code path → proportionally more errors)? A cause with no dose-response relationship to the symptom is weaker evidence than one with a clear one.
4. **Test by removal, not just by timing.** The strongest evidence a suspected cause is the actual cause: removing it (rollback, flag off) resolves the symptom, and reintroducing it in a controlled way (canary, staging) reproduces it again.

## Diagnose under partial information

During a live incident, you rarely have complete telemetry. Debug-thinking under these conditions means making the incompleteness explicit instead of pretending you have full information:

- **State your confidence level out loud.** "I'm fairly confident it's the connection pool, based on the exhaustion metric, but I haven't confirmed the trigger" is more useful to a team than a flat, unqualified claim — it tells others what still needs checking and prevents premature commitment to one theory.
- **Actively look for disconfirming evidence, not just confirming evidence.** Under time pressure, the pull toward the first plausible theory is strong (confirmation bias gets worse, not better, under stress). Explicitly ask: "what would I expect to see if this hypothesis is wrong?" and check for it.
- **Avoid tunnel vision by timeboxing each hypothesis.** If a hypothesis hasn't produced confirming or disconfirming evidence within a set time, park it and check the next-most-plausible one — don't let sunk investigation time keep you on a dead-end theory.
- **Extract a minimal reproduction once mitigated.** After the incident is stable, try to reduce the failure to the smallest input/environment that still reproduces it. A production-only bug that resists minimal reproduction usually means the model of the cause is still incomplete — keep narrowing.

## A concrete example

**Symptom:** During a traffic spike, the checkout service becomes fully unresponsive for 90 seconds, then recovers on its own. Recurs roughly weekly, always during peak traffic, never reproducible in staging load tests.

**Mitigate first:** On-call adds a circuit breaker that's already built but disabled, cutting calls to the slow downstream inventory service when its latency exceeds a threshold — stops the cascading unresponsiveness within the incident, before the cause is confirmed.

**Model the interaction, not the components:** Checkout and three other unrelated services all share one connection pool to the inventory service. Under peak traffic, inventory's own database occasionally has a brief GC pause; checkout's calls to inventory queue up; checkout's shared connection pool — used by every endpoint, not just the inventory-dependent one — exhausts; unrelated checkout endpoints that never call inventory now fail too, because they're waiting on the same pool.

**Separate correlation from causation:** The deploy two days earlier is not the cause — the dose-response check shows the failure correlates with *traffic volume crossing a threshold*, not with time-since-deploy, and it reproduced identically on the pre-deploy version once traffic was replayed at the same volume in a test environment.

**Root cause:** A shared, unbounded connection pool means one slow downstream dependency can exhaust resources needed by unrelated code paths — an architectural issue, not a code bug in any single function.

**Fix:** Separate connection pools per downstream dependency, with a bounded size and the circuit breaker enabled permanently, not just as an incident-response patch.

**Verify:** Replay the peak-traffic pattern that previously triggered the failure, with the fix in place, and confirm checkout endpoints unrelated to inventory stay responsive even when inventory is artificially slowed in the test.

## Common mistakes at senior level

| Mistake | Consequence | Fix |
|---|---|---|
| Waiting for full root-cause confidence before mitigating | User impact continues far longer than necessary | Mitigate on a plausible, reversible hypothesis; diagnose fully afterward |
| Treating "right after the deploy" as proof of causation | Real cause (a load-dependent architectural issue) goes unfixed and recurs | Require a stated mechanism and a dose-response check, not just timing |
| Debugging components in isolation when the failure is emergent | Each component "looks fine" individually; the actual shared-resource contention is never found | Model shared resources (pools, locks, rate limits) across components, not just the call graph |
| Committing to the first plausible theory under time pressure | Confirming evidence gets over-weighted, disconfirming evidence gets ignored | Actively look for what would disprove the current theory; timebox and rotate hypotheses |
| Declaring the incident resolved when the symptom stops, without a minimal repro or confirmed mechanism | The same failure recurs under a slightly different trigger | Don't close the loop until you can explain the mechanism and, ideally, reproduce it on demand |

## Hands-on exercise

Take a past incident (or a plausible one for your system) that involved more than one component.

1. Write the mitigation you'd apply first, and state what makes it safe to apply *before* full root-cause confidence.
2. Draw the shared-resource graph (pools, locks, rate limits, shared dependencies) for the components involved — not just the logical call graph.
3. Write the suspected cause as a causal mechanism (not just a correlation), and describe the dose-response check that would support or refute it.
4. Write one piece of evidence that would disprove your leading hypothesis, and check whether it's present.
5. Describe what a minimal reproduction of this failure would look like, and what data or environment it would need.

## Verify your thinking

- [ ] Did you mitigate on a plausible, reversible hypothesis rather than waiting for full certainty?
- [ ] Can you state the causal mechanism, not just the timing correlation, for your leading hypothesis?
- [ ] Did you check for a dose-response relationship or a confounding factor before committing to a cause?
- [ ] Did you model shared resources across components, not just each component in isolation?
- [ ] Did you actively look for evidence that would disprove your leading theory, not just evidence that confirms it?

Continue to [`professional.md`](professional.md).
