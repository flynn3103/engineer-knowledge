# Sum, Product & Unit Types — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Sum, Product & Unit Types** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Discriminant encoding: tag, niche, and the in-between

A sum's runtime representation answers one question: *how do we know which variant this is?* Compilers use a spectrum:

- **Explicit tag.** A separate integer field (`u8`/`u32`, sized to the variant count) precedes or follows the payload. Simple, always works. `size ≈ align_up(tag) + max(payload)`.
- **Niche / direct tagging.** If some payload type has invalid bit patterns (a "niche"), the discriminant is stored *in those patterns*, costing zero extra bytes. `Option<&T>` uses the null pointer; `Option<NonZeroU32>` uses 0; `Option<bool>` uses the 254 unused byte values of a `bool`; an enum of C-like fieldless variants is just an integer.
- **Multi-niche / nested.** The compiler can niche-pack *recursively*: `Result<&T, &U>` where one side is a reference, or `Option<Option<&T>>` collapsing two layers into a single pointer's spare patterns. The general problem ("find the largest set of invalid bit patterns across all variants and assign discriminants into them") is what Rust's layout algorithm solves.

The professional consequence: **identical algebra, wildly different bytes.** `Option<&T>` is 8 bytes; `Option<u64>` is 16 (no niche in a `u64`). You cannot reason about size or FFI from cardinality alone — you must know the niche situation.

### 2. Variant arity and zero-cost cases

- **Fieldless variants** (arity 0) carry only the discriminant. An all-fieldless enum is *exactly* a C enum — an integer. The `Red | Green | Blue` enum is `0 | 1 | 2`.
- **Unit-like variants** inside a bigger sum (e.g. `None`, `Nil`) are pure-tag: they occupy a discriminant value and no payload.
- **Newtype/single-field products** are layout-transparent to their inner type in many compilers (`struct Wrapper(u64)` is laid out like `u64`), which is what makes newtypes zero-cost.

This is why `enum` in Rust spans "free C enum" to "tagged union with heap-boxed payloads" depending entirely on the variants — the keyword is the same; the representation is a function of the contents.

### 3. GADTs: when the matched variant refines a type

Ordinary sums are *uniform*: every variant of `Expr` produces an `Expr`. **GADTs** let each constructor produce a *differently-indexed* result, so matching a variant teaches the type checker a *type equation*. The motivating example is a typed expression AST:

```haskell
{-# LANGUAGE GADTs #-}
data Expr a where
  IntLit  :: Int  -> Expr Int
  BoolLit :: Bool -> Expr Bool
  Add     :: Expr Int  -> Expr Int  -> Expr Int
  If      :: Expr Bool -> Expr a -> Expr a -> Expr a

eval :: Expr a -> a            -- returns the RIGHT type per branch, no casts
eval (IntLit n)   = n          -- here the compiler KNOWS a ~ Int
eval (BoolLit b)  = b          -- here a ~ Bool
eval (Add x y)    = eval x + eval y
eval (If c t e)   = if eval c then eval t else eval e
```

Matching `IntLit` *refines* `a` to `Int` in that branch — so `eval` can return `n :: Int` even though its signature is `Expr a -> a`. There is **no runtime type tag inspection and no possibility of a type error**: an ill-typed expression like `Add (BoolLit True) (IntLit 1)` *doesn't typecheck*, so the evaluator can't be handed one. This is the bridge from "sum of types" to "sum carrying type equations," and it's the on-ramp to dependent types: GADTs are indexed sums, and dependent sums (`Σ`) generalize them further (see `professional`-level type-system material elsewhere).

Rust, Swift, OCaml, Scala, and Kotlin have varying degrees of this; OCaml and Haskell have full GADTs, Scala/Kotlin approximate via sealed hierarchies + bounded type members, Rust mostly lacks them (you reach for trait objects or const generics).

### 4. The category theory, as an engineering tool

Map each construct to its categorical identity, and read off *why* the design is forced:

```
product A × B      = categorical PRODUCT     (terminal w.r.t. projections)
sum A + B          = COPRODUCT                (initial w.r.t. injections)
Unit               = TERMINAL object 1        (unique arrow A → 1: const ())
Void               = INITIAL object 0         (unique arrow 0 → A: absurd)
function A → B     = EXPONENTIAL B^A          (currying = the exponential adjunction)
```

A category with all of these is **cartesian closed** — and that's exactly the structure a (total, pure) functional core needs. The payoffs are concrete:

- **Uniqueness of the fold.** A recursive ADT is the **initial algebra** of a *polynomial functor* `F` (built from `+`, `×`, constants, identity). "Initial" means: for any algebra `F r -> r` there is a **unique** map `cata :: Fix F -> r`. That uniqueness is *why* `fold` is canonical and why two folds with the same algebra must be equal — it's a theorem, not a convention.
- **Mechanical deriving.** Because the ADT is built from `+`/`×`, the compiler can *derive* `Functor` (`map`), `Foldable` (`fold`), `Traversable` (effectful map), `Eq`, and `Ord` by structural induction on the polynomial shape. `#[derive(...)]` / `deriving (...)` is the polynomial functor being walked.
- **Soundness of the algebra.** The `|A+B|=|A|+|B|` arithmetic is the cardinality functor being a semiring homomorphism from (finite types, +, ×) to (ℕ, +, ×). The "high-school algebra" works because of this homomorphism — not by coincidence.

You don't *need* the vocabulary to ship, but it's what lets you assert "this fold is the only correct one" and "these derives are total" with confidence rather than hope.

### 5. Traverse: the (de)serialization workhorse

`traverse` ("map an effectful function over a structure, collecting the effects") is derivable for any ADT and is the principled core of parsing/serialization: decoding a `List<Field>` is `traverse decodeField`, turning a `List<Result<T,E>>` into a `Result<List<T>,E>` that short-circuits on the first error. Recognizing serialization as `traverse` over the type's polynomial shape is what lets generic (de)serializers (serde, aeson, protobuf codegen) exist: they walk sums (pick a branch by tag) and products (sequence the fields) uniformly.

### 6. Cross-boundary reality #1: ABI and FFI

In-process, a sum's layout is the compiler's business. Across an FFI boundary it becomes a *contract*:

- **Default layout is unspecified.** Rust's default `enum`/`struct` layout may reorder fields, pick any discriminant encoding, and change between compiler versions. **Never** send a default-`repr` type across FFI.
- **`#[repr(C)]` / `#[repr(u8)]` / `#[repr(C, u8)]`** force a stable, documented layout: a C-compatible struct, an explicit discriminant type, or a "tag + union" C representation for data-carrying enums. This is how you hand a tagged union to C.
- **C unions are the untagged primitive.** To expose a Rust enum to C you typically emit a `struct { tag; union payload; }` — manually reconstructing the tag the safe sum had, because C's `union` has none. The discipline you get for free in-language becomes your responsibility at the boundary.

### 7. Cross-boundary reality #2: serialization and schema evolution

A sum on the wire is a *tag-compatibility* problem, and the closed-world exhaustiveness that protects you in-process becomes an **open-world** forward/backward-compatibility problem:

- **Tag stability.** The integer/string that names each variant must be **stable forever**. Reordering enum variants (and thereby their discriminants) silently reinterprets old data — a classic corruption bug. Pin discriminants explicitly; never rely on declaration order.
- **Unknown variants.** A new producer can send a variant an old consumer doesn't know. Closed exhaustiveness can't help across versions — the consumer needs an explicit `Unknown(tag)` catch-all or a "must-understand" rejection policy. This is precisely why mature formats (protobuf `oneof`, Thrift unions, Avro unions, Cap'n Proto) define unknown-field/unknown-branch behavior.
- **Adding/removing variants.** Adding a variant is forward-incompatible for old readers unless they tolerate unknowns; removing one is backward-incompatible for old writers. Schema-evolution rules for sums are stricter than for products (where adding an optional field is usually safe).
- **Optional ≠ nullable ≠ absent.** `Option<Option<T>>`-style distinctions (present-null vs absent) surface as real wire concerns (JSON `null` vs missing key; protobuf `optional` vs default). The algebra (`2 + A`) you saw at the middle level is now a compatibility decision.

The professional stance: **in-process, exploit closed-world exhaustiveness; on the wire, design for the open world** — stable tags, explicit unknown handling, documented evolution rules.

### 8. Performance engineering of sums

- **Box the fat variant** so the sum is "tag + pointer," keeping common small variants cache-friendly.
- **Order matters for niches** — sometimes restructuring lets the compiler niche-pack, shrinking the type.
- **Branch prediction on the discriminant.** A hot match is a switch on the tag; arranging the common case first, or using jump tables, affects throughput. Profile-guided optimization helps.
- **Struct-of-arrays for bulk sums.** Storing a `Vec<Enum>` wastes the max-variant size per element; splitting into per-variant arrays (an SoA / "columnar" representation) can dramatically cut memory and improve vectorization for data-parallel workloads.
- **Tagged pointers** (steal low/high pointer bits for a small tag) are a manual niche trick used in VMs and allocators when you control the layout.

---

## Code Examples

### Inspecting representation: tag vs niche (Rust)

```rust
use std::mem::{size_of, align_of};
use std::num::NonZeroU32;

enum Color { Red, Green, Blue }            // fieldless → just an integer

fn main() {
    // Fieldless enum: a bare discriminant. 1 byte is enough for 3 variants.
    assert_eq!(size_of::<Color>(), 1);

    // Niche: a reference is never null → None reuses the null pattern. No extra tag.
    assert_eq!(size_of::<Option<&u32>>(), size_of::<&u32>());       // 8

    // Niche: NonZeroU32 can't be 0 → None = 0. Still 4 bytes, no extra tag.
    assert_eq!(size_of::<Option<NonZeroU32>>(), 4);

    // No niche: u32 uses ALL bit patterns → needs a separate tag → padded to 8.
    assert_eq!(size_of::<Option<u32>>(), 8);

    // Box is a non-null pointer → Result<Box<u8>, ()> niches into the pointer.
    assert_eq!(size_of::<Option<Box<u8>>>(), size_of::<*const u8>()); // 8

    println!("align of Option<u32> = {}", align_of::<Option<u32>>());
}
```

### A GADT-typed evaluator with no runtime type errors (OCaml)

```ocaml
(* Each constructor's RESULT type is refined: matching teaches a type equation. *)
type _ expr =
  | Int  : int  -> int expr
  | Bool : bool -> bool expr
  | Add  : int expr * int expr   -> int expr
  | Eq   : int expr * int expr   -> bool expr
  | If   : bool expr * 'a expr * 'a expr -> 'a expr

let rec eval : type a. a expr -> a = function
  | Int n        -> n               (* a = int   here *)
  | Bool b       -> b               (* a = bool  here *)
  | Add (x, y)   -> eval x + eval y
  | Eq  (x, y)   -> eval x = eval y
  | If  (c, t, e) -> if eval c then eval t else eval e

(* `Add (Bool true, Int 1)` is a COMPILE error: Bool true : bool expr,
   but Add demands int expr. The evaluator can never see ill-typed input. *)
```

### Deriving fold/map/traverse from the polynomial shape (Haskell)

```haskell
{-# LANGUAGE DeriveFunctor, DeriveFoldable, DeriveTraversable #-}
data Tree a = Leaf | Node (Tree a) a (Tree a)
  deriving (Functor, Foldable, Traversable)
  -- Tree is the initial algebra of  F x = 1 + (x × a × x), a polynomial functor.
  -- Because it's polynomial, map/fold/traverse are derivable by structural induction.

-- Foldable gives sum, toList, length for free:
total :: Num a => Tree a -> a
total = sum

-- Traversable gives effectful traversal for free — the core of (de)serialization:
-- traverse :: Applicative f => (a -> f b) -> Tree a -> f (Tree b)
validatePositives :: Tree Int -> Maybe (Tree Int)
validatePositives = traverse (\x -> if x > 0 then Just x else Nothing)
-- one negative anywhere short-circuits the whole tree to Nothing.
```

### Crossing FFI: forcing a stable tagged-union layout (Rust)

```rust
// Default repr is UNSPECIFIED — never send it to C.
// repr(C, u8) gives the classic "tag byte + C union of payloads" layout.
#[repr(u8)]
enum Message {
    Ping,
    Text { len: u32, ptr: *const u8 },
    Close { code: u16 },
}
// `repr(u8)` pins the discriminant type; the compiler emits a C-compatible
// struct-with-tag the C side can mirror as:
//   struct Message { uint8_t tag; union { struct {...} text; struct {...} close; }; };
// Reordering variants here renumbers tags → silently breaks the C contract.
```

### Wire-format sum with explicit unknown handling (schema evolution)

```rust
// On the wire, the closed-world exhaustiveness does NOT protect you across versions.
// Pin discriminants explicitly and tolerate unknown variants.
#[repr(u16)]
enum EventKind {
    Click   = 1,    // tags are STABLE FOREVER — never reuse or reorder
    Scroll  = 2,
    KeyDown = 3,
    // A future producer may send 4, 5, ... that THIS binary doesn't know.
}

enum DecodedEvent {
    Known(EventKind, Payload),
    Unknown { tag: u16, raw: Vec<u8> },   // open-world catch-all: don't crash
}
struct Payload;

fn decode(tag: u16, raw: Vec<u8>) -> DecodedEvent {
    match tag {
        1 => DecodedEvent::Known(EventKind::Click,   Payload),
        2 => DecodedEvent::Known(EventKind::Scroll,  Payload),
        3 => DecodedEvent::Known(EventKind::KeyDown, Payload),
        other => DecodedEvent::Unknown { tag: other, raw }, // forward-compatible
    }
}
```

### Struct-of-arrays representation for a bulk sum (performance)

```rust
// Array-of-sums: each element reserves space for the largest variant.
enum Cell { Empty, Int(i64), Text(String) }
// Vec<Cell>: every slot is sized for the biggest variant (String = 24 bytes),
// even the Empty ones. Poor cache density for columnar workloads.

// Struct-of-arrays: one column per variant + a tag column.
struct Column {
    tags:  Vec<u8>,            // 0 = Empty, 1 = Int, 2 = Text
    ints:  Vec<i64>,           // only the Int payloads
    texts: Vec<String>,        // only the Text payloads
}
// Same logical data; far better memory density and vectorization for scans.
// This is how columnar databases store heterogeneously-typed columns.
```

---

## Coding Patterns

### Pattern 1: Pin discriminants and design for unknowns at every boundary

Give every wire/storage variant an explicit, permanent tag; never rely on declaration order. Always provide an `Unknown(tag, raw)` branch (or a documented must-understand rejection) so newer producers don't crash older consumers.

### Pattern 2: `repr(C, u8)` (or equivalent) for any sum that crosses FFI

Force a documented tag+union layout. Mirror it exactly on the foreign side. Treat reordering variants as a breaking ABI change.

### Pattern 3: Box fat variants and niche-friendly types for size

Use `Box`/pointer for the large outlier variant; prefer `NonZero`, references, and other niche-bearing payloads so the compiler packs the tag for free. Verify with `size_of`.

### Pattern 4: Express recursive operations as folds; derive map/fold/traverse

Lean on `deriving`/`#[derive]` for `Functor`/`Foldable`/`Traversable` (or hand-write them as the polynomial structure dictates). Implement codecs as `traverse`.

### Pattern 5: GADTs (where available) for type-refining invariants

When a runtime type tag would otherwise be inspected, reach for a GADT/indexed sum so the match *refines the type* and the unsafe case becomes unrepresentable.

### Pattern 6: Struct-of-arrays for bulk heterogeneous data

When storing millions of sum values in a hot scan path, split into per-variant columns plus a tag column for density and vectorization.

---

## Best Practices

- **Reason in all three representations (algebraic, physical, boundary) and know which one the current problem lives in.** Most leaks come from conflating them.
- **Inside the process: exploit closed-world exhaustiveness; no wildcards over your own sums.** At the boundary: design open-world with stable tags and explicit unknown handling.
- **Never expose a default-layout sum across FFI.** Use `repr(C)`/`repr(C, u8)` and document the contract.
- **Pin wire/storage discriminants forever.** Renumbering or reordering corrupts persisted/in-flight data.
- **Prefer derived `map`/`fold`/`traverse` over hand-rolled recursion** — they're the polynomial functor walked correctly and totally.
- **Use GADTs surgically.** They pay for themselves on typed interpreters and indexed data; they cost inference and error-message quality, so don't reach for them by default.
- **Measure layout decisions.** `size_of`/`align_of`, profiling, and cache-miss counters — boxing and SoA are performance claims that need evidence.
- **Document schema-evolution rules for every persisted/transmitted sum:** what adding, removing, and reordering variants does to forward/backward compatibility.

---

## Edge Cases & Pitfalls

- **Algebraic equivalence ≠ representational/wire equivalence.** `(A, B)` and `(B, A)` are isomorphic but have different byte layouts and different wire encodings. Never substitute one for the other across a boundary.
- **Default `repr` is not stable across compiler versions.** Code that serializes a default-layout type via `unsafe` byte copies (or shares it across an FFI built with a different toolchain) is undefined behavior waiting to happen.
- **Reordering variants renumbers discriminants.** In-process this is invisible; for any persisted/transmitted enum it silently reinterprets old data. Pin discriminants.
- **Niche optimization is not guaranteed by the spec.** It's an optimization Rust *currently* performs for certain types; don't hardcode `size_of` assumptions in code that must be portable across compiler versions unless documented (`Option<&T>` and `Option<NonZero…>` are documented; many others aren't).
- **GADTs break inference and exhaustiveness ergonomics.** Type refinement can make the compiler unable to infer types, force annotations, and produce baffling errors; pattern coverage over GADTs is subtler (some "impossible" branches must be omitted, not handled).
- **Unknown-variant data loss.** If `Unknown(tag, raw)` discards the raw bytes, a proxy/round-tripping service silently drops data a newer peer sent. Preserve and re-emit unknown payloads when acting as a relay.
- **`traverse` short-circuits — sometimes you want to collect *all* errors.** Plain `Result`-traverse stops at the first failure; validation often wants accumulation (a `Validation`/`Either`-with-`Semigroup` applicative). Choose the applicative deliberately.
- **Tagged-pointer tricks assume alignment/pointer-bit availability.** Stealing pointer bits is platform- and allocator-dependent; it breaks under tagging schemes like ARM MTE/top-byte-ignore or non-aligned allocations.
- **`repr(C, u8)` enums and C `union` must agree on alignment and size exactly.** A mismatch is silent memory corruption, not a compile error.

---

## Apply it

1. Define the user or business outcome that **Sum, Product & Unit Types** should improve.
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

- Which measurable outcome justifies investing in Sum, Product & Unit Types?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
