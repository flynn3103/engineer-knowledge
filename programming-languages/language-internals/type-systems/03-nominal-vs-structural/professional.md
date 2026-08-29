# Nominal vs Structural Typing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Nominal vs Structural Typing** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Rust Traits: Nominal Conformance with Global Coherence

Rust traits are nominal — a type implements a trait only via explicit `impl`:

```rust
trait Summary { fn summarize(&self) -> String; }

struct Article { title: String }
impl Summary for Article {            // explicit, nominal conformance
    fn summarize(&self) -> String { self.title.clone() }
}
```

The decisive extra property is **coherence**: for any (trait, type) pair there is *at most one* `impl` in the entire program. This is what lets `x.summarize()` resolve unambiguously and lets generic code `fn f<T: Summary>(t: T)` rely on a single canonical behavior. Structural systems cannot promise this — if conformance is "having the right shape," a type can "be a `Monoid`" in two incompatible ways and nobody can pick the canonical one.

Coherence is enforced by the **orphan rule**: you may write `impl Trait for Type` only if *your crate defines `Trait`* or *your crate defines `Type`*. You cannot, in your crate, implement someone else's trait for someone else's type — because two different crates could then both do it, breaking the single-impl guarantee globally.

### 2. The Newtype Workaround for the Orphan Rule

The orphan rule blocks `impl ForeignTrait for ForeignType`. The standard escape is — again — the **newtype pattern**: wrap the foreign type in your own type, which you *do* own, then implement the trait on the wrapper:

```rust
use std::fmt;

// We want Display for Vec<String>, but both are foreign → orphan rule forbids it.
struct Wrapper(Vec<String>);          // OUR type now

impl fmt::Display for Wrapper {        // legal: we own Wrapper
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "[{}]", self.0.join(", "))
    }
}
```

Here the newtype is not for ID safety but to *legally re-home a trait impl*. Same mechanism, different purpose — a sign of how central newtypes are to nominal systems.

### 3. Coherence Is the Trade for Retroactive Conformance

There is a fundamental tension a senior architect must internalize: **global coherence and unrestricted retroactive conformance are mutually exclusive.**

