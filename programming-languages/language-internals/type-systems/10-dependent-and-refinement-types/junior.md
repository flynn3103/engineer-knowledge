# Dependent & Refinement Types — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Dependent & Refinement Types** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Ordinary types throw away information

Think about the type `int`. It tells you "this is an integer." It does **not** tell you whether the value is positive, even, in range, or non-zero. So when you write a function:

```text
divide(a: int, b: int) -> int
```

the type system is perfectly happy to let someone call `divide(10, 0)`. The crash is not the type system's fault — the type `int` *includes* zero, and you asked for an `int`. The information "b must not be zero" lives only in your head (and maybe a comment, and maybe a runtime `if b == 0` check you remembered to write).

Same story with lists. The type `List<int>` covers the empty list and the billion-element list identically. So:

```text
first(xs: List<int>) -> int
```

is a function that *cannot keep its promise*. If `xs` is empty, there is no first element. Either it crashes, or it returns some fake value, or it forces the caller to handle an `Optional`. The type `List<int>` simply does not carry the fact "this list is non-empty."

**The core insight of this whole topic:** these bugs exist because the type is too *coarse*. It admits values it shouldn't. If we could make the type *finer* — exactly the positive ints, exactly the non-empty lists — the bugs would have nowhere to live.

### 2. Refinement types: a base type plus a condition

A **refinement type** is the simpler of the two ideas, so start here. You take a normal type and attach a predicate — a true/false condition. The notation, read aloud, is "values `v` of this base type *such that* the condition holds":

```text
{ v: Int | v > 0 }          -- positive integers
{ v: Int | v >= 0 }         -- non-negative integers (naturals)
{ v: Int | v /= 0 }         -- non-zero integers
{ s: String | length s > 0 } -- non-empty strings
```

Now rewrite `divide` with a refinement on the divisor:

```text
divide(a: Int, b: { v: Int | v /= 0 }) -> Int
```

The divisor's type **excludes zero**. The compiler will now reject any call where it cannot be sure `b` is non-zero. The "don't divide by zero" rule has moved out of your head and into the type. You did not write a runtime check; the *type* is the check.

The beautiful part: in tools like Liquid Haskell and F\*, you do **not** prove these conditions by hand. An **SMT solver** — an automated logic engine — figures out "is `b` always non-zero here?" for you. You write the refinement; the machine does the reasoning. That makes refinement types relatively *practical*.

### 3. Dependent types: a type that mentions a value

A **dependent type** goes further: the type itself contains an actual value. The textbook example is the length-indexed vector, written `Vec n a`:

- `Vec 0 Int` — a vector of **exactly zero** ints (the empty one).
- `Vec 3 Int` — a vector of **exactly three** ints.
- `Vec n Int` — a vector of `n` ints, where `n` is a length that may vary.

The number `n` is a *value*, and it is sitting *inside the type*. That is the defining move of dependent typing: **types can depend on values**. In ordinary languages there is a strict wall between "values" (run at runtime) and "types" (checked at compile time). Dependent types knock a door in that wall.

Why is this powerful? Because now functions can make precise promises in their signatures:

```text
append : Vec n a -> Vec m a -> Vec (n + m) a
```

Read it: "give me a vector of length `n` and a vector of length `m`, and I will give you back a vector of length **exactly `n + m`**." The compiler **checks** that the implementation actually produces a vector of that length. If you wrote `append` with an off-by-one bug, it would not compile.

And the showstopper:

```text
head : Vec (n + 1) a -> a
```

Read it: "`head` only accepts a vector whose length is `n + 1`" — i.e. *at least one element*. It is **impossible to call `head` on an empty vector**, because `Vec 0 a` does not match the shape `Vec (n + 1) a`. The empty-list crash is not handled at runtime; it is forbidden at compile time. There is no code path to test, because the broken program does not typecheck.

### 4. Why your everyday language doesn't do this

If this is so great, why isn't Java doing it? Three reasons, which the higher tiers explore in depth:

1. **Cost.** Dependent types can require you to *write proofs* by hand. That is slow, specialized work.
2. **Compile times and complexity.** Checking these types is expensive, and the type systems are intricate.
3. **Ergonomics.** The languages that do this well (Agda, Coq, Idris) are research-grade. The tooling and learning curve are steep.

So these tools live where the payoff justifies the cost: **verified crypto, compilers, operating-system kernels, avionics** — places where a single bug is catastrophic. For everyday CRUD apps, the trade is usually not worth it... *yet*. The trend is that pieces of this are slowly arriving in mainstream languages, which is why it is worth understanding now.

### 5. The two are a spectrum, not a binary

Refinement types and dependent types are two points on a gradient of "how much can a type say":

```text
ordinary types            refinement types            full dependent types
(int, List<T>)            ({v:Int | v>0})             (Vec n a, proofs)
        |                        |                            |
  says almost nothing     says "satisfies P",          says anything you can
                          SMT checks it for you         state — but you may
                                                        have to prove it by hand
        less expressive  ----------------------------->  more expressive
        less effort      <-----------------------------  more effort
```

**Refinement types are more automatable but less expressive** (the SMT solver does the work, but it can only handle conditions it understands). **Dependent types are maximally expressive but more effortful** (you can state anything, but you may have to prove it). That trade-off is the single most important thing to take from this page.

---

## Code Examples

These are deliberately small. The point is to *read* them and feel the idea, not to install a compiler.

### Example 1: Refinement type for a non-zero divisor (Liquid Haskell flavor)

```haskell
-- A refinement: the second argument's type forbids zero.
-- The {-@ ... @-} comment is the refinement annotation.

{-@ divide :: Int -> { v:Int | v /= 0 } -> Int @-}
divide :: Int -> Int -> Int
divide a b = a `div` b

-- This call is fine — 3 is provably non-zero:
ok = divide 10 3

-- This call is REJECTED at compile time — 0 violates the refinement:
bad = divide 10 0     -- ❌ Liquid type error: 0 /= 0 is false
```

You wrote no runtime `if`. The `{ v:Int | v /= 0 }` *is* the guard, checked by an SMT solver before the program runs.

### Example 2: A safe array index (refinement, conceptual)

```text
-- "i is a valid index into arr" expressed as a refinement:
get : (arr: Array a) -> (i: { v: Int | 0 <= v && v < length arr }) -> a
```

The index `i`'s type says it must be at least 0 and less than the array's length. A call with a possibly-out-of-range index simply will not typecheck. The classic "index out of bounds" crash is **gone by construction** — and so is the runtime bounds check the CPU would otherwise perform.

### Example 3: Length-indexed vectors (Idris flavor)

```idris
-- Vect n a : a vector of EXACTLY n elements of type a.
-- The length n is part of the type.

-- Joining two vectors: the result length is the SUM, stated in the type.
append : Vect n a -> Vect m a -> Vect (n + m) a
append []        ys = ys
append (x :: xs) ys = x :: append xs ys

-- head only accepts a NON-EMPTY vector: shape Vect (S k) a means "length is some k+1".
head : Vect (S k) a -> a
head (x :: xs) = x

-- These typecheck:
v3 : Vect 3 Int
v3 = [1, 2, 3]

firstElem : Int
firstElem = head v3          -- ✅ v3 has length 3, which is S 2

-- This does NOT typecheck — you literally cannot write it:
empty : Vect 0 Int
empty = []

oops = head empty            -- ❌ type error: Vect 0 Int doesn't match Vect (S k) a
```

Notice: there is **no runtime check** in `head` for emptiness. There doesn't need to be. The empty case can't reach it.

### Example 4: The same idea, peeking in TypeScript (a weak taste)

Mainstream languages can imitate a sliver of this. TypeScript *literal types* let a type be a specific value:

```typescript
// A literal type: this value must be exactly the number 200, not any number.
type HttpOk = 200;

function classify(status: 200 | 404 | 500): string {
  switch (status) {
    case 200: return "ok";
    case 404: return "not found";
    case 500: return "server error";
  }
}

classify(200);   // ✅
classify(201);   // ❌ Argument of type '201' is not assignable to '200 | 404 | 500'
```

