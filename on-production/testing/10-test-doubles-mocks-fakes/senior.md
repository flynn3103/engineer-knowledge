# Test Doubles: Mocks & Fakes — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Test Doubles: Mocks & Fakes** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Doubles: Mocks & Fakes
>
> *Most mock-heavy tests prove only that the code calls the methods the code calls. The senior skill is designing so you need almost none of them.*

---

## Core Concept 1 — The Over-Mocking Trap

When you mock every collaborator, your test stops describing *behavior* and starts describing *the call graph*. Consider a `PriceCalculator` whose only real job is arithmetic, but whose test mocks everything it touches:

```python
def test_total_price():
    discounts = Mock(); taxes = Mock(); rounding = Mock()
    discounts.apply.return_value = 90
    taxes.apply.return_value = 99
    rounding.apply.return_value = 99
    calc = PriceCalculator(discounts, taxes, rounding)

    calc.total(100)

    discounts.apply.assert_called_once_with(100)
    taxes.apply.assert_called_once_with(90)
    rounding.apply.assert_called_once_with(99)
```

What does this verify? Only that `total` calls `discounts.apply`, then `taxes.apply`, then `rounding.apply`, in that order, with those arguments. It says **nothing** about whether the final price is correct — every return value was made up. If you reorder tax and discount (a real behavior change!) but keep the same call sequence, the test might still pass; if you refactor the *exact same result* into two steps instead of three, it fails. The test is **coupled to the implementation and decoupled from the behavior** — the worst possible combination. This is the over-mocking trap, and it's the central failure of mock-heavy suites.

---

## Core Concept 2 — Tautological Tests: Before and After

The fix is almost always to **replace mocks with real objects or fakes and assert on the result.**

**Before — tautological, mock-everything:**

```python
def test_register_user():
    repo = Mock(); hasher = Mock(); emailer = Mock()
    hasher.hash.return_value = "HASHED"
    svc = SignupService(repo, hasher, emailer)

    svc.register("ada@x.io", "pw")

    hasher.hash.assert_called_once_with("pw")
    repo.save.assert_called_once()                    # what got saved? unchecked
    emailer.send.assert_called_once()                 # to whom? unchecked
```

This passes whether or not the saved user is correct. Rename `hash` to `derive` and it breaks despite identical behavior.

**After — real value logic, fake repository, assert on state:**

```python
def test_register_persists_a_user_with_a_hashed_password():
    repo = InMemoryUserRepo()              # FAKE, real round-trip behavior
    svc = SignupService(repo, BcryptHasher(), spy_emailer := SpyEmailer())

    svc.register("ada@x.io", "pw")

    saved = repo.get_by_email("ada@x.io")  # assert on actual STATE
    assert saved is not None
    assert saved.password_hash != "pw"     # really hashed
    assert BcryptHasher().verify("pw", saved.password_hash)
    assert spy_emailer.sent_to == ["ada@x.io"]   # behavior only where it IS the contract
```

The "after" test checks what *actually matters*: a user with a correctly hashed password exists and a welcome email went to the right address. It survives renaming internal methods, reordering steps, and re-implementing the hasher — because it asserts on **observable outcomes**, not call structure. Note the deliberate split: state for persistence, behavior (spy) only for the email, which genuinely *is* a required side effect.

---

## Core Concept 3 — Don't Mock What You Don't Own

Steve Freeman and Nat Pryce's rule: **never create a double for a type you don't own** — a third-party SDK, a database driver, an HTTP client. Two reasons:

1. **You mock your *mental model* of the library, which is often wrong.** You stub `s3.PutObject` to return success, but you don't know it can throw `SlowDown`, partial-failure, or eventual-consistency surprises. Your test passes against your fantasy of the API; production meets the real one. The mock *lies* — and it lies confidently.
2. **You couple your tests to an interface you can't control.** When the vendor changes a signature, your hand-built mock silently keeps matching the *old* shape, so your green tests no longer reflect reality.

The honest verification that your code works against a real external service is **contract testing** ([05-contract-testing](../05-contract-testing/senior.md)) — recording or asserting the real request/response shape against the actual provider — not a mock you invented. Mocks tell you "given my assumptions, my code is consistent"; contract tests tell you "my assumptions match reality."

---

## Core Concept 4 — Wrap, Then Fake the Wrapper

If you don't mock the library, how do you keep its slowness and nondeterminism out of unit tests? You **wrap** it behind a thin interface *you* own (a port), and fake *that*.

```go
// A port YOU own — your domain's vocabulary, not the vendor's.
type FileStore interface {
    Put(key string, data []byte) error
    Get(key string) ([]byte, error)
}

// Adapter: the ONLY place the third-party SDK appears.
type s3Store struct{ client *s3.Client }
func (s *s3Store) Put(key string, data []byte) error { /* real SDK calls */ }

// Fake YOU own — safe to use everywhere in tests.
type memStore struct{ m map[string][]byte }
func (s *memStore) Put(key string, data []byte) error { s.m[key] = data; return nil }
func (s *memStore) Get(key string) ([]byte, error)    { return s.m[key], nil }
```

Now domain code depends on `FileStore`, unit tests inject `memStore`, and the *only* code that touches the real SDK is the tiny `s3Store` adapter — which you cover with a small set of **integration tests** against a real (or LocalStack) S3. You've localized the untrustworthy boundary to one thin, separately tested layer. This is the practical synthesis of "don't mock what you don't own" + ports-and-adapters.

---

## Core Concept 5 — Design for Testability: Fewer Doubles by Construction

The deepest senior move: **structure code so most of it needs no doubles at all.**

