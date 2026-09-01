# Rollback & Roll-Forward — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Rollback & Roll-Forward** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Rollback & Roll-Forward

*Reversibility is an architectural property you design for, pay for, and govern — not a feature you bolt on after the outage. At scale, the question is organizational as much as technical.*

---

## Core Concept 1 — Reversibility as a first-class design constraint

> The professional reframe: **reversibility is a requirement, evaluated at design and code-review time, with the same weight as correctness, security, and performance.** "How do we undo this?" is asked *before* merge, not discovered during an outage.

Operationalize it as a checklist applied to every non-trivial change:

```text
Reversibility review (gate before merge of risky changes):
  [ ] Schema changes are expand/contract; no destructive step in this release.
  [ ] Previous artifact is retained and will remain rollback-able.
  [ ] N-1 ↔ N API/message compatibility verified in CI (contract tests, buf breaking).
  [ ] Side-effecting code (email/payment/webhook) is flag-gated or has a compensation.
  [ ] Data written in a new format is readable by N-1 (dual-format window defined).
  [ ] Rollback procedure is automated or documented AND has been exercised.
  [ ] Cache keys are versioned so N-1 doesn't mis-read N's entries.
```

- This makes reversibility a *standing constraint* rather than a heroic recovery skill.
- Borrow Amazon's **one-way / two-way door** language: most changes should be engineered into two-way doors (reversible, decide fast, undo if wrong).
- When a change is genuinely a one-way door — a destructive migration, an irreversible data transformation — it must be *flagged as such*, reviewed at a higher bar, and sequenced so the irreversible step happens only after the reversible parts have been proven in production.

---

## Core Concept 2 — The irreversible-release anti-pattern

Name it so you can reject it in review. An **irreversible release** is any release you cannot roll back. They are almost always *accidental* — engineers don't set out to make a release irreversible; they make a local decision that silently removes the rollback option. The recurring causes:

1. **Destructive migration coupled to the deploy.** `DROP`/`RENAME` in the same release as the code using it.
2. **Broken N↔N-1 compatibility.** Removing an API field, tightening a contract, changing a message schema incompatibly.
3. **Irreversible side effects.** Sending emails, capturing payments, firing webhooks with no compensation.
4. **New-format data with no tolerant reader in N-1.** N writes records N-1 can't parse.
5. **Garbage-collected prior artifacts.** Retention policy deleted the only thing you could roll back to.

The professional discipline is to **convert one-way doors into two-way doors by sequencing**:

```text
Want to: delete a column and change the API.   (irreversible if done at once)

Sequence it:
  R1: EXPAND schema + tolerant-reader code      (reversible)
  R2: switch reads to new column, flag-gated     (reversible — flip flag)
  R3: additive API change, old field retained    (reversible — N-1 compatible)
  R4: soak; prove stability                       (reversible)
  R5: CONTRACT — drop column, remove old field   (the ONLY irreversible step,
                                                   taken only after R1–R4 proven)
```

The irreversible step shrinks to a single, late, well-understood release with nothing risky riding on it. **You don't avoid irreversibility; you isolate and defer it.**

---

## Core Concept 3 — Coordinating rollback across dependent services

- In a microservice system, rolling back one service can break others.
- Service A's N-1 may not understand service B's N, and vice versa. Rollback becomes a *distributed* problem.

**Principles for cross-service reversibility:**

- **Independent deployability requires independent reversibility.** If A can deploy without B, A must be able to *roll back* without B. This is purchased with N↔N-1 compatibility *at every interface*, enforced by contract tests so a rollback of A never breaks B.
- **Order matters, both ways.** If A's new feature depends on B's new capability, deploy B before A — and roll back A before B. Capture these dependencies explicitly; an ordered rollback runbook for a coordinated launch is part of the launch plan.
- **Avoid lockstep releases.** A release that requires three services to flip simultaneously is an irreversible release in disguise — there's no clean rollback point. Decompose it into independently reversible steps using flags and additive contracts.
- **Distributed side effects need sagas/compensations.** When a workflow spans services and has committed effects, "rollback" means executing **compensating transactions** (refund, cancel, retract), not reverting code. Design the saga's compensations up front. See the `event-driven-architecture` concepts and the `high-availability-patterns` skill.

```text
Coordinated launch rollback order (recorded in the launch runbook):
  Deploy order:   B (capability) → A (consumer) → flag on
  Rollback order: flag off → roll back A → roll back B
  Verify N-1 compatibility at each hop before proceeding.
```

