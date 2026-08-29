# Behavior-First Mindset — Middle

> **What?** The mindset applied in practice — a step-by-step refactoring of an anemic class into a behavior-first object, the moves that get you there, and the points where you stop pulling behavior in.
> **How?** By following a real order-processing class through Move Method, Replace Conditional with Polymorphism, and Encapsulate Collection — and by watching where each move lands.

---

## 1. The starting point — an anemic order

A typical "Spring-shaped" service layer looks like this. `Order` is data; `OrderService` does everything.

```python
@dataclass
class Order:
    id: int
    customer_id: int
    lines: list[OrderLine] = field(default_factory=list)
    status: str = "DRAFT"
    total: Decimal = Decimal("0")
    placed_at: datetime | None = None
    currency: str = "USD"
```

```python
class OrderService:
    def place(self, order: Order) -> None:
        if order.status != "DRAFT":
            raise ValueError("only drafts can be placed")
        if not order.lines:
            raise ValueError("empty order")
        order.total = sum((line.unit_price * line.quantity for line in order.lines), Decimal("0"))
        order.status = "PLACED"
        order.placed_at = datetime.now(UTC)

    def cancel(self, order: Order) -> None:
        if order.status == "SHIPPED":
            raise ValueError("shipped orders cannot be cancelled")
        order.status = "CANCELLED"

    def add_line(self, order: Order, line: OrderLine) -> None:
        if order.status != "DRAFT":
            raise ValueError("can only modify drafts")
        order.lines.append(line)
```

Symptoms, before we change a line:

- Every rule lives in the service. `Order` is unable to refuse anything.
- `getStatus()` is consulted from outside. `setStatus()` lets anyone write any string.
- The collection of lines leaks: `order.getLines().add(...)` mutates internal state without the order knowing.
- The total is stored, then recomputed externally, then written back. Two sources of truth.

This is the **anemic domain model** — see `[../../07-antipatterns-and-code-smells/02-anemic-domain-model/](../../07-antipatterns-and-code-smells/02-anemic-domain-model/)`. The refactor below is the antidote.

---

## 2. Move 1 — Move Method: pull `place` into the order

The first move is mechanical. `OrderService.place(order)` works exclusively on `order` and its lines. That's the textbook signal for **Move Method**: the method belongs on the data it operates on.

```python
class Order:
    # Fields are unchanged for now.
    def place(self) -> None:
        if self.status != "DRAFT":
            raise ValueError("only drafts can be placed")
        if not self.lines:
            raise ValueError("empty order")
        self.total = sum((line.unit_price * line.quantity for line in self.lines), Decimal("0"))
        self.status = "PLACED"
        self.placed_at = datetime.now(UTC)
```

```python
class OrderService:
    def place(self, order: Order) -> None:
        order.place()
```

The service is now a one-line forwarder. That's a smell of its own — but a useful one, because it tells you the service has no reason to exist for this method. Apply the same move to `cancel` and `addLine`.

---

## 3. Move 2 — Extract Method: name the steps

`place()` does three things: validate, compute the total, transition the state. Extract them so each step has a name.

```python
class Order:
    def place(self) -> None:
        self._require_draft()
        self._require_non_empty()
        self.total = self._compute_total()
        self.status = "PLACED"
        self.placed_at = datetime.now(UTC)

    def _require_draft(self) -> None:
        if self.status != "DRAFT":
            raise ValueError("only drafts can be placed")

    def _require_non_empty(self) -> None:
        if not self.lines:
            raise ValueError("empty order")

    def _compute_total(self) -> Decimal:
        return sum((line.subtotal() for line in self.lines), Decimal("0"))
```

Two side-effects of this small step:

1. `OrderLine.subtotal()` appears naturally. The line knows its own price and quantity — it should compute its own subtotal. Behavior follows data.
2. The validation methods are named. `requireDraft()` is a domain phrase, not an `if`.

---

## 4. Move 3 — Replace primitive status with a real type

`status` is a `String`. Any string compiles. The compiler can't help when someone writes `"PAYED"` instead of `"PAID"`, or compares against `"placed"` instead of `"PLACED"`.

Replace it with an enum:

```python
class OrderStatus(Enum):
    DRAFT = auto()
    PLACED = auto()
    PAID = auto()
    SHIPPED = auto()
    CANCELLED = auto()

class Order:
    def __init__(self) -> None:
        self._status = OrderStatus.DRAFT

    def _require_draft(self) -> None:
        if self._status is not OrderStatus.DRAFT:
            raise ValueError("only drafts can be placed")
```

The enum is a small step, but it eliminates an entire class of typo bugs and gives the IDE something to autocomplete. It also sets up Move 5 (polymorphism).

---

## 5. Move 4 — Encapsulate Collection: stop leaking `lines`

`order.getLines().add(line)` is a hole in the encapsulation: the caller mutates the internal list directly. The order can neither validate nor react. Close the hole.

```python
class Order:
    def __init__(self) -> None:
        self._lines: list[OrderLine] = []

    def add(self, product: Product, quantity: int) -> None:
        self._require_draft()
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._lines.append(OrderLine(product, quantity))

    def remove(self, product: Product) -> None:
        self._require_draft()
        self._lines = [line for line in self._lines if line.product != product]

    @property
    def lines(self) -> tuple[OrderLine, ...]:
        return tuple(self._lines)
```

Now there is no way for a caller to add a line to a non-draft order — the rule is enforced by the only path into the collection. `lines()` returns a snapshot, not the internal reference; callers can iterate but not mutate.

This is also where **Law of Demeter** stops being violated—see [Law of Demeter](../../02-coupling-and-cohesion/04-law-of-demeter/). Callers no longer reach through an order's lines to mutate them; they tell the order what to do.

---

## 6. Move 5 — Replace Conditional with Polymorphism

After a few rounds, the order looks like this:

```python
def cancel(self) -> None:
    match self.status:
        case OrderStatus.DRAFT | OrderStatus.PLACED:
            self.status = OrderStatus.CANCELLED
        case OrderStatus.PAID:
            self.status = OrderStatus.CANCELLED
            self._refund()
        case OrderStatus.SHIPPED:
            raise ValueError("already shipped")
        case OrderStatus.CANCELLED:
            raise ValueError("already cancelled")

def ship(self) -> None:
    if self.status is not OrderStatus.PAID:
        raise ValueError("must be paid to ship")
    self.status = OrderStatus.SHIPPED

def pay(self, payment: Payment) -> None:
    if self.status is not OrderStatus.PLACED:
        raise ValueError("must be placed to pay")
    self.status = OrderStatus.PAID
```

Every transition starts with `if (status != ...)`. That repetition is the smell. The rules are about *what each status allows*. Push them onto the status itself:

```python
@dataclass(frozen=True)
class StateRules:
    can_place: bool = False
    can_pay: bool = False
    can_ship: bool = False
    can_cancel: bool = False

RULES = {
    OrderStatus.DRAFT: StateRules(can_place=True, can_cancel=True),
    OrderStatus.PLACED: StateRules(can_pay=True, can_cancel=True),
    OrderStatus.PAID: StateRules(can_ship=True, can_cancel=True),
    OrderStatus.SHIPPED: StateRules(),
    OrderStatus.CANCELLED: StateRules(),
}
```

```python
class Order:
    def ship(self) -> None:
        if not RULES[self.status].can_ship:
            raise ValueError(f"cannot ship from {self.status.name}")
        self.status = OrderStatus.SHIPPED
```

The transition rule lives next to the state it concerns. Adding a new status (say `RETURNED`) means editing one enum constant, not hunting `switch` statements across the codebase.

For richer state machines, sealed types per state (`DraftOrder`, `PlacedOrder`, `PaidOrder`) make illegal transitions un-callable at compile time. That's a senior-level refactor; the enum form is the right pragmatic stop for most code.

---

## 7. Move 6 — Inline the dead service

After moves 1–5, `OrderService` looks like this:

```python
class OrderService:
    def place(self, order: Order) -> None: order.place()
    def cancel(self, order: Order) -> None: order.cancel()
    def add_line(self, order: Order, line: OrderLine) -> None:
        order.add(line.product, line.quantity)
```

It's pure forwarding. Delete it. Have callers talk to `Order` directly.

What stays in service-shaped classes:

| Concern                                           | Belongs in service? |
|---------------------------------------------------|---------------------|
| Business rules of one order                       | No — on `Order`     |
| Coordinating multiple orders / aggregates         | Yes                 |
| Calling external systems (payment gateway, email) | Yes                 |
| Loading and saving from a repository              | Yes                 |
| Transactions, retries, locking                    | Yes                 |

A leaner `OrderingService` survives — but it orchestrates, it doesn't enforce rules.

---

## 8. The cohesion lens — does this method belong here?

After each move, ask:

1. Does the method use mostly this object's fields? If yes, it belongs.
2. Does it need to reach into another object's internals to work? If yes, it probably belongs there instead.
3. Does it need *external* services (DB, HTTP, queue) to do its job? Then it doesn't belong on the domain object — it belongs on something that can hold collaborators.

For `Order.computeTotal()`: uses `lines`, calls `OrderLine.subtotal()`. Belongs on `Order`. Good.

For `Order.sendConfirmationEmail()`: would need an `EmailService`. Doesn't belong on `Order`. The order can *return* a `ConfirmationRequest`; the orchestrator sends it.

For `Order.save()`: would need a database connection. Doesn't belong on `Order`. The repository handles persistence; the order knows nothing about it.

This is the cohesion test in one line: **a method belongs where its data lives, not where its side-effects fire.**

---

## 9. Mistakes that look like progress

**Mistake 1: methods that wrap a single setter.**

```python
def change_status(self, status: OrderStatus) -> None:
    self.status = status
```

You renamed `setStatus`. The object still has no opinion about which transitions are legal. This is **setter cosplay**, not behavior. A real method names a domain operation (`ship`, `cancel`) and enforces the rule.

**Mistake 2: getters in disguise.**

```python
def has_status(self, status: OrderStatus) -> bool:
    return self.status is status
```

If callers are constantly asking `hasStatus(SHIPPED)` and branching on the answer, you haven't moved the rule into the object — you've just changed the syntax of the leak. Replace `if (order.hasStatus(PLACED)) order.pay(p);` with `order.pay(p);` and let the order refuse if it must.

**Mistake 3: "do everything" methods.**

```python
def update(self, changes: dict[str, object]) -> None: ...
```

A god-method that takes a bag of fields and applies whatever's inside. The caller decides what to change; the object obeys. This is a setter for every field, wearing one signature. Split into named operations: `add`, `remove`, `applyDiscount`, `changeShippingAddress`.

**Mistake 4: stripping getters too aggressively.**

You still need a few. `total()`, `status()`, `lines()` — a UI has to render *something*. The rule isn't *no getters*; it's *no getters that exist only so external code can decide on the object's behalf*. A getter that exposes a value for display is fine. A getter that exists so a service can read, branch, and write back is not.

**Mistake 5: pulling persistence in.**

```python
def place(self) -> None:
    self._enforce_rules()
    repository.save(self)  # Do not couple a domain object to persistence.
```

The order now needs a repository to exist. Tests need a fake. The aggregate has grown a tentacle into infrastructure. Keep `place()` pure; let the caller save. Behavior-first does not mean *everything* on the object — only behavior that depends on the object's own state.

---

## 10. The result, side by side

| Aspect                       | Before                                | After                                                    |
|------------------------------|----------------------------------------|----------------------------------------------------------|
| Lines on `Order`             | 12 fields, mostly setters              | 6 fields, ~10 named operations                           |
| Rules location               | `OrderService` + caller code           | `Order` + `OrderStatus`                                  |
| Status type                  | `String`                               | `OrderStatus` enum                                       |
| Total                        | Stored, recomputed externally          | Computed by `computeTotal()`, single source              |
| Lines collection             | Exposed via `getLines()`               | `add` / `remove` / `lines()` snapshot                    |
| Service                      | Holds all logic                        | Orchestrates persistence + integrations only             |
| Adding a state               | Change `switch` in N service methods   | Add one enum constant                                    |
| Test setup                   | Mock service, set fields, assert       | New `Order`, call methods, assert state via accessors    |

The codebase grew shorter, not longer. The shape of "what an order is" became visible from one file.

---

