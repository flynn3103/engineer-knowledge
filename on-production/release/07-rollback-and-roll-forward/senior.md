# Rollback & Roll-Forward — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Rollback & Roll-Forward** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Rollback & Roll-Forward

*A rollback path that has never been exercised is a hope, not a plan. Make recovery a tested, automated, measured capability — not a runbook nobody has read.*

---

## Core Concept 1 — Rollback as a tested, rehearsed capability

> The defining senior belief: **an unexercised rollback path does not exist.** Treat rollback like a backup — backups that are never restored are folklore. You verify rollback the same way: by doing it, regularly, on purpose.

**What "tested" means in practice:**

- **Retention is enforced and verified.** The previous N artifacts are pinned in the registry and protected from GC. A scheduled job actually pulls and runs the N-1 image to confirm it still starts. (Immutability and retention live in [Registries & Distribution](../05-registries-and-distribution/senior.md).)
- **The migration is provably reversible.** CI runs the N-1 code against the post-migration schema and asserts it passes. If it doesn't, the migration is destructive and the release is blocked until expand/contract is applied.
- **Game days exercise the real path.** On a schedule, in staging that mirrors production, deploy a known-bad version and recover using only the documented procedure and tooling — measuring how long it takes and where people stumble.

```bash
# Game-day skeleton: deploy a deliberately bad version, then recover.
kubectl set image deployment/checkout app=registry/checkout:chaos-bad
kubectl rollout status deployment/checkout --timeout=120s || true
START=$(date +%s)
kubectl rollout undo deployment/checkout            # the rehearsed move
kubectl rollout status deployment/checkout
echo "rollback took $(( $(date +%s) - START ))s"    # this number is the deliverable
```

- The output of a game day is not "it worked." It is a *number* (recovery time), a *list of friction points*, and *fixes* for them.
- Run it often enough that the muscle memory survives the panic of a real Sev-1.

---

## Core Concept 2 — Automated rollback on SLO breach

- Humans are slow and stressed during incidents.
- The fastest, most reliable rollback is one that fires automatically when objective health signals degrade — before a human even pages.
- Progressive-delivery controllers make this declarative.

**Argo Rollouts** with an analysis template that auto-aborts on error-rate breach:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata: { name: checkout }
spec:
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 10m }
      analysis:
        templates: [{ templateName: error-rate }]
        startingStep: 1            # begin analysis at 10% weight
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata: { name: error-rate }
spec:
  metrics:
    - name: error-rate
      interval: 30s
      failureLimit: 2              # 2 bad samples → abort
      successCondition: result < 0.01
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            sum(rate(http_requests_total{job="checkout",code=~"5.."}[2m]))
            / sum(rate(http_requests_total{job="checkout"}[2m]))
```

- When the canary's 5xx ratio exceeds 1% for two intervals, the rollout **auto-aborts**: traffic snaps back to the stable ReplicaSet and the new version is held at zero weight.
- No human, no page-to-action delay. The same applies to Flagger with its `webhooks` and metric checks.

Two design notes:

- **Auto-rollback only works if the *automated* path is safe** — i.e., no destructive migration in the rollout. Automation cannot un-drop a column. Auto-rollback is the *enforcement* of the expand/contract discipline.
- **Pick signals that move fast and matter.** Error rate and latency (golden signals) react in seconds; business KPIs are better as a slower, secondary gate. The `monitoring-alerting` skill covers choosing SLIs that make good rollback triggers.

---

## Core Concept 3 — Rollback time as an SRE metric (MTTR)

- If you can't measure recovery, you can't improve it.
- **Rollback time is a first-class reliability metric** and a major component of MTTR (Mean Time To Recovery), one of the four DORA metrics.

Decompose the recovery clock so you can attack each segment:

```
MTTR = detect + decide + act + verify

  detect  : time from bad deploy to alert (improve: better SLIs, faster windows)
  decide  : time from alert to "roll back" decision (improve: clear authority, runbook)
  act     : time to execute the rollback (improve: kill switch > redeploy; automation)
  verify  : time to confirm health restored (improve: health checks, dashboards)
