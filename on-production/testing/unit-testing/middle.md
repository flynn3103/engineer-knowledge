# Unit Testing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Unit Testing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Unit Testing
>
> *What is a "unit"? Classical vs mockist, table-driven tests, and the discipline of testing behavior instead of implementation.*

---

## Core Concept 1 — What Counts as a "Unit": Classical vs Mockist

There are two long-standing answers, and the debate is older than most frameworks you use.

**The classical school (Detroit / Chicago, "state-based").** A unit is a *unit of behavior*. The test may exercise several real classes together as long as the cluster is fast and has no out-of-process dependency. You replace only **shared, mutable, or slow** dependencies (a database, the clock). Two real collaborators talking to each other inside one test is fine — even desirable.

**The mockist school (London, "interaction-based").** A unit is a single *class*. Every collaborator is replaced with a mock, so the SUT is tested in genuine isolation. Tests verify the *interactions* between the SUT and its (mocked) neighbors.

```text
                CLASSICAL                         MOCKIST
   ┌─────────────────────────────┐    ┌─────────────────────────────┐
   │  [Order]──▶[PriceCalc]──▶[$] │    │  [Order]──▶(mock PriceCalc)  │
   │   real       real            │    │   real      verify .calc()  │
   │  assert on final result      │    │   was called with X         │
   └─────────────────────────────┘    └─────────────────────────────┘
   tests BEHAVIOR of a slice           tests one class in isolation
```

What each buys you:

| | Classical | Mockist |
|---|---|---|
| Failure localization | Coarser — a failure may be in any class in the slice | Precise — points at one class |
| Resistance to refactoring | **High** — internal restructuring doesn't break tests | **Lower** — tests know the call shape |
| Coupling to implementation | Low | High (mocks encode *how* the SUT collaborates) |
| Speed of running | Fast (collaborators are real but in-memory) | Fast |
| Design feedback | Less | More — pain from setup nudges you toward smaller classes |

