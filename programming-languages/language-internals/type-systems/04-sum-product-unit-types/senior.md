# Sum, Product & Unit Types — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Sum, Product & Unit Types** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The expression problem, precisely

You have a datatype with **variants** (kinds of value) and **operations** (functions over them). Lay them out as a grid:

```
              area()   perimeter()   draw()      ← operations (columns)
   Circle      ✓          ✓           ✓
   Square      ✓          ✓           ✓
   Triangle    ✓          ✓           ✓
      ▲
   variants (rows)
```

You want to add a **new column** (operation) *and* a **new row** (variant) without editing existing cells and without runtime casts. The expression problem is that mainstream tools make exactly one of these cheap:

- **Sum + pattern match (FP style):** a function spans a column. Adding an **operation** = writing one new function, exhaustiveness-checked, touching nothing. Adding a **variant** = editing *every* function (every match grows an arm) — but the compiler lists them for you.
- **Interface + classes (OO style):** a class spans a row. Adding a **variant** = writing one new class implementing the interface, touching nothing. Adding an **operation** = adding a method to the interface, forcing edits to *every* class.

Neither is "better." The senior question is: **which axis of this datatype is volatile?** If you'll add operations forever over a stable set of cases (an AST whose node kinds rarely change but whose passes keep growing) → sum types win decisively. If you'll add cases forever with a stable set of operations (a plugin system where each plugin is a new kind, all answering the same fixed interface) → interfaces win. Choosing wrong means a lifetime of "shotgun surgery" on every change.

Solutions that get *both* exist (typeclasses + open data via "Data Types à la Carte," the visitor with double dispatch, multimethods, tagless-final encodings) but they cost complexity. Reach for them only when you genuinely need both axes open.

### 2. The visitor pattern is a closed sum in disguise

When an OO language lacked sum types, the **visitor pattern** reconstructed them. A sealed set of node classes (`Circle`, `Square`) plus a `Visitor` interface with one method per node *is* a closed sum plus a match: the node set is the variants, the visitor is the function-out-of-the-sum, and "every visitor must implement every method" is hand-rolled exhaustiveness. Recognizing this tells you when a visitor is the right tool (closed variant set, many operations, in a language without native sums) and when it's ceremony you can delete (a language with sealed types and pattern matching). Java's `sealed` + `record` + switch patterns make the visitor obsolete for closed hierarchies.

### 3. Recursive ADTs are initial algebras; folds fall out

A recursive ADT references itself:

```
List a  =  Nil  |  Cons a (List a)        -- 1 + a × List a
Tree a  =  Leaf a | Node (Tree a) (Tree a) -- a + Tree × Tree
Expr    =  Lit Int | Add Expr Expr | Mul Expr Expr
```

Each is the **least fixed point** of a "shape functor" — the *initial algebra*. The payoff: every initial algebra has a **unique** structure-collapsing function, the **catamorphism** (`fold`). You don't invent `fold`; you read it off the constructors. For `Expr`, the fold replaces each constructor with a function of the same arity:

```
foldExpr  litF addF mulF  on  (Lit n)    = litF n
                              (Add a b)   = addF (rec a) (rec b)
                              (Mul a b)   = mulF (rec a) (rec b)
```

An evaluator is `foldExpr id (+) (*)`. A pretty-printer is a different algebra over the same fold. A node-counter is another. This is why interpreters built on ADTs are so clean: the recursion scheme is mechanical, and structural recursion over a *finite* value always terminates (every recursive call is on a strictly smaller subterm — no separate termination proof needed).

### 4. "Make illegal states unrepresentable" — the methodology

The junior slogan becomes a discipline with several moves:

- **Replace flags+nullables with sums** (the entry move): a state-bearing struct → a sum where each variant carries exactly its state's data.
- **Smart constructors** make a type's inhabitants *exactly* the legal values (`Percent` is `0..=100`, an `Email` has parsed structure). The raw constructor is private; the public one validates and returns `Option`/`Result`.
- **Newtypes** give same-shaped values distinct identities (`UserId` vs `OrderId`, `Meters` vs `Feet`) so the compiler refuses to mix them — units bugs, ID swaps, and tainted-vs-clean string confusion become type errors.
- **Parse, don't validate** (Alexis King's framing): instead of a `validate(input): bool` you call once and hope nobody forgot, write `parse(input): Result<Validated, Error>` that *returns a more precise type*. Downstream code takes `Validated`, and the *existence of that value is the proof* the data is good. You can't "forget to check" because there's nothing un-checked to pass.
- **Typestate / phantom types** push a value's *state-machine position* into its type, so calling `send()` on an unopened `Connection<Closed>` is a compile error, not a runtime panic.

