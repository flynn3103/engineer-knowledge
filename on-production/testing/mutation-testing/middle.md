# Mutation Testing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Mutation Testing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Mutation Testing
>
> *Learn the operators, read a real PIT report, and understand why mutation score is a different — and harder — number than coverage.*

---

## Core Concept 1 — The Mutation Operators in Full

Mutation operators are deliberately small, because real bugs are small. Each one models a category of human error. Here are the standard families with what each *probes*:

| Operator | Example | What a survivor reveals |
|---|---|---|
| **Conditional boundary** | `a < b` → `a <= b` | You never tested the *edge* of the range (off-by-one). |
| **Negate conditional** | `a == b` → `a != b` | You never exercised *both* branches with distinguishing inputs. |
| **Math / arithmetic** | `a + b` → `a - b`, `*` → `/` | You never checked the *computed value*, only that it returned. |
| **Increment** | `i++` → `i--` | Loop/counter behavior is unverified. |
| **Return value** | `return x` → `return null`/`0`/`""` | The caller never asserts on what comes back. |
| **Void method call removal** | `log.write(e)` → *(deleted)* | A side effect (logging, persisting, notifying) is unverified. |
| **Constant / literal** | `0.9` → `1.0`, `100` → `101` | A magic value isn't pinned by any assertion. |
| **Boolean** | `return true` → `return false` | A flag/predicate result isn't checked. |
| **Negation** | `-x` → `x` | Sign handling is untested. |

PIT groups these into mutator sets: `DEFAULTS` (a safe, low-noise set) and `STRONGER` / `ALL` (more operators, more mutants, more noise). Stryker has a similar configurable mutator list. Starting with defaults keeps the report readable.

A useful habit: when you see a survivor, name its operator. "Surviving boundary mutant" immediately tells you to add an edge-case test; "surviving void-call removal" tells you to assert a side effect.

---

## Core Concept 2 — Mutation Score vs Coverage

The **mutation score** is:

```text
                 mutants killed
score = ───────────────────────────────────
        total mutants − equivalent mutants
```

It looks like a coverage number, but it answers a fundamentally different question.

| | Coverage | Mutation score |
|---|---|---|
| **Measures** | Did the line *execute*? | Would a test *fail* if the line were wrong? |
| **Can be gamed by** | Calling code with no assertions | Almost nothing — you must assert real behavior |
| **A high value means** | Code ran during tests | Code is genuinely protected |
| **Typical "good" value** | 80–90%+ | 60–80% is strong; depends on module |
| **100% is...** | Often achievable | Neither achievable nor the goal (equivalent mutants) |

**Why isn't 100% the goal?** Two reasons. First, **equivalent mutants** can never be killed — they don't change behavior, so no test can distinguish them (senior tier covers this). Second, chasing the last few percent costs enormous effort for tests that may not add real value. A score of 70–80% on a critical module, with the *remaining* survivors reviewed and consciously accepted, beats a meaningless 100% line-coverage badge.

Treat the score as a **diagnostic on important code**, not a number to maximize everywhere. (The Goodhart trap of turning it into a target is covered at the professional tier and in [Engineering Metrics & DORA](../../engineering-metrics-and-dora/).)

---

## Core Concept 3 — Reading a Real PIT Report

Here's an annotated PIT run on a Java method. The code:

```java
public class Pricing {
    public int finalPrice(int base, int qty) {
        int total = base * qty;
        if (qty > 10) {              // bulk discount
            total = total - (total / 10);
        }
        return total;
    }
}
```

The only test:

```java
@Test void computesTotal() {
    assertEquals(50, new Pricing().finalPrice(10, 5)); // qty=5, no discount
}
```

PIT console output:

```text
>> Generated 7 mutations Killed 3 (43%)
>> Ran 7 tests (1.0 tests per mutation)

- Pricing.java
  line 3  Replaced integer multiplication with division   KILLED
  line 3  Replaced integer multiplication with subtraction KILLED
  line 4  changed conditional boundary  (qty > 10 → qty >= 10)  SURVIVED
  line 4  negated conditional           (qty > 10 → qty <= 10)  SURVIVED
  line 5  Replaced integer subtraction with addition            SURVIVED
  line 5  Replaced integer division with multiplication          SURVIVED
  line 7  replaced int return with 0                            KILLED

Mutation score: 43% (3/7)
```

Read it like a checklist of holes:

- **Lines 4 and 5 survive entirely.** The test only uses `qty=5`, so the *discount branch never runs*. Every mutant inside it survives — there's no input that reaches that code. This is the classic "no coverage" signature.
- **Line 3 killed.** The `assertEquals(50, ...)` pins the multiplication, so swapping `*` for `/` or `-` is caught.
- **Line 7 killed.** Returning `0` instead of `total` breaks the assertion.

The report has handed you a precise task: add a test with `qty > 10` and assert the discounted value.

PIT also writes an HTML report (`target/pit-reports/index.html`) that colors source lines green (mutants killed) or red/pink (survived), so you can see the holes against the code.

---

