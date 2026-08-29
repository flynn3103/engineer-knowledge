# Static vs Dynamic Typing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Static vs Dynamic Typing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Gradual Typing: A Dial, Not a Switch

Gradual typing replaces the binary "static OR dynamic" with a **dial** you can turn per-variable, per-function, per-file. An unannotated parameter is dynamic (typed `any`/`Any`); an annotated one is static. The two coexist in the same program, and crucially, **values cross the boundary in both directions**.

```typescript
function lengthOf(x: string): number {  // statically typed
    return x.length;
}

let data: any = JSON.parse(input);       // dynamic — could be anything
let n = lengthOf(data);                  // boundary: `any` flows into a `string` param — allowed, NOT checked
```

The type checker allows `data` (an `any`) to be passed where a `string` is expected. It assumes you know what you're doing. If `data` is actually a number at runtime, plain TypeScript will *not* catch it — the types were erased, and there's no runtime guard. (This is the unsoundness; more below.)

### 2. The Escape Hatch: `any` / `Any`

`any` is the single most important — and most dangerous — feature of gradual typing. It is the type that is **assignable to and from everything**:

```typescript
let x: any = 42;
let s: string = x;     // allowed — any -> string, no check
let n: number = x;     // also allowed — any -> number
x.foo.bar.baz();       // allowed — any access on any is "valid"
```

`any` is "turn off the type system here." It exists so you can incrementally adopt types (the un-migrated parts are `any`) and so you can model genuinely dynamic data (parsed JSON, plugin systems). But it has a **viral, silent** failure mode: once a value is `any`, anything *derived* from it is also unchecked, so a single `any` at the top of a data-flow chain disables checking all the way down. The error that `any` would have caught reappears — at runtime, exactly where static typing was supposed to save you.

> The mid-level discipline in one rule: **every `any` is a debt. Pay it down or quarantine it.** A typed codebase's real safety is roughly `1 - (fraction of values that are any)`.

### 3. The Gradual Guarantee

The **gradual guarantee** (Siek, Vitousek, et al.) is the formal contract a *well-designed* gradual type system makes:

> Adding type annotations to a working program should only ever *add checks* — it must not change the program's runtime behavior (beyond possibly raising a type error sooner). Conversely, removing annotations (making things `any`) must never introduce a *static* type error.

In plain terms: **types are a monotonic safety net.** You can always make a program "more dynamic" by deleting annotations without breaking the build, and "more static" by adding them without changing what the program does (when correct). This is what makes gradual migration *safe to do piecemeal* — you can type one module at a time and trust that you haven't silently changed behavior elsewhere.

Note: TypeScript and Python-with-mypy **erase** types and so don't enforce types at the boundary at runtime — they uphold the *static* half of the guarantee but not the runtime-check half that fully-sound gradual systems (with runtime "casts" inserted at boundaries) would. This is a deliberate performance trade-off, and it's why a wrong `any` becomes a silent runtime bug rather than a clean boundary error.

### 4. Optional Typing: Annotations the Runtime Ignores

**Optional typing** is the special case where the annotations have *zero* runtime effect — they're purely a tool for the checker. This describes Python type hints (by default) and TypeScript:

```python
def greet(name: str) -> str:
    return "Hello, " + name

greet(42)   # mypy: ERROR. But at RUNTIME this raises TypeError on "+", because Python ignores the hint.
```

Python's interpreter does **not** check `name: str` at runtime — you can call `greet(42)` and Python will happily try, then fail on the `+` for a *different* reason (string + int). The hint guided the *checker*, not the *runtime*. (Libraries like `pydantic` and `typeguard` *opt in* to runtime enforcement, but that's extra machinery, not the language.)

This is the connection to **erasure** (next concept and `senior.md`): optional types are erased, so they cost nothing at runtime and guarantee nothing at runtime. Their entire value is delivered before the program runs.

### 5. Erasure vs Reification (Introduction)

- **Erased**: types are removed before running. TypeScript compiles to plain JavaScript with no type info. Java generics are erased — `List<String>` and `List<Integer>` are the same `List` at runtime. You *cannot* ask "what type parameter is this?" at runtime.
- **Reified**: types survive to runtime and can be inspected. Python values carry their type (`type(x)`, `isinstance(x, int)`). Go has runtime type information (reflection, type switches). C# generics are reified — `List<int>` truly knows it's `int` at runtime.

Why it matters here: in an **erased** gradual system, the `any` escape hatch leaks silently because there's no runtime type to catch the mismatch. In a **reified** dynamic language, the runtime *always* knows the real type, which is exactly how dynamic checking works in the first place — and why `isinstance` is available for hand-rolled validation. `senior.md` goes deep; for now: erased = cheap + silent failures; reified = costs memory + enables runtime introspection.

### 6. Duck Typing vs Structural vs Nominal Typing

These three answer the question: *when is value X acceptable where type Y is expected?*