The throughline: every illegal state you make unrepresentable is a class of runtime bug — and a class of defensive `if`-checks — that you delete permanently.

### 5. Null is a missing sum type; `Option` restores it

`null` is the degenerate, *implicit* sum: every reference type is secretly `T + null`, but the `+ null` is invisible, unchecked, and infectious. The compiler can't force you to handle the `null` branch because the branch isn't in the type — hence Hoare's "billion-dollar mistake." `Option<T>` makes the *exact same* `1 + T` **explicit and checked**: now "absent" is a real variant you must pattern match, and a plain `T` *guarantees presence*. The fix isn't a new idea; it's making the sum that was always there visible to the type checker.

Crucially, `Option` *composes* where null doesn't: `map`, `and_then`/`flatMap`, `unwrap_or`, `?`. Null forces nested defensive `if x != null` pyramids; `Option` flattens them into a pipeline.

### 6. `Result`/`Either` is exceptions-as-data

Exceptions are an *invisible* sum on the return type: a function "returning `T`" actually returns `T + (some unspecified set of throwables)` via a hidden control channel. The type doesn't say which errors, callers can't be forced to handle them, and the happy path and error path live in different syntactic worlds. `Result<T, E>` (= `T + E`) puts the error case **in the return type**, makes it **part of the function's contract**, and forces handling. Trade-offs are real and worth naming as a senior:

- **Pro:** errors are explicit, exhaustively typed, local, and visible in signatures; no invisible non-local control flow.
- **Pro:** you can model an *error taxonomy* as a sum (`enum DbError { Timeout, NotFound, Conflict(Id) }`) and exhaustively handle it.
- **Con:** boilerplate without sugar — which is why ergonomic languages add `?`/`try` operators, `map_err`, and error-conversion traits (`From`) so propagation is one character.
- **Con:** truly *exceptional* conditions (OOM, stack overflow, programmer-bug panics) are still better as unwinding; `Result` is for *expected* failures.

The senior stance: **`Result` for expected, recoverable, part-of-the-contract failures; panic/exception for bugs and unrecoverable conditions.** Don't `Result`-ify a logic error; don't `throw` a "file not found."

### 7. Railway-oriented programming: composing `Result` pipelines

A chain of fallible steps composes as a two-track railway: stay on the success track, and any failure switches you onto the error track and skips the rest.

```
parse ──► validate ──► enrich ──► save        (success track)
   │          │           │         │
   └──────────┴───────────┴─────────┴──►  error track (short-circuits to the end)
```

`and_then`/`flatMap` is the switch; `?` is its syntax. This turns a nest of `if err != nil { return }` into a linear pipeline, and because each step's error type is part of the sum, the final error is exhaustively known.

### 8. When sums are the *wrong* tool

Seniority includes knowing the anti-cases:

- **Open, plugin-style extensibility** where third parties add variants you'll never enumerate → interfaces/traits, not a closed sum.
- **Wide, sparse data** (hundreds of optional fields, like a config or a protobuf message) → a product with optionals is often clearer than an explosion of variants; the algebra would be enormous but the *modeling* is genuinely "lots of independent optionals."
- **Performance-critical hot paths** where a fat sum forces large allocations or branch-heavy matching → sometimes a struct-of-arrays or a hand-tuned layout beats the idiomatic sum.
- **Over-encoded invariants** where pushing *everything* into types yields unreadable, un-evolvable type-level gymnastics. "Make illegal states unrepresentable" has a point of diminishing returns; some invariants are better as a runtime check with a good error.

---

## Code Examples

### The two sides of the expression problem (Rust sum vs trait)

```rust
// ---- SUM SIDE: operations are cheap, variants are expensive ----
enum Shape { Circle(f64), Square(f64) }

fn area(s: &Shape) -> f64 {            // new OPERATION = new fn, nothing else changes
    match s {
        Shape::Circle(r) => std::f64::consts::PI * r * r,
        Shape::Square(s) => s * s,
    }
}
fn perimeter(s: &Shape) -> f64 {       // another new operation, again trivial
    match s {
        Shape::Circle(r) => 2.0 * std::f64::consts::PI * r,
        Shape::Square(s) => 4.0 * s,
    }
}
// But adding `Triangle` forces edits to BOTH area and perimeter
// (the compiler will list them — non-exhaustive match errors).

// ---- TRAIT SIDE: variants are cheap, operations are expensive ----
trait Shape2 { fn area(&self) -> f64; }      // operations live in the trait
struct Circle2(f64);
struct Square2(f64);
impl Shape2 for Circle2 { fn area(&self) -> f64 { std::f64::consts::PI * self.0 * self.0 } }
impl Shape2 for Square2 { fn area(&self) -> f64 { self.0 * self.0 } }
// Adding `Triangle2` = one new impl, touch nothing.
// But adding `perimeter` to the trait forces edits to EVERY impl.
```

