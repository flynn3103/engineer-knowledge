# Property-Based Testing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Property-Based Testing** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Property-Based Testing

*PBT as an executable specification, adopted across a team, validated by mutation testing, and justified by ROI. The organizational and architectural view.*

---

## Core Concept 1 — PBT as executable specification

The deepest framing of PBT: **a property is a specification.** "Decode is the inverse of encode," "the queue is always FIFO," "merging two replicas converges regardless of order" — these are not test cases, they are *statements of intent*, written in code, checked by machine against thousands of inputs.

This matters organizationally because specifications are usually the missing artifact. Requirements docs rot; the property test does not, because it fails the build when it diverges from the code. When you express the contract as properties:

- **The spec is executable and verified continuously**, not a stale wiki page.
- **Reviewers read the properties to understand intent.** A PR's properties tell you what the author believes must hold — often clearer than the implementation.
- **The spec drives the design.** Articulating "what must always be true" before coding (property-first, akin to TDD) exposes ambiguous requirements early: "wait, *should* merge be commutative? what happens on conflict?"

```python
# This reads as the specification of a money type, not as three examples.
@given(money(), money())
def test_addition_is_commutative(a, b):
    assert a + b == b + a

@given(money(), money(), money())
def test_addition_is_associative(a, b, c):
    assert (a + b) + c == a + (b + c)

@given(money())
def test_zero_is_identity(a):
    assert a + Money.zero(a.currency) == a

@given(money(), st.integers())
def test_scaling_distributes(a, n):
    assert a * n == sum([a] * n, Money.zero(a.currency)) if n >= 0 else True
```

Those four properties *are* the algebraic spec of money. Anyone reading them knows the contract; any implementation that violates it fails CI. That is what "PBT as specification" means in practice.

---

## Core Concept 2 — Teaching teams to find properties

Adoption fails for one reason: people can't find properties and conclude "PBT doesn't fit our code." Your job is to make property-finding a *learnable, repeatable* skill, not a flash of insight.

**Concrete tactics that work:**

- **Hand out the pattern checklist** (round-trip, invariant, idempotence, commutativity, oracle, metamorphic, equivalence) as a literal review step: "for this function, which rows of the table apply?" Reference the `property-based-testing` skill so the catalogue lives somewhere durable.
- **Run property-storming sessions.** Put a function on the screen; the team brainstorms every rule that must hold, no filtering. Most functions yield 3–5 once the room warms up.
- **Start where it's free.** The first PBT in a codebase should be a round-trip on an existing serializer — guaranteed value, near-zero effort, an instant win that converts skeptics.
- **Pair PBT with the oracle pattern for migrations.** When rewriting a component, the old implementation is a free oracle for the new one. This is the single most persuasive on-ramp: "we found three behavior differences before shipping the rewrite."
- **Codify the "find with PBT, pin with `@example`" loop** so discovered bugs visibly accrue value.

The leadership outcome is cultural: engineers reach for "what's always true here?" reflexively, the way they reach for "what's the edge case?" today.

---

## Core Concept 3 — Validating properties with mutation testing

A property that *passes* tells you little — it might be **vacuous** (always true regardless of correctness). The acid test for property strength is **mutation testing**: deliberately inject faults into the production code and confirm your properties *fail*.

```text
Original:   if a <= b: ...
Mutant 1:   if a <  b: ...      # off-by-one boundary
Mutant 2:   if a >  b: ...      # inverted comparison
Mutant 3:   if True:   ...      # condition removed
```

Run the mutation tool (mutmut/Cosmic Ray for Python, PIT for Java, Stryker for JS). For each mutant it reruns your tests; a mutant that survives is a fault your properties *can't see*. A surviving mutant on code your PBT supposedly covers means one of:

- the property is **vacuous** (e.g., `assert len(out) >= 0`),
- the **generator never reaches** the relevant input region (distribution gap), or
- the property is **too weak** (checks length but not ordering).

This pairing is powerful precisely because PBT and mutation testing are complementary: PBT generates *inputs*, mutation testing generates *faults*. Together they answer "do strong checks meet thorough inputs?" A high mutation score on PBT-covered code is the strongest evidence you can produce that your specification actually constrains behavior. Make "mutation-test the PBT-covered modules" part of the definition of done for critical logic. See `../07-mutation-testing/`.

---

## Core Concept 4 — PBT and the relationship to formal methods

PBT sits on a spectrum between example tests and full formal verification:

```
example tests  →  property-based tests  →  model checking (TLA+)  →  proof (Coq/Lean)
 (some inputs)     (many random inputs)     (all states, bounded)     (all inputs, proven)
   cheap                cheap-ish              moderate                 expensive
```

PBT is **lightweight formal methods**: you write a specification (the property) and check it against a large *sample* of the input space, not the whole space. It will not *prove* correctness — a property can pass a million inputs and still fail on the one you didn't generate — but it captures most of the value of a formal spec at a fraction of the cost, and it does so in the language and CI your team already uses.

The professional judgment: use PBT as the default rigor for invariant-heavy code; escalate to model checking or proof only where the cost of a missed bug justifies it (consensus protocols, cryptography, safety-critical control). Often the same invariant is *expressed* in a property test and *also* in a TLA+ spec — the property test guards the implementation, the model checks the design. See `../../formal-methods-and-verification/` for where to draw that line.