**Duck typing (dynamic):** X is acceptable if, *at runtime*, it happens to have the methods you call on it. No declaration, no check beforehand.

```python
def make_it_quack(thing):
    thing.quack()   # works for ANYTHING with a .quack(), discovered at call time

class Dog:
    def quack(self): print("woof-ish quack")

make_it_quack(Dog())   # fine — Dog walks like a duck
```

**Structural typing (static):** X is acceptable if its *shape* (fields/methods) matches Y — verified by the compiler, no declared relationship needed. This is "duck typing checked at compile time."

```go
type Quacker interface { Quack() }

type Dog struct{}
func (Dog) Quack() {}   // Dog never says "implements Quacker" — but structurally it does

func main() {
    var q Quacker = Dog{}   // compiles: Dog has the right shape
}
```

```typescript
interface Quacker { quack(): void }
const dog = { quack() {}, bark() {} };
const q: Quacker = dog;   // compiles: dog's shape includes quack()
```

**Nominal typing (static):** X is acceptable only if it *declares* a relationship to Y. Shape alone is not enough.

```java
interface Quacker { void quack(); }
class Dog implements Quacker {   // MUST say "implements Quacker"
    public void quack() {}
}
// A class with a quack() method but no "implements Quacker" is NOT a Quacker in Java.
```

The mapping is the punchline: **structural typing is the static, compile-time-verified version of duck typing.** Go and TypeScript give you duck-typing's flexibility *with* a compiler checking it. Java and Rust are nominal — more explicit, less accidental coupling, but more ceremony.

### 7. Type Inference Makes Static Feel Dynamic (Forward Reference)

A big reason people *think* they want dynamic typing is the terseness — no annotations. But much of that terseness is available statically through **type inference**: the compiler figures out the type from the value.

```go
x := 5            // inferred int — no annotation, still fully static
name := "Ada"     // inferred string
```

```typescript
const nums = [1, 2, 3];   // inferred number[]
```