### Recursive ADT + a fold-derived interpreter (Haskell)

```haskell
data Expr = Lit Int
          | Add Expr Expr
          | Mul Expr Expr
          | Neg Expr

-- The fold (catamorphism) reads straight off the constructors:
foldExpr :: (Int -> r) -> (r -> r -> r) -> (r -> r -> r) -> (r -> r) -> Expr -> r
foldExpr lit add mul neg = go where
  go (Lit n)   = lit n
  go (Add a b) = add (go a) (go b)
  go (Mul a b) = mul (go a) (go b)
  go (Neg a)   = neg (go a)

eval :: Expr -> Int
eval = foldExpr id (+) (*) negate          -- one algebra

countNodes :: Expr -> Int
countNodes = foldExpr (const 1) (\a b -> 1+a+b) (\a b -> 1+a+b) (\a -> 1+a)  -- another

-- Add an operation (a new fold algebra) = trivial. Add a constructor = edit every fold.
```

### Parse, don't validate (Rust)

```rust
// WEAK: a bool check you can forget to call, and a type that lies.
fn is_valid_email(s: &str) -> bool { s.contains('@') }
fn send_weak(addr: &str) { /* hopefully someone validated... */ }

// STRONG: parsing returns a MORE PRECISE TYPE; its existence is the proof.
pub struct Email(String);                    // private field: only `parse` can build one
impl Email {
    pub fn parse(s: &str) -> Result<Email, &'static str> {
        if s.contains('@') && !s.starts_with('@') {
            Ok(Email(s.to_string()))
        } else {
            Err("invalid email")
        }
    }
    pub fn as_str(&self) -> &str { &self.0 }
}
fn send_strong(addr: &Email) { /* CANNOT be called with unvalidated input */ }
// Downstream takes `&Email`, never `&str`. The check happens exactly once, at the boundary.
```

### Typestate: illegal transitions don't compile (Rust phantom types)

```rust
use std::marker::PhantomData;

struct Open; struct Closed;                      // zero-size state markers (phantoms)

struct Door<State> { _state: PhantomData<State> }

impl Door<Closed> {
    fn new() -> Door<Closed> { Door { _state: PhantomData } }
    fn open(self) -> Door<Open> { Door { _state: PhantomData } }   // Closed -> Open
}
impl Door<Open> {
    fn close(self) -> Door<Closed> { Door { _state: PhantomData } } // Open -> Closed
    fn walk_through(&self) { /* only legal while Open */ }
}

fn demo() {
    let d = Door::<Closed>::new();
    let d = d.open();
    d.walk_through();          // OK: it's Open
    let _d = d.close();
    // _d.walk_through();      // COMPILE ERROR: no such method on Door<Closed>
}
```

The state machine's legality is now a *type* fact: you cannot call `walk_through` on a closed door, cannot `open` an already-open one, etc. Unit-like zero-size types (`Open`, `Closed`) carry the state with no runtime cost.

### Error taxonomy as a sum + railway pipeline (Rust)

```rust
#[derive(Debug)]
enum AppError { NotFound, Timeout, Invalid(String) }

fn load(id: u32) -> Result<Raw, AppError> { /* ... */ Ok(Raw) }
fn parse(r: Raw) -> Result<Parsed, AppError> { /* ... */ Ok(Parsed) }
fn save(p: Parsed) -> Result<(), AppError> { /* ... */ Ok(()) }

struct Raw; struct Parsed;

fn pipeline(id: u32) -> Result<(), AppError> {
    let raw = load(id)?;        // `?` = the railway switch: on Err, return early
    let parsed = parse(raw)?;
    save(parsed)?;              // happy path reads top-to-bottom; errors short-circuit
    Ok(())
}

fn handle(id: u32) {
    match pipeline(id) {
        Ok(())                  => println!("done"),
        Err(AppError::NotFound) => println!("404"),
        Err(AppError::Timeout)  => println!("retry later"),
        Err(AppError::Invalid(why)) => println!("bad input: {why}"),
        // exhaustive: add a variant to AppError and this match won't compile
    }
}
```

### Java: closed hierarchy with `sealed` + records + switch patterns (modern)

