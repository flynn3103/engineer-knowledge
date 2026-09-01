# Testing in Production — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Testing in Production** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Testing in Production
> *Building the capability: the platform, the maturity ladder, SRE/error-budget integration, governance, and the culture that makes it safe.*

---

## Core Concept 1 — The Testing-in-Production Platform

The capability is a set of composable, self-service building blocks owned centrally so product teams don't reinvent (or skip) them.

```text
                 ┌──────────────────────────────────────────────┐
                 │            DEVELOPER EXPERIENCE                │
                 │  merge -> automatic gated progressive rollout  │
                 └───────────────────────┬──────────────────────┘
                                         │
   ┌─────────────┬──────────────┬───────┴───────┬───────────────┬──────────────┐
   │ FLAG SVC    │ CANARY/      │ TRAFFIC        │ CHAOS         │ OBSERVABILITY │
   │ targeting,  │ ROLLOUT      │ MGMT           │ TOOLING       │ metrics/logs/ │
   │ rings,      │ controller + │ shadow/mirror, │ fault inject, │ traces, RUM,  │
   │ kill switch │ auto-analysis│ split, teeing  │ game-day fwk  │ error track   │
   └─────────────┴──────┬───────┴───────────────┴───────────────┴───────┬──────┘
                       │                                                 │
                ┌──────┴───────┐                              ┌──────────┴────────┐
                │ AUTO-ROLLBACK│◄─────── SLO breach signal ───┤ SLO / ERROR-BUDGET│
                │ controller   │                              │ engine            │
                └──────────────┘                              └───────────────────┘
```

Building blocks, with the design constraint for each:

| Block | Self-service capability | Non-negotiable constraint |
|-------|------------------------|---------------------------|
| **Feature-flag service** | Targeting, rings, instant kill | < 5s propagation; audited changes |
| **Rollout controller** | Canary stages + automated analysis | Promote/abort decided by the platform, not a human |
| **Traffic management** | Shadow, mirror, split, regional | Side-effect isolation enforced by default |
| **Chaos framework** | Fault injection, game-day scheduling | Blast-radius cap + abort built in |
| **Observability** | Version-tagged metrics/logs/traces, RUM | Required before a service may use the road |
| **Auto-rollback** | SLO-breach revert | Wired to the SLO engine, on by default |

The win is *consistency*: every team gets the same guardrails for free, and the platform team can raise the safety bar for everyone at once. This is the deployment side of [feature flags & progressive delivery](../../release/feature-flags-and-progressive-delivery/) and [rollback/roll-forward](../../release/rollback-and-roll-forward/), unified.

---

## Core Concept 2 — The Maturity Ladder

Adoption is staged. You cannot jump a team straight to continuous chaos; each rung depends on the one below.

```text
L0  AD HOC        Manual deploys to 100%. Watch a dashboard, hope.
                  Risk: full blast radius, human-speed reaction.

L1  OBSERVABLE    Version-tagged metrics/logs/traces + alerting in place.
                  (Prerequisite for everything above — DO THIS FIRST.)

L2  PROGRESSIVE   Feature flags + manual canary (1% -> watch -> expand).
                  Blast radius bounded; rollback still manual.

L3  AUTOMATED     Automated canary analysis + auto-rollback on SLO breach.
                  Shadow traffic for validation. Synthetic + RUM standard.

L4  RESILIENCE    Scheduled chaos game days. Error budgets govern release risk.
                  Resilience hypotheses tested, not assumed.

L5  CONTINUOUS    Continuous automated chaos in prod. Cell-based architecture.
                  Testing in prod is invisible, default, boring.
```

How to use the ladder as a leader:

- **Assess honestly.** Most orgs that *say* they're at L4 are at L2 with aspirations. The tell is L1: is telemetry version-tagged and is rollback automated? If not, you're below L3.
- **Sequence investments by rung.** Don't fund a chaos team (L4) before observability (L1) is solid — you'll inject failures you can't see.
- **Different teams, different rungs.** A team owning a payments service may need L4; an internal tool can sit at L2. Match the rung to the risk.

---

## Core Concept 3 — Organizational Readiness

Testing in production demands organizational maturity, not just tooling. A readiness assessment before you push the practice:

```text
TECHNICAL
  [ ] Observability is version-aware and trusted (L1 met)?
  [ ] Rollback is fast, automated, and itself tested?
  [ ] Deploys are frequent + small (big-bang releases can't canary well)?
  [ ] Architecture supports traffic splitting / flags?

ORGANIZATIONAL
  [ ] SLOs exist and are agreed with the business?
  [ ] On-call exists and incidents are handled blamelessly?
  [ ] Leadership accepts that a bounded, deliberate amount of failure is the price?
  [ ] Engineers are TRUSTED to roll back without sign-off?

CULTURAL
  [ ] "Test in prod" understood as discipline, not corner-cutting?
  [ ] Postmortems are blameless and produce real fixes?
  [ ] Risk is discussed in error-budget terms, not blame terms?
```

When an org is **not** ready: when there's no observability, when failures trigger blame and reorgs, when the business treats any user-visible error as a fireable offense, or when deploys are quarterly big-bang events. Pushing prod testing into that environment is genuinely reckless — the joke version. The professional's job is sometimes to say *"we are not ready; here's the L1/L2 work that comes first."*

---

## Core Concept 4 — Integrating with SRE & Error Budgets

Testing in production and SRE are two views of the same discipline; integrate them explicitly via the **error-budget policy** — the pre-agreed contract for what happens as the budget depletes.

```text
ERROR-BUDGET POLICY (agreed by eng + product + leadership)
  budget > 50%  : ship aggressively; run chaos game days; widen canaries faster
  budget 25-50% : normal posture; standard canary bakes
  budget < 25%  : tighten gates; slow rollouts; defer non-critical chaos
  budget = 0    : FEATURE FREEZE — reliability work only until budget recovers
  exceptional   : break-glass override requires VP sign-off + recorded justification
```

Why this matters at the professional level:

- **It removes the per-decision argument.** Nobody debates "can we risk this canary?" — the budget already answered. Risk-taking becomes accounting.
- **It aligns incentives.** Product and engineering both signed the SLO, so the budget is a neutral arbiter, not ops-vs-dev. (See the `monitoring-alerting` skill for SLO/SLI mechanics.)
- **Testing in prod is a budgeted activity.** Chaos experiments, canary regressions, and shadow-induced load all *spend* budget; track that spend so the practice stays within means.
- **It connects to DORA.** Mature progressive delivery improves all four DORA metrics — higher deploy frequency, shorter lead time, lower change-failure rate (small blast radius), faster MTTR (auto-rollback). Use DORA to make the business case.

---

## Core Concept 5 — Governance & Safety Review for Chaos

Higher-risk experiments — especially chaos with real user impact — need governance proportional to their blast radius. Not bureaucracy; a lightweight, tiered safety review.

```text
CHAOS SAFETY-REVIEW TIERS (gate by blast radius, not by paranoia)
  TIER 1 (read-path, single cell, < 1% traffic, auto-abort)
     -> self-service; log it; no approval needed.

  TIER 2 (write-path OR multi-cell OR 1-10% traffic)
     -> service owner + on-call present; scheduled game day;
        documented hypothesis, blast radius, abort, rollback.

  TIER 3 (cross-service, > 10%, or touching payments/PII/safety)
     -> safety review board approval; comms plan; stakeholder notice;
        explicit abort owner; recorded go/no-go.
```

Every experiment, regardless of tier, must carry the senior-level artifact: **measurable steady-state hypothesis, bounded blast radius, abort conditions, automated rollback, and a learning record.** Governance adds, on top: an approver proportional to risk, a comms plan so other teams aren't surprised, and a postmortem-quality writeup of what was learned. The goal is to make *safe* experiments frictionless (Tier 1 self-service) while ensuring *dangerous* ones get the eyes they need — exactly the inverse of the "test in prod = reckless" caricature.

---

## Core Concept 6 — Relationship to the Rest of the Pyramid

A leader must keep the practice in its proper place or it metastasizes into an excuse.

> Testing in production is the **apex** of the confidence pyramid — it sits on top of a healthy base; it is **not** a substitute for it.

```text
            ▲   TESTING IN PRODUCTION
           ╱ ╲   (apex: canary, shadow, chaos, synthetic, RUM)
          ╱   ╲   — earns confidence ONLY prod can give
         ╱─────╲   — expensive, risky, slow: use sparingly
        ╱  E2E  ╲
       ╱─────────╲
      ╱INTEGRATION╲
     ╱─────────────╲
    ╱     UNIT      ╲   ← fast, cheap, deterministic: do MOST here
   ╱─────────────────╲
```

