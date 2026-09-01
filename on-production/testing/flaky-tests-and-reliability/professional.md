# Flaky Tests & Reliability — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Flaky Tests & Reliability** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Flaky Tests & Reliability
> *Run a flaky-test management program at scale — detection infra, dashboards, a flake budget/SLO, ownership, fix-or-delete policy, the economics of reruns, and a culture where ignored red is unacceptable.*

---

## Core Concept 1 -- A Flaky-Test Management Program

A program has these pillars; the rest of this page details them:

1. **Detection** — automated infrastructure that *identifies* flaky tests (rerun-to-detect, cross-run analysis) and records them — never to hide them.
2. **Measurement & dashboards** — pass rate, per-test flake score, retry rate, quarantine size, all trended.
3. **Budget / SLO** — an explicit reliability target so "good enough" is defined, not argued.
4. **Ownership** — every flake auto-routed to a named owner/team.
5. **Policy** — fix-or-delete within an SLA; quarantine with deadlines; rerun rules.
6. **Culture** — flakiness treated as a P-level bug; ignored red is unacceptable.

The program's purpose is to make reliability a managed property of the org rather than the heroics of whichever senior is annoyed today. Without a program, large suites reliably decay into "everyone re-runs until green," which is the death state.

## Core Concept 2 -- Detection Infrastructure at Scale

You cannot eyeball flakiness across thousands of tests. You build (or buy) infrastructure that detects it automatically:

- **Rerun-to-detect (not to hide).** When a test fails in CI, re-run it once on the *same commit*. If it flips fail→pass, it's flagged flaky and recorded — the merge may proceed, but the flake event is logged, attributed, and dashboards updated. This is the load-bearing distinction: the rerun's job is to *classify and surface*, never to silently green the build.
- **Cross-run statistical detection.** Aggregate every test's outcomes across all runs. A test that produces different results on the *same commit hash* over time is flaky by definition; flag it without needing a special rerun.
- **Tooling.** `pytest-rerunfailures`, Maven Surefire / Gradle `test-retry`, and `go test -count` provide the rerun mechanics; platform layers — **Gradle Develocity (Enterprise)**, **Datadog Test Optimization**, **BuildPulse**, **CircleCI test insights**, and **Google's internal flaky-test infrastructure** — aggregate fail-then-pass and same-commit-different-result events into per-test flake scores and dashboards. **Test-impact / target-determination systems** (Bazel's, Google's TAP) shrink each run to only affected tests, reducing total flake exposure.

```python
# Detection harness: deflake a suspect against a single commit and report.
# (Identification — the result is RECORDED, not used to silently pass CI.)
import subprocess, json

def flake_score(test_id, runs=100):
    fails = 0
    for _ in range(runs):
        r = subprocess.run(["pytest", test_id, "-q"], capture_output=True)
        fails += (r.returncode != 0)
    return {"test": test_id, "runs": runs, "fails": fails, "rate": fails / runs}

print(json.dumps(flake_score("tests/test_orders.py::test_webhook")))
```

The data this produces — per-test flake score, attributed to an owner, trended over time — is the fuel for every other pillar.

## Core Concept 3 -- The Flake Budget / Reliability SLO

Borrowing from SRE error budgets, set an explicit **reliability SLO** for the suite so the org agrees on what "trustworthy enough" means and has a trigger for action.

Example SLOs:

- **≥ 99.5% of merges are green on the first run** (no rerun needed).
- **Per-test flake rate < 0.1%** over a 30-day window; anything above is auto-quarantined.
- **Quarantine queue < N tests and average age < 14 days.**

The budget makes consequences automatic instead of political:

- When the suite is **within budget**, teams ship features.
- When the suite **breaches budget** (pass rate drops below the SLO), a **reliability freeze or rotation** kicks in: a portion of engineering effort redirects to flake-fixing until the suite is back in budget — exactly like burning an error budget halts risky deploys.

