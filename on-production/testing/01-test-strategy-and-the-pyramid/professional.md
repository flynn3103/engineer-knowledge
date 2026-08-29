# Test Strategy & the Pyramid — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Test Strategy & the Pyramid** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Strategy & the Pyramid
> *Governing a test strategy across many teams: making it a living document, measuring whether it works, and evolving it as the architecture moves.*

---

## Core Concept 1 -- Strategy as a living document, not a triangle on a wiki

A test strategy that is written once and never revisited is dead on arrival — the architecture moves, the risk profile shifts, and the document becomes folklore. A *living* strategy has four properties:

1. **Versioned and owned.** It lives in source control next to the code (or in an ADR), with a named owner (often a guild/working group, not one person).
2. **Revised on a cadence and on triggers.** Quarterly review *plus* event-driven revisions: a major incident, a re-architecture, a new compliance requirement, a CI-time regression.
3. **Prescriptive about defaults, permissive about adaptation.** It states the org default (e.g. "pyramid by default; trophy for front-ends; honeycomb + contracts for services") and the *conditions* under which a team deviates — with a documented rationale.
4. **Connected to outcomes.** It cites the metrics it is meant to move (escaped defects, CI time, flake rate) so revisions are evidence-driven, not opinion-driven.

The deliverable is short — a few pages — because a strategy people actually read beats an exhaustive one they don't.

## Core Concept 2 -- Governing across teams without central bottlenecks

The failure mode of org-wide testing is a central QA team that becomes a queue. The scalable alternative is **paved roads + thin governance**:

- **Paved road.** Provide a supported default: test framework, fixtures, CI templates, contract-testing harness, an in-memory infra library, flakiness dashboards. Teams that stay on the paved road get speed and support for free; the strategy is *embodied in tooling*, not enforced by reviewers.
- **Thin governance.** A small set of org-level *invariants* enforced as policy-as-code (see Quality Gates), e.g. "every cross-service dependency has a contract test," "pre-merge CI must finish under N minutes," "no PR merges with a quarantined-but-unowned flake older than 14 days."
- **Federated ownership.** Each team owns its risk map and its deviations; a guild reviews patterns across teams and folds learnings back into the paved road.

The principle: **make the right thing the easy thing.** Most adoption comes from good defaults, not from mandates.

## Core Concept 3 -- Measuring whether the strategy works

A strategy you cannot measure is a belief. Four metrics, read together, tell you if it's working:

```text
Metric                    What it tells you                  Healthy direction
-----------------------------------------------------------------------------------
Escaped defects / level   is the suite catching the right     down; and caught at
                          bugs at the right level?            the LOWEST useful level
Suite wall-clock (p95)    is the feedback loop fast enough?   under the CI budget
Flake rate (test+suite)   is the suite trustworthy?           under the ceiling
Test ROI / maintenance    is the suite worth its upkeep?      confidence up, cost flat
```

No single number suffices — they trade against each other. Driving CI time down by deleting tests can raise escaped defects; chasing zero escaped defects can blow the time budget and flake rate. The strategy's job is to hold *all four* in an acceptable region, and the metrics make that trade visible. Beware optimising any one (Goodhart): a team told only "raise coverage" will write assertion-free tests; a team told only "cut CI time" will delete the tests that matter.

## Core Concept 4 -- The escaped-defect feedback loop

The single most valuable signal is **escaped defects classified by the level that *should* have caught them.** Every production incident or customer-reported bug gets a one-line post-hoc tag:

```text
Incident #4471 -- refund applied twice on retry
  Root cause     : non-idempotent refund handler
  Lowest level that could have caught it: UNIT (idempotency of the handler)
  Was there a test there? NO
  Action: add unit test for idempotency; this is a strategy gap, not a fluke
```

Aggregate these over a quarter and a pattern emerges: *"40% of escaped defects were catchable by a unit test we didn't write"* points at an under-invested base; *"most escapes are seam/integration bugs"* points at thin integration coverage or missing contracts; *"escapes are all in flows with no E2E"* points at an over-thin top. This loop is what converts the strategy from static to *self-correcting* — each escape either confirms the allocation or names the gap. It also catches the subtle case where a bug escaped *despite* a test at the right level — meaning the test was weak (a job for [Mutation Testing](../07-mutation-testing/)).

## Core Concept 5 -- Test ROI and the economics of confidence

Every test has a lifetime cost — authoring, every run forever, and maintenance on every related change — paid against the confidence it buys. Framing tests as investments clarifies the whole strategy:

```text
ROI(test) ≈ (probability it catches a real, costly defect × cost of that defect)
            ----------------------------------------------------------------
            (authoring cost + Σ run cost over lifetime + maintenance cost)
```

This explains, quantitatively, the patterns the lower tiers asserted by instinct:

- **Unit tests have high ROI**: tiny run cost, low maintenance, and they catch defects close to the source. The denominator is small.
- **E2E tests have low ROI per test**: large run cost (× every run, forever), high maintenance (brittle to UI change), and flakiness tax. They are worth it *only* where the numerator is huge — a critical journey whose failure is catastrophic.
- **Redundant tests have negative ROI**: the numerator is ~zero (the defect was already catchable elsewhere) while the denominator keeps charging.