## Core Concept 4 — Coverage Is a Ceiling on Mutation Score

This is the structural relationship to internalize:

> A mutant on a line that **no test executes** can never be killed. So your mutation score can never exceed your coverage.

```text
   uncovered line  →  mutant runs, but no test touches it  →  SURVIVES (always)
   covered line    →  mutant runs; test MAY or MAY NOT notice it
```

In the PIT example, the discount branch had **zero coverage**, so all four of its mutants survived automatically. Coverage capped the score before assertions even entered the picture.

The implication for workflow:

1. **Coverage first, to a point.** You can't kill mutants on code no test reaches. Get the important paths covered.
2. **Then mutation, to harden.** Once covered, mutation tells you whether the *assertions* are strong enough.

Coverage is necessary but not sufficient; mutation score is the sufficiency check on top of it. This is exactly why the [Code Coverage](../../code-coverage/) section and this one are two halves of the same story.

---

## Core Concept 5 — From Survivor to Assertion

Every survivor maps to a concrete fix. The skill is reading the operator and writing the test that distinguishes mutant from original.

Fixing the PIT example — add a discount test:

```java
@Test void appliesBulkDiscountAboveTen() {
    // qty=11 enters the discount branch; total = 110, minus 11 = 99
    assertEquals(99, new Pricing().finalPrice(10, 11));
}

@Test void noDiscountAtExactlyTen() {  // boundary!
    assertEquals(100, new Pricing().finalPrice(10, 10));
}
```

Re-run:

```text
>> Generated 7 mutations Killed 7 (100%)
  line 4  qty > 10 → qty >= 10   KILLED  (qty=10 test now distinguishes them)
  line 4  qty > 10 → qty <= 10   KILLED
  line 5  subtraction → addition KILLED  (expected 99, got 121)
  line 5  division → multiplication KILLED
```

Note the **boundary test at exactly 10** is what kills the `>` → `>=` mutant. Without it, both operators agree for every input you tried. This is mutation testing's superpower: it forces you to test the *edges*, not just the middle.

To turn this into a habit, lean on the **`unit-testing-patterns`** skill for assertion patterns — assert the value, the boundary, and the side effect, not merely that something happened.

---

## Core Concept 6 — Tools by Ecosystem

| Ecosystem | Tool(s) | Notes |
|---|---|---|
| **Java / JVM** | **PIT (Pitest)** | The gold standard. Fast (bytecode mutation), great HTML reports, Maven/Gradle plugins, incremental analysis. |
| **JS / TS / C# / Scala** | **Stryker** | Mature, configurable, "test strength" reporting, IDE and CI integrations. |
| **Python** | **mutmut**, **cosmic-ray** | mutmut is simple and fast to start; cosmic-ray is more configurable/distributed. |
| **Go** | **go-mutesting**, **gremlins** | gremlins is the more actively maintained, with incremental mode. |
| **Rust** | **cargo-mutants** | Integrates with `cargo`; good diff/incremental support. |

A minimal Stryker (JS/TS) report looks like:

```text
#  Mutant status        count
✓  Killed                 142
✗  Survived                18
⏰ Timeout                  4
🚫 No coverage              9

Mutation score: 79.21%   (killed+timeout / total)
Test strength:  88.75%   (killed+timeout / covered mutants only)
```

Two numbers worth distinguishing: **mutation score** (over *all* mutants) and **test strength** (over only *covered* mutants). A big gap between them means you have a coverage problem (the "no coverage" bucket); a low test strength means you have an *assertion* problem.

---

## Real-World Examples

**The branch with no inputs.** A `refund()` path only triggers for orders over $1000. The team's tests never use such an order. PIT shows every mutant in that branch surviving as "no coverage" — a whole feature path silently untested behind 100% *overall* coverage of the cheaper paths.

**The validator that always says yes.** `isValid()` has `return true` mutated to `return false` and it **survives** — meaning no test ever expects `isValid()` to return `true` for a valid input *and* compares against an invalid one. The boolean mutant exposes a validator nobody actually validated.

**Stryker on a date utility.** A `daysBetween(a, b)` function had 100% coverage. Stryker's arithmetic mutants (`b - a` → `a - b`, `+ 1` → `- 1`) survived because tests only checked `daysBetween(d, d) == 0`. Adding asymmetric-date assertions killed them.

---

## Common Mistakes

- **Comparing mutation score to coverage as if they're the same scale.** A 70% mutation score is often *stronger* than 95% coverage.
- **Running `ALL` mutators on day one.** The flood of low-value mutants buries the important survivors. Start with defaults.
- **Ignoring the "no coverage" bucket.** Those aren't assertion problems — they're missing tests. Fix coverage first there.
- **Killing a mutant by weakening it (e.g., `--exclude`) instead of adding a test.** That hides the hole instead of closing it.
- **Forgetting the boundary test.** `>` vs `>=` survivors are the most common; only an exact-edge input kills them.

---

## Apply it

1. Find a real component where **Mutation Testing** affects an interface or dependency.
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

- Which boundary is most affected by Mutation Testing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
