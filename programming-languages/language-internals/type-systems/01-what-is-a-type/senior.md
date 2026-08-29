# What Is a Type — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **What Is a Type** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Lens One: Types as Sets

The most natural formalization: a type **is** the set of its values. `Bool = {true, false}`. `Nat = {0, 1, 2, ...}`. Under this lens, the type-system operations become set operations, and a lot falls out elegantly:

- **Subtyping is subset.** `S <: T` ("S is a subtype of T") means *the values of `S` are a subset of the values of `T`*. `PositiveInt <: Int` because every positive integer is an integer. A value of the subtype is usable wherever the supertype is expected — the **Liskov substitution** principle is "subset" in disguise.
- **Union types are set union.** `Int | String` is the set of all ints *and* all strings.
- **Intersection types are set intersection.** `Serializable & Comparable` is the set of values that are *both*.
- **The empty type** (`Never`, `Void`, `⊥`) is the empty set `∅` — no values inhabit it.
- **The top type** (`any`, `Object`, `⊤`) is the universal set — every value belongs.

This lens is genuinely how TypeScript's union/intersection types, Scala's `with`, and most subtyping intuition work. It's powerful and you should keep it.

### 2. Where Types-as-Sets Breaks

But "a type is just a set" leaks badly under pressure, and a senior must know exactly where:

**(a) Function types.** What *set* is `Int → Int`? Naively, the set of all functions from `Int` to `Int`. But that set is enormous — for an infinite domain it's uncountable, while the functions a program can *express* are countable. The set of *mathematical* functions and the set of *computable/definable* functions diverge. Treating `A → B` as a plain function set leads to cardinality trouble.

**(b) Recursive types.** Define `Tree = Leaf | Node(Tree, Tree)`. As a set equation, this is `Tree = 1 + (Tree × Tree)` — a set defined in terms of itself. Does a solution even exist? Naively iterating can blow up. The honest answer requires *domain theory* (least fixed points of monotone operators on a lattice of sets), not naive set theory. The intuition "a type is its set of values" doesn't tell you how to *construct* that set when the definition is circular.

**(c) The "set of all sets" paradox.** If a type is a set, and there is a *type of all types* (a top type that contains itself), you reproduce **Russell's paradox**: the set of all sets that don't contain themselves cannot consistently exist. A naive "type of all types : type" is *inconsistent*. This is why dependently typed systems introduce a **hierarchy of universes** (`Type₀ : Type₁ : Type₂ : ...`) — to avoid the type of all types containing itself. The set lens, taken literally, is logically unsound.

The lesson: **types-as-sets is an excellent intuition and a poor foundation.** Use it to reason about subtyping and unions; abandon it the moment you hit functions, recursion, or types-of-types.

### 3. Lens Two: Curry–Howard — Types as Propositions, Programs as Proofs

Here is the deep one. The **Curry–Howard correspondence** observes that the typing rules of a programming language and the inference rules of constructive (intuitionistic) logic are *the same rules*, written in different notation. It is a structural isomorphism, not an analogy:

| Logic | Types |
|-------|-------|
| proposition `P` | type `P` |
| proof of `P` | value/program of type `P` |
| `P ∧ Q` (and) | product type `(P, Q)` — a pair |
| `P ∨ Q` (or) | sum type `Either P Q` — a tagged union |
| `P ⇒ Q` (implies) | function type `P → Q` |
| `True` | unit type `()` — trivially inhabited |
| `False` | empty type `Void`/`Never` — uninhabited |
| `¬P` | `P → Void` (a function that, given a `P`, derives absurdity) |
| proof simplification | program evaluation (β-reduction) |

Read the table as: **a type is a proposition, and a value of that type is a proof that the proposition holds.** To *have* a value of type `T` is to have *evidence* that `T` is inhabited — that the proposition `T` is true.

This reframes everything. A function `(A, B) → C` is a *proof* that "`A` and `B` together imply `C`." A function `A → (B → C)` is a proof of `A ⇒ (B ⇒ C)` — and currying is exactly the logical equivalence `(A ∧ B ⇒ C) ⟺ (A ⇒ B ⇒ C)`. The empty type `Void` is `False`: you can't construct a value of it, just as you can't prove falsehood. A function `A → Void` is a proof of `¬A` — "assuming `A`, I reach a contradiction."

Why this matters operationally:

