# Mutation Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Mutation Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Mutation Testing
>
> *Code coverage tells you a line ran. Mutation testing tells you a line was actually tested. Those are not the same thing.*

---

## Core Concept 1 — Coverage Lies, and Here's the Proof

Let's make this concrete. Here is a tiny function and a test for it.

```python
# discount.py
def apply_discount(price, is_member):
    if is_member:
        return price * 0.9   # members get 10% off
    return price
```

```python
# test_discount.py
def test_member_gets_discount():
    result = apply_discount(100, is_member=True)
    assert result is not None   # <-- weak assertion!
```

Run coverage:

```text
Name          Stmts   Miss  Cover
---------------------------------
discount.py       4      0   100%
```

**100% coverage.** Every line ran. The test passes. Looks done.

But the test only checks that the result is *not None*. It never checks the result is `90`. If someone changed `0.9` to `0.5`, or deleted the discount entirely, this test would **still pass**. Coverage gave you a green light on code that isn't really tested.

This is the gap mutation testing exposes. Coverage = **executed**. Mutation = **tested**.

---

## Core Concept 2 — What a Mutant Is

A **mutant** is your program with one tiny fault planted in it. The tool generates these automatically by applying **mutation operators** — simple find-and-replace rules that mimic the bugs humans actually write.

A few of the common ones:

| Original | Mutated | Operator name |
|---|---|---|
| `a < b` | `a <= b` | conditional boundary |
| `if (cond)` | `if (!cond)` | negate condition |
| `a + b` | `a - b` | math operator swap |
| `return x` | `return null` / `return 0` | return-value mutation |
| `foo()` | *(call removed)* | void method call removal |
| `x = 5` | `x = 0` | constant replacement |
| `return true` | `return false` | boolean swap |

Each operator probes a different kind of mistake. The boundary mutant (`<` → `<=`) checks whether you tested the *edge* of a range. The negate-condition mutant checks whether you tested *both* branches. The math swap checks whether you verified the actual computed value, not just "it returned something."

The tool makes one mutant at a time, re-runs your tests against it, records killed-or-survived, then throws that mutant away and makes the next one.

---

## Core Concept 3 — Killed vs Survived

There are exactly two outcomes that matter for each mutant:

```text
Mutant injected  →  run tests
                       │
        ┌──────────────┴───────────────┐
   a test FAILS                  all tests PASS
        │                              │
     KILLED                        SURVIVED
  (good — tests                (bad — tests ran the
   caught the bug)              code but didn't check it)
```

- **Killed** means a test *failed* when the code was broken. That's the result you *want* — a broken behavior was noticed. (Yes, the failing test is the success here.)
- **Survived** means every test *passed* even though the code is now wrong. Your tests touched that code but asserted nothing that depended on it being correct.

Every survived mutant is a concrete sentence: *"If this exact bug shipped, none of your tests would catch it."* That is far more useful than a coverage percentage.

---

## Core Concept 4 — Your First Survived Mutant

Back to our discount function. Run a mutation tool (`mutmut` for Python) on it:

```text
$ mutmut run

⠏ Generating mutants
⠹ Running tests on 3 mutants

Killed 0 out of 3 mutants

Surviving mutants:
  discount.py:3   price * 0.9   →   price / 0.9
  discount.py:3   price * 0.9   →   price * 1.0  (constant 0.9 → 1.0)
  discount.py:2   if is_member  →   if not is_member
```

Three mutants, **zero killed**. Every one survived. The tool changed multiplication to division, changed the discount rate, and even flipped the membership check — and the test never complained.

Why? Because the test only asserts `result is not None`. None of these mutations make the result `None`, so the test stays green. The mutation report just proved, mutant by mutant, that this code is effectively untested despite "100% coverage."

---

## Core Concept 5 — Killing the Mutant

Fix the test by asserting the actual behavior:

```python
def test_member_gets_ten_percent_off():
    assert apply_discount(100, is_member=True) == 90

def test_non_member_pays_full_price():
    assert apply_discount(100, is_member=False) == 100
```

Run again:

```text
$ mutmut run

Killed 3 out of 3 mutants  🎉

  discount.py:3  price * 0.9 → price / 0.9   KILLED (test expected 90, got 111.1)
  discount.py:3  price * 0.9 → price * 1.0   KILLED (test expected 90, got 100)
  discount.py:2  if is_member → if not...    KILLED (test expected 90, got 100)
```

Same coverage as before — still 100%. But now the tests **mean** something. The lesson: a survived mutant points you at a **specific missing or weak assertion**. You don't guess what's under-tested; the tool tells you exactly where and how.

---

## Core Concept 6 — Reading a Mutant Line by Line

When a tool reports a survivor, it tells you three things: the **file and line**, the **original code**, and the **mutation it applied**. Read it as a sentence.

```text
discount.py:2   if is_member  →   if not is_member   SURVIVED
└── file:line   └── original      └── the mutant     └── outcome
```

Translate it: *"On line 2, I flipped the membership check, and not one test failed."* That immediately tells you no test distinguishes a member from a non-member by the actual price. The fix writes itself — assert that a member gets `90` and a non-member gets `100`, so the two branches produce *different* results a test can see.

The habit to build: never just look at the score. Read each survivor line, say it out loud as a sentence, and the missing assertion becomes obvious.

---

## Real-World Examples

**The "asserts nothing" test.** A teammate's test calls `processOrder(order)` and asserts `assertNotNull(result)`. Coverage: 100% on `processOrder`. Mutation testing kills *zero* mutants inside it — proof the test verifies nothing about how the order was processed.

**The off-by-one that hid.** A function `is_eligible(age)` uses `age >= 18`. The only test passes `age = 25`. The boundary mutant `>= 18` → `> 18` **survives**, because 25 is true under both. The mutation report flags it; you add a test at `age = 18`, and now the boundary is pinned.

**The forgotten log-or-side-effect.** A method calls `auditLog.record(event)`. A "remove void call" mutant deletes that line and **survives** — no test checks the audit log was written. The report reveals a behavior nobody verifies.

---

## Common Mistakes

- **Trusting coverage as "tested."** Coverage is a *floor*, not proof. 100% coverage with weak assertions kills no mutants.
- **Writing `assertNotNull` / `assert result` as the whole test.** These run the code without checking it. Mutation testing eats them alive.
- **Panicking at a low score the first time.** It's normal. The score is a diagnostic, not a grade. Start by killing the scariest survivors.
- **Running mutation testing on everything at once.** It's slow (you'll learn why in the middle tier). Start with one important function.
- **Thinking "killed" is bad.** Killed = caught = good. Survived = missed = bad.

---

## Apply it

1. Choose one small, known input for **Mutation Testing**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Mutation Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