```

- Track the *distribution*, not just the mean — p50 and p95 rollback times tell different stories.
- Set an explicit objective, e.g. "p95 rollback under 5 minutes for tier-1 services," and treat regressions against it as bugs.
- Auto-rollback collapses `detect + decide + act` into near-zero, which is why it's the single biggest MTTR lever you have.
- A useful corollary: **the cheaper and faster rollback is, the more aggressively you can ship.** Fast recovery is what *licenses* high deploy frequency — the two DORA velocity metrics and the two stability metrics reinforce each other.

---

## Core Concept 4 — Mixed-version compatibility as a contract

- At the middle level you learned N and N-1 must interoperate.
- At senior level you make that a *contract you can verify in CI*, not a hope.

- **API compatibility** — enforce with consumer-driven contract tests (Pact) and schema linting (e.g., `buf breaking` for protobuf, OpenAPI diff). A breaking change *fails the build*, not production.

```bash
# protobuf: fail CI if the new schema breaks the previous one
buf breaking --against '.git#branch=main'
```

- **Message/event compatibility** — register schemas in a schema registry with a compatibility policy (`BACKWARD` so new producers don't break old consumers). For a rollback you also need `FORWARD` (old producers, new consumers), so practically you want `FULL` compatibility across the rollback window.
- **Tolerant readers everywhere** — code must ignore unknown fields and supply defaults for missing optional ones. This is what lets N and N-1 share a wire format without lockstep deploys.

> The senior framing: **backward compatibility is not a courtesy, it's the precondition for rollback.** Any change that breaks N↔N-1 interop has secretly converted itself into an *irreversible* release. Catch those in CI.

---

## Core Concept 5 — Idempotency and the safe-to-retry property

- Rollbacks, rollouts, and automated recovery all re-run operations: a pod restarts, a migration step re-applies, a message redelivers, a reconcile loop fires again.
- If those operations aren't **idempotent**, the chaos of a rollback *creates* corruption.

Design for safe replay:

- **Migrations** — `ADD COLUMN IF NOT EXISTS`, guarded backfills (`WHERE col IS NULL`), upserts over inserts. A half-applied migration must be safe to re-run from the top.
- **Message handlers** — dedupe on an idempotency key so a redelivered event during version churn doesn't double-charge a customer.
- **Reconcilers** — converge to desired state regardless of current state; never assume a delta.

```sql
-- Idempotent backfill: re-running it is a no-op once complete.
UPDATE users SET name = full_name
WHERE name IS NULL AND full_name IS NOT NULL;
```

- During a rollback, the system is in a *partially transitioned* state by definition — some nodes new, some old, some operations half-done.
- Idempotency is what makes that state recoverable rather than corrupting.

---

## Core Concept 6 — Stateful systems: when rollback is genuinely hard

Stateless services roll back trivially. The hard cases are stateful, and a senior must recognize them:

- **Databases** — handled by expand/contract; the schema is forward-only, so "rollback" means rolling back *code*, never the schema. You essentially never roll a schema backward in production.
- **Data already written in the new format** — if N wrote records the old format can't parse, you must keep a tolerant reader in N-1 or you cannot roll back. Plan the dual-format window *before* shipping N.
- **Caches and derived state** — a rollback may leave caches populated with new-format entries the old code mis-reads. Version your cache keys (`cache:v2:...`) so old and new code don't collide.
- **External side effects** — emails sent, payments captured, webhooks delivered. These *cannot* be rolled back at all. The only mitigation is to gate side-effecting code behind flags so you can stop the effect, and to design compensating actions (refund, retraction).
- **Stateful workloads (StatefulSets, leader election)** — rolling these back has ordering and quorum constraints; an in-place rollback can violate invariants. The `high-availability-patterns` skill covers safe rollback of stateful clusters.

> The principle: **identify every piece of state your release touches and ask "does this come back when the code does?" If not, you have an irreversibility you must design around** — usually with flags, dual-format reads, or compensating actions.

---

## Core Concept 7 — Roll-forward culture vs rollback culture

Mature organizations make a deliberate *cultural* choice between two valid stances:

| | **Rollback culture** | **Roll-forward culture** |
|---|---|---|
| Default recovery | Return to N-1 | Fix and ship N+1 fast |
| Requires | Reliable, fast, tested rollback | Very high deploy frequency, fast pipeline, trunk-based, flags |
| Strength | Proven artifact, low risk per recovery | No "stuck on old version," small forward diffs |
| Risk | Rollback can be impossible (state) | Fixing forward under pressure can introduce new bugs |
| Fits | Lower deploy frequency, regulated, batch releases | Continuous deployment, feature-flag-heavy, elite DORA |

- The highest-performing teams trend toward **roll-forward via feature flags**: deploy continuously, gate everything behind flags, and "recover" by flipping flags (itself an instant rollback of *behavior* without a code rollback). The deploy and the release are decoupled — see [Feature Flags & Progressive Delivery](../06-feature-flags-and-progressive-delivery/senior.md).
- This is *not* universal advice. If your pipeline takes 40 minutes, roll-forward means 40 minutes of pain; rollback is correct.
- The senior job is to *choose consciously* based on deploy frequency, pipeline speed, and how much of your system is flag-gated — and to invest in whichever path you've chosen so it's genuinely fast.

---

## Real-World Examples

- **Auto-abort saves the SLO.** A canary at 10% trips the error-rate analysis after 90 seconds; Argo Rollouts aborts automatically and snaps traffic back to stable. The on-call engineer wakes up to a resolved incident and a clean post-mortem timeline. `detect + decide + act` was effectively zero.
- **The game day that found the gap.** A team's quarterly game day reveals the N-1 image was garbage-collected by an aggressive registry retention policy — they literally *could not* roll back. They fix retention before it bites them in a real incident. The rollback "plan" had been fiction.
- **Irreversible side effect.** A release double-sends order-confirmation emails. Code rolls back in seconds, but the emails are gone — irreversible. Postmortem action: gate all outbound email behind a flag and add idempotency keys so redelivery during churn can't double-send.
- **Contract test catches an irreversible release.** A proto change removes a field N-1 consumers still read. `buf breaking` fails CI. The change is reworked as additive — preserving the rollback window — *before* it ever reaches production.

---

## Common Mistakes

- **A rollback runbook nobody has executed.** Game-day it or assume it's broken.
- **Auto-rollback over a destructive migration.** Automation will roll the *code* back into a schema it can't read. Auto-rollback presumes expand/contract.
- **Triggering auto-rollback on slow/noisy signals.** Use fast golden signals; business KPIs flap and cause false aborts.
- **Not measuring rollback time.** If MTTR isn't tracked with an SLO, it silently regresses.
- **Treating compatibility as etiquette.** Breaking N↔N-1 interop quietly makes the release irreversible. Gate it in CI.
- **Ignoring side effects.** Emails, payments, and webhooks don't roll back. Flag them; design compensation.
- **Choosing roll-forward culture with a 40-minute pipeline.** Roll-forward only works when forward is *fast*.

---

## Apply it

1. State the system invariant that **Rollback & Roll-Forward** must protect.
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

- Which invariant must remain true when Rollback & Roll-Forward fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
- How would you design an automated rollback that triggers on SLO breach, and what precondition does it depend on?
- How would you measure whether your rollback capability is actually good?
- A release drops a column and the checkout error rate spikes — what's your recovery path, and why can't you just roll back?
- Why is an unexercised rollback runbook effectively no rollback plan at all?
- A release double-sends confirmation emails; the code rollback finishes in seconds — is the incident over? Why or why not?
- During a rollout you see intermittent, non-deterministic request failures — what's your first hypothesis and how do you confirm it?
