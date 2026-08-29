# Evaluation Strategies (call-by-x) — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Evaluation Strategies (call-by-x)** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Parameter Passing IS Reduction Order

In the pure lambda calculus there are no side effects and no references — only substitution. The only freedom is **which redex you reduce next**, and that single freedom *is* the evaluation strategy:

- **Applicative order:** given `(λx. body) arg`, first reduce `arg` to a value `v`, then reduce `body[x := v]`. Arguments are values before substitution → **call-by-value**.
- **Normal order:** reduce the outer application *first*, substituting the *unreduced* `arg` into `body`, and only reduce occurrences of `arg` as the body demands them → **call-by-name**.

Everything else (sharing, references, copy-restore) is what you get when you add *mutable state* and *memory* to this skeleton. The reduction-order skeleton is the part the theory pins down exactly.

### 2. Church-Rosser and Why Normal Order Terminates More

The **Church-Rosser theorem** (confluence) says reduction is *deterministic in its result*: a term has **at most one** normal form, regardless of the order you reduce. The companion **standardization theorem** says **normal-order reduction will find that normal form if it exists.** Applicative order has no such guarantee.

The canonical witness is:

```text
(λx. y) ((λz. z z) (λz. z z))
```

The argument `(λz. z z)(λz. z z)` (call it Ω) reduces to itself forever.
- **Applicative order** insists on reducing Ω first → never terminates.
- **Normal order** substitutes Ω into `λx. y`, which *discards* `x`, yielding `y` immediately.

This is the rigorous, side-effect-free version of the middle page's `const 42 undefined`. Termination is a property of *order*, and normal order is the maximally-terminating choice. The price is that normal order may **duplicate** the argument (reduce it multiple times), which is exactly what call-by-need fixes.

### 3. Call-by-Need as Graph Reduction

Normal order's flaw: if the body uses `x` three times, the unreduced argument is substituted three times and reduced three times. **Call-by-need** implements normal order over a **shared graph**: all occurrences of `x` point at *one* node; the first demand reduces it in place; later demands read the reduced node. You get normal order's termination behavior with applicative order's no-recomputation efficiency — paid for with the bookkeeping of indirection nodes and (in practice) space leaks. This is the implementation model behind Haskell's STG machine and lazy graph reduction.

### 4. Strictness Analysis: Reclaiming Eagerness

Pure laziness is expensive (a thunk per binding). Lazy compilers run **strictness analysis**: if they can *prove* an argument is always evaluated (e.g. `f x = x + 1` definitely forces `x`), they compile it as call-by-value — no thunk, often in a register. The semantics are unchanged because a *needed* argument's evaluation order is observationally identical whether eager or deferred. This is why "Haskell is slow because lazy" is too glib: GHC eagerly evaluates strict positions and only pays for laziness where it's actually exploited.

### 5. Call-by-Move: The Modern Strategy

The classic taxonomy (value/reference/name/need/copy-restore) was settled before resource-owning value types were mainstream. Modern systems languages add **call-by-move**: pass an object by **transferring ownership of its internals** (heap buffer, file handle, lock) rather than copying them or aliasing them.

- A `std::vector<int>` of a million elements passed **by value** copies a million ints. Passed **by move**, only the three-word header (pointer, size, capacity) is transferred; the source is left empty. Same surface as call-by-value (a fresh object in the callee, no aliasing), but with the cost of a reference.
- It is *not* call-by-reference: there is no aliasing, no shared mutable state, and the source can no longer be used (Rust enforces this statically; C++ leaves it "valid but unspecified").

Move semantics is best understood as **call-by-value where the "value" being copied is cheap to copy because it's just a handle, and the source's handle is nulled to preserve the single-owner invariant.** It threads the needle between value's safety and reference's cheapness.

### 6. The Full Grid

| Strategy | Evaluation (when) | Aliasing | Mutates caller? | Cost model |
|----------|-------------------|----------|------------------|-----------|
| Call-by-value | strict | none (copy) | no | copy of whole value |
| Call-by-reference | strict | full alias | yes (rebind + mutate) | one pointer, indirection |
| Call-by-sharing | strict | shares object | mutate yes, rebind no | one reference copy |
| Call-by-copy-restore | strict | none during call | yes (at return) | copy in + copy out |
| Call-by-name | non-strict | (re-eval each use) | via expr side effects | thunk + N evaluations |
| Call-by-need | non-strict | shared thunk | via expr side effects | thunk + 1 evaluation + memo |
| **Call-by-move** | strict | none (ownership moved) | source invalidated | one handle transfer |

