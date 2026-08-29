# Nominal vs Structural Typing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Nominal vs Structural Typing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Compatibility Is Subtyping

Whenever you assign, pass, or return a value, the checker asks `S <: T`. Both type systems answer this question — they just compute it differently.

**Nominal procedure (sketch):**
```
S <: T  iff  T == S, or T is a declared super-interface/super-class of S
             (transitively, following extends/implements edges)
```
It's reachability in a directed graph of *programmer-declared* edges. If you didn't write the edge, it doesn't exist.

**Structural procedure (sketch):**
```
S <: T  iff  for every member m required by T,
                 S has a member m' with the same name and  type(m') <: type(m)
```
It's a recursive, member-by-member comparison. No declarations consulted.

### 2. Width and Depth Subtyping (Structural)

Structural subtyping has two axes:

**Width** — having *more* makes you a subtype. An object with extra fields fits a type that asks for fewer:

```typescript
type P = { x: number };
const big = { x: 1, y: 2 };  // {x, y}
const p: P = big;            // ✅ {x,y} <: {x} — width subtyping
```

**Depth** — having *more specific* field types makes you a subtype:

```typescript
type HasAnimal = { pet: { legs: number } };
type HasDog    = { pet: { legs: number; bark(): void } };
const d: HasDog = { pet: { legs: 4, bark() {} } };
const h: HasAnimal = d;      // ✅ HasDog <: HasAnimal via depth (pet is more specific)
```

Together, width + depth define structural subtyping for records. Nominal systems have **neither** by default — `{x, y}` is not a subtype of `{x}` unless declared.

### 3. Go's Method Sets: Structural, But With Receiver Rules

Go's interface satisfaction is structural — but *which* methods count depends on value vs pointer receivers, a rule that bites everyone:

```go
type Speaker interface{ Speak() string }

type Dog struct{}
func (d *Dog) Speak() string { return "Woof" }  // POINTER receiver

func main() {
    var s Speaker
    s = &Dog{}   // ✅ *Dog has Speak() in its method set
    s = Dog{}    // ❌ Dog (value) does NOT — pointer-receiver method excluded
}
```

Rule: a method with a **value receiver** is in the method set of both `T` and `*T`; a method with a **pointer receiver** is only in the method set of `*T`. Structural matching then compares the *method set* of the value's type against the interface. So "does this type satisfy the interface?" is really "does this type's method set structurally cover the interface?"

### 4. Named Types: Go Is Nominal Too

Go interfaces are structural, but Go *named types* are nominal:

```go
type Celsius float64
type Fahrenheit float64

var c Celsius = 100
var f Fahrenheit = c   // ❌ cannot use Celsius as Fahrenheit (distinct named types)
var f2 Fahrenheit = Fahrenheit(c)  // ✅ explicit conversion required
```

Even though both are `float64` underneath, `Celsius` and `Fahrenheit` are *distinct* and not interchangeable without explicit conversion. This is the **newtype pattern**, built into Go's named types — a nominal feature inside a language famous for structural interfaces. Most languages mix the two models like this.

### 5. The Newtype Pattern as a Deliberate Tool

The newtype pattern: wrap a representation in a *distinct named type* so the compiler treats semantically different values as different, even though they share a layout.

```rust
struct UserId(u64);
struct ProductId(u64);

fn fetch_user(id: UserId) { /* ... */ }

let p = ProductId(42);
// fetch_user(p);  // ❌ ProductId is not UserId — bug caught at compile time
```

This is *opting into stronger nominal distinctions* than the raw representation gives you. It costs a wrapper and sometimes some unwrapping, and buys you immunity to an entire class of "passed the right-shaped value into the wrong slot" bugs. In Haskell it's `newtype UserId = UserId Int`; in Rust it's a tuple struct; in TypeScript it's a branded type (next section).

### 6. Branded Types: Faking Nominal in a Structural Language

TypeScript is structural, so `type UserId = string` and `type ProductId = string` are *the same type* — useless for separation. The **branded type** trick adds a phantom marker:

```typescript
type Brand<T, B extends string> = T & { readonly __brand: B };
type UserId    = Brand<string, "UserId">;
type ProductId = Brand<string, "ProductId">;

function asUserId(s: string): UserId { return s as UserId; }

function getUser(id: UserId) { /* ... */ }

const pid = "p_99" as ProductId;
// getUser(pid);  // ❌ ProductId lacks the "UserId" brand — now incompatible!
```

The `__brand` property never exists at runtime — it's a compile-time-only marker that makes the two structurally-identical strings *structurally different* (because the brand fields differ). This recovers nominal behavior inside a structural system. The `as` cast is the controlled "minting" point where a raw string becomes a `UserId`.

---

## Code Examples

### Nominal subtyping is declaration-driven (Java)

```java
interface A { void f(); }
interface B { void f(); }   // identical shape, different name

class Impl implements A {
    public void f() {}
}

A a = new Impl();   // ✅
// B b = new Impl(); // ❌ Impl doesn't declare implements B, despite identical shape
// A x = (A) someB;  // even a cast requires a declared relationship to be sound
```

### Structural subtyping is shape-driven (TypeScript)

```typescript
interface A { f(): void; }
interface B { f(): void; }   // identical shape, different name

const impl = { f() {} };
const a: A = impl;   // ✅
const b: B = impl;   // ✅ — both fit because the SHAPE matches; names ignored
const a2: A = ({} as B);  // ✅ B is structurally an A too — fully interchangeable
```

