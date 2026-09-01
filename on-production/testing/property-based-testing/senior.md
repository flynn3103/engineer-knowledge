# Property-Based Testing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Property-Based Testing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Property-Based Testing

*Stateful/model-based PBT finds the ordering bugs no single-call property can. Add determinism, seed discipline, and the judgment of where PBT actually earns its keep.*

---

## Core Concept 1 — Stateful / model-based testing

The idea: instead of testing one call, you let the framework generate a **sequence** of operations against a real system *and* against a simple **model** of that system, then assert they agree at every step.

- **Model** — a trivially correct mirror. For a stack, the model is a Python list. For a key-value store, a dict. The model is allowed to be slow or naive; it just has to be *obviously right*.
- **Commands** — the operations the framework can choose from (`put`, `get`, `delete`, `flush`).
- **Preconditions** — when a command is legal (can't `pop` an empty stack).
- **Postconditions** — after running a command on the real system, assert the result matches what the model predicts.

The framework generates a random program — say `put(a,1); put(b,2); delete(a); get(a); flush()` — runs it against both, and reports any divergence. Then it **shrinks the program**: it deletes operations and simplifies arguments until it has the shortest sequence that still triggers the divergence. A 40-operation failure shrinks to "`put(x); delete(x); get(x)` returns the old value" — a precise reproduction of a lifecycle bug.

This technique has found real bugs in databases, distributed systems, and file systems where single-call testing found nothing. It is the highest-leverage form of PBT for stateful code.

---

## Core Concept 2 — A worked stateful model in Hypothesis

Hypothesis's `RuleBasedStateMachine` generates and shrinks operation sequences for you:

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant
from hypothesis import strategies as st

class BoundedQueueModel(RuleBasedStateMachine):
    """Test a real BoundedQueue (capacity 3) against a plain list model."""

    def __init__(self):
        super().__init__()
        self.system = BoundedQueue(capacity=3)   # system under test
        self.model = []                          # the obvious-correct model

    @rule(value=st.integers())
    @precondition(lambda self: len(self.model) < 3)
    def enqueue(self, value):
        self.system.enqueue(value)
        self.model.append(value)

    @rule()
    @precondition(lambda self: len(self.model) > 0)
    def dequeue(self):
        assert self.system.dequeue() == self.model.pop(0)   # FIFO must agree

    @invariant()
    def size_matches(self):
        assert self.system.size() == len(self.model)

    @invariant()
    def never_exceeds_capacity(self):
        assert self.system.size() <= 3

TestBoundedQueue = BoundedQueueModel.TestCase
```

Hypothesis will weave together enqueues and dequeues in every order, check the FIFO contract and the invariants after each, and if it finds a divergence, hand you the minimal failing sequence. jqwik offers the same via `@StateMachine`/`Action` classes; fast-check via `fc.commands([...])` with `fc.modelRun`. The pattern is identical across ecosystems: **system + model + commands + invariants**.

---

## Core Concept 3 — Determinism, seeds, and reproducibility

PBT is randomized, but it must be *reproducible*. Every framework derives all its inputs from a **seed** — one number. Same seed ⇒ same inputs ⇒ same pass/fail. Reproducibility hinges on three rules:

1. **The framework reports the seed on failure.** Hypothesis prints a `@reproduce_failure` decorator or the failing example itself; fast-check prints `seed` and `path`; jqwik prints the random seed. Capture it from the CI log.
2. **Replay the exact failure locally.** fast-check: `fc.assert(prop, { seed: 1234, path: "5:2" })`. Hypothesis: paste the printed `@reproduce_failure(...)` decorator above the test, or rely on its example **database** (`.hypothesis/`), which automatically replays the last failure first.
3. **The property itself must be deterministic.** If your property reads the wall clock, a global RNG, network, or filesystem ordering, the *same input* can pass once and fail next time — and now the seed doesn't reproduce anything. Inject the clock, seed any internal randomness, and avoid order-dependent reads. A non-reproducible PBT failure is almost always a non-deterministic *property*, not a framework quirk.

```python
# Make the property deterministic: pass time in, don't read it inside.
@given(st.datetimes(), st.integers(min_value=0, max_value=10_000))
def test_token_expiry(issued_at, ttl_seconds):
    token = make_token(issued_at, ttl_seconds)
    assert not token.is_expired(at=issued_at)                       # fresh
    assert token.is_expired(at=issued_at + timedelta(seconds=ttl_seconds + 1))
```

---

## Core Concept 4 — PBT without flakiness in CI

The legitimate fear: "random tests = random red builds." Manage it deliberately.

**Two valid strategies, pick one per suite:**

- **Fixed seed in CI (deterministic mode).** Pin the seed so every CI run executes the *same* inputs. Builds are reproducible; a failure is a real failure, never noise. Cost: you stop discovering *new* inputs in CI — the property only ever sees one fixed sample set. Good for the merge-gating suite where determinism matters most.
- **Random seed + report it (exploratory mode).** Let CI roam new inputs every run for maximum bug-finding, but ensure the framework prints the seed on failure so any red build is reproducible. Cost: a green PR can go red later when CI rolls a new seed onto a latent bug — which is *correct* (the bug was always there) but surprises teams. Best run on a nightly/scheduled job, not as a blocking PR gate.

A common mature setup: **deterministic, bounded PBT on the PR gate** (fixed seed, modest example count) + **exploratory PBT nightly** (random seed, high example count, longer deadlines). New bugs surface in the nightly with a reproducible seed; the PR gate stays stable.

**Other controls:** cap per-example time (`deadline` in Hypothesis) so a slow generated input doesn't cause timeout flakiness; set a sensible `max_examples` (more in nightly, fewer on the gate); keep the `.hypothesis/` example database **out** of CI caches if you want CI runs independent, or **in** a persistent cache if you want CI to remember and re-check past failures. The key principle: *a PBT failure must always be reproducible from information in the build log.* If it isn't, fix the property's determinism before touching seeds. See `../flaky-tests-and-reliability/`.

---

## Core Concept 5 — Regression: pinning a counterexample

When PBT finds a bug, the discovered counterexample is gold — but a future random run might not hit it again. Promote it to a **permanent example test** so it's checked on every run, deterministically, forever:

```python
from hypothesis import given, example, strategies as st

@given(st.lists(st.integers()))
@example([0, 0])                      # the shrunk counterexample PBT found
@example([-1, 2_147_483_648])         # an overflow case it found later
def test_sort_is_ordered(xs):
    result = my_sort(xs)
    assert all(result[i] <= result[i+1] for i in range(len(result)-1))
```

`@example(...)` forces that exact input to run *in addition to* generated ones (jqwik: `@Example` / a seeded data point; fast-check: add an explicit unit test). Now the regression is locked in regardless of seed, and the property keeps hunting for *new* bugs. This is the standard discipline: **find with PBT, pin with `@example`.** Hypothesis's example database does this automatically for the *last* failure, but `@example` makes it explicit, reviewable, and durable in source control.

---

## Core Concept 6 — The tool landscape by ecosystem

| Ecosystem | Tool | Entry points | Notes |
|-----------|------|--------------|-------|
| Python | **Hypothesis** | `@given`, `strategies as st`, `@example`, `RuleBasedStateMachine` | The reference implementation; best-in-class shrinking, example DB, stateful. |
| Java/JVM | **jqwik** | `@Property`, `@ForAll`, `Arbitraries`, `@Provide`, state machines | JUnit 5 platform; integrated shrinking. |
| JS/TS | **fast-check** | `fc.property`, `fc.assert`, arbitraries, `fc.commands` | Mature shrinking; `seed`/`path` replay; model-based via commands. |
| Rust | **proptest**, **quickcheck** | `proptest!` macro / `Arbitrary` trait | `proptest` has integrated shrinking + a persistence file; `quickcheck` is the classic port. |
| Go | **gopter**; **`testing.F`** (native fuzzing) | gopter generators/commands; `f.Fuzz` | Go's native `go test -fuzz` is **coverage-guided fuzzing**, adjacent but distinct (below). |

**Where coverage-guided fuzzing fits.** Fuzzing (libFuzzer, AFL, Go's native fuzzer, Atheris) also generates many inputs, but its engine is *mutation + coverage feedback* aimed at crashes/hangs/sanitizer trips, usually on byte/string inputs. PBT is *property-driven*, checks rich logical invariants, and emphasizes shrinking to a clean counterexample. They overlap (Hypothesis can run in a fuzzing mode; Go blurs the line) but serve different goals. **Fuzzing is covered in `../../dynamic-analysis-and-sanitizers/` — don't duplicate it here.** The senior heuristic: structured logical invariants → PBT; "does any byte sequence crash the parser?" → fuzzing; and a parser deserves *both*.

---

## Core Concept 7 — Where PBT pays off, and where it doesn't

**High ROI (write PBT first):**

- **Parsers, serializers, codecs** — round-trip is free money; the input space is exactly where humans miss cases.
- **Data structures** — heaps, trees, ring buffers, LRU caches; oracle and stateful testing shine.
- **Encoding / financial / date-time logic** — rounding, overflow, time zones, money; clear invariants, catastrophic bugs.
- **Anything with an algebra** — sets, intervals, CRDTs; commutativity/associativity/idempotence are testable laws.
- **State machines / protocols** — stateful PBT finds ordering and lifecycle bugs nothing else does.

**Poor fit (don't force it):**

- **Thin glue / CRUD with no logic** — the only property is "it calls the dependency," which a mock-based unit test states more clearly.
- **Code with no statable invariant** — if you can't articulate a rule, PBT degenerates into a slow, vague example test.
- **Heavily side-effecting code without a clean model** — building the model costs more than it returns; reach for integration tests.
- **UI rendering / look-and-feel** — snapshot/approval testing (`../snapshot-and-approval-testing/`) fits better.

The judgment: PBT's cost is the *skill of finding properties* and slightly slower tests; its payoff is finding the bug class you'd never enumerate. Spend it where invariants are clear and bugs are expensive.

---

## Real-World Examples

- **A connection pool.** Stateful PBT generates acquire/release/timeout sequences; invariant: leased + idle == total, never over capacity, no double-lease. Finds the "release twice" and "leak on exception" bugs.
- **A JSON/Protobuf codec.** Round-trip across a recursive generator finds the unicode, deep-nesting, and integer-boundary losses; the failure pins as an `@example`.
- **An interval/calendar library.** Metamorphic + invariants on overlap/merge; stateful add/remove sequences catch the "merge leaves a gap" bug.
- **A CRDT.** Commutativity and convergence are *the* correctness laws; PBT is essentially the spec.

---

## Common Mistakes

- **Non-deterministic properties.** Reading the clock/RNG/network inside the property makes failures irreproducible and seeds useless.
- **Random seed on the blocking PR gate with no plan for the surprise red build.** Use fixed seed on the gate, random seed nightly.
- **Skipping the model in stateful tests.** Asserting ad-hoc facts after each command misses divergences; a real model catches them.
- **Letting a discovered counterexample evaporate.** If you don't pin it with `@example`, the next seed may never find it again.
- **Forcing PBT onto glue code.** No invariant ⇒ no value; use the right test type.
- **Confusing PBT with fuzzing and writing both in the wrong section** — keep coverage-guided fuzzing in dynamic-analysis.

---

## Apply it

1. State the system invariant that **Property-Based Testing** must protect.
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

- Which invariant must remain true when Property-Based Testing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