## 11. Where to stop — honest limits

Behavior-first is a direction, not a religion. Real Java code has constraints:

- **JPA / Hibernate** wants a no-arg constructor and field access. You can keep that and still avoid public setters — use package-private setters for the ORM only, or use field access mode.
- **Jackson / serialization** can deserialize via constructors (records do this for free). You don't need setters to deserialize.
- **Validation frameworks** (`@NotNull`, `@Min`) expect fields. Compatible with behavior-first — the object still owns its rules; the annotations are a redundant safety net.
- **DTOs at the edge of your system** *should* be anemic. A `CreateOrderRequest` from a controller is a transport object — it has no behavior because it has no domain meaning. Convert it to a domain `Order` at the boundary. Don't apply behavior-first to DTOs; they're not objects in West's sense.
- **Read models / projections** for queries are also fine as records of fields. Read-side and write-side have different shapes — that's CQRS, and it's compatible with behavior-first on the write side.

The rule of thumb: **behavior-first applies to objects that own decisions**. It does not apply to objects whose only job is to cross a boundary.

---

## 12. A second example — Subscription

To see the pattern transfer, here is the same refactor compressed for a different domain.

Before:

```python
@dataclass
class Subscription:
    plan_id: int
    started_at: datetime
    cancelled_at: datetime | None
    state: str

class SubscriptionService:
    def pause(self, subscription: Subscription) -> None:
        if subscription.state != "ACTIVE":
            raise ValueError("only active subscriptions can pause")
        subscription.state = "PAUSED"

    def resume(self, subscription: Subscription) -> None: ...
    def cancel(self, subscription: Subscription) -> None: ...
```

After:

```python
class Subscription:
    def __init__(self, plan: Plan, clock: Clock) -> None:
        self._plan = plan
        self._started_at = clock.now()
        self._state = SubscriptionState.ACTIVE
        self._cancelled_at: datetime | None = None

    def pause(self) -> None: self._state = self._state.pause()
    def resume(self) -> None: self._state = self._state.resume()

    def cancel(self, clock: Clock) -> None:
        self._state = self._state.cancel()
        self._cancelled_at = clock.now()

    @property
    def is_active(self) -> bool: return self._state is SubscriptionState.ACTIVE

    @property
    def plan(self) -> Plan: return self._plan
```

The state transitions live in `SubscriptionState`; the `Subscription` exposes domain verbs. No `SubscriptionService` survives — only an orchestrator that loads, calls, and saves.

---

## 13. Recap — the moves in order

When you face an anemic class, the refactor is mechanical:

1. **Move Method** — pull each service method onto the object that owns its data.
2. **Extract Method** — name the steps inside the now-on-object operation.
3. **Replace Primitive with Type** — strings become enums, doubles become `Money`, longs become `OrderId`.
4. **Encapsulate Collection** — replace `getLines()` with `add` / `remove` / read-only snapshot.
5. **Replace Conditional with Polymorphism** — push state-specific behavior onto the state.
6. **Inline / shrink the service** — what's left is orchestration, not rules.

Each move is small. Each move is safe under tests. The aggregate isn't done — it's just *moving toward behavior-first*. Stop when the next move would drag infrastructure into the object.

---

## 14. What's next

| Topic                                                     | File              |
|-----------------------------------------------------------|-------------------|
| Behavior-first under ORM, performance, framework pressure | `senior.md`        |
| Driving the mindset across a team and a codebase          | `professional.md`  |
| Hands-on exercises                                        | [check your understanding](#check-your-understanding)         |

---

**Memorize this:** behavior-first refactoring is six moves — Move Method, Extract Method, Replace Primitive, Encapsulate Collection, Replace Conditional with Polymorphism, Inline Service. Stop where infrastructure begins. The object owns its rules; the orchestrator owns its collaborators.

---

---

## Check your understanding

1. Explain Behavior-First Mindset in your own words and name the problem it solves.
2. How would you apply the ideas around The starting point — an anemic order, Move 1 — Move Method: pull `place` into the order, Move 2 — Extract Method: name the steps in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. Which local design trade-off would make you choose or reject Behavior-First Mindset in an existing codebase?
5. What observable result would convince you that the approach improved the system?