Reading this grid fluently — and knowing which cell a given language's `f(x)` lands in — is the senior-level competency.

---

## Code Examples

### Example 1: Normal vs Applicative Order, Mechanically

```text
Term:  (λx. λy. x) A B            -- returns A, ignores B
                                  -- let B = Ω, a diverging term

Applicative order:  evaluate B (=Ω) first → loops forever.   NON-TERMINATING
Normal order:       (λx. λy. x) A B
                    → (λy. A) B           [x := A]
                    → A                   [y := B, but y unused → B never reduced]
                                          TERMINATES with A
```

This is Church-Rosser/standardization in action: a normal form (`A`) exists, and normal order finds it; applicative order does not.

### Example 2: C++ — Value, Reference, and Move Side by Side

```cpp
void byValue(std::vector<int> v);          // COPIES the whole vector (deep)
void byConstRef(const std::vector<int>& v);// aliases, read-only, no copy
void byRef(std::vector<int>& v);           // aliases, can mutate caller's vector
void byMove(std::vector<int>&& v);         // takes OWNERSHIP; source emptied

std::vector<int> data(1'000'000);

byValue(data);            // 1M-element deep copy; 'data' still usable
byConstRef(data);         // zero copy; 'data' unchanged, read-only inside
byRef(data);              // zero copy; callee may modify 'data'
byMove(std::move(data));  // O(1) handle transfer; 'data' now valid-but-empty
```

`std::move` is just a cast to `T&&` — it *enables* the move overload; the actual stealing happens in the move constructor (swap the pointer, null the source).

### Example 3: Rust — Move by Default, Borrow to Avoid It

```rust
fn consume(v: Vec<i32>) { /* owns v; freed at end */ }
fn borrow(v: &Vec<i32>) -> usize { v.len() }       // shared borrow, no move
fn borrow_mut(v: &mut Vec<i32>) { v.push(1); }      // exclusive borrow, can mutate

let data = vec![1, 2, 3];
let n = borrow(&data);      // data still owned by caller
consume(data);              // OWNERSHIP MOVES into consume
// println!("{:?}", data);  // COMPILE ERROR: use after move — affine types catch it
```

Rust makes call-by-move the *default* and enforces single ownership at compile time (affine typing). The very confusion that plagues call-by-sharing — "did I just give away mutation rights?" — is turned into a type error.

### Example 4: Faking Call-by-Reference Across Languages

```c
void out_param(int* result) { *result = 42; }   // C: pass &x, deref *p
```
```cpp
void out_param(int& result)  { result = 42; }    // C++: true reference
```
```csharp
void OutParam(out int result) { result = 42; }   // C#: 'out' must be assigned
void RefParam(ref int x)      { x += 1; }         // C#: 'ref' in/out
```
```go
func outParam(result *int) { *result = 42 }      // Go: pointer, like C
```
```python
# Python: no reference params at all — return, or pass a mutable container
def out_param(box): box[0] = 42                  # mutate a shared object
```

The pattern is universal: where the language lacks built-in reference passing, you **pass a pointer/box by value and mutate through it**. Pointers are how every "by reference" effect is reconstructed on top of call-by-value.

### Example 5: The Performance Triangle

```text
Pass a 1MB struct...

call-by-value:   memcpy 1MB on every call            ← time ∝ size
const-reference: copy one 8-byte pointer, indirect   ← O(1) + cache misses on deref
call-by-move:    copy one handle, null the source    ← O(1), no aliasing
call-by-name:    allocate a thunk, re-run each use   ← alloc + N× the arg's cost
call-by-need:    allocate a thunk, run once, memo    ← alloc + 1× the arg's cost
```

---

## Coding Patterns

**Pattern: Take by value, then move (the "sink" idiom).** In C++ a constructor that stores a parameter should take it by value and `std::move` it in — one overload handles both lvalues (copy) and rvalues (move) optimally.

