# Subtyping & Liskov Substitution — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Subtyping & Liskov Substitution** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Subtyping Is "Usable Where Expected"

Forget inheritance for a moment. The clean definition is about *usage*:

> **S is a subtype of T if a value of type S can be used in every context that expects a value of type T.**

If `printArea(Shape s)` expects a `Shape`, and `Circle` is a subtype of `Shape`, then `printArea(new Circle(...))` must work. That is the entire idea. The subtype is *at least as capable* as the supertype — it has every method, it accepts every input the supertype accepted, and it makes every guarantee the supertype made.

This is why subtyping is sometimes called the **substitution relation**: the subtype can substitute for the supertype.

### 2. The Subsumption Rule: An S Value "Has Type" T

Here is the rule that makes the whole thing tick. In type theory it is called **subsumption**, and it reads:

```text
   If e has type S,  and  S <: T,
   then e also has type T.
```

In plain terms: a `Dog` value doesn't *stop* being a `Dog` — it just *also* counts as an `Animal`. So when you write:

```java
Animal a = new Dog();   // a Dog value, viewed at type Animal
```

you have applied subsumption. The value is a `Dog`; the *static type* of the variable is `Animal`. That widening from the specific type to the general one is what lets the same `feed(Animal)` function accept dogs, cats, and goldfish without knowing about any of them.

### 3. Nominal vs Structural — Two Ways to Be a Subtype

There are two schools of thought on *how* the compiler decides `S <: T`.

