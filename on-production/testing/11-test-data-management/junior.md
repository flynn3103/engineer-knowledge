# Test Data Management — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Test Data Management** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Data Management
>
> *A test is only as good as the data it runs against — learn to build data that is realistic, minimal, and under your control.*

---

## Core Concept 1 — Why Test Data Is a Real Problem

Consider this test:

```python
def test_free_shipping_over_100():
    order = Order(
        id=1,
        customer=Customer(id=7, name="Jane Doe", email="jane@x.com",
                          tier="standard", created_at=datetime(2020, 1, 1)),
        items=[LineItem(sku="A", qty=2, price=60.0)],
        address=Address("12 Main St", "Boston", "MA", "02101", "US"),
        status="pending",
        created_at=datetime(2021, 5, 1),
    )
    assert order.shipping_cost() == 0.0
```

The one fact this test asserts — total is $120, so shipping is free — is buried under twelve fields the test does not care about. Worse, every change to the `Order` constructor breaks this test and dozens like it. And if a reader wonders *why* shipping is free here, they must add `60.0 × 2` in their head while skimming over a name, an email, and two dates.

The data is the test's foundation. If the foundation is noisy, the test is unreadable; if it's wrong, the test lies. Test data management is the discipline of making that foundation **clear, correct, and cheap to build**.

---

## Core Concept 2 — Only Specify What Matters to This Test

The governing principle: **state only the data relevant to the behavior under test; let everything else default.** Irrelevant data is noise, and noise hides intent.

Rewritten with that principle, the same test becomes:

```python
def test_free_shipping_over_100():
    order = an_order().with_total(120.0).build()
    assert order.shipping_cost() == 0.0
```

A reader now sees the whole point in one line: an order with a $120 total ships free. The customer, address, and dates still exist — the builder filled them with valid defaults — but they're out of sight because they're out of scope. When the constructor gains a field next month, you change the builder once, not this test or its fifty siblings.

This is the habit to internalize before any tool: **every value a test sets should be a value the test depends on.** If you can delete a value and the test still means the same thing, that value belonged in a default.

---

## Core Concept 3 — The Test Data Builder

A **Test Data Builder** is a tiny fluent object: it knows valid defaults for every field and exposes `with_*` methods to override the few that matter. Here it is in full, in Python:

```python
class OrderBuilder:
    def __init__(self):
        # Sensible, valid defaults — a "boring but correct" order.
        self._customer = a_customer().build()
        self._items = [LineItem(sku="DEFAULT", qty=1, price=10.0)]
        self._status = "pending"
        self._created_at = datetime(2021, 1, 1)  # fixed, never datetime.now()

    def with_total(self, total):
        # One item priced to hit the requested total.
        self._items = [LineItem(sku="ITEM", qty=1, price=total)]
        return self

    def with_status(self, status):
        self._status = status
        return self

    def with_customer(self, customer):
        self._customer = customer
        return self

    def build(self):
        return Order(customer=self._customer, items=self._items,
                     status=self._status, created_at=self._created_at)

def an_order():
    return OrderBuilder()
```

Three properties make this powerful:

1. **Defaults are valid.** `an_order().build()` always returns a usable order. A test never has to know about fields it doesn't care about.
2. **Each `with_*` returns `self`**, so calls chain: `an_order().with_status("paid").with_total(120).build()`.
3. **It reads like a sentence.** `an_order().with_status("cancelled")` says exactly what kind of order you need.

The same idea in Go uses functional options, which are the idiomatic builder there:

```go
type OrderOption func(*Order)

func WithStatus(s string) OrderOption { return func(o *Order) { o.Status = s } }
func WithTotal(t float64) OrderOption {
	return func(o *Order) { o.Items = []LineItem{{SKU: "ITEM", Qty: 1, Price: t}} }
}

func AnOrder(opts ...OrderOption) Order {
	o := Order{ // valid defaults
		Customer:  ACustomer(),
		Items:     []LineItem{{SKU: "DEFAULT", Qty: 1, Price: 10}},
		Status:    "pending",
		CreatedAt: time.Date(2021, 1, 1, 0, 0, 0, 0, time.UTC),
	}
	for _, opt := range opts {
		opt(&o)
	}
	return o
}

// Usage: AnOrder(WithTotal(120))
```

