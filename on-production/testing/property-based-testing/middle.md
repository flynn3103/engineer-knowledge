# Property-Based Testing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Property-Based Testing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Property-Based Testing

*Finding the property is the real skill. Here is the catalogue of patterns, how to build generators that produce the inputs you need, and how shrinking actually works.*

---

## Core Concept 1 — The property-pattern catalogue

You rarely invent a property from scratch. You match your function to one of these patterns:

| Pattern | Shape | When it fits |
|---------|-------|--------------|
| **Round-trip** | `decode(encode(x)) == x` | Inverse function pairs: serialize/parse, encode/decode, compress/inflate. |
| **Invariant** | `P(f(x))` always holds | Output has a structural guarantee: sorted, balanced, non-negative, valid. |
| **Idempotence** | `f(f(x)) == f(x)` | Normalizers, dedupers, "ensure exists", clamps, CSS minifiers. |
| **Commutativity / associativity** | `f(a,b) == f(b,a)` | Set union, max, merge, addition. |
| **Oracle (model-based)** | `fast(x) == slow_reference(x)` | You have a simple, obviously-correct reference impl. |
| **Metamorphic** | `f(x)` relates to `f(transform(x))` | No oracle, but related inputs have predictable relationships. |
| **Symmetry / equivalence** | two code paths agree | Old vs. new implementation, two algorithms for the same result. |

Memorize this table. "I don't know what to test" almost always means "I haven't tried each row of this table against my function yet."

---

## Core Concept 2 — Round-trip and oracle in code

**Round-trip** is the highest-value, lowest-effort property — show it once more in Java with **jqwik**:

```java
import net.jqwik.api.*;

class CodecProperties {
    @Property
    void encodeThenDecodeIsIdentity(@ForAll String original) {
        String encoded = UrlCodec.encode(original);
        assertThat(UrlCodec.decode(encoded)).isEqualTo(original);
    }
}
```

`@ForAll String original` is jqwik generating arbitrary strings — including unicode, empty, and control characters.