- **"Make illegal states unrepresentable" is the engineering shadow of Curry–Howard.** If you encode an invariant as a type, *constructing a value of that type is a proof the invariant holds.* A `NonEmptyList` value is a proof the list is non-empty. The type checker checks your proof.
- **Total functions are proofs; partial functions are not.** A function that might loop forever or throw doesn't correspond to a valid proof — which is why proof assistants (Coq, Agda, Lean, Idris) require *totality*.
- **Dependent types push this to the limit.** When types can mention values, `∀n. Vec n → Vec n` is a genuine universally-quantified theorem, and the program is its proof. Proving and programming become the same activity.

You don't need a proof assistant to benefit. The mindset — *a type is a claim; a value is its evidence* — sharpens API design enormously.

### 4. Lens Three: Types as Interfaces / Capabilities

The third lens drops "what values are in the set" entirely and asks: **what can I *do* with this?** A type, under this view, is a *set of operations* (a capability, an interface, a contract of behavior):

- A Java/Go **interface** says "any value here supports these methods." It says nothing about the value's representation — only its capabilities.
- A Haskell **type class** / Rust **trait** says "any type implementing this provides these operations." `Ord` means "can be ordered"; `Show` means "can be rendered."
- **Structural typing** (TypeScript, Go interfaces, OCaml objects) makes this literal: a value *has* a type iff it *has the operations*, regardless of name or declared inheritance. "If it walks like a duck and quacks like a duck, it's a `Duck`."

This is the lens that powers decoupling. When a function takes a `Reader` interface, it doesn't care whether the value is a file, a socket, or an in-memory buffer — only that it supports `read`. The type is the *capability boundary*. Note this is *dual* to the set lens: the set lens describes a type by its inhabitants (extensionally); the interface lens describes it by its operations (intensionally). The pragmatic junior definition — "values *plus operations*" — is really these two lenses stapled together, and the staple is doing real work.

### 5. Lens Four: "Untyped" Is Uni-Typed

A claim that sounds like a riddle but is precise. People call assembly, raw Lisp, or the untyped lambda calculus "untyped." But from a type-theory standpoint, **they are not untyped — they are *uni-typed*: they have exactly one type**, the universal type of all values.

In the untyped lambda calculus, everything is a function, so there is one type, "term," and every term inhabits it. In a dynamic language, every value inhabits the single static type "Value" (or `Dynamic`, or `Object`), and the language inserts a runtime check at *every* operation to defend against misuse — `x.foo()` is "if the value tagged at `x` supports `foo`, dispatch, else error." Robert Harper's framing: **a dynamically typed language is a statically typed language with a single recursive type into which all values are injected, with tag-checking projections out of it.**

This reframing has teeth:

- It dissolves the "static vs dynamic" war into "how many static types: one, or many?" Dynamic languages chose *one*.
- It explains why you can *embed* a dynamic language inside a static one (a `Dynamic` type plus tag checks) but the reverse requires throwing information away.
- It clarifies that "untyped" code still pays for types — just at run time, on every operation, with a tag check — rather than once, at compile time.

### 6. Synthesizing the Lenses

No single lens is "the truth." A type is the object that:

- has an **extension** (its set of values — the set lens),
- carries a **logical meaning** (its proposition — the Curry–Howard lens),
- exposes an **interface** (its operations — the capability lens),
- and exists to make **soundness** provable.

