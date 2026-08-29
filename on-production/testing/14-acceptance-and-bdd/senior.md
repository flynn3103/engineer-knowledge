# Acceptance & BDD — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Acceptance & BDD** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Acceptance & BDD
>
> *BDD is a collaboration practice wearing a testing costume. This tier is the honest cost/benefit calculus — when the ceremony pays for itself, when it's pure tax, and where acceptance tests belong in the pyramid.*

---

## Core Concept 1 — BDD Is Collaboration First, Tooling Second

This is the load-bearing insight of the entire topic, and the one most organisations invert.

> **BDD's primary product is shared understanding. The executable specification is a secondary artefact — valuable, but a by-product of the conversation, not the point of it.**

Dan North's original framing was about *communication*: behaviour language ("should…", "given/when/then") existed to make requirements unambiguous across business, dev, and QA. Gojko Adzic's *Specification by Example* made the mechanism explicit — concrete examples are simultaneously the spec, the acceptance criteria, the tests, and (later) the documentation, *because everyone agreed on them together*.

The practical consequence for a senior: **you cannot buy BDD's benefit by adopting a tool.** Installing Cucumber changes nothing about whether business, dev, and QA talk before coding. If they don't, you've added an expensive serialization format on top of the same misunderstandings. The decision "should we do BDD?" is therefore a **process and culture decision**, not a tooling decision — and you evaluate it like one: does this org have a real communication gap that structured examples would close?

If the answer is "no — the same developer writes the story, the code, and the test, and there's no business stakeholder in the loop," then BDD is almost certainly the wrong investment, regardless of how nice the living-docs HTML looks.

---

## Core Concept 2 — The ATDD Loop Around the TDD Loop

BDD's automation, when it earns its place, drives development through **two nested loops**:

```text
OUTER LOOP (ATDD — acceptance/behaviour)
  1. Three Amigos agree on a scenario
  2. Write the scenario; it FAILS (red) — nothing implements it yet
  3. ┌──────────────────────────────────────────────┐
     │ INNER LOOP (TDD)                               │
     │   write a failing unit test → make it pass →   │
     │   refactor → repeat                             │  ← many cycles
     └──────────────────────────────────────────────┘
  4. The scenario passes (green) — the story is genuinely done
  5. Refactor at the feature level; move to the next scenario
```

The acceptance test is your **definition of done made executable**: it's red while the feature is incomplete and turns green only when the observable behaviour the business agreed on actually works. Inside that, you do ordinary TDD (the `test-driven-development` skill) to build the units. This is the healthy relationship between the two: BDD does *not* replace TDD — it wraps it. A team doing "BDD" with no inner-loop unit tests has built the ice-cream cone (Concept 3).

---

## Core Concept 3 — Where Acceptance Tests Sit in the Pyramid

Automated acceptance tests are typically realised at the **integration or E2E level** — they exercise the system through a real-ish stack to verify business-observable behaviour. That makes them, in pyramid terms, **slow and expensive**, which dictates one rule:

> Keep them **few and stable**. Acceptance scenarios cover *critical business journeys and complex business rules*, not every permutation. Permutations belong in unit tests.

```text
        /\        E2E / acceptance (Gherkin):  few, slow, business-critical
       /  \                                     ← "does the feature work end to end?"
      /----\      Integration: more, medium
     /      \
    /--------\    Unit / TDD inner loop: many, fast
   /__________\                                  ← "is each piece correct?"
```

The common BDD pathology is to push *every* acceptance criterion into a browser-driven Cucumber scenario, inverting the pyramid into an **ice-cream cone**: hundreds of slow, flaky, business-language tests and a thin layer of unit tests. The suite becomes the bottleneck and the flake source. Cross-reference [Test Strategy & the Pyramid](../01-test-strategy-and-the-pyramid/) and [End-to-End Testing](../04-end-to-end-testing/): the discipline that keeps E2E sane keeps acceptance sane, because they're usually the same tests.