**Nominal subtyping** (Java, C#, C++, Scala): you are a subtype **because you said so**. The subtype relation follows the declared hierarchy — `class Dog extends Animal` or `class ArrayList implements List`. If you didn't write `extends`/`implements`, you are not a subtype, even if your class happens to have all the right methods.

**Structural subtyping** (TypeScript, Go's interfaces): you are a subtype **because your shape fits**. If a type has all the methods/fields the target needs, it qualifies automatically — no declaration required. In Go, a type satisfies an interface just by having its methods; it never names the interface.

```typescript
// TypeScript — structural. No "implements" needed.
interface Named { name: string; }
function greet(x: Named) { console.log(x.name); }

const dog = { name: "Rex", legs: 4 };   // not declared as Named...
greet(dog);                              // ...but it fits the shape, so it's accepted
```

Both styles produce a subtype relation; they just disagree about what *establishes* it. (This split is covered in depth in the nominal-vs-structural topic of this section.)

### 4. The Real Contract: Preconditions, Postconditions, Invariants

The compiler checks *signatures*. LSP is about something the compiler can't see: **behavior**. A method's real contract has three parts.

- **Precondition** — what the method demands *before* it runs. `withdraw(amount)` might require `amount > 0 && amount <= balance`.
- **Postcondition** — what it promises *after* it runs. `withdraw` promises `balance == old_balance - amount`.
- **Invariant** — what stays true the whole time the object lives. A `BankAccount` might guarantee `balance >= 0`, always.

A subtype is allowed to *override* methods, but only if it keeps the contract honest. And the rules for "keeping it honest" are the heart of LSP — covered fully in `middle.md`, but worth previewing:

- A subtype **may not strengthen preconditions** — it can't demand *more* than the base did. (If `Animal.eat(food)` accepts any food, `Dog.eat(food)` can't reject vegetables — callers holding an `Animal` won't know to avoid them.)
- A subtype **may not weaken postconditions** — it can't promise *less*. (If `Account.withdraw` guarantees the money is gone, an overriding subtype can't sometimes leave it.)
- A subtype **must preserve invariants** — it can't break a truth the base type guaranteed.

### 5. Inheritance Is Not Subtyping

This trips up almost everyone early. **Inheritance** (`extends`) is a tool for *reusing code*. **Subtyping** is a relation about *substitutability*. In most OO languages, `extends` happens to give you both at once — which is exactly why people conflate them. But they are different ideas:

- You can have **subtyping without inheritance**: implementing an interface, or structural typing in Go/TypeScript.
- You can *abuse* inheritance to get code reuse where the subtype is *not* substitutable — and that is precisely the LSP violation. `class Square extends Rectangle` reuses the rectangle's code, but a `Square` is *not* a substitutable `Rectangle`, as we'll see.

The classic advice "**prefer composition over inheritance**" exists largely because inheritance tempts you into LSP violations. If you only need the code, compose. Only subtype when the subtype is genuinely substitutable.

---

## Code Examples

### Example 1: Sound subtyping — `Dog` substitutes for `Animal`

```java
class Animal {
    String describe() { return "an animal"; }
    int legs()        { return 4; }
}

class Dog extends Animal {
    @Override String describe() { return "a dog"; }   // still returns a String — OK
    void fetch() { /* extra ability, fine */ }
}

void printInfo(Animal a) {            // expects an Animal
    System.out.println(a.describe() + " with " + a.legs() + " legs");
}

printInfo(new Animal());   // an animal with 4 legs
printInfo(new Dog());      // a dog with 4 legs   <-- Dog substitutes cleanly
```

`Dog` adds an ability (`fetch`) and refines a result (`describe`) without removing or weakening anything. Any code holding an `Animal` keeps working. This is LSP done right.

### Example 2: The canonical violation — Square breaks Rectangle

This is *the* example to internalize. A `Rectangle` has an implicit **invariant**: width and height are independent. A `Square` enforces width == height. Make `Square extends Rectangle` and the invariant breaks.

```java
class Rectangle {
    protected int width, height;
    void setWidth(int w)  { this.width = w; }
    void setHeight(int h) { this.height = h; }
    int area()            { return width * height; }
}

class Square extends Rectangle {
    // A square must stay square, so setting one side sets both:
    @Override void setWidth(int w)  { this.width = w; this.height = w; }
    @Override void setHeight(int h) { this.width = h; this.height = h; }
}
```

Now write innocent, polymorphic code against the *base* type:

```java
void resizeAndCheck(Rectangle r) {
    r.setWidth(5);
    r.setHeight(4);
    // The base contract says width and height are independent,
    // so the area MUST be 5 * 4 = 20.
    assert r.area() == 20 : "expected 20, got " + r.area();
}

resizeAndCheck(new Rectangle());  // area 20  ✓
resizeAndCheck(new Square());     // area 16  ✗  setHeight(4) also set width to 4!
```

The function never mentions `Square`. It relies on a promise `Rectangle` made — "set width and height independently." `Square` silently broke that promise. The code compiled. It ran. It is *wrong*. **`Square` is not a subtype of `Rectangle`**, no matter what geometry class taught you.

### Example 3: The bird that can't fly

```java
class Bird {
    void fly() { /* flap, take off */ }
}

class Penguin extends Bird {
    @Override void fly() {
        throw new UnsupportedOperationException("penguins can't fly");
    }
}

void migrate(Bird b) {
    b.fly();   // perfectly reasonable to call on a Bird
}

migrate(new Penguin());   // 💥 crashes at runtime
```

`Penguin.fly()` **strengthens the precondition** to the impossible ("you may only call me if I'm not a penguin") and **weakens the postcondition** (it promises a crash instead of flight). Any code that holds a `Bird` and calls `fly()` is now a landmine. The fix is to not put `fly()` on `Bird` — separate `Bird` from `FlyingBird`.

### Example 4: The "read-only" list that throws — a real-world LSP violation

Java's standard library does this *on purpose*, and it's a famous LSP wart. `Collections.unmodifiableList` returns a `List` whose mutating methods throw:

```java
List<String> base = new ArrayList<>(List.of("a", "b"));
List<String> view = Collections.unmodifiableList(base);

view.add("c");   // 💥 UnsupportedOperationException at runtime — but view IS-A List!
```

`List` declares `add()`. A caller holding a `List` is entitled to call `add()`. The unmodifiable view *claims* to be a `List` but **strengthens the precondition** ("you may call `add` only if I happen to be mutable") and crashes otherwise. The compiler can't catch it because the *signature* is satisfied. This is the textbook case of a library shipping an LSP violation because the type hierarchy lacks a real "read-only list" supertype.

### Example 5: Structural subtyping in Go — no `extends` in sight

```go
type Stringer interface {
    String() string
}

type Point struct{ X, Y int }

func (p Point) String() string {              // Point never names Stringer...
    return fmt.Sprintf("(%d, %d)", p.X, p.Y)
}

func describe(s Stringer) {                    // ...but it satisfies the shape,
    fmt.Println(s.String())                    //    so it's a subtype structurally
}

describe(Point{1, 2})   // (1, 2)
```

`Point` is a subtype of `Stringer` purely because it has a matching `String()` method. Go decides subtyping by *shape*, not by declaration — the structural model.

---

## Coding Patterns

**Pattern 1 — Program to the supertype, not the subtype.** Accept and store the most general type that supports what you need. `void render(Shape s)`, not `void render(Circle c)`. This is the discipline that makes subtyping pay off.

```java
List<Shape> shapes = new ArrayList<>();   // List + Shape: general on both axes
shapes.add(new Circle(3));
shapes.add(new Rectangle(2, 4));
for (Shape s : shapes) System.out.println(s.area());
```

**Pattern 2 — Split the hierarchy when behavior diverges.** When a "subtype" can't honor the base contract, that's a signal to split the type, not to override-and-throw.

```java
interface Bird { void eat(); }
interface FlyingBird extends Bird { void fly(); }

class Sparrow implements FlyingBird { /* eat + fly */ }
class Penguin implements Bird       { /* eat only — no fly() to break */ }
```

**Pattern 3 — Make the problematic type immutable.** The Square/Rectangle break depends on *mutation* (`setWidth`). Immutable shapes don't have that problem: a square just *is* a square, and producing a "wider" one returns a new object.

```java
final class Rectangle {
    final int width, height;
    Rectangle(int w, int h) { width = w; height = h; }
    Rectangle withWidth(int w) { return new Rectangle(w, height); }
    int area() { return width * height; }
}
// A Square is just a Rectangle factory: Rectangle.square(5) -> new Rectangle(5,5).
// No subtype, no broken invariant.
```

**Pattern 4 — Compose instead of inherit when you only want the code.** If you need a `Rectangle`'s behavior inside a `Square`, hold one as a field rather than extending it — then expose only the operations that stay valid.

---

## Best Practices

- **Ask "can a stranger substitute this subtype blindly?"** If the honest answer is "only if they know it's actually the subclass," you have an LSP violation. Fix the design, not the caller.
- **Write the base type's contract down.** Even a one-line comment — "invariant: balance >= 0; width and height independent" — turns an implicit promise into a checkable one.
- **Never override a method just to throw `UnsupportedOperationException`.** That is the loudest possible LSP alarm. The type doesn't belong under that base type.
- **Prefer interfaces (pure contracts) over concrete base classes** when you mainly want subtyping. Concrete inheritance drags implementation details into the relationship and invites violations.
- **Prefer composition over inheritance** whenever you want code reuse without substitutability. Reach for `extends` only when the subtype is genuinely a stand-in for the base.
- **Treat "is-a" as a question, not an answer.** "Is a Square a Rectangle?" → "In code that mutates width and height independently? No." Always check against the actual contract.

---

## Edge Cases & Pitfalls

- **The override that *narrows* what it accepts.** A subtype method that rejects inputs the base accepted (a strengthened precondition) is a violation, even though it compiles. `Dog.eat(food)` that throws on vegetables breaks any caller holding an `Animal`.
- **The override that *throws where the base returned*.** Replacing a normal return with an exception weakens the postcondition. Callers expecting a value now get a crash.
- **Silent invariant corruption.** Square/Rectangle: nothing throws, nothing warns — `area()` just returns the wrong number. These are the hardest to catch because there's no exception, only a wrong answer downstream.
- **Empty/no-op overrides.** A subtype that overrides a method to "do nothing" often weakens a postcondition (the base promised an effect that no longer happens). Sometimes fine, often a smell.
- **Mutability is the accomplice.** Most classic LSP breaks (Square, mutable collections) need mutation to manifest. Immutable designs sidestep a whole category of these.
- **Structural typing's accidental matches.** In Go/TypeScript a type can satisfy an interface *by accident* because its method names happen to match — and then violate the *behavioral* contract you never declared. Structural subtyping checks shape, never meaning.
- **Confusing "compiles" with "substitutable."** The single most common junior trap: the code passes the type checker, so it must be a valid subtype. The type checker only ever checked the signature.

---

## Apply it

1. Choose one small, known input for **Subtyping & Liskov Substitution**.
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

- What problem does Subtyping & Liskov Substitution solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