The pragmatic "set of values + operations" is the set lens and the interface lens fused. Curry–Howard explains *why* well-typed programs are meaningful (they're proofs). The uni-typed observation explains what "no types" really costs. A senior reaches for whichever lens makes the current design decision clearest — unions and subtyping (sets), invariants and evidence (Curry–Howard), decoupling and polymorphism (interfaces).

---

## Code Examples

### Types-as-sets: subtyping is subset, unions and intersections

```typescript
// TypeScript makes the set lens literal.
type Animal = { name: string };
type Dog = { name: string; bark(): void };
// Dog <: Animal  ⟺  every Dog is an Animal  (subset)

type Id = string | number;          // UNION = set union: all strings ∪ all numbers
type Both = Serializable & Loggable; // INTERSECTION = set intersection

type Never = string & number;        // empty set: no value is both → effectively `never`
```

### Curry–Howard: types are propositions, values are proofs

```haskell
-- AND  ≅  product (pair)
type And a b = (a, b)
-- proof of "A and B" is a pair: you must supply both
proofAnd :: And Int Bool
proofAnd = (42, True)

-- OR  ≅  sum (Either)
type Or a b = Either a b
-- proof of "A or B" is a choice of one side
proofOr :: Or Int Bool
proofOr = Left 42

-- IMPLICATION  ≅  function
modusPonens :: (a -> b) -> a -> b   -- given (A ⇒ B) and A, derive B
modusPonens f x = f x

-- FALSE  ≅  uninhabited type; no value can be built
data Void                            -- no constructors → no proof of False

-- NOT A  ≅  A -> Void
type Not a = a -> Void
```

The key insight: `modusPonens` is literally the logical rule "from `A ⇒ B` and `A`, conclude `B`," and it *is* function application. The program is the proof.

### Curry–Howard in Rust: `Never` as `False`, and impossible code

```rust
// `!` (never) is the uninhabited type — Rust's False.
fn unreachable_branch(x: u8) -> u8 {
    match x {
        0..=255 => x,        // exhaustive
        // any further arm would have type `!` — impossible to reach
    }
}

// A function returning `!` never returns normally — it's a proof of "no normal exit".
fn always_panics() -> ! {
    panic!("this never returns a value")
}

// Result<T, Infallible>: the error case is uninhabited → a PROOF it can't fail.
use std::convert::Infallible;
fn cannot_fail(x: i32) -> Result<i32, Infallible> {
    Ok(x)   // the Err variant can never be constructed; the type proves totality
}
```

`Infallible` (an uninhabited error type) is "make illegal states unrepresentable" as a *proof*: the type guarantees, by inhabitation, that no error path exists.

### Make illegal states unrepresentable as proof-carrying construction

```rust
// A NonEmptyVec: constructing one is a PROOF the collection is non-empty.
pub struct NonEmptyVec<T> {
    head: T,            // there is always at least this one
    tail: Vec<T>,
}

impl<T> NonEmptyVec<T> {
    pub fn new(head: T) -> Self { Self { head, tail: vec![] } }
    pub fn first(&self) -> &T { &self.head }   // total — no Option needed, no panic
}
// `first()` can never fail. The TYPE carries the proof, so the runtime never checks.
```

### The interface/capability lens — Go structural typing

```go
// A type here = a set of operations, not a set of values.
type Reader interface { Read(p []byte) (n int, err error) }

// Anything with a Read method IS a Reader — no declaration of intent needed.
func consume(r Reader) { /* works for files, sockets, buffers, ... */ }

// *bytes.Buffer, *os.File, net.Conn all satisfy Reader structurally:
// they have the Read method, therefore they have the type.
```

### Haskell type classes — capability as constraint

```haskell
-- `Ord a` is the capability "a can be totally ordered".
maximum' :: Ord a => [a] -> a       -- works for ANY a that supports ordering
maximum' = foldr1 (\x y -> if x >= y then x else y)
-- The type doesn't name concrete values; it names a REQUIRED OPERATION SET.
```

### Uni-typed: "untyped" is one type with runtime tag checks

```python
# Conceptually, every Python value has the single static type "object",
# and each operation defends itself with a runtime tag check.
def add(a, b):
    return a + b      # runtime: look up __add__ on a's dynamic tag; error if absent

add(1, 2)             # 3
add("x", "y")         # "xy"
add(1, "y")           # TypeError — the tag-checking "projection out of the universal type" fails
```

Harper's point made concrete: this is a statically typed program over a single universal type `object`, with a tag check at every `+`.

---

## Coding Patterns

### Pattern 1: Encode invariants as constructible-only-when-valid types

A value of `EmailAddress`, `NonEmptyList`, `SortedVec`, or `ValidatedForm` can only be *constructed* through a checking constructor. Once you hold one, the invariant is *proved* — downstream code never re-checks. This is Curry–Howard applied: the constructor is the proof; the type is the theorem.

### Pattern 2: Use uninhabited types to prove "can't happen"

Return `Result<T, Infallible>` (Rust), use `Void`/`never` for unreachable branches, model "this enum case is impossible here" with an empty type. The compiler then *proves* the dead path is dead and can optimize it away.

### Pattern 3: Program to capabilities, not representations

Accept the narrowest interface that supports the operations you need (`Reader`, `Ord`, `Iterator`), not a concrete type. You're naming the *proposition* "this value supports these operations," which is the most reusable contract.

### Pattern 4: Choose nominal vs structural deliberately

Use **nominal** typing when identity/intent matters (a `Meters` must not be confused with a `Feet` even though both are `f64`). Use **structural** typing when you want maximal interop with anything shaped right (duck-typed adapters, config objects). The lens (set+name vs operations) tells you which you're choosing.

---

## Best Practices

- **State which lens you're using when reasoning.** "Is this a subtype?" is a set question; "does this carry the invariant?" is a Curry–Howard question; "what operations does it need?" is an interface question. Mixing them silently causes confused designs.
- **Treat construction as proof.** If a value of type `T` should imply an invariant, make the invariant *impossible to violate at construction*, and never re-validate downstream.
- **Use the empty/never type intentionally.** It documents and proves impossibility; it's not a curiosity. `-> Never` and `Result<_, Infallible>` are precise communication.
- **Don't oversell types-as-sets.** When a colleague reasons about a recursive or higher-order type as "just a set," gently flag the leak — it's where subtle bugs and misunderstandings live.
- **Prefer capabilities over concretes at boundaries.** It maximizes reuse and testability and names exactly the proposition you depend on.
- **Know your language's logic is probably inconsistent.** Any language with non-termination, exceptions, or `null` corresponds to an inconsistent logic — so you can "prove" `False` (e.g. `let x: Void = loop {}`). Useful to know when you reach for "the type proves it": it proves it *only if the producing code is total*.

---

## Edge Cases & Pitfalls

- **Function types aren't honest sets.** Reasoning about `A → B` as the full mathematical function set overcounts (uncomputable functions) and invites cardinality confusion. Think "computable maps," or switch to the Curry–Howard reading (a proof of `A ⇒ B`).
- **Recursive types need fixed points, not enumeration.** "List is Nil or Cons of (T, List)" isn't a set you enumerate; it's a least fixed point. Naive set reasoning gives wrong answers about inhabitation and equality.
- **`Type : Type` is inconsistent.** A type of all types containing itself reproduces Russell's paradox; this is why dependent type theories stratify into universes. If you design a "type of types," beware.
- **Inhabitation can be undefined to decide.** Whether an arbitrary type is inhabited (provable) is, in rich type systems, undecidable — the same wall as the halting problem. Don't expect a checker to always answer "can this be constructed?"
- **Structural matches can be semantically wrong.** Two types with the same shape (`{ x: number; y: number }` as both a `Point` and a `Vector`) are interchangeable structurally but may mean different things. The interface lens sees operations, not meaning.
- **"The type proves it" only holds in a total fragment.** If the constructor can loop, throw, or be bypassed by reflection/`unsafe`, the "proof" has a hole. Curry–Howard guarantees are as strong as your language's totality and soundness.

---

## Tricky Points

- **Curry–Howard is an isomorphism, not an analogy.** The typing rules and the natural-deduction rules are *the same rules*. This is why advances in logic and in type systems track each other historically (intuitionistic logic ↔ simply typed lambda calculus; second-order logic ↔ System F; predicate logic ↔ dependent types).
- **Currying is a logical theorem.** `(A × B → C) ≅ (A → B → C)` is the type-level statement of `(A ∧ B ⇒ C) ⟺ (A ⇒ (B ⇒ C))`. The everyday refactor "uncurry/curry" is a proof transformation.
- **Negation is a function to `Void`.** `¬A` is `A → Void`: "give me an `A` and I'll produce absurdity." Double-negation `((A → Void) → Void)` is *not* the same as `A` in constructive logic — which is exactly why constructive type theory rejects the law of excluded middle and classical proofs by contradiction don't always yield programs.
- **The pragmatic definition is two lenses fused.** "Set of values + operations" = the set lens (values) ∧ the interface lens (operations). Recognizing this explains why it's so durable *and* why it quietly omits the Curry–Howard meaning.
- **Uni-typed framing inverts the usual story.** Instead of "dynamic languages have no types," say "they have *one* type and check it everywhere at run time." This is more accurate and more useful, and it makes gradual typing (adding *more* static types incrementally) the natural next step rather than a paradigm switch.

---

## Apply it

1. State the system invariant that **What Is a Type** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when What Is a Type fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