- **Functional core, imperative shell.** Push pure logic (calculations, decisions, transformations) into functions with no I/O. Pure functions need *zero* doubles — just inputs and outputs, state verification. Keep the I/O in a thin shell that you cover with a handful of fakes. Most over-mocked tests exist because business logic is tangled with I/O; separate them and the mocks evaporate.

```python
# Pure core — no doubles needed, ever.
def decide_renewal(subscription, now) -> Decision:
    if subscription.expires_at <= now:
        return Decision.RENEW
    return Decision.SKIP

# Thin shell — the only part that needs a fake clock / repo.
def run_renewals(repo, clock, gateway):
    for sub in repo.due():
        if decide_renewal(sub, clock.now()) is Decision.RENEW:
            gateway.charge(sub)
```

The interesting logic (`decide_renewal`) is tested with plain values. Only the orchestration touches the clock, repo, and gateway.

- **Ports and adapters.** Doubles belong at *architectural boundaries* (ports), and there should be few of them. If a class has eight collaborators all needing mocks, that's a design smell — it's doing too much (violates SRP; see the `solid-principles` skill).
- **Prefer values to collaborators.** A method that takes the data it needs as arguments needs no double; a method that reaches out to fetch that data does. Pass data in.

**A mock-heavy suite is feedback about your design, not just your tests.** When you find yourself needing many mocks, the fix is usually to refactor the production code, not to write better mocks.

---

## Core Concept 6 — When a Mock Is Genuinely the Right Tool

Overcorrecting into "never mock" is also wrong. A mock is the *correct* tool when **the interaction itself is the observable behavior — there is no state to assert.** The contract is "you must make this call."

Canonical cases:

- **"Must publish exactly one `OrderPlaced` event."** The event publication *is* the requirement; there's no resulting state in your unit to check. A spy/mock asserting one publish with the right payload is exactly right.
- **"Must not call the payment gateway when the cart is empty."** Verifying a call *didn't* happen is a behavior assertion with no state equivalent.
- **"Logs an audit record on every privileged action."** The side effect is the point.
- **Notifying / fire-and-forget side effects** where the SUT returns nothing meaningful.

```python
def test_empty_cart_does_not_charge():
    gateway = Mock()
    Checkout(gateway).submit(cart=EmptyCart())
    gateway.charge.assert_not_called()        # the absence of a call IS the contract
```

The test: *is the call genuinely the contract, or am I just unable to see the resulting state?* If there's state to assert, assert it. If the call truly is the deliverable, mock it — and assert the **payload and count**, not just that *something* was called.

---

## Core Concept 7 — Tools by Ecosystem, and Their Default Pull

Each tool nudges you toward a style; know the pull and resist when needed.

- **Mockito (Java).** `when(repo.find(7)).thenReturn(user)` for stubbing; `verify(emailer).send(msg)` for behavior. Powerful and ubiquitous — and *easy to overuse*. Prefer `when/thenReturn` (stub) and reserve `verify` for true interaction contracts.
- **gomock (Go).** Code-generated mocks with strict expectations (mockist by default — unmet expectations fail). Heavy; for most Go code a **hand-rolled fake/spy struct** or `testify`'s `mock.Mock` is lighter and clearer.
- **testify mock (Go).** `m.On("Find", 7).Return(user)` + `m.AssertExpectations(t)`. Convenient, but the same over-mocking risk.
- **unittest.mock (Python).** One `Mock`/`MagicMock` is stub, spy, and mock depending on use. `return_value` (stub), `assert_called_with` (spy/mock). Flexible; name them by role for clarity.
- **Jest / Sinon (JS/TS).** `jest.fn().mockReturnValue(...)` (stub), `expect(fn).toHaveBeenCalledWith(...)` (behavior); Sinon distinguishes `stub`/`spy`/`mock` explicitly — use that vocabulary.
- **mockall (Rust).** `#[automock]` generates a mock from a trait; expectations via `expect_find().returning(...)`. Trait-based, so it pairs naturally with ports.

The pattern across all of them: the framework makes *behavior verification* one line, so teams reach for it reflexively. Senior discipline is to lean on **stubbing + state assertions**, and use the `verify`/`AssertExpectations`/`toHaveBeenCalled` family only where the interaction is the contract.

---

## Real-World Examples

- **A green suite that broke on every refactor.** Diagnosis: 90% behavior verification over mocked collaborators. Fix: introduce fakes behind ports, switch to state assertions; refactors stopped reddening tests.
- **A mock that lied about S3.** Tests stubbed `PutObject` → success; production hit `SlowDown` throttling and lost data. Fix: thin S3 adapter + integration tests against LocalStack; unit tests use an in-memory `FileStore` fake.
- **Event-sourced service.** "Exactly one `OrderPlaced` emitted" is correctly a mock/spy assertion — there's no other observable outcome in the unit.
- **Untangling a god-service.** A class with seven mocked dependencies was split into a pure pricing core (no doubles) and a thin orchestrator (two fakes). Test count dropped, coverage of *behavior* rose.

---

## Common Mistakes

- **Mocking everything "for isolation"** and ending up with tautological tests that survive nothing but a no-op.
- **Mocking third-party SDKs directly**, encoding a wrong mental model that production later violates.
- **Asserting `assert_called` with no payload check** — "something was called" is nearly worthless; check *what* and *how many times*.
- **Over-correcting to "never mock,"** then writing convoluted state checks for things that are genuinely interaction contracts (event publication).
- **Treating a mock-heavy suite as a test problem** when it's a *production-code* problem — too many collaborators, logic fused with I/O.
- **Letting a fake drift** from the real adapter; without a shared contract suite it green-lights broken code.

---

## Apply it

1. State the system invariant that **Test Doubles: Mocks & Fakes** must protect.
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

- Which invariant must remain true when Test Doubles: Mocks & Fakes fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