---

## Core Concept 5 — Integrating PBT into a suite at scale

Running PBT across a large codebase without slowing teams down or adding flakiness requires deliberate placement (building on the senior-level CI mechanics):

- **Tier the runs.** Fast, fixed-seed, low-`max_examples` PBT on the PR gate (must stay green and quick); high-`max_examples`, random-seed exploratory PBT nightly with seeds reported. New bugs surface nightly with a reproducible seed; gates stay stable.
- **Budget runtime explicitly.** PBT is slower than example tests. Set per-property example counts by *value*: 1000+ for codecs and core data structures, 50–100 for cheaper checks. Use deadlines to prevent slow generated inputs from causing timeout flakiness.
- **Persist the example database deliberately.** Decide whether the framework's failing-example store (Hypothesis `.hypothesis/`, proptest regressions file) is cached in CI (remembers past failures) or not (fully independent runs). Commit the *regressions file* where the framework supports it so discovered counterexamples are shared and reviewed.
- **Centralize domain generators.** A shared module of `Arbitrary`/strategy builders for your core types (User, Money, Order, Event) is the highest-leverage shared asset — it makes every new PBT cheap to write and keeps distributions realistic.
- **Standardize the regression loop.** "Find with PBT, pin with `@example`, commit it" as a documented, enforced practice so bug knowledge accumulates in source control.

---

## Core Concept 6 — ROI, cost, and the skill investment

Make the case honestly; PBT is not free.

**Costs:**

- **Skill ramp.** Finding properties is a genuine new skill; expect a few weeks before a team is fluent. This is the dominant cost.
- **Runtime.** Hundreds of inputs per property are slower than one example. Manageable with tiering, but real.
- **Generator maintenance.** Custom generators are code that must evolve with your types.
- **Cultural friction.** "Random tests scare me" must be answered with the seed/determinism discipline from the senior level, or adoption stalls.

**Benefits:**

- **Finds the bug class humans skip** — boundary, unicode, ordering, overflow, lifecycle — exactly the bugs that reach production.
- **One property replaces dozens of example tests**, and keeps finding *new* cases as code changes.
- **The property doubles as living specification** — design clarity and onboarding value beyond bug-finding.
- **Shrinking slashes debugging time** — failures arrive as minimal reproductions.

**Where to invest first** (the senior-level ROI map applies): parsers, serializers, codecs, data structures, financial/date/encoding logic, protocols and state machines. **Where to decline:** invariant-free glue, thin CRUD, UI look-and-feel. The principal-level move is to *target* PBT at the high-invariant, high-cost-of-failure modules rather than mandating it everywhere — a blanket mandate produces vacuous properties and resentment; a focused deployment produces caught bugs and converts.

---

## Core Concept 7 — Anti-patterns and governance

- **Vacuous-property theater.** Teams under a PBT mandate write `assert result is not None` to tick a box. Governance: require mutation testing on PBT-covered critical modules so vacuous properties are exposed.
- **Re-implementing the SUT in the property.** The property duplicates the production algorithm, so both share the same bug. Enforce independent reasoning (structure, oracle, metamorphic) in review.
- **Distribution blind spots.** Generators that never reach the interesting region (e.g., dates always in 2024) give false confidence. Review generator distributions; mutation survivors flag the gaps.
- **Flaky PBT on the gate.** Random seed on a blocking gate without reproduction discipline erodes trust in the whole suite. Fixed seed on the gate, random nightly.
- **PBT-everywhere mandates.** Forcing properties onto code with no invariant wastes effort and discredits the practice. Govern by *targeting* high-value modules.

---

## Real-World Examples

- **A payments ledger.** Properties encode the algebra (commutativity, associativity, identity, conservation of total). Mutation testing on the ledger module confirms the properties kill boundary and sign mutants. The properties *are* the reviewed spec of the money type.
- **A protocol rewrite.** Old implementation is the oracle for the new one; stateful PBT generates operation sequences and finds three behavior differences pre-launch. Each is pinned as `@example`.
- **A serialization library team.** Centralized generators for every wire type; round-trip properties per type; nightly exploratory run with reported seeds; PR gate fixed-seed. Discovered counterexamples committed to the regressions file and shared.
- **A safety-critical scheduler.** Invariants expressed *both* as PBT (guards the code) and as a TLA+ model (checks the design) — PBT for the implementation, model checking for the protocol.

---

## Common Mistakes

- **Mandating PBT everywhere**, producing box-ticking vacuous properties instead of caught bugs.
- **Never validating property strength** — passing properties are assumed strong; without mutation testing they may be vacuous.
- **Letting generators drift from reality**, so whole input regions are never tested.
- **Treating PBT as a proof.** It samples the input space; it does not exhaust it. Don't oversell certainty.
- **Skipping the spec framing**, so PBT stays a niche trick instead of becoming the team's contract language.
- **No shared generator library**, making every new property expensive and inconsistently distributed.

---

## Apply it

1. Define the user or business outcome that **Property-Based Testing** should improve.
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

- Which measurable outcome justifies investing in Property-Based Testing?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
