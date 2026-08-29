# Testing in Production — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Testing in Production** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Testing in Production
> *Observability as foundation, blast-radius math, automated rollback, chaos discipline — and what only production can verify.*

---

## Core Concept 1 — Observability Is the Foundation

Testing in production is *meaningless* without observability — it is the precondition that makes every other technique safe. The logic is mechanical:

> A guardrail can only fire on a signal it can see. No signal → no guardrail → no safe test.

The maturity check before you allow prod testing at all:

```text
Can you, within 60 seconds, answer per deployed version:
  [ ] error rate (by endpoint, by status class)?
  [ ] latency distribution (p50/p95/p99, not just mean)?
  [ ] saturation (CPU, memory, connection pools, queue depth)?
  [ ] business KPIs (checkout rate, signups, revenue/min)?
  [ ] a single request's path across services (distributed trace)?
If any box is empty, you are not ready to test in production.
```

Three observability requirements specific to prod testing:

1. **Version-tagged telemetry.** Every metric, log, and span must carry the build/version label, or you can't separate canary from baseline. This is the single most common gap.
2. **High-cardinality, event-based telemetry.** Aggregates hide the bug ("p99 is fine") that high-cardinality data reveals ("p99 is fine *except* for users in region X on app v2.3 calling endpoint Y"). Charity Majors' core argument for observability over classic monitoring.
3. **Distributed tracing.** When the canary's error rate rises, traces tell you *where* — which downstream call, which service boundary — turning a symptom into a diagnosis.

The `observability-stack` skill is the dependency this entire topic is built on. Sequence it first in any platform plan.

---

## Core Concept 2 — Blast-Radius Control as Engineering

"Small blast radius" is an engineering quantity, not a vibe. Make it explicit and bound it on multiple axes:

| Axis | Control | Example |
|------|---------|---------|
| **Traffic %** | Weighted routing | 1% → 5% → 25% → 50% → 100% |
| **Audience** | Flag targeting | Internal → beta → free-tier → paying |
| **Geography** | Regional rollout | One low-traffic region first |
| **Cell / shard** | Cell-based architecture | One cell of N before the fleet |
| **Time** | Bake duration | 30 min minimum to surface slow leaks |
| **Reversibility** | Kill switch latency | Disable in < 5s, no deploy |

Quantify the worst case *before* you start: *"At 1% with our 2M daily users and a hypothetical 100% failure of the new path, ~20k users are affected for up to 5 minutes until auto-rollback — within our error budget."* If that sentence is unacceptable, shrink the radius (smaller %, internal-only, shorter bake) until it is.

**Cell-based architecture** is the senior-grade structural answer: partition the fleet into independent cells, each serving a subset of users, so any change — and any failure — is naturally contained to one cell. Testing in production becomes "test in one cell," and the blast radius is architecturally bounded rather than configured per-deploy.

---

## Core Concept 3 — Automated Rollback on SLO Breach

A human watching a dashboard is not a guardrail; they blink, sleep, and take 4 minutes to react. The rollback decision must be **automated and fast**. Wire SLO breach directly to revert:

```yaml
# rollback-controller.yaml — automated abort on multi-window burn rate
gate:
  baseline: app=payments,track=stable
  canary:   app=payments,track=canary
  rules:
    - name: error-rate
      query: errors / total
      # compare canary to baseline using a robust test, not a fixed threshold
      condition: "canary_p > baseline_p * 1.5 AND canary_p > 0.005"
    - name: latency-p99
      condition: "canary_p99 > baseline_p99 * 1.2"
    - name: budget-burn
      # multiwindow: fast burn (5m) AND slow burn (1h) both hot => page+abort
      condition: "burn_5m > 14.4 AND burn_1h > 6"
  on_breach:
    - action: rollback          # shift traffic back to stable, instantly
    - action: page              # then tell a human what already happened
    - action: freeze            # block further promotions until reviewed
```

Design principles for the rollback decision:

- **Compare to a live baseline pool**, not to fixed numbers — prod's "normal" drifts.
- **Use robust statistics** (Mann-Whitney U, median absolute deviation), not mean ± threshold, so one outlier request doesn't trip or mask the gate.
- **Multi-window burn-rate alerting** (fast + slow windows) catches both sudden cliffs and slow leaks while suppressing false pages — see the `monitoring-alerting` skill and Google's SRE alerting guidance.
- **Rollback must itself be safe and tested.** A rollback that breaks (e.g., a non-backward-compatible DB migration) is worse than the bug. This is the hard coupling to [rollback/roll-forward](../../release-engineering/07-rollback-and-roll-forward/): forward-compatible schema changes, expand/contract migrations, no destructive steps mid-rollout.

