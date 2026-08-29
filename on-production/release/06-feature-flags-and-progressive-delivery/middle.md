# Feature Flags & Progressive Delivery — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Feature Flags & Progressive Delivery** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Feature Flags & Progressive Delivery

*Not all flags are the same. Different types have different owners, different lifecycles, and different ways to hurt you.*

---

## Core Concept 1 — The Four Flag Types

Martin Fowler's taxonomy is the one to internalize. Two axes matter: **how long the flag lives** and **how often its value changes**.

| Type | Lifespan | Changes how often | Owner | Example |
|---|---|---|---|---|
| **Release toggle** | Days–weeks | Once (off→on, then deleted) | Dev team | Hide unfinished checkout redesign |
| **Ops / kill-switch** | Months–years | Rarely, in emergencies | Ops / SRE | Disable recommendation engine under load |
| **Experiment** | Weeks (one experiment) | Per-user, fixed during the run | Product / data | Green vs blue buy button |
| **Permission / entitlement** | Permanent | When a customer's plan changes | Product / billing | "Pro plan gets export" |

Why the distinction is load-bearing:

- A **release toggle** is *meant to die*. If it's still around after the feature is at 100%, that's debt and you should be embarrassed by it.
- A **kill-switch** is *meant to live*. Deleting it removes your emergency brake. It needs a clear default (subsystem on) and must be tested by actually exercising the off path.
- An **experiment** must give a *consistent* answer per user for the whole run — a user who flips between variations pollutes your data. It's owned by people who care about statistical rigor, not by whoever wrote the code.
- A **permission toggle** is really business logic in flag clothing. It changes when contracts change, lives forever, and shouldn't be in your "clean these up" pile.

> **The test:** before you create a flag, name its type. If you can't, you don't yet understand why you're adding it — and you won't know when to remove it.

---

## Core Concept 2 — Targeting Rules in Practice

Targeting answers "what value does *this* user get?" Rules are evaluated top to bottom; first match wins; the default catches everyone else.

```json
{
  "key": "new-search-ranking",
  "defaultVariation": "control",
  "variations": ["control", "treatment"],
  "rules": [
    { "clauses": [{ "attribute": "email", "op": "endsWith", "value": "@ourcompany.com" }],
      "variation": "treatment" },
    { "clauses": [{ "attribute": "plan", "op": "in", "value": ["enterprise"] }],
      "variation": "treatment" },
    { "rollout": { "treatment": 10, "control": 90 } }
  ]
}
```

This says: staff get `treatment`; enterprise accounts get `treatment`; everyone else is split 10/90. Two subtleties that bite people:

1. **Consistency requires a stable bucketing key.** The 10% rollout isn't "roll a die each request." The SDK hashes `targetingKey` (usually user id) into a bucket 0–99; the *same* user always lands in the same bucket, so they get a stable experience and your rollout percentage is meaningful. Use a key that's stable across sessions.
2. **Attribute hygiene matters.** Targeting on `email endsWith @ourcompany.com` is convenient but brittle — contractors, test accounts, and acquisitions break it. Prefer an explicit attribute like `isInternal: true` set by your auth layer.

```go
// Passing rich context so rules have something to match on.
ctx := openfeature.NewEvaluationContext(user.ID, map[string]interface{}{
    "plan":       user.Plan,
    "country":    user.Country,
    "isInternal": user.IsStaff,
})
variation, _ := client.StringValue(ctx2, "new-search-ranking", "control", ctx)
```

---

## Core Concept 3 — Progressive Delivery Mechanics

"Progressive delivery" = release the change to a growing audience while watching health, with the ability to halt or reverse. Four mechanisms, often combined:

- **Canary (traffic-level).** Route, say, 5% of requests to a new *deployment* of the service. This is infrastructure-level and flag-independent — it ships a whole new version to a slice of traffic.
- **Percentage rollout (flag-level).** One deployment, but the *flag* is on for a growing % of users. Finer-grained than a canary and doesn't require a second deployment.
- **Ring / cohort deployment.** Named audiences in order: internal → beta opt-in → GA. Each ring is a gate.
- **Automated rollout by health metric.** A controller advances the rollout only if metrics (error rate, latency, custom SLOs) stay healthy, and auto-rolls-back if not.

That last one is where **Argo Rollouts** and **Flagger** live. A Flagger canary, for example, drives the percentage up automatically while checking metrics:

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata: { name: checkout }
spec:
  targetRef: { apiVersion: apps/v1, kind: Deployment, name: checkout }
  analysis:
    interval: 1m
    threshold: 5            # roll back after 5 failed metric checks
    maxWeight: 50           # cap canary at 50% before promoting fully
    stepWeight: 10          # +10% traffic each healthy interval
    metrics:
      - name: request-success-rate
        thresholdRange: { min: 99 }   # halt if success rate < 99%
      - name: request-duration
        thresholdRange: { max: 500 }  # halt if p99 latency > 500ms
