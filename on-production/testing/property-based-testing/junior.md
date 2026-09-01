# Property-Based Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Property-Based Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Property-Based Testing

*Stop hand-picking a handful of examples. State a rule that must hold for **all** inputs, and let the machine hunt for the case that breaks it.*

---

## Core Concept 1 — Example tests vs. property tests

Here is an example-based test for a `sort` function:

```python
def test_sort_examples():
    assert my_sort([3, 1, 2]) == [1, 2, 3]
    assert my_sort([]) == []
    assert my_sort([5]) == [5]
```

This passes if `my_sort` handles *these three lists*. But what about `[1, 1, 1]`? Negative numbers? A 10,000-element list? A list with `None` in it? You'd have to write each one out, and you'd still miss some.

The property-based mindset asks a different question: **what is always true about the output of a correct sort, regardless of the input?**

1. The output has the **same length** as the input.
2. The output is **ordered** (each element ≤ the next).
3. The output is a **permutation** of the input (same elements, possibly reordered).

If all three hold for *any* list you can throw at it, the function sorts correctly. We don't need to know the expected answer in advance — we describe what a right answer *looks like*.

---

## Core Concept 2 — Your first property with `@given`

In Python's **Hypothesis**, `@given` decorates a test and supplies generated inputs:

```python
from hypothesis import given
from hypothesis import strategies as st

@given(st.lists(st.integers()))
def test_sort_length_is_preserved(xs):
    assert len(my_sort(xs)) == len(xs)

@given(st.lists(st.integers()))
def test_sort_output_is_ordered(xs):
    result = my_sort(xs)
    assert all(result[i] <= result[i + 1] for i in range(len(result) - 1))

@given(st.lists(st.integers()))
def test_sort_is_a_permutation(xs):
    from collections import Counter
    assert Counter(my_sort(xs)) == Counter(xs)
```

`st.lists(st.integers())` is the generator: "lists of integers, any length, any values." Run this and Hypothesis will execute each test function ~100 times with different lists — empty ones, huge ones, all-negative ones, all-duplicates ones — and only pass if the property held every single time. You wrote three rules; the framework wrote the test cases.

The same idea in **fast-check** (JavaScript/TypeScript):

```javascript
import fc from 'fast-check';

test('sort preserves length', () => {
  fc.assert(
    fc.property(fc.array(fc.integer()), (xs) => {
      return mySort(xs).length === xs.length;
    })
  );
});
```

`fc.array(fc.integer())` is the generator; `fc.assert(fc.property(...))` runs it many times.

---

## Core Concept 3 — What a generator is

A **generator** (Hypothesis calls them *strategies*, jqwik calls them *Arbitraries*, fast-check calls them *arbitraries*) is just a recipe for producing random values of some shape. The framework ships with generators for the basics:

```python
st.integers()                      # any int
st.integers(min_value=0)           # non-negative ints
st.text()                          # any unicode string (yes, emoji and control chars)
st.booleans()
st.lists(st.integers())            # list of ints
st.lists(st.text(), max_size=5)    # short lists of strings
st.dictionaries(st.text(), st.integers())   # dict[str, int]
```

You compose them like Lego: `st.lists(st.lists(st.integers()))` is "a list of lists of integers." The generator is *the reason* PBT finds weird inputs — `st.text()` will happily hand you `"\x00"` or `"💩"` or a 4,000-character string, exactly the cases a human writing examples skips. You'll learn to build custom generators for your own types at the middle level.

---

## Core Concept 4 — Shrinking: the minimal counterexample

This is the feature that makes PBT *worth it*. Suppose we have a buggy `my_sort` that mishandles negative numbers. The raw failing input Hypothesis first stumbles on might be:

```
[847, -12, 0, 9931, -4, 22, -4, 100000, -7771, 6, ...]   # 60 elements
```

Useless to debug. But Hypothesis doesn't stop there. Once it finds *any* failure, it **shrinks**: it repeatedly tries simpler versions of the input — shorter lists, smaller numbers, values closer to zero — and keeps whichever still fails. It walks that 60-element monster down to:

```
Falsifying example: test_sort_output_is_ordered(xs=[-1, 0])
```

