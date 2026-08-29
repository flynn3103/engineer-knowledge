# Bounded Polymorphism — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Bounded Polymorphism** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The cost model: monomorphization vs dynamic dispatch

Every bounded generic must, at some point, be *given* its operations. Two strategies, with opposite cost profiles:

**Monomorphization (static).** The compiler stamps out a fresh, specialized copy of the function for each concrete type it's used with, inlining the bound's operations. Used by Rust (default), C++ templates, and (partially) specialized JITs.

- *Pros:* no runtime indirection, full inlining, the fastest possible dispatch, often zero abstraction cost.
- *Cons:* **code bloat** (N types → N copies), longer compile times, larger binaries, worse instruction-cache behavior if the copies are hot and numerous, and slower incremental builds.

**Dynamic dispatch (witness table).** One copy of the function; the bound's operations reached through a runtime pointer to a vtable/dictionary (`&dyn Trait`, a Java interface reference, a Go interface value, a Swift existential).

- *Pros:* one copy regardless of type count, smaller binaries, faster compiles, the ability to store heterogeneous types behind one bound (`Vec<Box<dyn Draw>>`).
- *Cons:* an indirect call per operation (defeats inlining, a branch-predictor and i-cache cost), often a heap allocation/boxing, and the trait must be **object-safe**.

The professional reflex: **monomorphize hot, small, few-typed generics; dynamically dispatch cold, large, or heterogeneously-typed ones.** A 3-line comparator used in a tight sort across 5 types: monomorphize. A 2,000-line request handler parameterized over a `Plugin` trait with 50 implementations: probably `dyn`, to keep the binary and compile sane. Many codebases mix both: a monomorphized fast path, a `dyn` slow/heterogeneous path.

### 2. Object safety: the gate on `dyn`

