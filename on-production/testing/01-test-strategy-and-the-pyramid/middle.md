# Test Strategy & the Pyramid — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Test Strategy & the Pyramid** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Strategy & the Pyramid
> *The pyramid is one shape among several — learn the trophy, the honeycomb, and the rule for picking the right one.*

---

## Core Concept 1 -- Shapes are answers to "where do bugs live?"

Every suite shape is implicitly answering: *where, in this kind of system, do defects actually occur — and where are they cheapest to catch?* The right shape follows from three properties of **your** system:

1. **Architecture.** A pure-logic library hides its bugs in algorithms (catch with unit tests). A microservice hides them at *boundaries* — serialization, HTTP, DB mapping (catch with integration/contract tests). A UI hides them in wiring components together.
2. **Change rate.** Code that changes often needs fast feedback, so push tests down. Stable boundaries can afford a few slower tests.
3. **Cost of a missed bug.** A wrong number in a payment service is catastrophic; a misaligned tooltip is not. Spend confidence where the blast radius is large.

There is no universally correct shape — only a correct shape *for a given system at a given time.*

## Core Concept 2 -- The Testing Pyramid (Cohn)

```text
        /\
       /E2\        few, slow, full system
      /----\
     / Integ\      moderate
    /--------\
   /   Unit   \    many, fast, isolated
  /____________\
```

Cohn's pyramid is the right default when **most of your complexity is in code logic** that can be exercised without I/O: business rules, calculations, algorithms, domain models. Classic back-end services with rich domains fit it well. The base is wide because logic has the most cases and they are cheapest to cover in isolation.

## Core Concept 3 -- The Testing Trophy (Dodds)

Kent C. Dodds argued that for **front-end / JavaScript** apps the pyramid mis-allocates: unit tests that mock everything around a component prove little, because most front-end bugs are in *how pieces wire together* and how a component behaves when rendered with its real children.

```text
        ___
       /E2E\        a few critical flows
      /-----\
     /       \
    | INTEGR. |     <- the fat middle: render real component trees
     \       /
      \-----/
       \Unit/        pure functions, small
        \_/
   ----static----    types + lint (the base)
```

The trophy has a **fat integration layer** and adds a **static** base (TypeScript types, ESLint) that catches a class of bugs before any test runs. Dodds's slogan: *"Write tests. Not too many. Mostly integration."* Use it when your bugs cluster in component composition and rendering rather than in deep logic.

```js
// Trophy-style "integration" test: render the real component tree, no deep mocks
test('submitting the form shows a success message', async () => {
  render(<CheckoutForm onSubmit={fakeApi} />);
  await userEvent.type(screen.getByLabelText('Card'), '4242424242424242');
  await userEvent.click(screen.getByRole('button', { name: 'Pay' }));
  expect(await screen.findByText('Payment received')).toBeVisible();
});
```

## Core Concept 4 -- The Honeycomb (Spotify)

For **microservices**, Spotify (André Schaffer) proposed the *honeycomb*: lots of **integration tests**, a thin layer of unit tests, and very few "integrated" (cross-service / E2E) tests.

```text
   integrated tests   (thin top -- few, expensive, flaky)
  /                  \
 |  INTEGRATION TESTS |  (fat middle -- the bulk)
  \                  /
   implementation     (thin bottom -- isolated unit, only where logic is real)
```