```java
sealed interface Shape permits Circle, Rectangle {}     // CLOSED sum
record Circle(double radius) implements Shape {}
record Rectangle(double w, double h) implements Shape {} // products via records

static double area(Shape s) {
    return switch (s) {                                  // exhaustive switch
        case Circle c    -> Math.PI * c.radius() * c.radius();
        case Rectangle r -> r.w() * r.h();
        // no default needed: `sealed` lets javac verify exhaustiveness.
        // Add a permitted type and forget a case -> compile error.
    };
}
```

`sealed` (Java 17) closes the permit-list so the compiler knows the full variant set; `record` gives concise product variants; switch patterns give the match. This is native ADTs reaching mainstream OO — the visitor pattern is no longer needed for closed hierarchies.

---

## Coding Patterns

### Pattern 1: Match the volatile axis

Decide sum-vs-interface by which dimension (variants or operations) will grow. Document the choice and its reason near the type definition, so the next engineer knows which changes are cheap.

### Pattern 2: Parse-don't-validate at every boundary

Every external input gets a `parse(raw) -> Result<Precise, Error>` at the edge. The core takes only the precise types. Validation happens exactly once, and "valid" is a type, not a convention.

### Pattern 3: Newtypes for every distinct identity and unit

Wrap `u64`s that mean different things (`UserId`, `OrderId`) and numbers with units (`Meters`, `Seconds`) in newtypes. Zero runtime cost, eliminates mix-ups the compiler can now catch.

### Pattern 4: Error taxonomy as a sum + `From` conversions + `?`

Model your domain errors as an `enum`, implement conversions from lower-level errors, and let `?`/`try` propagate. Handle exhaustively at the top.

### Pattern 5: Derive the fold; write operations as algebras

For recursive ADTs, write one `fold`/`cata` and express every operation (eval, print, count, optimize) as an algebra fed to it. New operation = new algebra, never new recursion.

### Pattern 6: Typestate for safety-critical lifecycles

When calling a method in the wrong state is dangerous (a closed socket, an uncommitted transaction), encode state in a type parameter so the wrong call doesn't compile.

---

## Best Practices

- **Choose sum-vs-interface by the volatility axis, and write down why.** This decision compounds for years.
- **Push validation to the boundary; carry proofs in types.** Parse, don't validate. The core should be unable to receive invalid data.
- **Use `Result` for expected failures, panic/exception for bugs.** Don't conflate "the file is missing" (a `Result`) with "this invariant is violated" (a bug → panic).
- **Model an error taxonomy as a sum and handle it exhaustively at the edges.** Avoid stringly-typed errors in the core.
- **Avoid wildcard arms over your own closed sums** so adding a variant remains a compiler-guided refactor.
- **Express recursive-type operations as folds/algebras,** not ad-hoc recursion, so they stay uniform and total.
- **Know when to stop.** "Make illegal states unrepresentable" has diminishing returns; some invariants belong in a runtime check with a clear error, not in a type-level proof nobody can read.
- **Prefer native sums (sealed/enum/data) over visitor or class-hierarchy fakes** when the language offers them.

---

## Edge Cases & Pitfalls

- **Variant-heavy datatypes punish the sum side.** If you keep adding cases, every operation grows. Re-evaluate whether an interface fits better — the compiler's "non-exhaustive" errors are a *symptom* you may be on the wrong axis.
- **`#[non_exhaustive]` / open enums break downstream exhaustiveness.** Marking a public enum non-exhaustive protects *you* from breaking changes but forces *every* downstream match to carry a wildcard — they lose the safety. Document it loudly.
- **Deep recursive folds overflow the stack.** A 1M-node list folded with naive recursion blows the stack in strict languages. Use an explicit stack, a trampoline, or tail-recursive accumulation.
- **Over-engineered typestate becomes unusable.** Phantom-type state machines with a dozen states and generic plumbing can make the API impenetrable. Encode the *dangerous* transitions, not every transition.
- **`Result` everywhere creates "error soup."** Without a deliberate taxonomy and conversion strategy, a function's error type becomes a sprawling union of everything below it. Define error boundaries; convert at module edges.
- **Smart constructors leak if the field isn't truly private.** If any code path can build the type without the validation, the invariant is a lie. Keep raw constructors private and audit every construction site.
- **Parsing twice defeats the point.** If both the boundary *and* the core re-validate, you've kept the runtime cost and the "forgot to check" risk. Validate once, then trust the type.
- **Sum types don't model "many independent optionals" well.** A record with 40 optional fields is not 2^40 variants; it's genuinely a product of optionals. Forcing it into a sum explodes pointlessly.

---

## Apply it

1. State the system invariant that **Sum, Product & Unit Types** must protect.
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

- Which invariant must remain true when Sum, Product & Unit Types fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