Languages with **Hindley–Milner** inference (Haskell, OCaml, ML, and Rust's local inference) take this furthest — you can write whole functions with *no* annotations and still get full static checking, because the compiler reconstructs every type. (The HM algorithm is a forward-referenced topic of its own.) The takeaway for this level: **"no annotations" does not mean "dynamic."** Inferred static typing gives you dynamic-looking source with compile-time guarantees — undercutting the main ergonomic argument for dynamic typing.

---

## Code Examples

### Gradual migration in Python: from dynamic to checked

```python
# Step 0 — fully dynamic, no hints
def total_price(items):
    return sum(i["price"] * i["qty"] for i in items)

# Step 1 — add hints; mypy now checks call sites, runtime unchanged
from typing import TypedDict

class Item(TypedDict):
    price: float
    qty: int

def total_price(items: list[Item]) -> float:
    return sum(i["price"] * i["qty"] for i in items)

# Now: total_price([{"price": "9.99", "qty": 1}])  -> mypy ERROR (price must be float)
# But at RUNTIME, with no enforcement, "9.99" * 1 == "9.99" and sum() then fails differently.
```

The hints upgraded the *checker's* knowledge without touching the *runtime*. That's optional + gradual typing in one snippet.

### The `any` leak, demonstrated

```typescript
interface User { id: number; name: string; }

function getUser(): User {
    const raw: any = JSON.parse('{"id": 1, "naem": "Ada"}');  // typo in data, but it's `any`
    return raw;   // `any` -> User: ALLOWED, no check. The typo passes straight through.
}

const u = getUser();
console.log(u.name.toUpperCase());  // RUNTIME: Cannot read properties of undefined (reading 'toUpperCase')
```

TypeScript's checker was *disabled* the moment data became `any`. The bug it exists to prevent happened anyway, at runtime — because the `any` punched a hole right at the data source. The fix is to validate at the boundary (next).

### Closing the `any` hole: validate at the boundary

```typescript
function parseUser(json: string): User {
    const raw: unknown = JSON.parse(json);   // `unknown`, not `any` — forces a check before use
    if (
        typeof raw === "object" && raw !== null &&
        "id" in raw && typeof (raw as any).id === "number" &&
        "name" in raw && typeof (raw as any).name === "string"
    ) {
        return raw as User;   // narrowed and verified — the cast is now justified
    }
    throw new Error("invalid user payload");
}
```

`unknown` is `any`'s safe sibling: it's compatible *from* everything but assignable *to* nothing without a check. Using `unknown` at boundaries and narrowing before use is how you keep the sieve hole-free. (Libraries like Zod or `io-ts` automate this; the principle is the same.)

### Structural vs nominal, side by side

```go
// Go — structural. No "implements" needed.
type Stringer interface{ String() string }
type Point struct{ X, Y int }
func (p Point) String() string { return fmt.Sprintf("(%d,%d)", p.X, p.Y) }
var s Stringer = Point{1, 2}   // works: Point structurally satisfies Stringer
```

```java
// Java — nominal. The declaration is mandatory.
interface Stringer { String stringify(); }
class Point /* must say */ implements Stringer {
    public String stringify() { return "(" + x + "," + y + ")"; }
}
// A Point class with a matching method but no `implements Stringer` is NOT a Stringer.
```

### Duck typing in Python = structural typing's dynamic cousin

```python
from typing import Protocol

# The dynamic version: duck typing, checked at runtime when .area() is called
def describe(shape):
    print(f"area is {shape.area()}")   # works for anything with .area()

# The static version: a Protocol (structural), checked by mypy at compile time
class HasArea(Protocol):
    def area(self) -> float: ...

def describe_typed(shape: HasArea) -> None:
    print(f"area is {shape.area()}")   # mypy verifies the argument has .area() BEFORE running
```

Python's `Protocol` (PEP 544) is literally "structural typing for Python" — the compile-time formalization of the duck typing Python always had at runtime. Same intuition, moved earlier in time.

---

## Coding Patterns

### Pattern 1: `unknown` at boundaries, never `any`

Treat data entering your program (JSON, env vars, network) as `unknown`, validate it into a real type, and let everything inside stay fully typed. `any` is for genuine "I give up"; `unknown` is for "I'll check first."

### Pattern 2: Quarantine the dynamic part

If a region must be dynamic (reflection, plugins, metaprogramming), wrap it behind a *typed* facade. The rest of the codebase sees a clean typed interface; the unsafe `any` lives in one small, well-tested module.

### Pattern 3: Strict mode on, ratchet only forward

Enable the strictest checker settings (`strict: true` in `tsconfig`, `--strict` in mypy) and add a CI check that the count of `any`/`type: ignore` never *increases*. Coverage ratchets up, never down.

### Pattern 4: Protocols/interfaces for structural seams

Use structural interfaces (Go `interface`, Python `Protocol`, TS `interface`) at module seams so callers can supply any conforming type — this gives you duck typing's flexibility without giving up the compiler.

### Pattern 5: Make illegal states unrepresentable with nominal wrappers

Wrap primitives in distinct nominal types (`type UserId = ...` branded types in TS, newtypes in Rust/Haskell) so the compiler stops you from passing an `OrderId` where a `UserId` belongs — a class of bug structural typing alone won't catch.

---

## Best Practices

- **Count your `any`s.** They're the real measure of how much your type system protects you. Track and reduce them. A "fully typed" codebase riddled with `any` is theater.
- **Prefer `unknown` to `any` at every boundary.** It forces a check instead of silently disabling one.
- **Turn on strict mode from day one** on new projects; ratchet it on for old ones. Lenient defaults let `any` breed.
- **Don't fight inference.** Let the checker infer locals; annotate the *interfaces* (function signatures, public types). Over-annotating internals is noise; under-annotating boundaries is danger.
- **Use structural typing for flexibility, nominal for safety-critical distinctions.** Know which your language gives you by default and reach for the other when needed.
- **Remember the runtime ignores your hints (erased systems).** If you need runtime enforcement (validating external input), add it explicitly — pydantic, Zod, `typeguard` — don't assume the annotation guards anything at run time.
- **Migrate hot spots first.** When typing a dynamic codebase, type the modules with the most bugs/most churn first — that's where static checking pays back fastest.

---

## Edge Cases & Pitfalls

- **`any` is viral.** Anything derived from an `any` is also `any`. One `any` at a data source disables checking for everything downstream — far beyond the line it appears on.
- **`any` vs `unknown` confusion.** They look similar but `any` *disables* checking while `unknown` *demands* a check before use. Reaching for `any` to silence an error is almost always the wrong move.
- **Erased types don't validate input.** A Python signature `def f(x: int)` does *not* stop someone passing a string at runtime — the hint is gone by then. External input still needs explicit validation.
- **Structural typing's accidental matches.** Two unrelated types with the same shape are interchangeable in a structural system — sometimes you *don't* want that (a `Meters` and a `Feet` both `{value: number}`). Use nominal/branded types to forbid it.
- **Monkeypatching defeats the checker.** Adding methods at runtime (Ruby, Python) is invisible to a static checker, which reasons about the code as written, not as mutated. Gradual checkers either model a fixed set or give up (`any`).
- **The gradual guarantee is about *correct* annotations.** It says adding *right* types doesn't change behavior. A *wrong* annotation plus an `any` boundary absolutely can let a bug through; the guarantee isn't "annotations make bugs impossible."
- **`type: ignore` / `@ts-ignore` are `any` in disguise.** They silence one error and create an unchecked island. Each one is a debt to track.
- **Inferred ≠ dynamic.** `x := 5` in Go and `const x = 5` in TS have no annotation but are fully static. Don't mistake terse inferred code for dynamic typing.

---

## Apply it

1. Find a real component where **Static vs Dynamic Typing** affects an interface or dependency.
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

- Which boundary is most affected by Static vs Dynamic Typing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
