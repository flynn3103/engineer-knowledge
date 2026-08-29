# What Is a Type — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **What Is a Type** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Type vs Representation: Same Logic, Different Bytes

A type has a *logical* identity (what it means, what operations it supports) and a *physical* representation (how the compiler stores it). These usually move together but are deliberately separable, and that separation is an engineering tool:

- **A `bool` is logically `{true, false}`** but is typically *represented* as one byte (sometimes a full word for alignment). The representation has 254 unused bit-patterns.
- **A newtype `UserId(u64)`** is logically distinct from a `ProductId(u64)` but has the *identical* representation — eight bytes — with **zero runtime cost**. The distinction exists only at compile time; at run time both are just a `u64`. This is the professional's favorite trick: buy type safety, pay nothing at run time.
- **Niche-filling** exploits unused bit-patterns: Rust's `Option<&T>` is the same size as `&T` because the null pointer (an invalid `&T`) is reused to mean `None`. The *type* `Option<&T>` has more values than `&T`, but its *representation* fits in the same bytes by stealing an invalid pattern. Logical cardinality went up; physical size didn't.

The discipline: **decouple the type you reason with from the bytes it costs.** You can refine types aggressively for safety (`Meters`, `Sanitized`, `NonZeroU32`) while paying little or nothing in representation, provided the compiler can erase the distinction.

### 2. A Type Is the Compiler's Layout Contract

For compiled languages, the type *is* the instruction to the code generator: how many bytes, what alignment, how to pass in registers vs on the stack, how to read each field. Practical consequences staff engineers manage:

- **Struct field order affects size** because of alignment padding. `struct { a: u8; b: u64; c: u8 }` may take 24 bytes (padding around the `u64`), while reordering to `{ b: u64; a: u8; c: u8 }` takes 16. The *type's logical content* is identical; the *layout* — and the cache behavior — differs.
- **Sum types cost a discriminant** plus the largest variant. An enum of `{ A(u8), B([u8; 1024]) }` costs ~1025 bytes per value *even when it's the `A` case*, because the representation must fit the worst case. This drives decisions like boxing the large variant.
- **Generics force a representation choice**: *monomorphization* (C++ templates, Rust generics — one specialized copy per type, fast but code-bloating) vs *boxing/type-erasure* (Java generics, Go interfaces — one copy, uniform pointer representation, an indirection per use). The *same* generic type yields different machine code under each strategy.

When you choose a type, you're choosing a memory and performance profile, not just a logical category.

### 3. Type Safety vs Memory Safety — Two Different Dials

This distinction is the source of more confused incident postmortems than almost anything else. They are *related but independent* guarantees:

- **Type safety** = operations are only applied to operands of compatible type. Violation: treating an `int` as a function pointer and "calling" it.
- **Memory safety** = no out-of-bounds access, use-after-free, double-free, or reading uninitialized memory. Violation: `arr[10]` on a length-5 array, or dereferencing a freed pointer.

The four quadrants are all real:

| | Memory-safe | Memory-unsafe |
|--|-------------|---------------|
| **Type-safe** | Java, Go, Python, Rust (safe) | (rare; type-safe but can corrupt — some FFI boundaries) |
| **Type-unsafe** | (rare in practice) | C, C++, assembly, Rust `unsafe` |

Key points for production:

- **Losing type safety usually opens the door to losing memory safety.** A type confusion (treating bytes as a pointer) is the classic exploit primitive — type-confusion CVEs in browsers and VMs are memory-corruption bugs that *start* as type violations.
- **You can be memory-safe but type-confused.** A dynamic language won't corrupt memory, but a value-of-wrong-type bug can still produce a logically catastrophic result (charging the wrong account).
- **Rust's design is the clearest articulation**: safe Rust is *both* type-safe and memory-safe with no GC; `unsafe` is an explicit, auditable region where *you* uphold the invariants the compiler can't. The boundary between the two is a deliberate engineering artifact.

Treat them as two dials you set per component, and never let a postmortem blur "we had a type error" with "we corrupted memory" — the fixes differ.

### 4. The Type of a Type: Kinds

Values have types; types have **kinds**. A kind is "the type of a type," and ignoring kinds causes a specific, recurring confusion: trying to use a type constructor where a concrete type is needed.