A useful reframing: a complex business *rule* (discount stacking, premium calculation) is best pinned by many cheap example rows at a **lower** layer; only the critical end-to-end *journey* (a customer completes a purchase) needs a true top-of-pyramid acceptance test.

---

## Core Concept 4 — The Cucumber-Without-Collaboration Trap

This is the failure mode you'll see most, and the one you must be able to name and dismantle.

**The symptoms:**

- Developers write the `.feature` files, alone, after the design is fixed.
- No business or QA person ever reads them; the PO has never opened the repo.
- Every scenario drives a browser via Selenium/Playwright; the suite takes 20–45 minutes and flakes weekly.
- Gherkin steps are imperative (`click`, `type`, `wait`) — effectively a macro language.
- The team experiences BDD as *pure overhead* and (correctly) resents it.

**The diagnosis:** they are paying 100% of the **automation tax** — writing and maintaining Gherkin, step-definition glue, and a slow brittle suite — for **0% of the collaboration benefit**, which is the only thing that justifies the tax. Gherkin is a worse way to write a test than plain code *unless a non-developer reads it*. If no one reads it, you've added a layer of indirection (sentence → regex → function) that buys nothing.

**The fix is rarely "more Gherkin":**

1. Stop writing scenarios developers don't share with anyone.
2. Push assertions *down*: convert imperative browser scenarios into fast API/service tests and unit tests. The pyramid heals.
3. Reintroduce Gherkin *only* where a genuine Three Amigos conversation happens and a non-dev actually reads the output.
4. If no such conversation will ever happen, drop Cucumber entirely and write plain expressive tests. **You can have excellent acceptance testing with zero Gherkin.**

---

## Core Concept 5 — When BDD Pays and When It's Tax

The balanced answer. BDD's value scales with the size of the **communication gap** and the **complexity of the business rules**; its cost is roughly fixed (the automation tax). So:

**BDD pays when:**

- There's a real **business ↔ dev ↔ QA gap** — domain experts who can't read code but must validate behaviour (insurance, finance, healthcare, logistics, tax).
- The domain has **complex, contested business rules** that benefit from a shared, example-based language (eligibility, pricing, compliance).
- **Requirements are ambiguous** and example-mapping conversations measurably reduce rework.
- The **living documentation** genuinely serves an audience (auditors, support, new joiners, the PO).

**BDD is tax when:**

- Developers write Gherkin **for themselves**; no non-dev is in the loop.
- The system is **technically complex but business-simple** (a cache, a build tool, a protocol library) — there's no business language to bridge.
- The team **lacks the discipline** to keep scenarios declarative and the suite fast, and will produce an ice-cream cone.
- It's adopted as a **tool mandate** ("we use Cucumber now") rather than a process change.

> Senior heuristic: **If you removed Cucumber and lost nothing but some HTML reports, you were never doing BDD — you were paying its tax.** The test is whether the *conversations* would survive the tool's removal.

---

## Core Concept 6 — Designing for the Right Drive Layer

The architectural decision that most affects an acceptance suite's health is *what the step definitions drive*. Three layers, decreasing cost:

| Drive layer | Speed | Stability | Use when |
|---|---|---|---|
| **UI (browser)** | Slow | Brittle | The scenario is specifically about the UI, or it's a thin critical smoke journey |
| **HTTP / API** | Fast | Stable | The behaviour is observable at the service boundary (most cases) |
| **In-process (hexagonal port)** | Fastest | Most stable | The behaviour is a domain rule; drive the application core directly through a port |

A **ports-and-adapters / hexagonal** architecture lets the *same* declarative scenario run against the in-process core *or* the deployed system by swapping the adapter behind the step definitions. The Gherkin (`When I place an order over $50`) is unchanged; the step definition either calls `app.placeOrder(...)` in-process or POSTs to `/orders`. This is how teams like the GOOS authors keep acceptance tests fast: drive the core, reserve the full-stack run for a thin layer.