**Oracle / model-based** testing compares your real implementation against a simpler reference whose correctness is obvious (even if it's slow or memory-hungry). Classic use: a fast, fancy data structure validated against the naive version.

```python
from hypothesis import given, strategies as st

# System under test: a custom counter with optimized internals.
# Oracle: a plain dict, obviously correct.

@given(st.lists(st.text()))
def test_counter_matches_dict_oracle(words):
    fast = MyOptimizedCounter()
    oracle = {}
    for w in words:
        fast.add(w)
        oracle[w] = oracle.get(w, 0) + 1
    for w in set(words):
        assert fast.count(w) == oracle[w]
```

The oracle pattern is how you test something for which "what's the right answer?" is genuinely hard — let a dumb-but-correct implementation define the right answer, and check the smart one agrees.

---

## Core Concept 3 — Invariants, idempotence, commutativity

**Invariant** — a structural truth about the output:

```python
@given(st.lists(st.integers()))
def test_heap_invariant(xs):
    h = build_heap(xs)
    # every parent <= its children
    for i in range(1, len(h)):
        assert h[(i - 1) // 2] <= h[i]
```

**Idempotence** — applying twice equals applying once. True of normalizers, sanitizers, "ensure"/"upsert" operations:

```python
@given(st.text())
def test_normalize_is_idempotent(s):
    once = normalize(s)
    twice = normalize(normalize(s))
    assert once == twice
```

If `normalize(normalize(s)) != normalize(s)`, your normalizer isn't reaching a fixed point — a real, common bug (trimming that leaves a trailing space, lowercasing that misses a locale, etc.).

**Commutativity / associativity** — order shouldn't matter:

```javascript
import fc from 'fast-check';

test('merge is commutative', () => {
  fc.assert(
    fc.property(fc.dictionary(fc.string(), fc.integer()),
               fc.dictionary(fc.string(), fc.integer()),
      (a, b) => _.isEqual(merge(a, b), merge(b, a))
    )
  );
});
```

(Use commutativity only when it *should* hold — last-write-wins merges are deliberately not commutative.)

---

## Core Concept 4 — Metamorphic relations

When there's no oracle and no obvious invariant, **metamorphic testing** saves you. You don't assert the exact output — you assert how the output *changes* when you transform the input in a known way.

Example: a search function. You can't predict the exact ranked results, but you know:

- Searching for `"x"` then **adding** documents that don't match should not *remove* any existing hit.
- Searching `"cat"` and `"CAT"` should return the same results (case-insensitive search).
- Shuffling the document order should not change the *set* of matching documents.

```python
@given(st.lists(st.text(min_size=1)), st.text(min_size=1))
def test_search_is_order_independent(docs, query):
    import random
    shuffled = docs[:]
    random.shuffle(shuffled)
    assert set(search(docs, query)) == set(search(shuffled, query))
```

Another classic: for a `sin` function, `sin(x) == sin(pi - x)` (a metamorphic relation), tested without ever knowing the exact value of `sin(x)`. Metamorphic relations are the property pattern that unlocks PBT for ML models, compilers, image processing, and other code where the "right answer" is impractical to state.

---

## Core Concept 5 — Generators: compose, map, filter, build

Generators are the engine. Three operations cover most needs:

**`map`** — generate, then transform:

```python
even_ints = st.integers().map(lambda n: n * 2)
sorted_lists = st.lists(st.integers()).map(sorted)
```

**`filter` / `assume`** — discard values failing a precondition (use sparingly; over-filtering wastes generation budget and can error out):

```python
positive = st.integers().filter(lambda n: n > 0)        # OK for cheap predicates
# better: generate the constraint directly
positive = st.integers(min_value=1)                      # preferred — no waste
```

Prefer *constructing* the constrained value over filtering it. Filtering throws away work and, if too aggressive, Hypothesis raises a "filtered too much" error.

**Custom generators for domain types** — compose primitives into your own types. Hypothesis's `@composite` (or `st.builds`) is the idiom:

```python
from hypothesis import strategies as st

@st.composite
def users(draw):
    name = draw(st.text(min_size=1, max_size=20))
    age = draw(st.integers(min_value=0, max_value=120))
    emails = draw(st.lists(st.emails(), max_size=3))
    return User(name=name, age=age, emails=emails)

@given(users())
def test_user_serialization_round_trips(user):
    assert User.from_json(user.to_json()) == user
```

In jqwik you register an `@Provide` method returning an `Arbitrary<User>`; in fast-check you compose with `fc.record({...})`:

```javascript
const userArb = fc.record({
  name: fc.string({ minLength: 1 }),
  age: fc.integer({ min: 0, max: 120 }),
  emails: fc.array(fc.emailAddress(), { maxLength: 3 }),
});
```

**Controlling distribution and size.** Frameworks bias toward small inputs early (faster, better shrinking) and grow over the run. You can tune ranges (`min_value`/`max_value`, `max_size`), weight choices (`st.one_of` with frequencies), and nudge the framework to hit edge values. Good generators produce *realistic* and *adversarial* values — both the happy path and the `0`, `""`, `NaN`, and duplicate cases.

---

## Core Concept 6 — How shrinking works

Shrinking turns a giant random failure into a minimal one. The high-level loop:

1. The property fails on some input `X`.
2. The framework asks the generator for *simpler candidates* near `X`: shorter lists, smaller integers, values closer to zero, fewer fields populated.
3. It re-runs the property on each candidate. If a candidate *still fails*, it becomes the new `X` and the search continues from there.
4. When no simpler candidate fails, the surviving `X` is the **minimal counterexample** reported to you.

Worked walkthrough — a buggy "remove duplicates" that breaks when an element appears three or more times:

```
Initial failing input:  [9, 9, 2, -55, 9, 17, 0, 9, 9]   (random, 9 elements)

Shrink: drop unrelated elements   ->  [9, 9, 9, 9]   still fails
Shrink: shorten the run           ->  [9, 9, 9]      still fails (3 copies trigger it)
Shrink: shorten again             ->  [9, 9]         PASSES (2 copies are fine) — reject
Shrink: shrink the value 9 -> 0   ->  [0, 0, 0]      still fails — accept

Falsifying example: dedupe(xs=[0, 0, 0])
```

The report `[0, 0, 0]` instantly says "three identical elements break it" — far more legible than the original noise.

**Integrated vs. type-based shrinking.** Modern frameworks (Hypothesis, fast-check, jqwik) use **integrated shrinking**: the shrink behavior is derived from how you built the generator, so your custom `map`/`composite`/`record` generators shrink correctly *for free*. Older QuickCheck-style designs require you to write a separate `shrink` function for each type — easy to get wrong, and the reason early adopters found PBT painful. When you build a custom generator with the operations above, you inherit good shrinking automatically.

---

## Real-World Examples

- **A date library.** Round-trip: `parse(format(d)) == d`. Invariant: `d.addDays(n).addDays(-n) == d`. Metamorphic: `d1 < d2  ⇒  d1.addDays(k) < d2.addDays(k)`.
- **A cache.** Oracle: behaves like a plain dict for `get`/`put` ignoring eviction; invariant: size never exceeds capacity.
- **A diff/patch tool.** Round-trip: `apply(diff(a, b), a) == b` for any two documents.
- **A rate limiter.** Invariant: across any sequence of requests in a window, the number admitted never exceeds the limit.

---

## Common Mistakes

- **Tautological properties.** A property that re-derives the output the same way the code does proves nothing. Use independent reasoning (structure, oracle, metamorphic).
- **Over-filtering generators.** Heavy `filter`/`assume` slows tests and can abort the run. Construct the value in range instead.
- **Asserting exact output when only a relation is knowable.** That's the situation metamorphic testing was invented for.
- **Custom generators with hand-rolled (or no) shrinking in older frameworks.** Prefer integrated-shrinking frameworks; you get minimal counterexamples without extra work.
- **Ignoring that floats include `NaN`/`inf`.** `st.floats()` will hand you those; either handle them or scope them out explicitly (`allow_nan=False`).

---

## Apply it

1. Find a real component where **Property-Based Testing** affects an interface or dependency.
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

- Which boundary is most affected by Property-Based Testing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