The pragmatic middle ground (Khorikov's recommendation, and the one this roadmap takes): **default to classical**, use real collaborators when they're in-memory and fast, and reserve mocks for **out-of-process, shared dependencies** that you don't own — the unmanaged ones (a payment gateway, an email service). Mocking a same-process, owned collaborator usually couples your test to the implementation. The full taxonomy of doubles lives in [Test Doubles, Mocks & Fakes](../test-doubles-mocks-fakes/README.md), and the strategy of *when* to reach for each is in the `mocking-strategies` skill.

---

## Core Concept 2 — Table-Driven and Parameterized Tests

When one behavior has many input cases, don't copy-paste a test five times. Drive a single test from a table of cases. This is the dominant idiom in Go and has direct equivalents everywhere.

**Go — table-driven with subtests:**

```go
func TestDiscount(t *testing.T) {
    tests := []struct {
        name       string
        price      float64
        percentOff float64
        want       float64
    }{
        {"no discount", 100, 0, 100},
        {"quarter off", 200, 25, 150},
        {"fully free", 50, 100, 0},
        {"fractional", 99.99, 10, 89.991},
    }
    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            got := Discount(tc.price, tc.percentOff)
            if got != tc.want {
                t.Errorf("Discount(%v, %v) = %v; want %v",
                    tc.price, tc.percentOff, got, tc.want)
            }
        })
    }
}
```

Each row becomes a named subtest (`TestDiscount/quarter_off`), so a failure tells you exactly which case broke, and adding a case is a one-line change.

**Python — `pytest.mark.parametrize`:**

```python
import pytest
from pricing import discount

@pytest.mark.parametrize("price, percent_off, expected", [
    (100, 0, 100),
    (200, 25, 150),
    (50, 100, 0),
    (99.99, 10, 89.991),
])
def test_discount(price, percent_off, expected):
    assert discount(price, percent_off) == pytest.approx(expected)
```

**Java — JUnit 5 `@ParameterizedTest`:**

```java
@ParameterizedTest(name = "{0}% off {1} = {2}")
@CsvSource({
    "0,   100, 100",
    "25,  200, 150",
    "100, 50,  0",
})
void discount(double percentOff, double price, double expected) {
    assertThat(Discount.apply(price, percentOff)).isEqualTo(expected);
}
```

Use a table when cases differ only in **data**. When cases differ in **setup or logic**, keep them as separate tests — forcing dissimilar cases into one table produces a tangle of conditional fields that's harder to read than the duplication it replaced.

---

## Core Concept 3 — Test Behavior, Not Implementation

This is the principle that separates a suite that helps you from one that holds you hostage.

**Assert on what the code *does* (observable output or state), not on *how* it does it (internal calls, private fields, intermediate steps).**

A test couples to the implementation when it:

- Calls or asserts on private methods.
- Verifies that an internal helper was invoked.
- Checks intermediate values that aren't part of the contract.
- Mocks a collaborator the SUT owns, then asserts the call shape.

Why it matters: the entire point of tests is that they let you **refactor fearlessly**. Refactoring changes the *how* while preserving the *what*. If your tests assert on the *how*, every refactor turns them red even though nothing is broken — so you either stop refactoring or stop trusting the tests. Both are disasters.

The litmus test: **"If I restructure the internals without changing behavior, does this test still pass?"** If no, the test is coupled to implementation.

Test through the **public API**. Treat the unit as a black box with a contract. Inputs in, outputs out, observable state changes checked. Private methods get tested *indirectly* through the public behavior that uses them — and if a private method is so complex it "needs" its own test, that's a signal it wants to become its own public unit elsewhere.

---

## Core Concept 4 — A Brittle Test, Made Resilient

Concretely, here's an implementation-coupled test and its resilient rewrite.

**❌ Brittle — couples to internal calls and private structure:**

```java
@Test
void placeOrder_brittle() {
    InventoryService inventory = mock(InventoryService.class);
    PricingEngine pricing = mock(PricingEngine.class);
    AuditLog audit = mock(AuditLog.class);
    OrderService service = new OrderService(inventory, pricing, audit);

    when(pricing.calculate(any())).thenReturn(150.0);

    service.placeOrder(new Order("widget", 2));

    // Asserting on HOW the work was done — internal call sequence:
    verify(inventory).reserve("widget", 2);
    verify(pricing).calculate(any());
    verify(audit).record(anyString());           // owned, in-process — over-mocked
    verifyNoMoreInteractions(inventory, pricing); // freezes the implementation
}
```

This test breaks the moment you rename a method, reorder two internal calls, or add a new (harmless) internal step — none of which changes what `placeOrder` *does*. It's a copy of the implementation written in mock syntax.

**✅ Resilient — uses real in-process collaborators, asserts on outcome:**

```java
@Test
void placeOrder_reservesStockAndReturnsTotal() {
    var inventory = new InMemoryInventory(Map.of("widget", 10)); // fake, in-process
    var pricing   = new PricingEngine();                          // real
    var service   = new OrderService(inventory, pricing, new NoopAuditLog());

    Receipt receipt = service.placeOrder(new Order("widget", 2));

    // Assert on OBSERVABLE behavior:
    assertThat(receipt.total()).isEqualTo(150.0);     // output
    assertThat(inventory.available("widget")).isEqualTo(8); // resulting state
}
```

The resilient version says *what the order placement accomplishes* — stock reserved, total returned — and is silent about the internal choreography. Rename `reserve` to `decrement`, reorder steps, inline a helper: the test stays green. It only fails if the **behavior** changes, which is exactly when you want it to. (`AuditLog`, an unmanaged side-effect dependency, *would* be a legitimate mock — but you'd assert on its message as a contract, not freeze every interaction.)

---

## Core Concept 5 — Fixtures, Setup, and Test Independence

Tests must be **independent**: any test, in any order, alone or with others, gives the same result. Shared mutable state between tests is the root of most "passes alone, fails in the suite" flakiness.

Use fixtures to build fresh state per test, not to share it:

```python
import pytest

@pytest.fixture
def account():
    return Account(balance=100)   # fresh instance for every test that asks

def test_withdraw_reduces_balance(account):
    account.withdraw(30)
    assert account.balance == 70

def test_overdraw_raises(account):
    with pytest.raises(InsufficientFundsError):
        account.withdraw(150)
```

```java
class AccountTest {
    private Account account;

    @BeforeEach
    void setUp() {            // runs before EACH test → fresh state
        account = new Account(100);
    }
    // ...
}
```

Keep setup minimal. Heavy, shared setup ("excessive setup") is a smell: it usually means the SUT has too many dependencies, or you're testing too much at once. If two tests need wildly different setup, don't force a shared fixture — the divergence is telling you they test different things.

---

## Core Concept 6 — Asserting on State vs Interactions

Two ways to verify a test passed:

- **State verification** — call the SUT, then inspect its return value or resulting state. *"After withdraw(30), balance is 70."*
- **Interaction verification** — assert the SUT called a collaborator in a specific way. *"withdraw() called repository.save() exactly once."*

Prefer **state verification**. It's the natural fit for the classical school and is far more resistant to refactoring, because state is part of the observable contract while internal call patterns usually aren't.

Reach for **interaction verification** only when the *interaction itself is the behavior under test* and the collaborator is an unmanaged, out-of-process dependency:

```python
def test_password_reset_sends_one_email(mailer_spy):
    service = PasswordResetService(mailer_spy)
    service.reset("user@example.com")
    # The OBSERVABLE behavior IS "an email is sent" — verifying it is correct.
    assert mailer_spy.sent == [("user@example.com", "Reset your password")]
```

Sending the email is the externally observable outcome — there's no return value or state to check, so the interaction *is* the contract. That's legitimate. Verifying that an internal, owned helper was called is not. The decision rule and the spy/mock vocabulary are detailed in the `mocking-strategies` skill and [Test Doubles](../test-doubles-mocks-fakes/README.md).

---

## Real-World Examples

**1. A migration that should have been painless.** A team rewrote a `TaxCalculator`'s internals for performance. Half their tests were mockist, asserting the old internal call sequence. The rewrite — behavior-identical — turned 40 tests red. They spent two days "fixing" tests that were never testing real behavior. A classical, state-based suite would have stayed green and *confirmed* the rewrite was safe. This is the cost of over-specified tests.

**2. The same bug, two suites.** A pricing rule had an off-by-one in the loyalty discount. The classical suite (real collaborators, assert on final price) caught it instantly — the total was wrong. The mockist suite was *green*, because each class was mocked to return the canned value the test expected; the wiring bug lived in the gaps between the mocks. Mocks can hide integration defects inside a "unit."

**3. Parameterization saving a contract.** A validation function had 14 documented rules. Expressed as a 14-row parameterized table, the rules became a readable spec, and adding the 15th rule was a one-line diff plus its implementation — reviewers could see the new behavior in the test table alone.

---

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Mocking owned, in-process collaborators | Couples tests to implementation; hides wiring bugs | Use real or in-memory fakes; mock only unmanaged out-of-process deps |
| Asserting on private methods / fields | Breaks on every refactor | Test through the public API |
| `verifyNoMoreInteractions` everywhere | Freezes the implementation in place | Assert on outcome, not exhaustive call lists |
| Forcing dissimilar cases into one table | Conditional fields, unreadable | Separate tests when setup/logic differs |
| Shared mutable fixture across tests | Order-dependent flakiness | Fresh state per test |
| Over-specified mocks during a migration | Behavior-preserving rewrite turns suite red | Prefer state verification |

---

## Apply it

1. Find a real component where **Unit Testing** affects an interface or dependency.
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

- Which boundary is most affected by Unit Testing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
