# Mutation Testing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Mutation Testing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Mutation Testing
>
> *The equivalent-mutant problem, the cost problem, and the engineering that makes mutation testing run on real codebases instead of toy functions.*

---

## Core Concept 1 — The Equivalent-Mutant Problem

An **equivalent mutant** changes the source but not the behavior. No test can kill it, because there's no input for which the mutant and the original differ.

A classic case:

```java
int index(int i, int size) {
    int j = i;
    if (j > size) {        // mutate >  →  >=
        j = size;
    }
    return clamp(j);       // clamp already caps at size
}
```

Mutate `j > size` to `j >= size`. When `j == size`, the original skips the assignment (leaving `j = size`) and the mutant runs `j = size` (setting `j` to... `size`). **Same result.** The mutant is equivalent — no test can ever distinguish it. It will show as "survived" forever and drag your score down.

Another common source: redundant code, dead branches, and statements whose result is later overwritten.

```python
x = compute()      # mutate compute() → compute() removed?  no: x reused
x = 0              # this overwrites x; a mutant on the first line is equivalent
```

**Why you can't just auto-detect them:** deciding whether two programs are behaviorally equivalent is **undecidable** in general — it reduces to the halting problem. Tools can catch *some* cases with heuristics (e.g., constraint solving, dataflow), but there's no complete solution.

How practitioners handle it:

- **Treat the score as approximate.** Don't chase 100%; assume a few percent are equivalents you'll never kill.
- **Triage survivors, mark equivalents.** Most tools let you ignore/annotate a mutant (`// pitest:skip`, Stryker `// Stryker disable`, mutmut allowlists). Review the survivor, confirm it's truly equivalent, suppress it with a comment explaining *why*.
- **Prefer operator sets that produce fewer equivalents.** PIT's `DEFAULTS` is tuned to minimize them vs `ALL`.
- **Budget time for it.** On a focused module, expect to manually classify the long-tail survivors; that triage is itself valuable — it forces you to reason about the code.

The equivalent-mutant problem is *why mutation score is a diagnostic, not a contract*. A "perfect" 100% is usually a sign you suppressed aggressively, not that your tests are flawless.

---

## Core Concept 2 — Why Naive Mutation Testing Doesn't Scale

The naive algorithm is brutally simple and brutally expensive:

```text
for each mutant m in all_mutants(source):     # thousands
    apply(m)
    run_entire_test_suite()                   # minutes each
    record(killed or survived)
    revert(m)
```

Cost ≈ **(number of mutants) × (full suite runtime)**.

Do the arithmetic on a modest service: 3,000 mutants × a 90-second suite = 270,000 seconds ≈ **75 hours**. For one run. That's why teams try mutation testing once, watch it run overnight, and abandon it.

Every serious mitigation attacks one of the two factors:

```text
COST  =  (# mutants)  ×  (suite runtime per mutant)
            │                      │
   sampling, diff-based      test selection (run fewer tests),
   (fewer mutants)           parallelization (more machines),
                             fast bytecode mutation (no recompile)
```

The next three concepts are exactly these levers.

---

## Core Concept 3 — Test Selection (Coverage-Aware Execution)

The single biggest win: **don't run the whole suite per mutant — run only the tests that execute the mutated line.**

The insight is that a mutant on line 200 of `Pricing.java` can only be killed by a test that *executes* line 200. Every other test is wasted work. So tools first build a **coverage map** (which tests cover which lines), then for each mutant run only the covering tests.

```text
Naive:    mutant × ALL tests
Selected: mutant × (tests that cover the mutated line)
```

PIT does this by default — it instruments once, records per-test line coverage, and dispatches each mutant only to its covering tests. On a typical codebase this turns "every mutant runs 5,000 tests" into "every mutant runs the 3–20 tests that touch it," often a 100×+ reduction. It also short-circuits: as soon as *one* test kills the mutant, it stops (a mutant only needs to be killed once).

This is why mutation testing on the JVM is viable at all. It also means **fast, well-isolated unit tests** make mutation testing dramatically cheaper — slow integration tests that cover everything blow up the per-mutant cost. Another reason the discipline in [Unit Testing](../02-unit-testing/) pays compound interest.