Two elements. Now the bug is obvious: the function doesn't order `-1` before `0`. A failing property doesn't just tell you *that* you're wrong — after shrinking, it tells you *the simplest way* you're wrong. That report is the single most valuable thing PBT gives a junior engineer: an unambiguous, minimal reproduction handed to you for free.

The mechanism (intuitively): "can I make the list shorter and still fail? can I make these numbers smaller and still fail? can I move them toward zero and still fail?" — repeat until nothing simpler fails.

---

## Core Concept 5 — The round-trip property

The single easiest property to find is the **round-trip**: if you transform data one way and then back, you should get the original. Encoding/decoding, serializing/parsing, and compress/decompress are all round-trips.

```python
import json
from hypothesis import given
from hypothesis import strategies as st

# A generator for "JSON-able" values
json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
)

@given(json_values)
def test_json_round_trips(value):
    assert json.loads(json.dumps(value)) == value
```

This one test exercises nested lists, dicts, unicode keys, deeply nested structures — thousands of shapes you'd never enumerate by hand. If your serializer ever loses data, round-trip catches it. In fast-check:

```javascript
fc.assert(
  fc.property(fc.jsonValue(), (value) => {
    return _.isEqual(JSON.parse(JSON.stringify(value)), value);
  })
);
```

Round-trip is your first reflex whenever you see a *pair* of inverse functions.

---

## Core Concept 6 — Reading a failure and reproducing it

When a property fails, Hypothesis prints a focused report — learn to read it:

```
Falsifying example: test_sort_output_is_ordered(
    xs=[-1, 0],
)
```

Three things to notice:

1. **The test name** tells you *which* property broke — here, "output is ordered," so the bug is about ordering, not length or element loss.
2. **The shrunk input** (`xs=[-1, 0]`) is the minimal case. You don't debug the original random monster; you debug this.
3. **It's reproducible.** PBT is random, but every run is driven by a **seed**. Hypothesis remembers the last failing example in a local `.hypothesis/` folder and replays it *first* on the next run, so once you've seen a failure it keeps failing until you fix it — no "it passed on my machine" surprise.

The first move after a failure is almost always: copy the shrunk input into a plain example test so it's checked forever, even after you fix the bug.

```python
from hypothesis import example

@given(st.lists(st.integers()))
@example([-1, 0])                      # the counterexample PBT just found
def test_sort_output_is_ordered(xs):
    result = my_sort(xs)
    assert all(result[i] <= result[i + 1] for i in range(len(result) - 1))
```

`@example([-1, 0])` forces that exact input to run alongside the generated ones — a permanent regression guarding against the bug coming back. The higher tiers go deep on seeds and reproducibility; for now, just remember: a PBT failure is a gift, and you pin it with `@example`.

---

## Real-World Examples

- **URL encoding.** `decode(encode(s)) == s` for any string `s`. PBT finds the space, the `+`, the `%`, the emoji that your three hand-written examples missed.
- **A `parse` / `format` pair for money.** `parse(format(amount)) == amount`. Catches rounding bugs around `0.10`, negative zero, very large values.
- **Reversing a list twice.** `reverse(reverse(xs)) == xs` — trivial but a real smoke test that your reverse handles empty and single-element lists.
- **Set operations.** `len(union(a, b)) <= len(a) + len(b)` — an invariant that holds for any two sets.

---

## Common Mistakes

- **Re-implementing the function inside the property.** `assert my_sort(xs) == sorted(xs)` only tests that you have `sorted`. Prefer structural properties (length, ordered, permutation) unless `sorted` is a trusted *oracle* (middle level).
- **Properties that are accidentally always true.** `assert len(my_sort(xs)) >= 0` passes for everything, including a broken sort. A property that can't fail tests nothing.
- **Forgetting edge generators.** `st.integers()` includes `0` and negatives; `st.text()` includes empty and unicode. Don't restrict the generator just to make the test pass — that hides the bug.
- **Treating PBT as a replacement for all unit tests.** It complements example tests; keep a few readable examples as documentation.

---

## Apply it

1. Choose one small, known input for **Property-Based Testing**.
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

- What problem does Property-Based Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
