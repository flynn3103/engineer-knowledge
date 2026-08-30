# Feature Flags & Progressive Delivery — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Feature Flags & Progressive Delivery** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Feature Flags & Progressive Delivery

*A flag change is a production change with no deploy. Treat it like one, or it will treat you like Knight Capital.*

---

## Core Concept 1 — Flags as the Primary Rollback Mechanism

When a release goes bad, you have three levers, in order of speed:

1. **Flag kill-switch** — seconds. Flip the flag off; the bad path stops executing. No build, no deploy, no traffic shift.
2. **Traffic shift / canary abort** — minutes. Route traffic back to the previous version (Argo/Flagger, load balancer).
3. **Binary rollback / redeploy** — many minutes to tens of minutes. Re-deploy the previous artifact; re-runs the whole pipeline.

For anything you can gate behind a flag, **the flag is your fastest rollback** — and speed is what bounds the damage. This is why senior engineers deliberately ship risky changes *behind flags they can kill*, not just behind flags they can roll out. The rollout flag and the kill-switch are often the same flag used in two directions.

```go
// A change shipped so it can be killed instantly, with a safe default.
// Flipping "risky-new-pricing" to false reverts behavior in seconds,
// no deploy — strictly faster than the rollback in 07-rollback-and-roll-forward.
if flags.BoolValue(ctx, "risky-new-pricing", false) {
    price = newPricing(cart)
} else {
    price = legacyPricing(cart)   // legacy path stays alive until the flag is retired
}
```

The caveat that makes this *senior*: a flag only rolls you back if **the old path still exists and still works.** The moment you delete `legacyPricing`, the flag is no longer a rollback — it's just a fork that both lead to new code. Keep the off-path viable for the whole life of a kill-switch, and verify it (Concept 6). For the full revert-vs-roll-forward picture, see [Rollback & Roll-Forward](../07-rollback-and-roll-forward/README.md).

---

## Core Concept 2 — The Knight Capital Lesson

On 1 August 2012, Knight Capital Group deployed new trading code to its servers. The deploy reused an old flag — specifically, it repurposed a flag bit that, on one of eight servers, still activated a long-dormant, defunct piece of code called *Power Peg*. The deploy was not applied to all eight servers, so one server ran the new meaning of the flag while still wired to the old, dead code path the flag used to control.

When trading opened, that server began sending millions of unintended child orders. In **about 45 minutes** Knight accumulated a roughly **$460 million** loss and was effectively bankrupted within days. It is the canonical disaster of flag/release engineering, and every clause of it is a lesson:

- **Reusing a flag's meaning is lethal.** The same flag controlled two different behaviors at two different times. A flag's identity must be permanent and singular. Never recycle a flag key for a new purpose.
- **Dead code behind a stale flag is a loaded gun.** *Power Peg* should have been deleted years earlier. It survived only because removing dead code felt unnecessary. The flag kept it reachable.
- **Inconsistent rollout across instances is a fault, not a detail.** One of eight servers differed. Flag/config state must be applied atomically and verified across the whole fleet, or you get exactly this split-brain.
- **There was no kill-switch for the kill-switch.** Once it started, there was no fast, rehearsed way to stop it. Speed of detection and disablement is the whole game.

> Knight Capital is why this entire topic harps on three things: *delete dead code*, *never reuse a flag*, and *apply flag state consistently across the fleet.* The cost of skipping them is not a bug ticket — it's a company.

---

## Core Concept 3 — Flag Config IS Production Config

A flag change does everything a deploy does — alters production behavior for real users — but typically with **none of the controls**: no PR review, no CI, no canary, no signed artifact, no automatic audit trail of "who changed what and why." That gap is the senior-level risk to close.

Apply deploy-grade discipline to flag changes proportional to blast radius:

| Control | Low-risk flag (1% experiment) | High-risk flag (global kill-switch) |
|---|---|---|
| **Approval** | self-serve | two-person rule |
| **Audit** | logged | logged + alert to owning team |
| **Change scope** | gradual % allowed | staged: internal → canary → all |
| **Rollback** | flip back | rehearsed runbook + on-call aware |
| **Blast-radius preview** | optional | mandatory ("this affects N users") |

Concretely: the flag platform should show *how many users a change will affect before you commit it*, require a reason string, log every change immutably, and (for high-risk flags) gate behind a second approver — the **two-person rule** you'd never skip for a prod deploy. Treating "flip flag" as a casual UI action while treating "deploy" as sacred is the asymmetry that kills you. The `ci-cd-pipeline-design` skill's review-before-prod mindset applies to flag changes too.

---