### Go method sets and interface satisfaction

```go
type Stringer interface{ String() string }

type T struct{ v int }
func (t T) String() string { return strconv.Itoa(t.v) }  // value receiver

func main() {
    var s Stringer
    s = T{1}    // ✅ value receiver => T and *T both satisfy
    s = &T{2}   // ✅
    // If String() used *T receiver, then s = T{1} would FAIL.
}
```

### Newtype prevents argument-swap bugs (Rust)

```rust
struct Meters(f64);
struct Feet(f64);

fn add_distance(a: Meters, b: Meters) -> Meters { Meters(a.0 + b.0) }

fn main() {
    let m = Meters(3.0);
    let f = Feet(10.0);
    // add_distance(m, f);  // ❌ Feet is not Meters — mismatched units caught
    let total = add_distance(Meters(3.0), Meters(2.0));  // ✅
    println!("{}", total.0);
}
```

### Branded types in TypeScript (nominal emulation)

```typescript
declare const __brand: unique symbol;
type Brand<T, B> = T & { [__brand]: B };

type AccountId = Brand<string, "AccountId">;
type SessionId = Brand<string, "SessionId">;

const mkAccount = (s: string) => s as AccountId;

function loadAccount(id: AccountId) {}

const sess = "s_1" as SessionId;
// loadAccount(sess);   // ❌ SessionId brand !== AccountId brand
loadAccount(mkAccount("a_1"));  // ✅
```

### Retroactive conformance: structural's superpower (Go)

```go
// This type was written long ago, before the Closer interface existed.
type LegacyHandle struct{}
func (l LegacyHandle) Close() error { return nil }

// Define the interface NOW:
type Closer interface{ Close() error }

func use(c Closer) {}
// LegacyHandle satisfies Closer with NO modification to LegacyHandle:
var _ = use(LegacyHandle{})   // ✅ retroactive conformance for free
```

In Java, `LegacyHandle` could not satisfy a `Closer` interface defined later without editing it (or wrapping it) to add `implements Closer`.

---

## Coding Patterns

**Pattern: "smart constructor."** Only mint a branded/newtype value through a function that validates, so a `UserId` always came from a real validation.

```typescript
function parseEmail(s: string): Email | null {
    return s.includes("@") ? (s as Email) : null;  // Email = Brand<string,"Email">
}
```

**Pattern: compile-time conformance assertion (Go).** Force the compiler to verify a type satisfies an interface, near the definition:

```go
var _ io.Writer = (*MyBuffer)(nil)  // fails to compile if MyBuffer isn't a Writer
```

**Pattern: phantom type parameters.** Tag a generic value with a marker that has no runtime cost (`State<"open">` vs `State<"closed">`).

**Pattern: adapter for nominal retrofitting.** In Java, wrap a foreign class in an adapter that `implements YourInterface` to bolt on conformance the original lacks.

---

## Best Practices

1. **Reach for newtypes/branded types whenever two values share a representation but not a meaning.** IDs, units, validated strings.
2. **In Go, write the `var _ Iface = (*T)(nil)` assertion** so accidental loss of conformance is a compile error, not a runtime surprise.
3. **Remember the receiver rule.** Pointer-receiver methods are only in `*T`'s method set; satisfy interfaces with the right value/pointer.
4. **Distinguish aliases from new types.** If you need separation, make sure your syntax creates a *new* type, not a nickname.
5. **Mint branded values at a single chokepoint** (a parser/validator), never with scattered `as` casts.
6. **In structural systems, treat renaming a public member as a breaking change** — it can silently drop conformance for consumers.
7. **Prefer small interfaces in structural languages**; they maximize flexibility and minimize accidental conformance surface.

---

## Edge Cases & Pitfalls

**1. Excess-property check fires only on literals.** Assigning a *variable* with extra fields is allowed (width subtyping); passing an *object literal* with extra fields is rejected. Same data, different rule, because TS heuristically assumes a literal with extra fields is a typo.

**2. Type aliases give false confidence.** `type UserId = string` looks like a distinct type but is just `string`. It documents intent but provides *zero* safety — a plain string passes everywhere. Only branding/newtype actually separates them.

**3. Go pointer/value receiver mismatch.** You define methods on `*T`, store a `T` value in an interface variable, and get "does not implement." The fix is to use `&t` or define value receivers — and the error message often doesn't make the receiver issue obvious.

**4. Structural matching recurses — and can be surprisingly permissive.** `{ id: number }` is a subtype of `{}` (the empty type), so a function expecting `{}` accepts almost anything. Empty/loose shapes silently accept too much.

**5. Optional/extra members and function-parameter bivariance.** TypeScript historically allowed method parameters to be compared bivariantly, letting unsound assignments through. (Covered formally in `senior.md`; just know structural function compatibility has subtle, sometimes-unsound corners.)

**6. Newtype ergonomics tax.** Wrapping a primitive means you can't use its operators directly (`a + b` on two `Meters` tuples needs `Meters(a.0 + b.0)`). Teams sometimes skip newtypes to avoid this friction — and then hit the swap bugs they were meant to prevent.

**7. Branded types are erased.** A brand is compile-time only; at runtime a `UserId` *is* a string. Don't expect runtime checks from branding — validate at the boundary.

---

## Apply it

1. Find a real component where **Nominal vs Structural Typing** affects an interface or dependency.
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

- Which boundary is most affected by Nominal vs Structural Typing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