This is a faint echo of refinement: the type `200 | 404 | 500` restricts which values are allowed, and the compiler enforces it. It's far weaker than a real refinement type (no arithmetic predicates, no SMT solver), but it shows the idea sneaking into everyday tools.

### Example 5: Rust const generics (a sliver of dependent typing)

```rust
// [T; N] is an array whose LENGTH N is part of its type.
// N is a value living in the type — a tiny piece of dependent typing.

fn first<const N: usize>(arr: [i32; N]) -> i32 {
    arr[0]   // still needs N >= 1 to be truly safe; Rust doesn't prove that here
}

let a: [i32; 3] = [10, 20, 30];   // type carries the length 3
let b: [i32; 5] = [1, 2, 3, 4, 5];
// a and b have DIFFERENT types because their lengths differ.
```

Rust's `[T; N]` puts a length *value* into the type, which is genuinely a fragment of dependent typing. Rust does not let you state and prove `N >= 1` the way Idris does — but the door is open.

---

## Coding Patterns

You won't write these daily yet, but recognizing them matters.

**1. Length-indexed collections.** Carry the size in the type (`Vec n a`, `[T; N]`) so functions can promise size relationships and forbid empty access.

**2. Refine at the boundary.** When data enters your program (parsing, input), refine it once into a precise type (`{v: Int | v > 0}`), then the rest of the code is guarded for free.

**3. Smart constructors.** Make the only way to build a refined value go through a function that establishes the predicate — so an invalid value cannot exist.

**4. Make illegal states unrepresentable.** Before adding a runtime check, ask: can I change the type so the bad state can't be built at all?

**5. Lean on the solver, not on yourself (refinement).** With Liquid Haskell / F\* / Dafny, state the property and let the SMT solver prove it. Reserve hand-written proofs for when the solver can't.

---

## Best Practices

- **Start with refinement, not full dependent types.** Refinement types give you most of the everyday safety (bounds, non-zero, non-empty) with the SMT solver doing the hard work. Save dependent types for when you truly need them.
- **Refine inputs as early as possible.** The closer to the system boundary you establish a property, the more code downstream gets it for free.
- **Keep predicates in the solver's "easy" fragment.** Linear arithmetic and equalities are SMT-friendly. Nonlinear or quantified predicates may need help.
- **Treat a type-level property as a spec.** When you write `Vec (n + m)`, you've written a contract — make sure it's the contract you actually want.
- **Don't over-reach.** Encoding *everything* in types is a research project. Encode the properties whose bugs would actually hurt.
- **Read the error.** Dependent/refinement type errors are wordy but precise — they usually tell you the exact predicate that couldn't be proven.

---

## Edge Cases & Pitfalls

- **A refinement only helps if it reaches the call site.** If you launder a value through an unrefined `Int`, you lose the guarantee. Keep the refined type as long as possible.
- **The SMT solver can time out or give up.** For predicates outside its comfort zone (nonlinear arithmetic, heavy quantifiers), it may fail to prove a true fact. That's a limitation, not a bug in your code.
- **`Vec 0` vs `Vec (n+1)` is the whole trick.** The reason `head` is safe is that the empty vector's type literally cannot match the non-empty shape. If you blur the two, the safety evaporates.
- **Termination matters for proofs (preview).** In proof assistants, a function that loops forever can "prove" false things. Higher tiers cover *totality checking* — why these languages insist your functions provably terminate.
- **More precise types can make code harder to write.** Sometimes you must convince the checker of a fact that's "obvious" to you. That friction is the cost side of the trade.
- **Performance of the *checker*, not the program.** The runtime can be fast (checks elided); it's the *compile-time* proving that's expensive.
- **These aren't magic.** A wrong specification, precisely enforced, is still wrong. The compiler proves your code matches your *types*, not that your types match your *intent*.

---

## Apply it

1. Choose one small, known input for **Dependent & Refinement Types**.
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

- What problem does Dependent & Refinement Types solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