> The flake budget converts "we should really fix flakiness someday" into "we breached SLO, so fixing flakes is now the priority." It gives reliability the same teeth as feature deadlines. (See [Engineering Metrics & DORA](../../engineering-metrics-and-dora/) for error-budget mechanics.)

A budget also legitimizes *some* flakiness: chasing 0% is uneconomic. The SLO names the line where flakiness becomes unacceptable, so effort is spent where it matters.

## Core Concept 4 -- Ownership & Fix-or-Delete Policy

**Ownership.** Every flaky test must route to a named owner — almost always the team that owns the code under test, derived from a `CODEOWNERS`/ownership map. Unowned flakes are nobody's job and therefore never fixed. Detection infra should **auto-file a ticket against the owning team** the moment a test crosses the flake threshold.

**Fix-or-delete policy.** The core organizational rule: a flagged flake gets exactly one of two outcomes within an SLA:

```text
Flake detected → auto-quarantine (unblock everyone) + auto-ticket to owner
  ├─ Owner FIXES within SLA (e.g. 10 working days) → back in blocking suite
  └─ Owner does NOT fix within SLA → test is DELETED (with notification)
```

Deletion-on-timeout sounds harsh but is the keystone: it guarantees the quarantine queue can never become an infinite graveyard, and it forces an honest decision — *this test matters enough to fix, or it doesn't matter enough to keep.* A flaky test that nobody will fix is providing negative value (it costs trust and compute while protecting nothing), so removing it is strictly better than letting it rot.

The policy must be *automated and enforced*, not aspirational. If enforcement depends on someone remembering, the graveyard wins.

## Core Concept 5 -- The Economics of Flakiness

To get organizational investment, quantify the cost. Flakiness is expensive in three currencies:

**1. CI compute.** Every rerun re-executes tests (often the whole suite or a large shard). At scale this is real money.

```text
10,000 merges/month × 30% need ≥1 rerun × 20 min CI × $0.10/min
  = 10,000 × 0.30 × 20 × $0.10 = $6,000/month in rerun compute alone
```

**2. Developer time — the dominant cost.** A red build interrupts an engineer: they context-switch, investigate, decide "probably a flake," re-run, wait, re-verify. Even 10 minutes of human attention per flaky failure dwarfs the compute:

```text
10,000 merges/month × 30% flaky × 15 min engineer time × $1.50/min (loaded)
  = 10,000 × 0.30 × 15 × $1.50 = $67,500/month in lost engineering time
```

**3. Trust — the priceless cost.** The unquantifiable but largest cost: once the team stops believing red, the suite stops preventing bugs, and a real defect ships. One shipped incident can dwarf a year of rerun compute. **Trust is the asset; flakiness spends it.**

> The economic case writes itself: a flake-management program that costs a fraction of an engineer pays for itself many times over in recovered compute, recovered developer hours, and — most of all — preserved trust that keeps real bugs out of production.

## Core Concept 6 -- Culture: Zero Tolerance for Ignored Red

Tools and budgets fail without culture. The cultural rules that make a program stick:

- **Red means stop — always.** The moment "just re-run it" becomes acceptable, trust is already gone. The cultural norm must be: a red build is investigated, not waved through.
- **Flakiness is a P-level bug, not a chore.** A flaky test that's eroding the suite gets the same urgency as a production defect, because it *is* attacking production safety (it's removing the net).
- **"A flaky test is a broken test"** is repeated until it's reflex. No one says "it's just flaky" as an excuse.
- **No silent skips.** Disabling a test without a ticket and owner is treated as introducing a bug.
- **Reliability is everyone's job, owned by someone.** A rotation (a "build cop" / flake-duty) owns suite health each week, but every engineer is expected to leave the suite no flakier than they found it.
- **Celebrate de-flaking.** Make fixing flakiness visible and valued, not invisible grunt work — otherwise it never gets done.