## Core Concept 4 — Evaluation Consistency and Performance

Two properties of flag evaluation become first-order concerns at scale.

**Consistency.** When you flip a flag, your fleet doesn't update atomically. Instance A (streaming) sees it in 200ms; instance B (polling, 30s) sees it 28 seconds later. During that **consistency window** users may get different behavior on consecutive requests — fine for a cosmetic toggle, *not* fine for a flag that changes a data write format or a stateful workflow. For those, you need either fast streaming with bounded skew, or you design the change so both values are simultaneously safe (Concept 6).

**Performance.** Flag evaluation sits on the hot path of every request. Rules:

- Evaluate **locally, in-process**, from a cached ruleset. A network call per evaluation couples your latency *and* availability to the vendor's — unacceptable on the hot path.
- The ruleset refresh (stream/poll) is the only network dependency, and it's off the request path.
- Persist LKG to disk so a cold start during a flag-service outage still has values.
- Watch the cost of rich targeting: a flag with hundreds of rules and large segment lists evaluated millions of times/sec is real CPU. Keep rules lean; prefer attribute checks over big inclusion lists.

```go
// Hot-path evaluation must be a local memory lookup, never a blocking RPC.
// The provider streams ruleset updates on a background goroutine;
// BoolValue here touches only in-memory state + a hash.
val := client.BoolValue(ctx, "feature-x", false)   // ~microseconds, no network
```

> If your p99 latency moves when the flag *vendor* has a bad day, your evaluation is on the wrong side of the network. Fix that before anything else.

---

## Core Concept 5 — Governance at Team Scale

One team with twenty flags governs itself. Forty teams with two thousand flags need *policy*, or the system rots into an unauditable mess where nobody dares delete anything. Governance has four pillars:

1. **Naming.** A convention that encodes type and owner: `team.domain.purpose`, e.g. `payments.checkout.new-flow` or `search.ops.ranking-killswitch`. The name should reveal who owns it and whether it's a kill-switch.
2. **Ownership.** Every flag has a named owning team (not a person who left). Orphan flags are a governance failure; CI/the platform should reject flags without an owner.
3. **Audit.** Every change — value, targeting, who, when, why — is immutable and queryable. When an incident's timeline says "behavior changed at 14:03 with no deploy," the flag audit log is where you find the cause.
4. **Lifecycle policy.** Release toggles must carry an expiry; the platform opens cleanup tickets and (escalating) fails builds for overdue flags. Kill-switches and permission toggles are exempt but must be *declared* as long-lived, not just un-cleaned.

```yaml
# Governance metadata enforced at flag creation (rejected if incomplete).
key: payments.checkout.new-flow
type: release            # release | ops | experiment | permission
owner: payments-team     # must resolve to an active team
expiresAt: 2026-08-01    # required for type=release
riskTier: high           # high → two-person rule + staged change
description: "Routes checkout through the rebuilt pricing pipeline."
```

The cultural half of governance: a flag change is a *change*, and changes belong to teams. "Anyone can flip anything" feels empowering and is, at scale, a recipe for an unattributable outage.

---

## Core Concept 6 — Designing Flags That Are Safe to Flip

A flag is only a safe rollback lever if *both* values are safe at *any* moment, including mid-flip during the consistency window. This is design work, not config.

- **Both paths must be simultaneously safe.** If `new-write-format` is on for instance A and off for instance B, both formats are being written *right now*. Readers must handle both. This is the expand/contract pattern from [Rollback & Roll-Forward](../07-rollback-and-roll-forward/README.md) and database-migration discipline: make the schema/format tolerant of both states before you let the flag move.
- **No flag should change irreversible state on flip.** If flipping a flag deletes data or performs a one-way migration, you can't flip back. Decouple the destructive action from the flag.
- **Default to the survivable value.** When the SDK has nothing, it returns the hardcoded default. That default must be the value the system survives indefinitely on.
- **Keep the off-path warm.** A kill-switch's off path (the legacy code) must stay tested and deployable for the flag's whole life. Run it in staging, and periodically in production via the flag, so it doesn't bit-rot into the Knight Capital scenario.

```go
// SAFE: reader tolerates both formats, so the writer flag can flip either way
// at any instant without corrupting data — the flag is a true rollback lever.
func readRecord(b []byte) (Record, error) {
    if isNewFormat(b) {
        return decodeV2(b)
    }
    return decodeV1(b)   // off-path stays alive and exercised
}
```

---

## Core Concept 7 — Progressive Delivery Wired to SLOs

A rollout that a human watches is a rollout that fails on weekends. Senior practice wires progressive delivery to **guardrail metrics tied to your SLOs**, so the system promotes or aborts on its own.