The anti-pattern to police: a team with a weak base ("our unit tests are flaky so we just canary everything") using prod testing to *avoid* writing cheaper tests. That inverts the economics — you're spending the most expensive, riskiest confidence on bugs a $0 unit test would have caught. The leader's rule: **push every check down to the cheapest layer that can hold it; reserve production for the residue that physically cannot be verified elsewhere** (real scale, real data, real deps, real concurrency, emergent behavior). A strong base is what *earns* a team the right to test in production. (See [test strategy and the pyramid](../test-strategy-and-the-pyramid/README.md), [unit testing](../unit-testing/README.md), [E2E](../end-to-end-testing/README.md).)

---

## Core Concept 7 — Culture: Blamelessness & the Right to Roll Back

The platform and the ladder fail without the culture. Two cultural primitives are load-bearing:

1. **Blameless postmortems.** Testing in production means engineers will sometimes cause a small, bounded incident *on purpose* (chaos) or *as a consequence* (canary regression). If that gets people blamed, they stop taking bounded risks — and then they ship big-bang to 100% to "avoid the canary that got me in trouble," which is *more* dangerous. Blamelessness is what keeps people on the safe path.

2. **The right to roll back without sign-off.** Any engineer must be able to roll back, kill a flag, or abort an experiment *immediately*, without asking permission. A rollback that needs a manager's approval is a rollback that arrives 20 minutes late. Make the safe action the unilateral, celebrated action.

The reframe a leader must repeatedly drive home: **testing in production is not "we're sloppy," it's "we're so rigorous we can safely experiment on the live system."** It signals the *highest* engineering maturity, not the lowest — but only if the org actually has the guardrails. Saying it without the guardrails is just the joke with extra steps.

---

## Core Concept 8 — Measuring the Capability Itself

Treat the capability as a product and measure its health:

| Dimension | Metric | Healthy direction |
|-----------|--------|-------------------|
| **Safety** | % deploys with auto-rollback enabled | → 100% |
| **Safety** | Mean time to rollback (MTTR-rollback) | → seconds |
| **Adoption** | % services on the paved road (canary + flags) | → 100% |
| **Blast radius** | Median user-minutes affected per bad deploy | ↓ over time |
| **Detection** | % regressions caught by canary vs. by users | canary share ↑ |
| **Resilience** | Chaos hypotheses run / failure modes fixed | steady cadence |
| **DORA** | Change-failure rate, MTTR | improving |
| **Budget** | Error-budget burn from prod testing | within policy |

The decisive metric: **"of regressions that reached production, what fraction were caught by automated canary analysis before significant user impact?"** Rising → the capability is working. Flat with rising user-reported incidents → you have the tools but not the discipline.

---

## Real-World Examples

- **Netflix:** the canonical paved road — Spinnaker (deployment), Kayenta (automated canary analysis), Chaos Monkey/ChAP (chaos as a platform feature); progressive delivery is the default, not a choice.
- **Google:** error-budget policy as organizational contract; SRE owns the budget; feature freeze when exhausted is a real, enforced consequence.
- **Amazon:** cell-based architecture + automated rollback ("automated rollback on alarm") as platform defaults; blast radius bounded by design.
- **Microsoft / Azure:** ring-based deployment (canary → pilot → broad → world) as a company-wide standard with safe-deployment-practice gates.
- **Financial / healthcare orgs:** tiered chaos governance and safety review boards because blast radius touches money and safety.

---

## Common Mistakes

| Mistake | Why it's wrong | Do instead |
|---------|----------------|------------|
| Unsafe path easier than safe path | People take it under pressure | Pave the safe road; make it the default |
| Chasing L4 chaos before L1 observability | Injecting failures you can't see | Sequence by rung; observability first |
| Prod testing to dodge a weak test base | Inverts the cost; expensive confidence for cheap bugs | Strengthen the base; reserve prod for residue |
| Rollback needs manager approval | Arrives too late | Unilateral right to roll back |
| Blaming engineers for bounded incidents | Drives them to riskier big-bang ships | Blameless postmortems |
| No error-budget policy | Risk decisions are ad-hoc arguments | Agree a written budget policy |
| Same governance for all chaos | Either bureaucratic or reckless | Tier review by blast radius |

---

## Apply it

1. Define the user or business outcome that **Testing in Production** should improve.
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

- Which measurable outcome justifies investing in Testing in Production?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