```

The mental shift: progressive delivery turns "release" from a *button you press* into a *process the system runs* — and the system can pull the brake faster than a human watching a graph. Pair this with the `monitoring-alerting` skill: an automated rollout is only as trustworthy as the metric it watches.

---

## Core Concept 4 — How Evaluation Actually Works

When you call the SDK, one of two things happens:

- **Local (in-process) evaluation.** The SDK has already downloaded the entire ruleset and evaluates the rules against your context *in memory*. No network call per request. The user's attributes never leave your process — good for privacy and latency. This is the default for server-side SDKs (LaunchDarkly, Unleash, Flagsmith server SDKs).
- **Remote evaluation.** The SDK sends the context to a server, which evaluates and returns the value. Used by lightweight/edge/client SDKs where you don't want to ship the whole ruleset to a browser. Costs a round trip; exposes context to the server.

How the ruleset gets to a local SDK:

- **Streaming.** A persistent connection (SSE/websocket) pushes updates; a flag flip propagates in well under a second. Best for kill-switches where seconds matter.
- **Polling.** The SDK fetches the ruleset every *N* seconds. Simpler, more resilient to flaky connections, but a flip takes up to one poll interval to land.

And the part that keeps you up at night — **what happens when the flag service is unreachable:**

```js
// The default is not a nicety — it is your contract during an outage.
const showFeature = await client.getBooleanValue("new-export", false, ctx);
//                                                              ^^^^^
// If the SDK has a cached ruleset: it uses the last-known-good value.
// If it has nothing (cold start + service down): it returns this default.
```

Order of resilience: **last-known-good cache → bootstrapped/local file → hardcoded default.** A mature SDK persists the last ruleset to disk so a cold start during an outage still has values. Your job is to make the hardcoded default the *safe* value, because that's the floor everything falls back to.

---

## Core Concept 5 — The Flag Lifecycle and Flag Debt

Every release toggle has a lifecycle: **created → rolling out → fully on → code path removed → flag deleted.** The failure mode is getting stuck at "fully on" forever.

Why stale flags are genuinely dangerous, not just untidy:

- **Combinatorial test surface.** *n* boolean flags imply 2ⁿ behavioral combinations. With 20 live flags that's over a million; you test a handful and *hope* about the rest.
- **Dead code paths.** The old branch behind a long-on flag stops being maintained. It still compiles, still ships, and is one bad flip away from running in production.
- **Cognitive load.** Every reader of the code has to figure out whether each flag still matters.

The discipline that prevents debt:

```yaml
# A flag with an expiry date is a flag that gets noticed.
flags:
  - key: new-checkout
    type: release            # release toggles MUST expire
    owner: payments-team
    created: 2026-06-01
    expiresAt: 2026-07-15    # CI fails the build if this date passes and the flag still exists
    jira: PAY-1423
```

Mature teams enforce this mechanically: a CI check (or the flag platform itself) flags release toggles past their expiry, opens a cleanup ticket automatically, and maintains a **flag inventory** linking each flag to its owner, type, and the code that reads it. The cleanest moment to remove a flag is the day it hits 100% — defer it and it never happens.

---

## Core Concept 6 — Testing Code That Has Flags

A flag forks your code, so it forks your tests. The contract you must uphold:

> **Any flag can be on or off independently, and the system must work in every combination you ship.**

You cannot test 2ⁿ combinations, so be deliberate:

- **Test both paths of each flag in isolation.** For every flag, a test with it on and a test with it off.
- **Test the realistic combinations,** not the cartesian product — the combinations that will actually coexist in production (e.g. new-checkout + new-pricing, since they ship the same quarter).
- **Make flags injectable, not global.** Tests should set flag values explicitly, never read prod config.

```go
// A fake provider lets tests pin flag values deterministically.
func TestCheckout_NewPath(t *testing.T) {
    fake := openfeature.NewInMemoryProvider(map[string]any{"new-checkout": true})
    openfeature.SetProvider(fake)

    got := Checkout(testUser, cart)
    assert.Equal(t, "new", got.Path)   // exercises ONLY the new branch
}
```

The `mocking-strategies` and `integration-testing` skills go deeper. The key habit: a flag is not an excuse to skip testing the old path — until you delete the flag, *both* paths are production code.

---

## Real-World Examples

- **Kill-switch saves Black Friday.** The recommendation service starts timing out under peak load. SRE flips its ops toggle off; the site serves a static fallback and stays up. The toggle was added a year ago and never used until that day — exactly its job.
- **Experiment with stable buckets.** A pricing test splits users 50/50. Because bucketing hashes the account id, a user sees the same price across devices for the whole experiment, so revenue numbers are trustworthy.
- **Flagger auto-rollback.** A new image is canaried at 10%. p99 latency crosses 500ms; Flagger halts promotion and shifts traffic back to the stable version — no human in the loop, the incident never reaches users.
- **Flag debt audit.** A team finds 340 flags; 60% are release toggles that hit 100% months ago. They delete 180 flags and the matching dead branches in a two-week cleanup, and add an expiry-enforcing CI check so it never piles up again.

---

## Common Mistakes

- **One undifferentiated bucket of flags.** Without types, you can't reason about lifecycle or ownership, and cleanup becomes impossible.
- **Unstable bucketing key.** Bucketing on something that changes per session means users flip variations — breaks both UX and experiment validity.
- **Trusting an automated rollout's metric blindly.** If `request-success-rate` doesn't count the new feature's specific errors, Flagger promotes a broken release happily. Pick metrics that actually see the change.
- **Kill-switch you never test.** An emergency brake you've never pulled may not work. Exercise the off path in staging on a schedule.
- **Skipping the old-path test once the new path "works."** Both paths ship until the flag is deleted; both deserve tests.
- **Polling when you needed streaming.** A kill-switch on a 60-second poll means up to a minute of outage after you've already hit the brake.

---

## Apply it

1. Find a real component where **Feature Flags & Progressive Delivery** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Feature Flags & Progressive Delivery?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