- The platform-level answer is **deploy/release decoupling via flags**: deploy all services dark in any order (they're all backward-compatible), then *release* the cross-cutting behavior with a single flag flip — which is also a single, instant, coordinated *rollback* point.
- This is the cleanest distributed rollback primitive that exists.

---

## Core Concept 4 — Rollback governance and decision authority

- At scale, the bottleneck in recovery is often not the mechanism but the *decision*.
- Who is allowed to roll back? Who decides between rollback and roll-forward at 3 a.m.? Governance answers this before the incident.

- **Single decision authority during incidents.** The **incident commander** owns the rollback/roll-forward call. Not a committee, not a Slack debate. Pre-authorize the IC to roll back tier-1 services without further sign-off — recovery speed dies in approval chains.
- **Pre-authorized, bounded autonomy.** On-call engineers should be *pre-approved* to execute rollback and kill-switches within a defined blast radius (their service). No change-advisory-board ticket to stop an outage.
- **Break-glass with audit.** Emergency rollback may bypass normal gates (e.g., expedited hotfix), but every bypass is logged, attributed, and reviewed afterward. Speed now, accountability later — see how quality gates handle break-glass in [Release Branching & Trains](../release-branching-and-trains/professional.md) and the broader quality-gates material.
- **Roll-forward vs rollback decision rights.** Codify the default: e.g., "roll back unless a destructive migration or irreversible state makes it unsafe, in which case roll forward; IC decides ties." Removing the ambiguity removes minutes from MTTR.
- **Blast-radius-aware authority.** Flipping a global kill switch that affects all customers may need a higher authority than rolling back one service in one region. Tier the authority to the blast radius.

```text
Decision matrix (encoded in the incident policy):
  Single service, no shared state      → on-call, pre-authorized, no approval
  Cross-service / shared data          → incident commander
  Global flag / all-customer impact    → IC + service owner ack
  Break-glass (bypass gate)            → allowed, auto-logged, post-incident review
```

> The governance goal: **make the safe action the fast action.** If the policy forces a debate to roll back, the policy is the outage.

---

## Core Concept 5 — The cost of fast rollback

Fast rollback is an insurance premium, and someone pays it. Professionals make the cost explicit and right-size it per workload tier.

| Capability | What it buys | What it costs |
|------------|--------------|---------------|
| **Blue-green** | Seconds to cut back; instant rollback | ~2× capacity during the window; orchestration complexity |
| **Warm standby (prior version kept running)** | No cold-start on rollback | Idle compute paying to wait |
| **Artifact retention (N..N-k)** | A binary to roll back to | Registry storage; retention/GC policy management |
| **Dual-format data / tolerant readers** | Rollback over data changes | Engineering effort; transient storage of both formats |
| **Feature-flag platform** | Instant behavioral rollback, no deploy | Flag-management tooling, flag debt/cleanup cost |
| **Auto-rollback (Argo/Flagger)** | Near-zero MTTR | Controller complexity; risk of false aborts |

- The trade-off is **rollback speed vs steady-state cost**. Blue-green gives the fastest cutover but doubles capacity; rolling deploys are cheaper but slower to reverse; flags are cheap at runtime but carry maintenance debt.
- Tier-1 revenue services may justify blue-green and warm standby; a batch job does not — a slow `rollout undo` is fine there.
- **A fast pipeline is itself a rollback-cost reducer.** If you can rebuild and ship in 3 minutes, roll-forward is cheap and you can carry less warm standby. Investing in pipeline speed (caching, fast gates — see [Release Automation](../release-automation/professional.md)) reduces the capacity you must pay to keep warm.
- The cheapest fast recovery is often a fast pipeline plus pervasive flags, not double infrastructure.

---

## Core Concept 6 — Choosing the strategy per workload, not per company

The senior level posed rollback culture vs roll-forward culture as an org choice. The professional refinement: **it's a per-workload decision, governed by org-wide policy but applied by tier.** A single company runs both.

```text
Workload tier      Recovery default        Mechanism investment
-----------------  ----------------------  -------------------------------
Tier-1 revenue     Auto-rollback           Blue-green + flags + warm standby
Customer-facing    Rollback, fast          Canary + auto-abort + flags
Internal tools     Roll-forward            Plain rolling deploy, fast pipeline
Batch / async      Roll-forward            rollout undo is fine; idempotent jobs
Data pipelines     Roll-forward + replay   Reprocessing; rarely roll back code
```

Drivers of the choice:

- **Deploy frequency** — high frequency favors roll-forward (forward is routine and fast).
- **Pipeline speed** — slow pipeline forces rollback (can't fix forward in time).
- **Flag coverage** — heavily flag-gated systems get instant behavioral rollback for free, pushing toward roll-forward-with-kill-switch.
- **Statefulness** — stateful systems make code rollback hard, often forcing roll-forward + compensation.
- **Regulatory/blast radius** — high-stakes systems favor the *most proven* recovery, which is usually rollback to a known-good artifact.

The professional sets the *policy* (which tier gets which default, what each must invest in) and ensures the platform makes the chosen path genuinely fast for each tier.

---

## Core Concept 7 — Organization-wide rollback as a platform capability

- The endgame: individual teams should not each invent rollback.
- The platform provides it as a **paved road**, so that *every* service inherits tested, fast, governed recovery by default.

What a platform team ships:

- **A standard progressive-delivery template** (Argo Rollouts/Flagger) with auto-abort wired to org-standard SLIs — opt-out, not opt-in.
- **Enforced artifact retention** in the registry so a prior version is *always* present to roll back to; GC cannot delete the last N.
- **CI gates for reversibility**: destructive-migration detection, `buf breaking`/contract tests, dual-format checks — a release that breaks reversibility fails to merge.
- **A central feature-flag platform** with audit, so kill-switch is a one-line capability for every team.
- **Org-wide MTTR / rollback-time dashboards** with SLOs per tier, so reversibility is measured and regressions are visible to leadership.
- **Game-day-as-a-service**: scheduled, automated chaos that exercises each service's rollback path and reports recovery time.

> This turns reversibility from a per-team heroics problem into an *org property*: the default service is reversible because the platform makes irreversibility hard to build by accident. That is the highest expression of this topic — **the safe thing is the easy thing, everywhere, by default.**

---

## Real-World Examples

- **Sequenced irreversibility.** A platform team needs to re-shard a core table — genuinely irreversible. They sequence it across five releases (dual-write, backfill, verify, switch reads behind a flag, soak two weeks) so that until the very last contract step, a flag flip restores the old path instantly. The one-way door is reduced to a single, boring, late release.
- **Cross-service rollback order saves a launch.** A coordinated launch spans payments, ledger, and notifications. The launch runbook encodes deploy order and the *reverse* rollback order, all behind a single feature flag. When a ledger bug appears, the IC flips one flag — instantly and atomically rolling back behavior across all three services. No service code was reverted.
- **Governance removes 12 minutes from MTTR.** A post-incident review finds rollback was delayed 12 minutes waiting for a manager to approve. The org pre-authorizes on-call to roll back tier-1 within their service blast radius. Next incident: rollback in 90 seconds.
- **Right-sizing cost.** Finance flags the bill for keeping blue-green warm on 40 internal services. The platform team downgrades non-tier-1 services to rolling deploys with a fast pipeline, keeping blue-green only where revenue justifies the 2× capacity. Recovery stays adequate; spend drops materially.

---

## Common Mistakes

- **Treating reversibility as an ops concern, not a design constraint.** It belongs in design review, with correctness and security.
- **Lockstep multi-service releases.** No clean rollback point; decompose with flags and additive contracts.
- **Approval chains in the recovery path.** Pre-authorize rollback; the safe action must be the fast action.
- **Paying for blue-green everywhere.** Tier the cost to the workload; a fast pipeline plus flags is often cheaper.
- **Letting retention GC the last good artifact.** Enforce minimum retention at the platform level.
- **Designing the saga's happy path but not its compensations.** Distributed rollback *is* the compensations.
- **One company-wide recovery doctrine.** Choose per workload tier; run both rollback and roll-forward.

---

## Apply it

1. Define the user or business outcome that **Rollback & Roll-Forward** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Rollback & Roll-Forward?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- A feature spans three services that must all change together — how do you keep it reversible?
- The org is debating rollback culture vs roll-forward culture — how do you frame the decision?
- Fast rollback isn't free — what does it cost, and how do you decide how much to buy per workload tier?
- Who should be allowed to roll back during an incident, and why does that governance matter for MTTR?
- How do you isolate and defer a genuinely irreversible change, such as dropping a column?