The mark of maturity: **the machine rolls back, then tells the human.** The human's job is to investigate, not to react.

---

## Core Concept 4 — What Only Production Can Verify

Be precise about *why* this practice exists — the bug classes that pre-prod testing structurally cannot catch:

| Class | Example | Why staging misses it |
|-------|---------|-----------------------|
| **Real-scale performance** | Query that's fine on 1k rows, times out on 40M | Staging lacks the data volume |
| **Real data edge cases** | A name with a zero-width space breaks parsing | Synthetic data is too clean |
| **Real dependency behavior** | Third-party API returns 200 with an error body, or throttles at p99 | Mocks are too cooperative |
| **Real concurrency** | A race that needs 5k simultaneous writers to manifest | Staging has no real concurrency |
| **Emergent / systemic** | Retry storm + thundering herd cascading across services | Only appears at fleet scale |
| **Real user behavior** | Users paste 10MB into a field "no one would" | Real users are adversarial and creative |
| **Config / infra drift** | Prod's load balancer timeout differs from staging's | Environments are never identical |

The strategic point for the pyramid: **push everything down that *can* go down.** Anything verifiable cheaply in a unit or integration test belongs there — fast, deterministic, no user risk. Reserve production for the residue in the table above: the confidence that is *physically impossible* to obtain elsewhere. Testing in production is the apex precisely because it's expensive and risky; spend it only on what nothing cheaper can buy. (See [test strategy and the pyramid](../01-test-strategy-and-the-pyramid/).)

---

## Core Concept 5 — Chaos Engineering as a Discipline

Chaos engineering is the scientific method applied to resilience. The discipline lives in the *hypothesis*, not the *injection*.

The canonical structure (per Rosenthal & Jones, *Principles of Chaos Engineering*):

1. **Define steady state** as a measurable output (business metric preferred): *"checkout success ≥ 99.9%, p99 < 800ms."* Not "the system is up" — a number.
2. **Hypothesize it holds** under a real-world fault: *"If one payment pod dies, steady state holds because traffic reroutes to the other two."*
3. **Inject the real-world event** in production (or a prod-like cell): kill the pod, add 300ms latency, blackhole a dependency.
4. **Try to disprove** the hypothesis — look for the steady state breaking.
5. **Bound the blast radius** and **arm abort conditions** so a disproved hypothesis is contained, not catastrophic.

```yaml
# game-day-experiment.yaml
title: "Payment service survives single-pod loss"
steady_state:
  metric: checkout_success_rate
  expected: ">= 0.999 over 5m"
fault:
  type: pod-kill
  target: { service: payments, count: 1, of: 3 }
blast_radius:
  scope: "cell-3 only (8% of traffic)"
  schedule: "Tue 14:00, on-call + service owner present"   # supervised game day
abort_when: "checkout_success_rate < 0.99"
auto_rollback: "restore pod + remove fault injection"
learning:
  record: "did it hold? what surprised us? what do we fix?"
```

Maturity progression: **manual game days** (supervised, scheduled) → **automated experiments in CI/staging** → **continuous automated chaos in prod** (Chaos Monkey style). You earn the right to the next stage by surviving the previous one. The point is never destruction — it's *converting unknown failure modes into known, fixed ones*. Chaos validates the resilience patterns from the `high-availability-patterns` skill (circuit breakers, bulkheads, timeouts, graceful degradation): an untested circuit breaker is a hypothesis, not a safeguard.

---

## Core Concept 6 — Designing a Statistically Sound Canary

A naive canary ("error rate < 1%") produces both false promotions and false rollbacks. A sound one treats canary analysis as a hypothesis test.

- **Run a control alongside the canary.** Three pools: stable (existing), baseline (same old code, fresh instances — to isolate the "new instance" effect), canary (new code). Compare *canary vs. baseline*, not canary vs. stable, so you don't attribute cold-cache effects to the new code.
- **Compare distributions, not point values.** Use Mann-Whitney U / Kolmogorov-Smirnov on latency; the median and tail, not the mean (means hide tail regressions).
- **Account for traffic mix.** A 1% canary may receive an unrepresentative slice (e.g., all from one region). Use consistent hashing on a stable key so the canary sample is representative.
- **Set the bake time by the slowest signal.** Memory leaks and cache effects need tens of minutes; don't promote faster than your slowest failure mode manifests.
- **Beware metric flakiness.** Canary analysis can be flaky for the same reasons tests are — see [flaky tests and reliability](../12-flaky-tests-and-reliability/). Require N consecutive bad windows, not one, before aborting.

