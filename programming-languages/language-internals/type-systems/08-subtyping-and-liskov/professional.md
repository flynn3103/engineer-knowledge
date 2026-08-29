# Subtyping & Liskov Substitution — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Subtyping & Liskov Substitution** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Anatomy of an LSP Production Incident

Every LSP incident has the same three actors:

1. **A base type with an implicit contract.** `Rectangle` promises independent width/height. `List` promises `add` works. `Bird` promises `fly` flies. The contract is often *unwritten* — that's part of the problem.
2. **Generic code that trusts the contract.** A reporting function that resizes any `Rectangle`. A pipeline that calls `list.add(item)`. A migration loop that calls `bird.fly()`. This code is *correct* — it relies only on the base type's promise.
3. **A subtype that breaks the contract, introduced separately.** `Square`, `unmodifiableList`, `Penguin`. Often added months later, by someone who never saw the generic code, who reasoned "a square *is a* rectangle, obviously."

The bug fires only when actor 3's instance flows through actor 2's code. Because that conjunction is rare, the defect evades tests proportional to how rare the bad subtype is on the hot path. The diagnostic signature: **a stack trace through generic, base-typed code, with a concrete subtype at the bottom that violated an assumption the generic code was entitled to make.** Once you learn to see that shape, you stop blaming "the edge case" and start naming "the substitutability break."

### 2. The Square/Rectangle Refactor — Three Real Exits

The canonical violation has three legitimate fixes, chosen by constraints:

**Exit A — Make them immutable.** The break needs mutation (`setWidth`). Remove the setters; "resizing" returns a new instance. Now a `Square` is just a `Rectangle` with `width == height` at construction, and there's no mutator to corrupt the invariant. This is usually the *best* fix when you control the type.

**Exit B — Don't subtype; both implement a common `Shape`.** `Square` and `Rectangle` are siblings under `Shape` (with `area()`), with no inheritance between them. You lose the (false) `Square <: Rectangle` relation you never legitimately had. Code that genuinely needed "a thing with an area" works; code that needed "a mutable rectangle" never gets a square.

**Exit C — Keep inheritance for reuse, drop substitutability.** If `Square` truly needs `Rectangle`'s code, hold a `Rectangle` by composition and expose only `setSide`. The `Square` is not a `Rectangle` subtype; it *uses* one. **Composition over inheritance** in its purest motivation.

The wrong "fix" — making `setWidth` on `Square` throw, or having it adjust height "smartly" — just relocates the violation. There is no override that makes `Square extends Rectangle` sound while both are mutable; the invariant is irreconcilable.

### 3. The Read-Only Collection Problem — A Shipped Violation

`Collections.unmodifiableList(list).add(x)` throws `UnsupportedOperationException`. This **violates LSP**: `List` declares `add`; a caller holding a `List` is contractually entitled to call it; the unmodifiable view strengthens the precondition to "only if mutable" and crashes otherwise. The JDK shipped this knowingly because, pre-generics and pre-`record`, the alternative (a separate `ImmutableList` type that is *not* a `List`) would have fragmented the entire collections API and broken interoperability with every method taking `List`.

The lesson isn't "the JDK was wrong" — it's a documented, conscious trade-off — but **don't copy the pattern blindly**. The principled design, when you have the choice, is a *type-level* split: a read-only supertype that genuinely lacks mutators, with the mutable type as a subtype.

```java
// Principled: the read view has no add() to break.
interface ReadOnlyList<E> { E get(int i); int size(); }
interface MutableList<E> extends ReadOnlyList<E> { void add(E e); }
```

Guava's `ImmutableList`, Kotlin's `List` vs `MutableList`, and C#'s `IReadOnlyList<T>` all take this principled route precisely to avoid the JDK's LSP wart.

### 4. The Bird/Penguin Refactor — Capability Interfaces

`Penguin extends Bird` with a throwing `fly()` is a **refused bequest**: the subtype inherits an ability it can't honor. The fix is to stop putting abilities on a type that not all subtypes possess. Decompose into **capability interfaces**:

```java
interface Bird { void eat(); }
interface Flyable { void fly(); }
interface Swimmable { void swim(); }

class Sparrow implements Bird, Flyable { /* ... */ }
class Penguin implements Bird, Swimmable { /* ... */ }
```

Now no caller can call `fly()` on a `Bird` — they must hold a `Flyable`, and only types that *can* fly are `Flyable`. The contract is enforced by the type system instead of by a hopeful runtime exception. This is the Interface Segregation Principle (the "I" in SOLID) working hand-in-glove with LSP: small, honest interfaces make substitutability breaks structurally impossible.

### 5. When a Pragmatic Violation Is Defensible — and How to Fence It

Sometimes shipping a violation is the right engineering call: a legacy interface you can't change, a third-party base class, an optional capability. The professional move is to **fence** it:

- **Make the violation loud and documented**, not silent. A `throw new UnsupportedOperationException("read-only view")` is at least *loud*; a `Square` silently returning a wrong area is the worse failure mode.
- **Provide a capability probe** so callers can check before they leap: `list instanceof RandomAccess`, `account.canWithdraw(amount)`, a `supportsX()` method. This converts a precondition the caller couldn't know about into one they can test.
- **Confine the blast radius.** Keep the violating subtype away from the generic code paths that would trip it; never hand it to an API that will exercise the broken operation.
- **Write it into the type's documentation as a known deviation**, so the next maintainer doesn't "fix" it by removing the guard.

The judgment is: a violation is defensible when it's *loud, probeable, confined, and documented*. It's indefensible when it's *silent, undetectable, and free to flow anywhere* — which is exactly the Square/Rectangle failure mode.

### 6. Designing Defensive Base Types

The best LSP strategy is to make violations *hard to introduce*. Defensive base types:

- **Are minimal.** Fewer methods = smaller contract = fewer promises a subtype can break. (ISP again.)
- **Are immutable where possible.** No setters, no mutation, no history-constraint problems.
- **Are sealed when the subtype set is closed** (Java/Kotlin `sealed`, Rust enums). A closed hierarchy you control can be *audited* for substitutability exhaustively, and exhaustive `switch`/`match` catches a missed case at compile time.
- **Expose capabilities, not classifications.** Prefer `Comparable`, `Iterable`, `Closeable` (what you can *do*) over deep taxonomic base classes (what you *are*). Capability interfaces are inherently easier to satisfy honestly.
- **Avoid protected mutable state.** Exposing `protected` fields invites subclasses to break invariants the base can no longer guard.

---

## Code Examples

### Example 1: Diagnosing the incident — the tell-tale stack shape

```java
// Generic code, written against the base type, entitled to trust the contract:
class ReportGenerator {
    void renderResized(List<Rectangle> shapes) {
        for (Rectangle r : shapes) {
            r.setWidth(100);
            r.setHeight(50);
            cells.add(r.area());     // base contract: must be 100*50 = 5000
        }
    }
}
// Months later, somewhere far away:
shapes.add(new Square());            // "a square is a rectangle, right?"
// Production: one report cell shows 2500 instead of 5000. No exception. No alert.
// The stack trace, if you even get one, runs through ReportGenerator (base-typed)
// with a Square at the bottom. THAT shape = LSP violation, not "weird edge case."
```

### Example 2: Refactor Exit A — immutability dissolves the violation

```java
public final class Rectangle {
    private final int width, height;
    public Rectangle(int w, int h) { this.width = w; this.height = h; }
    public Rectangle withWidth(int w)  { return new Rectangle(w, height); }
    public Rectangle withHeight(int h) { return new Rectangle(width, h); }
    public int area() { return width * height; }

    public static Rectangle square(int side) { return new Rectangle(side, side); }
}
// No setters -> no invariant to corrupt -> Square is just a construction, not a broken subtype.
// renderResized now uses withWidth/withHeight and CANNOT be sabotaged.
```

### Example 3: Refactor for read-only — the principled split

```java
public interface ReadOnlyList<E> {        // no add(): nothing for a view to break
    E get(int index);
    int size();
}
public interface MutableList<E> extends ReadOnlyList<E> {
    void add(E e);
    void remove(int index);
}

// An immutable implementation is honestly a ReadOnlyList, never claiming add():
public final class FrozenList<E> implements ReadOnlyList<E> { /* ... */ }

// Callers that need to mutate ask for MutableList; callers that read ask for ReadOnlyList.
// No caller can ever call add() on something that will throw — the type system forbids it.
```

### Example 4: Capability interfaces over taxonomy (Bird/Penguin done right)

```java
interface Bird  { void eat(); }
interface Flyable   { void fly(); }
interface Swimmable { void swim(); }

final class Eagle   implements Bird, Flyable             { public void fly()  {/*..*/} public void eat(){} }
final class Penguin implements Bird, Swimmable           { public void swim() {/*..*/} public void eat(){} }

void migrate(List<Flyable> flock) {   // only things that CAN fly are even accepted
    flock.forEach(Flyable::fly);      // no runtime UnsupportedOperationException possible
}
// migrate(List.of(new Penguin()));   // ✗ compile error — Penguin is not Flyable. Good.
```

### Example 5: Fencing a pragmatic violation with a probe

```java
interface PaymentMethod {
    void charge(Money amount);
    boolean supportsRefund();              // capability probe
    void refund(Money amount);             // may throw if !supportsRefund()
}

void issueRefund(PaymentMethod pm, Money amount) {
    if (!pm.supportsRefund()) {            // caller can CHECK before leaping
        queueManualRefund(amount);
        return;
    }
    pm.refund(amount);                     // safe: precondition verified
}
```