The cultural goal is simple and absolute: **green must mean safe, and red must mean stop.** Everything in the program exists to keep that equation true.

## Core Concept 7 -- Measuring Suite Reliability Over Time

The program lives or dies on its dashboard. Track and trend:

| Metric | Definition | Healthy direction |
|--------|-----------|-------------------|
| **First-run pass rate** | merges green without any rerun | ≥ SLO, stable/rising |
| **Per-test flake score** | failures / runs (same commit), 30-day | near 0; outliers triaged |
| **Retry rate** | share of passes that needed a retry | low and falling (leading indicator) |
| **Quarantine size & age** | count + mean days in quarantine | small, young, moving |
| **Mean time to de-flake** | detection → fixed/deleted | within SLA |
| **Flake-induced CI cost** | rerun compute + est. eng-time | trending down |

Review these in a regular reliability forum. A **falling first-run pass rate** or **rising retry rate** is an early warning that trust is leaking — act before the team starts ignoring red, not after. Reliability that isn't on a trended dashboard silently decays.

## Core Concept 8 -- Flakiness at Scale: Monorepo & Big-Org Approaches

At Google/Meta/large-monorepo scale, the math changes: with millions of tests, a non-trivial fraction is flaky at any instant, so the strategy is *statistical containment*, not zero-flakiness.

- **Continuous detection & flake scoring.** Every test carries a maintained flakiness score from historical pass/fail on identical commits; high-flake tests are automatically excluded from gating.
- **Test-impact / target determination.** Only run tests affected by a change (Bazel, Google's TAP). Fewer tests per run = fewer flake exposures and faster signal.
- **Automatic quarantine + auto-routing.** Tests crossing the flake threshold are auto-quarantined and a ticket auto-filed to the owning team — no human triage in the loop for detection.
- **Bisect-on-flake / culprit finding.** Automated systems re-run across commits to attribute a regression or identify a flake's introduction.
- **Hermeticity enforced by the build system.** Bazel's sandboxing makes tests hermetic by construction (no network, declared inputs only), eliminating whole flakiness families structurally rather than per-test.
- **Org-level SLO with enforced freezes.** Suite reliability is a tracked SLO; breaches trigger org-wide flake-fixing focus.

The lesson scales down: even a 500-test repo benefits from automated detection, scoring, auto-quarantine with deadlines, and a reliability SLO. The principles are identical; only the volume differs.

## Real-World Examples

- **Google's flaky infrastructure.** Google publicly documented that ~1.5% of test runs are flaky and that they manage it with continuous flake scoring, automatic quarantine, and excluding flaky tests from gating rather than chasing zero — a statistical-containment program, not a per-test cleanup.
- **Develocity dashboards change behavior.** A large org adopts Gradle Develocity's flaky-test dashboard; making per-test flake scores visible and attributed to teams drives the flake rate down simply because flakiness is now measured and owned, not invisible.
- **The deletion-SLA that drained the swamp.** A company with an ever-growing quarantine queue introduced auto-delete after a 10-day fix SLA. Within a quarter the queue stabilized small: teams fixed what mattered and let the rest be deleted — the policy forced the honest fix-or-delete decision that human goodwill never had.

## Common Mistakes

- **Detection without a budget/SLO** → you measure flakiness but never trigger action.
- **Budget without ownership** → flakes are detected but routed to no one.
- **Quarantine without deletion SLA** → infinite graveyard, silent coverage loss.
- **Optimizing for 0% flakiness** → uneconomic; chase the SLO, not perfection.
- **Counting only CI compute** → you miss the dominant cost (developer time) and the priceless one (trust).
- **Tools without culture** → the program exists on paper while everyone still re-runs to green.

---

## Apply it

1. Define the user or business outcome that **Flaky Tests & Reliability** should improve.
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

- Which measurable outcome justifies investing in Flaky Tests & Reliability?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