Netflix's **Kayenta** (automated canary analysis) encodes exactly this: weighted metric groups, statistical comparison, a pass/marginal/fail score. The takeaway: **canary analysis is itself a testing system and deserves testing-system rigor.**

---

## Core Concept 7 — Side-Effect Isolation & Idempotency

Zero-impact techniques (shadow, dark launch, chaos read paths) are only zero-impact if side effects are isolated. The senior responsibility is to make that guarantee real.

```text
SHADOW TRAFFIC — side-effect containment checklist
  [ ] DB writes -> routed to a shadow DB OR wrapped in a rollback'd txn OR no-op'd
  [ ] external calls (charge card, send email, push notif) -> stubbed/sandboxed
  [ ] message publishes -> dropped or routed to a /dev/null topic
  [ ] caches -> separate namespace (don't poison the prod cache)
  [ ] idempotency keys -> distinct, so shadow can't dedupe-collide with real
  [ ] shared downstream load -> capped (mirror % < 100 if dependency is hot)
```

Two deeper points:

- **Idempotency is the safety property that makes prod testing forgiving.** If retries, replays, and shadow requests are idempotent, a duplicate or a stray request is harmless. Designing operations to be idempotent (idempotency keys, upserts, dedup windows) widens what you can safely do in prod.
- **Read/write asymmetry.** Read-path testing in prod is cheap and safe; write-path testing is where the danger lives. Architect the new code so the write path is the *last* thing exposed, behind the strongest isolation.

---

## Core Concept 8 — Error Budgets Govern Risk

The error budget is the currency that makes "how much risk may we take in prod" a number instead of an argument.

- **Budget = (1 − SLO) × window.** A 99.9% monthly SLO ≈ 43 minutes of allowed badness per month.
- **Testing in production *spends* the budget.** Every canary regression, every chaos experiment that nicks steady state, every shadow-induced overload draws down the budget.
- **Budget remaining sets the risk posture:**

```text
budget healthy (> 50% left)  -> ship aggressively, run chaos, widen canaries faster
budget thin    (< 25% left)  -> tighten gates, slow rollouts, defer chaos
budget exhausted             -> FREEZE risky changes; reliability work only
```

This makes the practice *self-regulating* and aligns it with SRE: you are not asking permission to take risk; you are spending a pre-agreed budget, and the budget itself enforces the brakes. It also resolves the dev-vs-ops tension — both sides agreed to the SLO, so the budget is neutral. (Deepens in the professional page's SRE integration; grounded in the `monitoring-alerting` skill.)

---

## Real-World Examples

- **Netflix:** Kayenta for automated canary analysis + Chaos Monkey/Simian Army injecting failure continuously; resilience is *measured*, not assumed.
- **Google SRE:** error budgets as the formal governor of release risk; multi-window burn-rate alerting as the rollback trigger.
- **Amazon:** cell-based architecture as structural blast-radius control — a bad change is contained to a cell by design.
- **GitHub Scientist:** statistically rigorous shadowing of refactors against real traffic, returning only the trusted result.
- **Slack / Stripe:** heavy idempotency-key design so retries and replays in prod are inherently safe.

---

## Common Mistakes

| Mistake | Why it's wrong | Do instead |
|---------|----------------|------------|
| Untagged telemetry | Can't separate canary from baseline | Version-label every metric/log/span |
| Mean-based canary gates | Tail regressions hide in the mean | Compare distributions, p99, robust stats |
| Human-triggered rollback only | Too slow, fails at 3 a.m. | Automate SLO-breach → rollback |
| Rollback path untested | A broken rollback is worse than the bug | Test rollback; expand/contract migrations |
| Chaos without steady-state hypothesis | Destruction, not science | Define measurable steady state + abort |
| Ignoring shadow side effects | "Zero-impact" silently mutates prod | Isolate writes/external calls/caches |
| Testing in prod with budget exhausted | Compounding harm | Freeze risk when budget is spent |

---

## Apply it

1. State the system invariant that **Testing in Production** must protect.
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

- Which invariant must remain true when Testing in Production fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