```cpp
struct Widget {
    std::string name_;
    explicit Widget(std::string name) : name_(std::move(name)) {}  // copy-or-move, then steal
};
```

**Pattern: Consume `self` to express a one-shot transform (Rust builders).**

```rust
impl Builder {
    fn with_timeout(mut self, t: Duration) -> Self { self.timeout = t; self }  // moves self through
}
```

**Pattern: `const T&` for read, `T&&`/`&mut` for transfer, `T` for small.** A simple decision rule that captures 90% of API choices.

**Pattern: Thunk to defer, memoize to need.** Reuse the middle page's lazy wrapper when an argument is expensive and conditionally used.

---

## Best Practices

1. **Choose the cell deliberately.** For each parameter, decide: copy (value), borrow-read (const-ref/`&`), borrow-write (ref/`&mut`), take ownership (move), or defer (thunk). Don't default to "whatever the language makes easy."
2. **Prefer move over copy for resource-owning sinks**, and prefer `const&`/`&` for large read-only inputs.
3. **In C++, never read a moved-from object** beyond reassigning or destroying it. Treat `std::move(x)` as "x is dead now."
4. **Lean on Rust's borrow checker** rather than fighting it; it encodes the aliasing-vs-ownership distinction you'd otherwise track by hand.
5. **In lazy languages, force strict accumulators** and profile thunk buildup; let strictness analysis do the rest.
6. **Reason about termination via reduction order** when debugging "hangs only when the arg is computed" — the discarded-but-evaluated argument is the classic culprit.

---

## Edge Cases & Pitfalls

**Pitfall 1: Use-after-move in C++.** `auto y = std::move(x); use(x);` compiles and "works" but `x` is in an unspecified state. Rust rejects this at compile time; C++ won't.

**Pitfall 2: Applicative-order divergence on an unused argument.** A strict language evaluating a discarded but diverging argument hangs — the lambda-calculus Ω example, in production.

**Pitfall 3: Move that's secretly a copy.** A type without a move constructor (or with members that don't move) falls back to copy. `std::move` *requests* a move; it doesn't *guarantee* one.

**Pitfall 4: Self-move / move-assign aliasing.** `v = std::move(v)` or moving an element of a container into the same container can corrupt state if move-assignment isn't self-safe.

**Pitfall 5: Strictness analysis can't help across an effectful boundary.** If forcing an argument has side effects, the compiler can't reorder/eager it freely; laziness's observable semantics are preserved at the cost of the optimization.

**Pitfall 6: `const T&` dangling on a temporary.** Binding a const-reference parameter to a temporary is fine *during* the call, but storing that reference outlives the temporary and dangles — a reference is not ownership.

---

## Tricky Points

**Why call-by-need ≠ call-by-name observationally (with effects).** Without side effects, name and need give identical *values* (Church-Rosser). *With* side effects or *with performance as the observable*, they differ: name re-runs effects/computation per use; need runs once. The pure theory says "same answer"; the engineering reality says "wildly different cost and effect count."

**Move is not in the classic lambda-calculus taxonomy — and that's the point.** The lambda calculus has no notion of a resource that can be transferred and then unusable. Move semantics arises from **linear/affine typing** layered on call-by-value. It's an answer to a question (cheap, alias-free transfer of owned resources) the 1960s strategies never asked.

**`std::move` does not move.** It's a `static_cast<T&&>` — a *compile-time* relabeling that makes overload resolution pick the move constructor/assignment. The actual stealing is in those special members. Beginners think `std::move` "does" the move; it only *permits* one.

**RVO/NRVO can beat both copy and move.** Return-value optimization constructs the result directly in the caller's slot, so a returned local often costs *nothing* — no copy *and* no move. Prefer returning by value and letting the compiler elide.

**Out-parameters are a poor substitute for multiple return values.** Languages with tuples/destructuring (Go, Rust, Python) should return rather than mutate `out` params; the `ref`/`out` machinery is a workaround for languages that historically lacked cheap multiple returns.

---

## Apply it

1. State the system invariant that **Evaluation Strategies (call-by-x)** must protect.
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

- Which invariant must remain true when Evaluation Strategies (call-by-x) fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