You can only choose dynamic dispatch if the trait is **object-safe**. The core restrictions (Rust's formulation, but the principle is universal): the trait must not have methods that are *generic* over additional type parameters, must not return `Self` by value, and must not have non-`self` `Self`-typed parameters in dispatchable methods — because a vtable is a fixed table of monomorphic function pointers, and none of those shapes can be put in such a table. `Clone` (returns `Self`) and `Ord` (`cmp(&self, &Self)`) are **not** object-safe; `Display`, `Iterator` (mostly), and `Draw { fn draw(&self); }` are. A staff engineer designing a trait that *must* support `dyn` (plugin systems, heterogeneous collections) keeps it object-safe deliberately — and knows that a single `Self`-returning method forecloses that option permanently.

### 3. SFINAE: bounds without declarations (the bad old C++ way)

Before C++20, templates had **no way to declare a bound**. `template<class T> T max(T a, T b){ return a < b ? b : a; }` simply *assumed* `T` had `<`. If you instantiated it with a type lacking `<`, the error surfaced *deep inside the instantiation* — not at the call site — and dumped every candidate, every nested template, every overload considered. A missing `operator<` could produce hundreds of lines mentioning types you've never heard of.

To *emulate* bounds, library authors used **SFINAE** ("Substitution Failure Is Not An Error"): write overloads whose signatures are only valid when the type has the required operations, relying on the rule that an *ill-formed substitution* removes a candidate rather than erroring. The canonical tool was `std::enable_if`:

```cpp
template <class T,
          typename = std::enable_if_t<std::is_integral_v<T>>>   // bound, smuggled in
T half(T x) { return x / 2; }
```

This *worked* but was write-only: the constraint was buried in template metaprogramming, the diagnostics when it *failed* were still catastrophic, and expressing "has a `.size()` method" required detection idioms (`void_t`, expression SFINAE) that read like cryptography. SFINAE is bounded polymorphism with the bound *implicit and undiagnosable* — the worst of both worlds.

### 4. C++20 concepts: declared bounds, sane errors

**Concepts** finally give C++ *declared, named, checkable* bounds — exactly what `T: Ord` always was elsewhere:

```cpp
#include <concepts>

template <class T>
concept Sortable = std::totally_ordered<T> && requires(T a, T b) {
    { a < b } -> std::convertible_to<bool>;
};

template <Sortable T>                 // the bound, named and up front
T max_of(T a, T b) { return a < b ? b : a; }
```

What changes in practice:

- **Diagnostics collapse** from a wall of instantiation noise to *"constraint `Sortable<Widget>` not satisfied: `Widget` has no `operator<`"* — at the *call site*. This alone has measurably cut C++ debugging time.
- **Overload resolution improves** via **subsumption**: when several constrained overloads match, the compiler prefers the *more constrained* one, replacing fragile SFINAE-ordering tricks.
- **Contracts become readable**: a concept *documents* what a template needs, so the bound is part of the API, not buried in `enable_if`.

Concepts are *structural* (a type satisfies `Sortable` by *having* the operations, no declaration needed) — unlike Rust traits (nominal, you must `impl`). That keeps C++'s duck-typed template flavor while adding the missing declared-bound and diagnostic layer. The migration story for a large codebase: replace `enable_if` SFINAE with concepts incrementally; the payoff is error-message quality and overload clarity.

### 5. Designing bound hierarchies for an ecosystem

When your trait/typeclass is depended on by *other people's code*, design shifts from "does it compile" to "can it evolve and compose":

- **Granularity.** One fat trait (`trait Db { connect; query; migrate; backup; }`) forces every implementer to provide everything and every consumer to depend on everything. Many small traits (`Connect`, `Query`, `Migrate`) let consumers bound by exactly what they use and let implementers opt in. Prefer *fine-grained capability traits* with supertrait relationships over monoliths.
- **Default methods as evolution insurance.** Adding a method with a default to a published trait is (usually) non-breaking — existing impls inherit it. Adding a method *without* a default breaks every downstream impl. So: ship the minimal required surface, grow via defaulted methods.
- **Supertrait additions are breaking.** Tightening `trait Foo` to `trait Foo: Bar` requires every `Foo` implementer to now also implement `Bar` — a breaking change. Plan the hierarchy up front; loosening is fine, tightening is not.
- **Sealed traits to control the implementer set.** If you must be able to add methods freely later (or pattern-match exhaustively), *seal* the trait so only you can implement it. You trade extensibility for evolvability — a deliberate choice (e.g. `error` enums, protocol state machines).
- **Coherence shapes packaging.** Because of orphan rules, decide *who* ships the instance for popular foreign types. The idiomatic answer: the crate that *owns the trait* provides feature-gated impls for well-known external types, so downstream users don't need orphans.

### 6. API evolution under coherence: the breaking-change taxonomy

For a published trait `C`, classify each change:

| Change | Breaking? | Why |
|---|---|---|
| Add a method **with** a default | Usually no | Existing impls inherit it. |
| Add a method **without** a default | **Yes** | Every impl must now provide it. |
| Add a **supertrait** (`C: D`) | **Yes** | Every `C` impl must now also be a `D` impl. |
| Add a **new instance** for a type you own | No (but watch overlap) | New capability, no existing code changes — unless it overlaps. |
| Add a **blanket impl** (`impl C for all T: D`) | **Yes, often** | Can collide with existing/ downstream impls; coherence rejects overlaps. |
| Add an **associated type** | **Yes** | Impls must specify it (unless defaulted, where supported). |
| Loosen a bound on a function | No | Accepts strictly more types. |
| Tighten a bound on a function | **Yes** | Rejects previously-accepted callers. |

The staff takeaway: **a trait's required surface and its supertrait set are nearly frozen the moment you publish.** Everything growable should be defaulted; everything mandatory should be right the first time. Blanket impls are powerful and *especially* dangerous to add later because of overlap with downstream impls you can't see.

### 7. Choosing the mechanism: a decision framework

Given "this code needs capability `K` on type `T`," choose:

- **Static bounded generic (monomorphized trait/typeclass/concept)** — default for hot paths, small functions, few concrete types, and where you want maximum inlining. Best diagnostics in Rust/Haskell; in C++ use a *concept*, not SFINAE.
- **Dynamic dispatch (`dyn Trait` / interface / existential)** — for heterogeneous collections (`Vec<Box<dyn Draw>>`), plugin boundaries, large generic bodies you don't want duplicated, and ABI-stable boundaries. Requires object safety.
- **Subtype bound (Java/C#/Swift interface/protocol)** — when you're in an OO ecosystem, need runtime polymorphism by default, and don't need to retrofit foreign types.
- **`impl Trait` / `some`/`any` (existential return/param)** — to hide a concrete type behind a bound at an API boundary without committing callers to monomorphization choices.
- **Explicit operation argument (comparator/closure)** — when you need *per-call* behavior or multiple behaviors for one type, where coherence would otherwise force a newtype.

The mechanisms aren't mutually exclusive: large systems route the *common, hot* case through static bounds and the *heterogeneous, cold, or boundary* case through dynamic dispatch, sometimes behind the same trait.

---

## Code Examples

### Static vs dynamic, same trait (Rust)

```rust
trait Draw { fn draw(&self) -> String; }   // object-safe: no Self return, no generics

// STATIC: monomorphized — one copy per T, fully inlinable, no indirection.
fn render_static<T: Draw>(item: &T) -> String { item.draw() }

// DYNAMIC: one copy, vtable hop — enables heterogeneous storage.
fn render_dyn(item: &dyn Draw) -> String { item.draw() }

fn render_all(items: &[Box<dyn Draw>]) -> Vec<String> {   // heterogeneous: needs dyn
    items.iter().map(|i| i.draw()).collect()
}
```

`render_all` *cannot* be written with a single static `T` — the elements are different types. Dynamic dispatch is not a fallback here; it's the only option.

### Object-unsafe trait forecloses `dyn`

```rust
trait Cloneable { fn clone_box(&self) -> Self; }   // returns Self by value
// fn f(x: &dyn Cloneable)   // ERROR: `Cloneable` is not object-safe
// Fix idiom: trait CloneBox { fn clone_box(&self) -> Box<dyn CloneBox>; }
```

The `-> Self` makes it impossible to store in a vtable. A staff engineer who wants `dyn` support designs around this from the start.

### SFINAE (pre-concepts) vs concept (C++20)

```cpp
// PRE-C++20: bound smuggled via enable_if; failure = instantiation-deep error dump.
template <class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
T twice(T x) { return x + x; }

// C++20: declared concept; failure = one readable line at the call site.
template <class T>
concept Arithmetic = std::is_arithmetic_v<T>;

template <Arithmetic T>
T twice2(T x) { return x + x; }

// twice2(std::string{"x"});
//   -> "constraint 'Arithmetic<std::string>' was not satisfied"  (clear!)
```

### A concept with a `requires` expression (structural bound)

```cpp
template <class T>
concept HasSize = requires(const T& t) {
    { t.size() } -> std::convertible_to<std::size_t>;   // "must have a .size() returning size-like"
};

template <HasSize C>
bool nonEmpty(const C& c) { return c.size() > 0; }
// Works structurally for std::vector, std::string, your own type with .size() — no inheritance.
```

### Ecosystem-friendly trait design (Rust)

```rust
// Fine-grained capability + defaulted growth method = evolvable.
trait Encoder {
    fn encode(&self, out: &mut Vec<u8>);          // required, minimal
    fn encoded_len(&self) -> usize {              // defaulted: added later, non-breaking
        let mut buf = Vec::new();
        self.encode(&mut buf);
        buf.len()
    }
}
```

### Existential at the boundary (`impl Trait`)

```rust
// Caller gets "some Iterator of u32" without the concrete type leaking,
// and without forcing a dyn allocation.
fn evens(n: u32) -> impl Iterator<Item = u32> {
    (0..n).filter(|x| x % 2 == 0)
}
```

---

## Coding Patterns

### Pattern 1: Static fast path + `dyn` slow/heterogeneous path

```rust
fn handle<T: Handler>(req: &Req, h: &T) { h.handle(req); }        // hot, monomorphized
fn dispatch(req: &Req, h: &dyn Handler) { h.handle(req); }        // heterogeneous registry
```

Expose both; let the call site pick. Keep the trait object-safe so the `dyn` path is even possible.

### Pattern 2: Minimal required surface + defaulted extensions

Publish a trait with the *smallest* set of required methods; grow it only via defaulted methods so existing impls never break. This is your single most important evolution lever.

### Pattern 3: Prefer concepts over `enable_if` in modern C++

```cpp
template <std::integral T> T f(T);          // not: template<class T, enable_if_t<is_integral...>>
```

Named concepts as the *only* sanctioned way to constrain new templates — better errors, better overloads, self-documenting.

### Pattern 4: Trait aliases / bundled bounds for repeated constraint sets

When the same `T: A + B + C` recurs, bundle it (`trait Abc: A + B + C {}` + blanket impl in Rust; a `concept` in C++; a `type` alias for constraints in Haskell). DRY the bound and improve the failure message.

### Pattern 5: Seal traits you must evolve aggressively

If a trait is an internal extension point you need to keep changing, seal it (private supertrait marker) so only you implement it — then add methods freely.

### Pattern 6: Box the heterogeneous, monomorphize the homogeneous

`Vec<Box<dyn Trait>>` for mixed types; `Vec<T>` with a bounded function for one type. Don't pay `dyn` costs for homogeneous data, and don't try to force a single `T` over heterogeneous data.

---

## Best Practices

- **Choose dispatch per API consciously.** Document why a given generic is monomorphized vs `dyn`. Default to static for hot/small/few-typed, dynamic for cold/large/heterogeneous.
- **Keep traits object-safe unless you have a reason not to.** Object safety preserves the `dyn` option; a single `Self`-returning method throws it away forever. If you need both, split the `Self`-returning part into a separate trait.
- **Treat published required-surface and supertrait set as frozen.** Grow via defaults and new traits; never plan to tighten.
- **In C++, write concepts, never new SFINAE.** Migrate `enable_if` to concepts where touched; the diagnostic payoff is enormous.
- **Design bounds for legible failure.** Name your constraints; bundle repeated bound sets; imagine the error a downstream engineer sees.
- **Watch monomorphization bloat in widely-instantiated generics.** Measure binary size and compile time; consider a `dyn` inner core with a thin monomorphized outer shell (the "outline the cold path" technique) for huge generic bodies.
- **Provide instances for popular foreign types from the trait-owning crate** (feature-gated) so users never need orphans.
- **Reserve specialization/overlapping/blanket-impl additions for designed-in cases.** Adding a blanket impl post-publication is among the most coherence-dangerous changes you can make.

### "Outline the cold path" — taming bloat

```rust
// Thin monomorphized shell forwards to one shared non-generic body → less duplicated code.
fn parse<R: std::io::Read>(mut r: R) -> Result<Vec<u8>, std::io::Error> {
    let mut buf = Vec::new();
    r.read_to_end(&mut buf)?;
    parse_bytes(&buf)            // the heavy logic is NON-generic, compiled once
}
fn parse_bytes(_b: &[u8]) -> Result<Vec<u8>, std::io::Error> { /* big, shared */ Ok(vec![]) }
```

---

## Edge Cases & Pitfalls

- **A single object-unsafe method poisons the whole trait for `dyn`.** Adding `fn clone(&self) -> Self` to a trait silently removes the ability to use it as a trait object — a surprising, far-reaching consequence.
- **Monomorphization explosion.** A generic instantiated over hundreds of types (or recursively, like deeply nested combinators) can dominate compile time and binary size; profile with size/compile-time tooling, not intuition.
- **Adding a non-defaulted method or a supertrait silently breaks every downstream impl.** This is the #1 accidental breaking change in trait ecosystems.
- **Blanket-impl overlap.** Adding `impl C for all T: D` after publication can collide with downstream `impl C for SpecificType` — a hard, ecosystem-wide coherence conflict you can't see at design time.
- **C++ concept *subsumption* is partial-order, not total.** Two unrelated concepts both matching can be *ambiguous*; subsumption only disambiguates when one concept's requirements strictly imply the other's. Misdesigned concepts give "ambiguous overload" instead of the hoped-for resolution.
- **Concepts are structural, so unintended types may satisfy them.** A concept "has `.size()`" matches anything with a `.size()`, including types you never meant — the dual of Rust traits' nominal safety. Add semantic checks where it matters.
- **`dyn` boxing in hot loops.** A `Vec<Box<dyn Trait>>` iterated millions of times pays an allocation + an indirect call per element; if it's hot and homogeneous, you wanted monomorphization.
- **Cross-ABI monomorphization is impossible.** You cannot monomorphize across a stable dynamic-library boundary; such boundaries force dynamic dispatch (or a C-style erased interface).
- **`impl Trait` in return position pins one concrete type.** `-> impl Iterator` means *all* return paths must yield the *same* concrete type; branches returning different iterators won't compile (use `Box<dyn>` then).
- **Default-method changes can alter behavior silently.** Changing a defaulted method's body affects every impl that didn't override it — a subtle behavioral (not compile) break.

---

## Apply it

1. Define the user or business outcome that **Bounded Polymorphism** should improve.
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

- Which measurable outcome justifies investing in Bounded Polymorphism?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