```yaml
# Argo Rollouts: analysis gates each step on real SLI queries.
apiVersion: argoproj.io/v1alpha1
kind: Rollout
spec:
  strategy:
    canary:
      steps:
        - setWeight: 5
        - pause: { duration: 5m }
        - analysis:                         # SLO gate before going wider
            templates: [{ templateName: success-rate-and-latency }]
        - setWeight: 25
        - pause: { duration: 10m }
        - setWeight: 50
        - analysis: { templates: [{ templateName: success-rate-and-latency }] }
        - setWeight: 100
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata: { name: success-rate-and-latency }
spec:
  metrics:
    - name: error-budget-burn
      interval: 1m
      failureLimit: 2                       # abort + auto-rollback after 2 breaches
      provider:
        prometheus:
          query: |
            sum(rate(http_requests_total{job="checkout",code=~"5.."}[1m]))
              / sum(rate(http_requests_total{job="checkout"}[1m])) < 0.01
```

The principles: choose guardrails that *see the specific change* (a global success-rate may not catch a feature-specific bug — add a feature-scoped metric); make abort automatic and faster than a human; and remember that flag-level rollouts and deployment-level canaries are complementary — the flag controls *behavior*, the rollout controls *which binary serves traffic*. Lean on the `monitoring-alerting` skill to define guardrails that won't promote a quietly broken release.

---

## Core Concept 8 — Killing Flag Debt Systematically

Senior ownership means flag debt is *measured and bounded*, not hoped away.

- **Inventory as source of truth.** Reconcile the platform's flag list against code references (static analysis / linters that grep flag keys). Flags in the platform with no code reference are dead config; flags in code missing from the platform are unmanaged. Both are bugs.
- **Expiry enforcement with teeth.** Overdue release toggles escalate: ticket → warning in CI → failing build. Without teeth, expiry dates are decoration.
- **Cleanup as a first-class task.** Removing a flag means: confirm it's at a stable terminal value, delete the unused branch *and the now-dead function it called*, remove the flag from the platform, and verify nothing references it. The dead-code deletion is the Knight Capital lesson — a removed flag with surviving dead code is still a loaded gun.
- **Track the number.** Total live release toggles and median flag age are real engineering-health metrics. A rising trend means the cleanup loop is broken.

```bash
# Reconcile: flags defined in the platform but referenced nowhere in code = dead config.
comm -23 \
  <(flagctl list --type=release --json | jq -r '.[].key' | sort) \
  <(rg -o --no-filename 'flags\.\w+\("([a-z0-9.-]+)"' -r '$1' src/ | sort -u)
```

---

## Real-World Examples

- **Kill-switch beats rollback by 20 minutes.** A bad recommendation model ships. Redeploying the previous build would take ~25 minutes through CI; flipping the model's kill-switch reverts behavior in 4 seconds. Damage is bounded because the *lever was fast*.
- **The split-brain near-miss.** A flag flip propagates via 60s polling. A data-format flag goes on, and for ~50 seconds half the fleet writes v2 while half writes v1. It's fine *only* because the reader was built to accept both — a deliberate Concept-6 design. Had it not been, it's a smaller Knight Capital.
- **Governance catches an orphan.** An incident review traces a 14:03 behavior change to a flag with no owner and no audit reason. The org makes owner + reason mandatory at flag creation; the next incident's flag cause is found in 90 seconds.
- **SLO-gated rollout self-aborts.** A canary at 25% trips the error-budget-burn guardrail at 2am; Argo rolls back automatically. The on-call wakes to a resolved alert, not an outage.

---

## Common Mistakes

- **Deleting the legacy path while keeping the kill-switch.** Now the "off" position runs new code too — the flag is no longer a rollback, and you won't discover that until you need it.
- **Per-request remote evaluation on the hot path.** Couples your latency and availability to the vendor; the first vendor blip becomes your incident.
- **No blast-radius preview.** Flipping a global flag without seeing "this affects 4.2M users" is how a 1% intent becomes a 100% outage.
- **Reusing a flag key for a new purpose.** The literal Knight Capital mistake. A flag identity is permanent; new purpose = new flag.
- **Guardrail metrics that don't see the change.** A global success-rate green-lights a feature-specific bug. Add a metric scoped to the changed behavior.
- **Treating flag changes as un-auditable.** When an incident's cause is "config changed, no deploy," the absence of a flag audit log turns a 2-minute diagnosis into a 2-hour one.

---

## Apply it

1. State the system invariant that **Feature Flags & Progressive Delivery** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Feature Flags & Progressive Delivery fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