And in Java, the same builder reads naturally with chained setters returning `this`:

```java
Order order = anOrder().withStatus("paid").withTotal(120.0).build();
```

Whatever the language, the shape is constant: **valid defaults you never have to mention, plus a small set of overrides you do.** Once your team has builders for its core types, writing test data stops being typing and starts being a one-line statement of intent.

---

## Core Concept 4 — Factories and Object Mothers

Builders are great for one-off shaping. Two related patterns cover other needs.

**Object Mother** — a class of named methods returning canonical, ready-made objects. Use it when a handful of well-known shapes recur across many tests:

```python
class Orders:
    @staticmethod
    def paid():      return an_order().with_status("paid").build()
    @staticmethod
    def cancelled(): return an_order().with_status("cancelled").build()
    @staticmethod
    def free_shipping(): return an_order().with_total(120.0).build()

# Usage: order = Orders.paid()
```

The risk: an Object Mother grows into a junk drawer of dozens of slightly different methods. Prefer it for a *small, stable* set of names; reach for a builder when a test needs a one-off variation.

**Factory** — a library that produces valid objects in bulk, often persisting them to a database. In Python, `factory_boy` is the standard:

```python
import factory

class CustomerFactory(factory.Factory):
    class Meta:
        model = Customer
    name = factory.Faker("name")          # realistic-looking name
    email = factory.Faker("email")
    tier = "standard"

# One valid customer:        CustomerFactory()
# Ten of them:               CustomerFactory.create_batch(10)
# Override just one field:    CustomerFactory(tier="gold")
```

Ruby's FactoryBot and Go test helpers (`func newCustomer(t *testing.T, opts ...) Customer`) follow the same shape: **defaults plus targeted overrides, callable in one line.**

---

## Core Concept 5 — Fixtures: Static Files vs Code

A **fixture** is the baseline a test starts from. There are two flavors.

**Static fixtures** are files checked into the repo — a `users.json`, a SQL dump, a `.csv`. They're easy to eyeball and fine for read-only reference data.

```json
// fixtures/users.json
[{ "id": 1, "name": "Test User", "tier": "standard" }]
```

**Programmatic fixtures** are built in code in your test's setup:

```python
@pytest.fixture
def standard_user():
    return CustomerFactory(tier="standard")
```

Prefer programmatic fixtures for anything a test *acts on*. Static files drift: a field is added to the model, the JSON isn't updated, and tests silently load half-built objects. Code-built fixtures fail loudly the moment the model changes, and they let you express intent (`a_customer().with_tier("gold")`) instead of hand-editing JSON. Keep static files for large, stable reference data — country codes, a product catalog seed — where the content rarely changes and being human-readable is a genuine plus.

---

## Real-World Examples

- **The shipping test, revisited.** A team's `Order` constructor gained a `currency` field. Every test that built an order inline broke — 140 of them. The team that used `an_order()` changed one default and was green in minutes. Builders absorb schema churn.
- **The "name" that broke a search test.** A search test used `CustomerFactory()` which generates a random faker name. Once, the random name happened to contain the search term, and an assertion about "no results" failed. The fix: pin the relevant field (`CustomerFactory(name="Zzxq")`) so the test controls what it depends on. Randomness is fine *except* for the fields a test asserts on.
- **The JSON fixture nobody could read.** A 600-line `seed.json` underpinned an integration test. When it failed, no one could tell which of the 600 lines mattered. Splitting it into builders (`an_account().with_balance(0)`) made each test's dependencies visible at the call site.

---

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Inlining every field in every test | Unreadable; breaks on any schema change | Use a builder with defaults |
| Asserting on a randomly-generated field | Flaky — passes or fails by luck | Pin the field the assertion depends on |
| Static JSON fixtures for objects tests mutate | Drift; silent half-built objects | Build fixtures in code |
| One giant shared fixture for all tests | Mystery guest; tests coupled to each other | Local builders per test |
| `datetime.now()` inside a builder default | Non-deterministic; tomorrow it breaks | Use a fixed date |

---

## Apply it

1. Choose one small, known input for **Test Data Management**.
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

- What problem does Test Data Management solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