- `int`, `bool`, `String`, `User` have kind `*` — they classify *values* directly; they are "fully applied" concrete types.
- `List`, `Option`, `Vec`, `Array` have kind `* → *` — they are **type constructors**: give them a type and they produce a type. `List` alone is not a type; `List<Int>` is. `List : * → *`, `List<Int> : *`.
- `Map`, `Either`, `Result` have kind `* → * → *` — two type arguments to produce a concrete type.
- **Higher-kinded types** abstract over constructors: `Functor f` quantifies over `f : * → *`. This is what lets you write "map over *any* container" once. Languages differ sharply: Haskell and Scala have HKTs; Java, Go, Rust (mostly), and TypeScript don't, which is why "a generic `Monad` interface" is awkward or impossible in them.

The practical payoff: when a compiler says "expected a type, found a type constructor" or "`List` is not applied to enough arguments," you're hitting a *kind* error — a type-of-types mismatch. And when you wish you could write one abstraction over "any container `F`," you're wishing for higher kinds your language may not have.

### 5. Phantom Types: Compile-Time State With No Runtime Cost

A **phantom type** is a type parameter that appears in the *type* but not in the *representation* — pure compile-time bookkeeping. It's the professional's tool for encoding state machines, units, and permissions into types at zero runtime cost:

- `Temperature<Celsius>` vs `Temperature<Fahrenheit>` — both are a single `f64` at run time, but the compiler refuses to add them. The Mars Climate Orbiter was lost to a unit mismatch; phantom types make that a compile error.
- `Connection<Open>` vs `Connection<Closed>` — `send()` only exists on `Connection<Open>`; you *cannot* call it on a closed connection, and the state is tracked entirely in the type with no extra byte stored.
- `Request<Unvalidated>` vs `Request<Validated>` — a handler that requires `Request<Validated>` can never receive unvalidated input, because the only way to get a `Validated` is to pass through the validator.

This is "make illegal states unrepresentable" realized with phantom types: the illegal transition isn't checked at run time — it *doesn't typecheck*.

### 6. Types as the Cheapest Tests

The unifying professional thesis. Compare the cost and coverage of three ways to enforce a property "this list is never empty":

| Mechanism | When it checks | Coverage | Cost |
|-----------|----------------|----------|------|
| Runtime assertion | every execution, every call site | only paths actually run | runtime cost + crashes in prod |
| Unit test | once, in CI | only the examples you wrote | engineer time per case |
| **Type** (`NonEmptyList`) | once, at compile time | **every value, every call site, all inputs** | declare the type once |

A type is a test that:

- is written **once** (declare `NonEmptyList`),
- runs at **compile time** (no runtime cost, no production crash),
- covers **every** input and **every** call site (not just examples), and
- **can't be skipped** (you can't merge code that violates it).

This is why "make illegal states unrepresentable" is an incident-reduction strategy, not an aesthetic preference. Every invariant you lift into a type is a bug class you delete *permanently*, for the whole team, with no ongoing maintenance — strictly dominating the equivalent runtime check or test suite for that property. The art is knowing *which* invariants are worth the modeling effort (the high-frequency, high-cost ones) versus which are cheaper to assert at run time.

---

## Code Examples

### Newtype: maximal type distinction, zero runtime cost (Rust)

```rust
// Logically distinct, physically identical (both are u64), zero overhead.
#[derive(Clone, Copy)]
struct UserId(u64);
#[derive(Clone, Copy)]
struct OrderId(u64);

fn cancel(order: OrderId) { /* ... */ }

fn main() {
    let u = UserId(7);
    let o = OrderId(7);
    cancel(o);          // ok
    // cancel(u);       // COMPILE ERROR: expected OrderId, found UserId
    // ...even though both are 8 bytes holding 7. The distinction is compile-time only.
    assert_eq!(std::mem::size_of::<UserId>(), 8); // no wrapper cost
}
```

### Type vs representation: layout depends on field order

```rust
use std::mem::size_of;

struct Bad { a: u8, b: u64, c: u8 }   // padding around the u64
struct Good { b: u64, a: u8, c: u8 }  // packed tighter

fn main() {
    println!("{}", size_of::<Bad>());   // 24 on most targets (padding)
    println!("{}", size_of::<Good>());  // 16 — same logical content, smaller layout
}
```

### Niche-filling: `Option<&T>` is free

```rust
use std::mem::size_of;
fn main() {
    // Option adds a logical "None" case, but the null pointer (invalid for &T)
    // is reused, so the representation does not grow.
    println!("{}", size_of::<&i32>());          // 8
    println!("{}", size_of::<Option<&i32>>());  // 8 — niche-filled, not 16
}
```