---

## Core Concept 4 — Incremental / Diff-Based Mutation

The second-biggest win: **don't mutate the whole codebase — mutate only what changed.**

For a 50,000-line service, full mutation testing is a weekly/nightly batch at best. But in a pull request, you only changed 40 lines. Mutating just those 40 lines runs in seconds and gives the most relevant signal: *are the new/changed lines actually tested?*

Tools support this directly:

- **PIT** has `withHistory` / incremental analysis: it stores a results file and only re-analyzes mutants affected by changes. There's also `arcmutate` / `pitest-git` integrations for PR-diff scoping.
- **Stryker** has `--since` (diff against a git ref) to mutate only changed files/lines.
- **gremlins** (Go) and **cargo-mutants** (Rust) support diff/changed-file modes.

A typical CI setup:

```yaml
# Run mutation testing only on lines changed in the PR
- run: stryker run --incremental --since=origin/main
```

```text
Stryker --since main:
  Mutated 23 mutants across 2 changed files
  Killed 21, Survived 2

  src/pricing.ts:88  (qty > threshold → qty >= threshold)  SURVIVED
  src/pricing.ts:91  (total - fee → total + fee)           SURVIVED

  Mutation score (diff): 91.3%   ❌ below gate (95%)
```

This is the form most teams should run in CI: **fast, scoped to the diff, and pointed at exactly the code the author just wrote.** Full-repo runs become a periodic background job, not a per-PR blocker.

---

## Core Concept 5 — Parallelization and Sampling

Two more levers for the cases where selection and diff-scoping aren't enough.

**Parallelization.** Mutants are embarrassingly parallel — each is independent. PIT runs multiple threads; CI can shard mutants across machines. cosmic-ray (Python) is explicitly designed for distributed execution across a worker pool. If you have a big nightly full-repo run, throw cores at it.

```text
threads=8  →  ~8× throughput on the mutant queue (bounded by suite isolation)
```

**Sampling.** When even diff-scoped runs are too big, mutate a *random subset* of locations and estimate the score statistically. You trade precision for speed: a 20% sample gives a rough score in a fifth of the time. Useful for trend-tracking a large legacy module where you want a *direction*, not a precise number. The risk: sampling can miss the specific survivor that mattered, so it's a monitoring tool, not a gate.

**Operator pruning.** Fewer, higher-value operators = fewer mutants. PIT `DEFAULTS` over `ALL`; disable operators that produce mostly equivalents (e.g., some that touch logging) for your codebase.

Order of attack, in practice: **test selection (free, always on) → diff-scoping (CI) → parallelization (nightly) → sampling/operator-pruning (last resort for huge legacy).**

---

## Core Concept 6 — Acting on Results, Systematically

A survivor is a diagnosis. The senior skill is triage at scale, not killing one mutant.

For each survivor, classify into one of four:

```text
1. WEAK ASSERTION   → covered, but no assertion distinguishes the bug.
                      FIX: add the value/boundary/side-effect assertion.
2. MISSING TEST     → "no coverage"; the code never runs in any test.
                      FIX: add a test that reaches the line (not just an assertion).
3. EQUIVALENT       → behavior truly unchanged; unkillable.
                      FIX: suppress with a comment explaining WHY.
4. NOT WORTH IT     → trivial/defensive code, low risk, high cost to test.
                      FIX: consciously accept; document the decision.
```

The discipline is that **3 and 4 are explicit, reviewed decisions** — written down (a suppression comment, a code-review note), not silent. A repo where survivors are blindly suppressed teaches nothing; a repo where each survivor is classified and the equivalents are annotated is genuinely hardened.

This is also how you **find where coverage lies**: run mutation testing on a module with 95% coverage and a low test strength, and the survivor list *is* the list of behaviors the coverage badge was lying about.

A concrete triage on a PR survivor:

```text
src/pricing.ts:88  (qty > threshold → qty >= threshold)  SURVIVED

Diagnosis: WEAK ASSERTION — tests use qty=5 and qty=20, never qty == threshold.
Fix:       assert finalPrice at exactly threshold and threshold+1.
```

---

## Core Concept 7 — Where Mutation Testing Earns Its Cost

Because it's expensive, mutation testing is a **scalpel, not a floodlight.** It earns its cost where the cost of a *missed* bug is high and the code is subtle:

- **Critical business logic** — pricing, billing, tax, eligibility, access control, financial calculations. A survived boundary mutant here is a real-money bug.
- **Complex algorithms** — parsers, schedulers, state machines, retry/backoff logic, anything with many branches.
- **High-risk / security-sensitive code** — auth, permission checks, input validation, crypto wrappers.
- **A test suite you're about to trust** — before a big refactor, mutation-test the *current* suite to confirm it actually pins behavior (next tier expands this).

Where it does **not** pay:

- DTOs, getters/setters, trivial glue, generated code, simple delegation — high mutant count, low value.
- The whole repo, indiscriminately — cost explodes and the signal drowns.

The senior move is **scoping**: configure the tool to target the handful of packages/modules where correctness is load-bearing, and leave the rest to coverage and review. (The org-level governance of this scoping is the professional tier.)

---

## Core Concept 8 — Mutation Testing and the Test Pyramid

Mutation testing primarily grades **unit tests** — it needs fast, isolated, line-precise tests for test selection to work and for the run to finish. Slow integration/E2E tests that cover everything make per-mutant cost explode and rarely *kill* a specific mutant precisely.

It also has a natural partnership with **property-based testing**. PBT generates a wide range of inputs against an invariant; mutation testing checks whether those properties are *strong enough* to catch faults. A property that survives mutants is a property that's too weak — it asserts something true but unhelpful. Run mutation testing over your PBT suite and weak invariants surface immediately. See [Property-Based Testing](../06-property-based-testing/).

```text
Pyramid layer    Mutation testing fit
─────────────    ────────────────────
unit             ★★★ ideal — fast, isolated, line-precise
integration       ★  costly per mutant, rarely kills precisely
e2e               ✗  far too slow; not the right tool
property-based    ★★★ great pairing — grades invariant strength
```

---

## Real-World Examples

**The refactor safety net.** Before extracting a 400-line `OrderService` into smaller classes, a team mutation-tested the existing suite. Score: 58%. They discovered the tests barely pinned the discount and tax logic. They strengthened the suite to 85% *first*, then refactored with confidence the suite would catch a regression. Mutation testing converted "we have tests" into "we have tests that work."

**The auth check that lied.** An `hasPermission()` had 100% coverage. PIT showed the `return true`/`return false` and negate-conditional mutants surviving — tests only ever passed *authorized* users and asserted success, never asserting a *denied* user was actually denied. A boolean mutant exposed an authorization bypass that coverage blessed as fully tested.

**Diff-gated CI.** A payments team runs `stryker --since main` on every PR touching `billing/`, gating at 90% on the diff. Full-repo PIT runs nightly with 16-way parallelism and history enabled, finishing in ~25 minutes. Per-PR feedback is seconds; the expensive run is off the critical path.

---

## Common Mistakes

- **Chasing 100% and suppressing whatever's left.** That converts a diagnostic into theater and hides the equivalents you should be reasoning about.
- **Running full-repo on every PR.** It's slow and the signal is buried. Diff-scope in CI; full-run nightly.
- **Ignoring test selection.** Without coverage-aware execution, mutation testing is unaffordable. (PIT does it by default; some setups disable it accidentally.)
- **Letting slow integration tests dominate the covering set.** Per-mutant cost explodes. Keep the mutated modules backed by fast unit tests.
- **Suppressing equivalents without a reason comment.** The next engineer can't tell a justified suppression from a hidden hole.
- **Treating sampling output as a gate.** Sampling estimates a trend; it can miss the one survivor that mattered.

---

## Apply it

1. State the system invariant that **Mutation Testing** must protect.
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

- Which invariant must remain true when Mutation Testing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