The professional move is to **periodically compute rough ROI and prune the bottom of the distribution** — delete brittle, redundant, low-value tests. A smaller suite that is faster and more trusted often *raises* real safety. "More tests" is not the goal; "more confidence per minute" is.

## Core Concept 6 -- Evolving the strategy as architecture changes

The right shape is a function of the architecture, so when the architecture moves, the strategy must follow — and these migrations are where org-scale strategies most often rot.

```text
Architecture change           -> Strategy shift
---------------------------------------------------------------------------
Monolith -> microservices      pyramid -> honeycomb/diamond per service;
                               replace cross-module integration with CONTRACTS at new seams
Server-rendered -> SPA/React   add a static base (types/lint); shift to trophy on the front-end
Sync REST -> event-driven      contracts on message schemas; add consumer tests for events;
                               E2E becomes async/eventual -> needs different harness
Adding a 3rd-party dependency  add a contract or a fake; never let it into the hot test path live
Extracting a shared library    its logic moves to unit tests in the lib; callers drop redundant tests
```

The danger is **lag**: services get split but the old monolith-era E2E suite is kept, now booting six services and flaking constantly. Each architectural change should trigger a strategy review (see the living-document triggers in Concept 1) whose explicit output is *what coverage moves where* — what gets deleted, what new seams need contracts, what new fast tests replace old slow ones. Migrating coverage *down and to contracts* is usually the bulk of the work.

## Core Concept 7 -- Guardrails: gates, budgets, and quarantine policy

Turn the strategy's invariants into automated guardrails so it holds without constant policing:

- **Required checks** (policy-as-code): contracts exist for every declared dependency; pre-merge suite within budget; no merge if flake rate over ceiling. See Quality Gates.
- **A suite SLO**, treated like a production SLO: e.g. *p95 pre-merge CI < 10 min; suite flake < 0.1%.* Breaches page the suite's owners and trigger investigation, exactly like a latency SLO.
- **Quarantine policy with teeth.** A flaky test is quarantined (stops blocking merges) the moment it crosses a threshold, *and* gets an owner and a deadline. Quarantined-and-orphaned tests are deleted, not left to rot. Blanket auto-retry is banned — it hides the rot and burns the budget.
- **CI-time budget enforcement.** A regression in suite time fails the build or alerts, so the suite cannot creep toward the cone unnoticed.

These guardrails are what keep the strategy from drifting between the quarterly reviews.

## Core Concept 8 -- Anti-patterns at organisational scale

The single-service anti-patterns (cone, redundancy, coverage-worship) recur at org scale, plus some that only appear with many teams:

- **The org-wide ice-cream cone by acquisition.** A central E2E suite owned by no team grows until it's a 90-minute, 30%-flake gatekeeper everyone games with retries. Nobody decided it; it accreted.
- **Mandated uniform shape.** Forcing the pyramid onto front-end teams (or the trophy onto back-end services) ignores where bugs live and produces theatre.
- **Coverage gate as the whole strategy.** An org-wide "80% or no merge" rule with no risk weighting and no assertion-quality check — maximally Goodhart-able.
- **Strategy without a feedback loop.** A beautiful document with no escaped-defect classification; it cannot tell whether it works, so it never improves.
- **Central QA queue.** Governance via a bottleneck team instead of paved roads; scales linearly with headcount, which is to say, doesn't.

## Real-World Examples

**A platform org installs paved roads.** Instead of a QA mandate, the platform team ships a CI template (parallel sharding, flake quarantine, contract-test harness) and an in-memory infra library. Teams adopt it because it makes their CI 4× faster, *not* because they're told to. Strategy adoption follows tooling.

**Escaped-defect review changes the allocation.** A quarterly review classifies 60 production incidents by lowest-catching level. 38 were unit-catchable bugs in code with weak tests; 14 were seam bugs in services lacking contracts; the org had been pouring effort into E2E. The strategy is revised: invest in the base and in contracts, freeze E2E growth. Next quarter's escapes drop by half.

**A microservices migration that lagged.** A team split a monolith into five services but kept the monolith's 40-minute E2E suite, now booting all five and flaking at 25%. The strategy review mandates: replace the cross-service E2E with consumer-driven contracts, keep 6 platform smoke tests, push module logic into per-service unit tests. CI returns to 8 minutes; flake under 1%.

**Pruning for ROI.** An audit computes rough ROI across a 6,000-test suite and deletes ~800 brittle/redundant tests (mostly UI-level duplicates of unit-covered logic). CI drops 30%, trust rises, and the next quarter's escaped-defect count is unchanged — confirming the deleted tests bought no real confidence.

## Common Mistakes

- **Write-once strategy.** A wiki triangle nobody revisits; it diverges from reality within a quarter.
- **Governance by bottleneck.** A central QA/E2E team instead of paved roads and thin policy-as-code.
- **Measuring nothing, or one thing.** No escaped-defect loop (can't improve), or a single metric like coverage (Goodhart guarantees gaming).
- **Letting the org E2E suite become a no-owner gatekeeper.** It grows into a flaky 90-minute cone everyone games.
- **Skipping the migration review on re-architecture.** Old slow tests survive into a world they no longer fit.
- **Equating more tests with more safety.** Never pruning means an ever-slower suite with stagnant real confidence.

---

## Apply it

1. Define the user or business outcome that **Test Strategy & the Pyramid** should improve.
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

- Which measurable outcome justifies investing in Test Strategy & the Pyramid?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