```python
# Same step, two adapters chosen by config — Gherkin never changes
@when(parsers.parse("I place an order over ${amount:d}"))
def place_order(world, amount):
    world.result = world.driver.place_order(amount_over=amount)
    #            ^ driver is InProcessDriver in fast mode,
    #              HttpDriver in full-stack mode
```

---

## Core Concept 7 — Living Documentation as a Real Benefit

When done right, the scenarios become **living documentation**: a human-readable, *always-current* description of system behaviour, generated from the passing suite. Unlike a wiki, it can't silently go stale — if a scenario stops matching the system, it goes red. This is a genuine, underrated benefit:

- **Onboarding:** new joiners read the features to learn what the system *does*, not just how the code is structured.
- **Audit/compliance:** in regulated domains, "here are the executable specifications, all green" is a powerful artefact.
- **Support and product:** non-devs can answer "what's the expected behaviour when…?" from the docs.

But the benefit is **conditional on the scenarios being declarative and readable**. Living documentation generated from imperative click-scripts documents the test, not the system, and serves no one. Tools: Serenity BDD, Cucumber reports, Pickles, SpecFlow+ LivingDoc.

---

## Core Concept 8 — Keeping an Acceptance Suite Sustainable

An acceptance suite decays faster than a unit suite because it's slower and more coupled. Senior practices that keep it alive:

- **Cap the count.** Few, business-critical scenarios. Resist "let's add a scenario for every bug" — most bugs want a unit test.
- **Drive below the UI** by default (Concept 6); reserve browser runs for a thin smoke layer.
- **Stage with tags.** `@smoke` on every push; full set nightly. Don't make the slow suite a per-commit gate.
- **Zero tolerance for flake.** A flaky acceptance test is more corrosive than a flaky unit test because it's expensive to re-run. Quarantine fast, fix or delete (see [Flaky Tests & Reliability](../12-flaky-tests-and-reliability/)).
- **Own the step-definition library** like production code — DRY, well-factored, no dead steps.
- **Periodically ask the readers.** If the PO/QA have stopped reading the features, the collaboration is dead and you're back to paying tax — react.

---

## Real-World Examples

- **Mortgage eligibility engine.** Rules span income, credit, region, and regulation, and *must* be validated by non-technical underwriters. Example-mapping sessions produce ~60 scenario rows that underwriters review and sign off; living docs satisfy auditors. Textbook case where BDD's collaboration value dwarfs its tax.
- **A SaaS team's ice-cream cone.** 600 browser-driven Cucumber scenarios, 38-minute suite, 4% nightly flake, written and read only by devs. A senior killed 80% of them, moved assertions to API and unit level, kept 40 declarative end-to-end journeys driven below the UI. Suite dropped to 6 minutes; flake to near zero; nothing of value was lost — proving the 80% was tax.
- **A protocol library.** Pure technical domain, no business stakeholders. The team's brief Cucumber experiment added nothing; they reverted to expressive table-driven Go tests. Correct call: no communication gap to bridge.

---

## Common Mistakes

- **Adopting BDD as a tool, not a process.** "We use Cucumber" is not a BDD strategy; it's a purchasing decision with ongoing costs.
- **The ice-cream cone.** Every criterion becomes a slow browser scenario; the pyramid inverts; the suite becomes the bottleneck.
- **Scenarios no non-dev reads.** The defining symptom of paying the tax for nothing.
- **No inner TDD loop.** "BDD" with no unit tests underneath — slow, coarse, and unable to localise failures.
- **Treating living docs as automatic.** They're only documentation if the scenarios are declarative; imperative scripts document nothing.
- **Letting flake live.** A flaky acceptance test rots trust faster than any other test because re-running it is expensive.

---

## Apply it

1. State the system invariant that **Acceptance & BDD** must protect.
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

- Which invariant must remain true when Acceptance & BDD fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