The reasoning: a single microservice is usually **thin** — it receives a request, talks to a DB or another service, transforms data, responds. Its bugs live at the seams (HTTP, JSON, SQL), not in deep algorithms. So integration tests that exercise the service with real (or in-memory) infrastructure give the most confidence per test. *Integrated* tests across many services are kept few because they are slow and flaky — their job is largely replaced by **contract tests** (see [Concept 7](#core-concept-7----the-allocation-heuristic) and [Contract Testing](../05-contract-testing/)).

## Core Concept 5 -- The ice-cream cone anti-pattern

```text
  \                              /
   \   M A N U A L   T E S T S  /     <- biggest: humans clicking
    \--------------------------/
     \      E2E / UI tests     /      <- many, slow, flaky
      \----------------------/
       \   integration       /
        \------------------/
         \   unit          /          <- thinnest: almost none
          \--------------/
```

The pyramid turned upside down. It happens by **default**, not by decision: teams test through the UI because "that's how users use it," skip unit tests as "too granular," and lean on manual QA. The result is a suite that is slow (tens of minutes), flaky (UI timing), and uninformative (failures say "checkout broke" with no line number). If your CI takes 30+ minutes and people re-run failed jobs hoping they pass, you are probably standing on a cone. The fix is to **push coverage down** — re-prove logic in fast unit tests and delete redundant E2E cases.

## Core Concept 6 -- Sizes vs types: Google's small/medium/large

"Unit / integration / E2E" classifies by **scope** (how much code is exercised). Google's testing culture classifies by **size** — *what resources the test is allowed to touch* — and finds it more useful operationally.

| Size | May use | May NOT use | Speed target |
|---|---|---|---|
| **Small** | single process, single thread, in-memory | network, disk, real DB, `sleep`, system clock, multiple threads | < 100 ms |
| **Medium** | single machine, localhost (DB, server on loopback), multiple threads | network to other machines | < 1 s (cap ~minutes) |
| **Large** | multiple machines, real network, full environment | — (anything goes) | seconds to minutes |

Why size beats scope: the thing that actually makes a test **slow and flaky** is *touching shared, non-deterministic resources* — the network, the disk, the wall clock, real time. A "unit test" that calls `time.sleep()` or hits `localhost:5432` has the *cost profile* of an integration test no matter what you call it. Asking **"can this test touch the network/disk/clock?"** predicts speed and flakiness better than asking "is it a unit or integration test?"

```python
# Looks like a "unit" test by scope, but it's MEDIUM by size: it sleeps + uses the clock.
def test_token_expires():
    t = Token(ttl=1)
    time.sleep(1.1)          # <-- real clock, non-deterministic, slow
    assert t.expired()

# Same behaviour as a SMALL test: inject the clock.
def test_token_expires_small():
    clock = FakeClock(now=0)
    t = Token(ttl=1, clock=clock)
    clock.advance(2)
    assert t.expired()       # deterministic, microseconds
```

## Core Concept 7 -- The allocation heuristic

The decision rule for "where does this test go," combining everything above:

1. **Find the lowest level that can prove the behaviour.** Pure logic? Unit. Needs a real DB/HTTP round-trip? Integration. Needs the user-visible flow across the whole stack? E2E.
2. **Keep size small where possible.** Inject the clock, fake the network, use in-memory adapters — turn would-be medium/large tests into small ones.
3. **Cover each behaviour once.** If unit tests fully cover the discount matrix, integration/E2E should *not* re-test discount cases — they test *wiring*, not logic.
4. **Replace cross-service E2E with contract tests at boundaries.** Instead of booting six services to check service A talks to service B, write a contract: A's expectations of B, verified against B in isolation. (See [Contract Testing](../05-contract-testing/).)
5. **Reserve E2E for critical journeys only.** Sign-up, checkout, the one flow that loses money if it breaks — and just the spine of each.

Result: most behaviour is proven by fast small tests; a moderate set of integration tests proves the wiring and I/O; contract tests guard the seams between services; and a tiny, hand-picked set of E2E tests proves the whole machine assembles.

## Real-World Examples

**A React e-commerce front-end → trophy.** Static (TS + ESLint) catches typos and prop mismatches. A fat layer of React Testing Library tests renders real component trees ("clicking Add shows the cart badge incrementing"). Pure helpers (currency formatting) get small unit tests. Two or three Cypress E2E tests cover sign-up and checkout.

**A payments microservice → honeycomb/pyramid blend.** Deep money math is unit-tested exhaustively (pyramid instinct, because the logic is real and dangerous). The HTTP+DB seams get many integration tests (honeycomb instinct). A *contract* with the orders service replaces a flaky cross-service E2E.

**A 35-minute Selenium suite → an ice-cream cone being fixed.** The team finds that 80% of E2E cases re-test form validation already covered nowhere else. They move validation to unit tests, keep 6 journey E2E tests, and CI drops to 9 minutes.

## Common Mistakes

- **Cargo-culting the pyramid onto a front-end.** Mocking everything around a component yields green tests that prove nothing; the trophy exists for this reason.
- **Calling slow tests "unit tests."** Naming doesn't change cost; a sleeping/networking test is medium-sized whatever the folder it lives in.
- **Booting the whole world to test one seam.** Use contract tests instead of N-service E2E.
- **Redundant coverage across levels.** The same rule tested at unit, integration, *and* E2E — three places to maintain, triple the runtime, no extra confidence.
- **Letting the cone grow silently.** Nobody decides "let's invert the pyramid"; it happens when E2E is the path of least resistance. Watch CI time.

---

## Apply it

1. Find a real component where **Test Strategy & the Pyramid** affects an interface or dependency.
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

- Which boundary is most affected by Test Strategy & the Pyramid?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