The violation (some methods can't refund) is made *probeable* instead of silent, converting an LSP landmine into a checkable precondition.

### Example 6: Contract test — enforcing the behavioral contract the compiler can't

```java
// Every Account subtype must pass this. Run it parameterized over all implementations.
abstract class AccountContractTest {
    abstract Account newAccount(int initialBalance);

    @Test void withdraw_reduces_balance_for_any_positive_amount_up_to_balance() {
        Account a = newAccount(100);
        a.withdraw(80);                       // base contract: 80 is valid, must succeed
        assertEquals(20, a.balance());        // postcondition must hold for EVERY subtype
    }

    @Test void withdraw_never_makes_balance_negative() {  // invariant
        Account a = newAccount(100);
        assertThrows(Exception.class, () -> a.withdraw(150));
        assertTrue(a.balance() >= 0);
    }
}
class SavingsAccountTest extends AccountContractTest { Account newAccount(int b){ return new SavingsAccount(b);} }
class CheckingAccountTest extends AccountContractTest { /* ... */ }
```

A subtype that strengthens a precondition or weakens a postcondition fails the *base type's* contract test — turning LSP from discipline into a CI gate.

---

## Coding Patterns

**Pattern 1 — Contract-test every base type with multiple implementations.** Make the behavioral contract executable; run it against all subtypes in CI. This is the closest thing to a compiler for the behavioral half of LSP.

**Pattern 2 — Replace classification hierarchies with capability interfaces.** Whenever a base type has a method only *some* subtypes can honor, that method belongs on a capability interface, not the base. Lets the type system reject the bad combination.

**Pattern 3 — Split read and write into separate interfaces.** Hand callers the narrowest interface they need. A reader gets a read-only (covariant-friendly, mutation-free) interface that has no operation to break.

**Pattern 4 — Prefer composition + delegation to subclass inheritance for reuse.** When you want the *code* but not the *substitutability obligation*, hold the base as a field and expose only the operations that stay valid.

```java
final class Square {                 // NOT `extends Rectangle`
    private final Rectangle r;
    Square(int side) { this.r = new Rectangle(side, side); }
    int area() { return r.area(); }  // delegate the reuse; expose no width/height setters
}
```

**Pattern 5 — Seal hierarchies you control and `switch` exhaustively.** A closed subtype set lets the compiler enforce that every case is handled and lets you audit substitutability across a finite, known set.

---

## Best Practices

- **Treat an unwritten base-type contract as a bug.** If you can't state a base type's preconditions, postconditions, and invariants, neither can the people subtyping it — write them down.
- **Default to composition; reach for inheritance only when substitutability genuinely holds.** "Prefer composition over inheritance" exists primarily to prevent LSP violations.
- **Put abilities on capability interfaces, classifications on base types.** `Flyable.fly()`, not `Bird.fly()`. ISP and LSP reinforce each other.
- **Ship read-only as a real supertype, not a throwing view.** Avoid the `unmodifiableList` pattern in your own APIs when you control the design.
- **If you must violate LSP, make it loud, probeable, confined, and documented** — never silent and free-flowing.
- **Add a base-type contract test before you add the second subtype.** The cost is trivial then and enormous after ten subtypes have drifted.
- **In code review, scan for the violation shapes:** an override that throws/no-ops (refused bequest), an override that narrows accepted input, an override that changes a return's meaning, a subtype that adds mutation under an immutable base.

---

## Edge Cases & Pitfalls

- **The "smart" override that hides the break.** A `Square.setWidth` that "helpfully" adjusts height doesn't fix the violation — it makes the wrong answer look intentional and harder to spot. There is no correct override; the relationship is wrong.
- **Serialized-data lock-in.** You can't always split a hierarchy freely: persisted/serialized type tags, ORM mappings, and wire formats may pin the existing inheritance. Plan a migration, not a rename.
- **Liskov violations through equals/hashCode.** A subtype that adds a field but inherits `equals` breaks symmetry/transitivity — a substitutability break in the `Object` contract that corrupts hash-based collections silently.
- **Framework base classes you must extend.** Some frameworks force inheritance (`Activity`, `Servlet`). You inherit their contract and any leeway/violation they permit; keep your override surface minimal and honest.
- **Contract tests that test the implementation, not the contract.** A base-type contract test must assert only what the *base contract* promises. If it asserts subtype-specific behavior, it can't be shared and stops catching violations.
- **Capability-interface explosion.** Over-segmenting into dozens of one-method interfaces fragments the API and burdens implementers. Segment by *coherent capability*, not by individual method.
- **The covariant-array hole in real code.** Legacy `Object[]` APIs and varargs reintroduce the unsound covariance from `senior.md` into production, surfacing as `ArrayStoreException` far from the actual mistake.
- **"It's only internal" complacency.** Internal hierarchies grow callers too. An LSP violation in an internal base type has a blast radius equal to its internal usage — which is often larger than expected by the time it bites.

---

## Apply it

1. Define the user or business outcome that **Subtyping & Liskov Substitution** should improve.
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

- Which measurable outcome justifies investing in Subtyping & Liskov Substitution?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