- Go/structural: any type retroactively satisfies any matching interface → maximal flexibility, *no* coherence (a type can match two interfaces with the same method differently — there's nothing canonical).
- Rust/coherent-nominal: one canonical impl per (trait, type) → reliable dispatch and laws, but you *cannot* freely add impls for foreign type+trait pairs (orphan rule), and conformance is never implicit.

You cannot have both. Choosing a language — or designing a boundary — is choosing a point on this spectrum. Haskell sits near Rust (coherence, with the same orphan-instance hazards); TypeScript sits near Go (structural) with branding as a manual opt-out.

### 4. Hybrid System Design: Place Each Boundary Deliberately

Real architectures mix models *on purpose*:

- **Structural at integration seams.** Where you want unrelated components or third-party types to interoperate, use small structural/capability interfaces (Go `io.Reader`, a TS `{ log(msg): void }` logger port). Retroactive conformance is the feature.
- **Nominal at domain boundaries.** Where confusing two values is a costly bug, use newtypes/branded types and nominal opacity (`UserId`, `Money`, `JwtToken`). Enforced distinctness is the feature.
- **Nominal for evolvable public contracts.** Where you must evolve a published interface deliberately, prefer nominal so implementers opt in and breakage is a compile error, not silent shape drift.

The skill is recognizing which property each boundary needs and not defaulting to whatever the language makes easiest.

### 5. Branding Strategy and Migration at Scale

Introducing nominal IDs into a large structural (TypeScript) codebase is an **expand/contract** migration, not a flag day:

1. Define branded types and *smart constructors* (the only mint points).
2. Brand at the **boundaries first** (DB rows, HTTP deserialization, message decoders) so values are minted once where data enters.
3. Let inference propagate the brands inward; fix the compile errors the brands surface — *those errors are the latent bugs.*
4. Forbid raw `as`-casts outside the constructor module (lint rule) so the brand can't be forged casually.
5. Contract: remove the old un-branded signatures once consumers compile.

Done this way, branding pays for itself: each newly-surfaced error is a place the old code could have swapped IDs.

### 6. Performance of Structural Checking in Big Builds

Structural type-checking cost is real engineering at scale. In large TypeScript monorepos, `tsc` spends much of its time computing the assignability relation over deep generic graphs; the compiler memoizes relation results, but pathological types (huge unions, deeply nested conditional/mapped types, recursive instantiations) defeat the cache and cause multi-minute checks or "type instantiation is excessively deep" errors. Mitigations: name and reuse types (so they memoize), cap generic depth, prefer interfaces (which TS caches better than large anonymous intersections), and use project references/incremental builds. Nominal systems sidestep most of this — identity is a pointer — which is one underrated reason nominal languages often type-check faster on equivalent designs.

---

## Code Examples

### Coherence enables unambiguous generic dispatch (Rust)

```rust
trait ToJson { fn to_json(&self) -> String; }

impl ToJson for i32 { fn to_json(&self) -> String { self.to_string() } }
// Exactly ONE impl of ToJson for i32 may exist program-wide (coherence).

fn dump<T: ToJson>(x: T) -> String { x.to_json() }  // resolves canonically
```

If two crates could each define `ToJson for i32`, `dump` would be ambiguous — the orphan rule prevents that.

### Orphan-rule violation and the newtype fix (Rust)

```rust
// ❌ Not allowed: both serde::Serialize-like trait and Vec are foreign.
// impl ForeignTrait for Vec<u8> { ... }   // E0117 orphan rule

// ✅ Wrap it:
struct Bytes(Vec<u8>);
impl std::fmt::Display for Bytes {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{} bytes", self.0.len())
    }
}
```

### Branding discipline with a single mint point (TypeScript)

```typescript
// ids.ts — the ONLY place brands are minted
declare const brand: unique symbol;
type Brand<T, B extends string> = T & { readonly [brand]: B };
export type UserId  = Brand<string, "UserId">;
export type OrderId = Brand<string, "OrderId">;

// Mint only after validation, only here:
export const UserId  = (s: string): UserId  => s as UserId;
export const OrderId = (s: string): OrderId => s as OrderId;

// elsewhere.ts
function refund(user: UserId, order: OrderId) { /* ... */ }
declare const o: OrderId;
declare const u: UserId;
refund(u, o);          // ✅
// refund(o, u);       // ❌ swapped — caught at compile time
```

A lint rule banning `as UserId`/`as OrderId` outside `ids.ts` keeps the brand unforgeable.

### Hybrid boundary in Go: structural port, nominal domain type

```go
// Structural capability interface at the seam — anything that can store fits.
type Store interface {
    Get(id UserID) ([]byte, error)
    Put(id UserID, v []byte) error
}

// Nominal domain type so IDs can't be confused with raw strings or OrderIDs.
type UserID string
type OrderID string

func handle(s Store, u UserID) { /* s is any conforming impl; u is a distinct type */ }
```

`Store` is structural (mock it trivially in tests, swap implementations freely); `UserID`/`OrderID` are nominal named types (distinct, non-interchangeable).

### Scala refinement type: nominal base + structural narrowing

```scala
// Accepts any Resource that ALSO structurally has a close(): Unit method.
def use(r: Resource { def close(): Unit }): Unit = {
  try r.work() finally r.close()
}
```

A pragmatic hybrid: nominal `Resource` plus an inline structural requirement (reflective-call caveats apply on the JVM).

---

## Coding Patterns

**Pattern: single mint point + lint guard.** All brand/newtype values are created in one module; a lint rule forbids casts elsewhere. The brand becomes unforgeable.

**Pattern: brand at the boundary.** Mint nominal values during deserialization/DB reads; let inference carry them inward and surface latent swap bugs as errors.

**Pattern: newtype-to-bridge.** In Rust, wrap foreign types to implement foreign traits legally; expose ergonomic `Deref`/`From` so the wrapper is pleasant to use.

**Pattern: structural seams, nominal core.** Ports are small structural interfaces; the domain interior uses nominal types and opacity.

**Pattern: compile-time conformance pins (Go).** `var _ Store = (*PostgresStore)(nil)` so evolving `Store` breaks loudly at the implementation.

---

## Best Practices

1. **Choose the model per boundary, not per codebase.** Structural at seams; nominal at domain and public contracts.
2. **Default IDs/units/tokens to nominal.** The ergonomic tax is far cheaper than a production mix-up.
3. **Centralize minting; forbid ad-hoc casts.** A brand that anyone can forge isn't a guarantee.
4. **Respect and exploit the orphan rule.** Reach for the newtype wrapper instead of fighting coherence.
5. **Know that coherence and retroactive conformance can't coexist** at one boundary; pick consciously.
6. **Budget type-check time.** In large structural builds, name/reuse types, cap generic depth, use incremental/project builds, prefer interfaces over giant intersections.
7. **Migrate with expand/contract.** Introduce branded types alongside the old, brand at boundaries, fix surfaced errors, then remove the old signatures.
8. **Pin conformance** (`var _ Iface = ...`) so structural drift becomes a compile error.

---

## Edge Cases & Pitfalls

**1. Orphan-rule surprises in libraries.** You can't implement a third-party trait for a third-party type; downstream users hit `E0117`. Provide newtype wrappers or feature-gated impls in *your* crate so they don't have to.

**2. Coherence breakage via overlapping/blanket impls.** Two crates each adding a "harmless" blanket impl can collide; semver-breaking coherence conflicts are a known Rust ecosystem hazard. Be conservative with blanket impls in public crates.

**3. Forged brands.** A stray `value as UserId` deep in the code silently defeats branding. Without a lint guard, brand discipline erodes over time and the guarantee quietly disappears.

**4. Brands are erased — no runtime safety.** A branded `UserId` is a plain string at runtime; serialization, reflection, and `JSON.parse` all bypass it. Validate at the boundary; never assume the brand checks anything dynamically.

**5. Structural mock drift.** A hand-rolled structural mock satisfies the interface *today*; when the real interface gains a method, the mock may still compile in some languages (or silently diverge), hiding the gap. Pin conformance and prefer generated mocks.

**6. Type-check blowups.** Deeply recursive generics or huge unions defeat the relation cache and stall builds or trip depth limits. This is a *design* smell, not just a compiler quirk — flatten and name the types.

**7. Refinement/structural types on the JVM use reflection.** Scala structural refinement calls compile to reflective dispatch with performance and security caveats; don't use them on hot paths.

**8. Hybrid leaks.** A nominal opaque type can leak its base type through inference, `typeof`, or an over-eager `Deref`/implicit conversion, silently re-exposing the representation you meant to hide. Verify the boundary actually seals.

---

## Apply it

1. Define the user or business outcome that **Nominal vs Structural Typing** should improve.
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

- Which measurable outcome justifies investing in Nominal vs Structural Typing?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