### Type safety without memory safety: type punning in C

```c
#include <stdio.h>
int main() {
    float f = 3.1415927f;
    // Reinterpret the bytes under a different type — legal in C via union/pointer tricks,
    // a TYPE violation that is also a memory-level reinterpretation.
    unsigned int bits = *(unsigned int*)&f;   // type punning
    printf("%#010x\n", bits);                 // 0x40490fdb
    // One step further is genuinely unsafe:
    // int *p = (int*)0xdeadbeef; *p = 1;     // type-"valid" cast, memory-UNSAFE write
    return 0;
}
```

C lets you reinterpret bytes (lose type discipline) and dereference arbitrary addresses (lose memory safety) — two separate failures the language doesn't stop.

### Kinds: a type constructor is not a type (Haskell)

```haskell
-- Int      :: *          (a concrete type — classifies values)
-- Maybe    :: * -> *     (a type CONSTRUCTOR — needs an argument)
-- Maybe Int:: *          (now concrete)
-- Either   :: * -> * -> *

-- Higher-kinded abstraction: works for ANY container f :: * -> *
class MyFunctor f where
  fmap' :: (a -> b) -> f a -> f b   -- f is quantified at kind * -> *

instance MyFunctor Maybe where
  fmap' _ Nothing  = Nothing
  fmap' g (Just x) = Just (g x)
```

`f` ranges over *type constructors*, one rung up the kind ladder — exactly the abstraction Java/Go/TS can't express.

### Phantom types: compile-time state machine, zero runtime state (Rust)

```rust
use std::marker::PhantomData;

struct Open;
struct Closed;

struct Connection<State> { fd: i32, _state: PhantomData<State> }

impl Connection<Closed> {
    fn open(fd: i32) -> Connection<Open> {
        Connection { fd, _state: PhantomData }
    }
}
impl Connection<Open> {
    fn send(&self, _data: &[u8]) { /* ... */ }
    fn close(self) -> Connection<Closed> {
        Connection { fd: self.fd, _state: PhantomData }
    }
}

fn main() {
    let c = Connection::<Closed>::open(3);
    c.send(b"hi");          // ok — c is Connection<Open>
    let c = c.close();
    // c.send(b"late");     // COMPILE ERROR: send() doesn't exist on Connection<Closed>
}
// `State` is never stored — PhantomData is zero-sized. The state machine is purely in types.
```

### Types as the cheapest test: validation as construction (TypeScript)

```typescript
// A branded type: a string that PROVES it passed validation.
type Email = string & { readonly __brand: "Email" };

function parseEmail(raw: string): Email | null {
  return /^[^@]+@[^@]+$/.test(raw) ? (raw as Email) : null;
}

function sendWelcome(to: Email) { /* never re-validates; the type guarantees it */ }

const e = parseEmail(userInput);
if (e) sendWelcome(e);       // ok
// sendWelcome(userInput);   // COMPILE ERROR: string is not Email
// One declaration replaces a re-validation at every call site, for every input.
```

---

## Coding Patterns

### Pattern 1: Parse, don't validate

Convert unstructured input into a *type that proves validity* at the boundary, once. Downstream code takes the validated type and never re-checks. `parseEmail: string -> Email | null` beats `isValidEmail: string -> bool` because the result *carries the evidence*. (This is the engineering name for construction-as-proof.)

### Pattern 2: Newtype every ID and unit

Never pass two semantically different `u64`s or `string`s with the same raw type. Wrap each (`UserId`, `OrderId`, `Cents`, `Meters`). The compiler then catches every transposition — a bug class that's otherwise invisible and routinely ships.

### Pattern 3: Typestate for protocols

Model each state of a stateful object as a distinct type (`Builder<Incomplete>` → `Builder<Ready>`; `File<Open>` → `File<Closed>`). Make state-illegal operations *not exist* on the wrong-state type. The state machine becomes uncheckable-at-runtime because it's enforced at compile time.

### Pattern 4: Decouple logical type from representation explicitly

When performance demands a tight layout, keep the *logical* type clean and confine the representation trick (packing, niche, union) behind a small, well-documented module with the invariant stated. Don't let layout leak into business logic.

### Pattern 5: Box the large variant

When a sum type has one huge variant, the whole enum pays for it on every value. Box the large case (`enum E { Small(u8), Big(Box<[u8;1024]>) }`) so the common path stays small. A type-and-representation co-design.

---

## Best Practices

- **State logical and physical identity separately in design docs.** "Logically a validated, non-empty UTF-8 path; physically a `String` — no overhead." This pre-empts the "won't that be slow?" objection.
- **Keep type safety and memory safety as separate review checklist items.** Don't let a postmortem conflate them; the root causes and remediations differ.
- **Scope and audit every `unsafe`/FFI/cast.** That's where both dials can drop. Comment the invariant *you* are now responsible for that the compiler no longer checks.
- **Reach for phantom/typestate when a runtime state check recurs.** If you keep asserting "connection must be open," lift it into the type.
- **Don't over-model.** Not every invariant deserves a type. Reserve the heavy machinery (phantom types, typestate, refined types) for high-frequency, high-cost invariants. A runtime check is fine for the long tail.
- **Mind generic instantiation strategy at scale.** Monomorphization bloat can dominate binary size and compile time; erasure costs indirection. Choose per hot path, not by reflex.
- **Watch struct layout in hot or large data.** Field ordering, padding, and variant sizes are real performance and memory levers — measure with `size_of`/`offsetof` and a profiler.
- **In every incident review, ask the type question.** "Could this state have been unrepresentable?" Turn recurring incident classes into compile errors; that's the highest-ROI use of types in production.

---

## Edge Cases & Pitfalls

- **Newtypes can leak their inner type.** If you expose the wrapped value freely (auto-deref, public field), you lose the protection — code starts mixing `UserId` and `OrderId` via their raw `u64`. Keep the wrapper opaque.
- **Layout is not guaranteed unless you ask.** Default struct layout can be reordered by the compiler (Rust) or fixed by declaration (C). Don't assume field order maps to byte order unless you specify `repr(C)`/`#pragma pack`/equivalent — critical at FFI/serialization boundaries.
- **Phantom-typed state doesn't survive serialization.** Write `Connection<Open>` to disk and read it back, and the phantom state is gone — it was never represented. Re-establish invariants on deserialization.
- **Erasure removes runtime type info you might want.** Java generics, TypeScript types: you can't reflect on them at run time. Designs that need runtime type identity must carry a discriminant explicitly.
- **Type punning is undefined behavior in many languages.** C/C++ strict-aliasing rules mean `*(int*)&float_var` may be UB; the "it works" can vanish under optimization. Use the language's sanctioned mechanism (`memcpy`, `std::bit_cast`, `transmute` with care).
- **Higher-kinded wishes hit hard walls.** In Java/Go/Rust/TS, "an interface for any monad" is awkward or impossible. Don't design an API assuming HKTs your language lacks; you'll end up with macros, codegen, or duplication.
- **A type proves nothing about data you didn't construct through it.** Deserialization, FFI, `unsafe`, and casts can fabricate a "valid" value that never passed the constructor. The guarantee is only as strong as the constructor monopoly.

---

## Tricky Points

- **Zero-cost abstraction is a representation claim, not a logical one.** "Zero-cost" means the *physical* representation and dispatch are as good as hand-written; the *logical* distinctions (newtype, phantom) add safety the compiler erases. When someone says "newtypes are free," they mean physically free, infinitely valuable logically.
- **Type confusion is the bridge from type-unsafety to memory-unsafety.** Most VM/browser RCE exploits begin as a type confusion (the engine believes an object is type `A`, it's type `B`) that yields a memory-corruption primitive. This is precisely why type safety is a *security* property, not just a correctness one.
- **Kinds are where Java/Go/Rust hit their ceiling.** The lack of higher-kinded types is *the* reason these languages can't express a generic `Functor`/`Monad`/`Traversable` cleanly, and why their effect/async/collection abstractions look the way they do. Recognizing a "missing HKT" explains a lot of library design.
- **A sum type's runtime size is dominated by its worst variant.** This couples logical design (how many/what variants) to representation cost in a way newcomers miss; one fat variant taxes every value. Boxing decouples them.
- **"Make illegal states unrepresentable" has a representation cost ceiling.** Encoding an invariant in a type is free when it erases (phantom, newtype) and *not* free when it changes representation (adding a discriminant, an extra field). The strategy is cheapest exactly when the distinction is compile-time only.

---

## Apply it

1. Define the user or business outcome that **What Is a Type** should improve.
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

- Which measurable outcome justifies investing in What Is a Type?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
