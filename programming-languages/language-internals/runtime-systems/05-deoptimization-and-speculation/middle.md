# Deoptimization & Speculation — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Deoptimization & Speculation** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The hard problem: rewinding from native code to virtual state

An optimizing compiler is free to:

- keep a Java/JS local variable entirely in a CPU register, never writing it to memory,
- compute a value early and reuse it,
- eliminate a variable that's provably unused,
- reorder operations,
- inline three or four method bodies into one flat native function,
- delete an object and keep only its fields in registers (scalar replacement — covered in `senior.md`).

All of that makes the optimized frame **unrecognizable** compared to the tidy bytecode model where every local has a numbered slot and the operand stack is explicit. Yet when a guard fails, the runtime must resume in the interpreter, which *only* understands that tidy bytecode model. So the compiler must leave behind, at every deopt point, enough information to **translate** the messy physical reality back into the clean virtual model.

### 2. Deopt points and what they record

A **deopt point** is any place the compiler emitted a guard or otherwise produced code that's only valid under a speculation. At each one, the compiler records metadata answering: *if we have to bail out here, where does every live value go in the reconstructed interpreter frame(s)?*

In HotSpot this metadata is the **scope descriptor** (one per inlined method scope at that point) plus the **OopMap** (which slots hold GC-visible references). Conceptually it's a table:

```text
At deopt point P (bci = 23 in method foo, inlined into bar at bci = 7):
  scope foo:
    local[0] -> RSI            (in a register)
    local[1] -> [RSP+16]       (spilled to stack)
    local[2] -> constant 0     (compiler proved it constant)
    stack[0] -> RAX
  scope bar (caller):
    local[0] -> [RSP+40]
    ...
```

In V8 the equivalent is the **translation array** in the deopt data: a compact instruction stream that the deoptimizer "interprets" to materialize each frame. Note the **inlining** wrinkle: if the optimized code inlined `foo` into `bar`, then a deopt inside the inlined `foo` must reconstruct **two** interpreter frames — one for `foo`, one for `bar` — out of the **single** optimized frame. The metadata describes the whole inlined scope chain.

### 3. The frame-reconstruction algorithm

When an eager deopt fires, the deoptimizer roughly:

1. **Captures** the current optimized frame: register contents and stack slots at the deopt point.
2. **Reads** the deopt metadata for this exact PC (program counter).
3. **Allocates** one new interpreter/baseline frame *per inlined scope* (so an N-deep inline expands into N frames).
4. **Fills** each frame's locals and operand stack by copying values from wherever the metadata says they physically live (register, stack slot, or an inlined constant).
5. **Sets** each frame's bytecode index (`bci` / bytecode offset) to the resume point.
6. **Replaces** the single optimized frame on the stack with the stack of reconstructed frames.
7. **Resumes** execution in the interpreter at the innermost reconstructed frame.

The cost is roughly proportional to inline depth and number of live values — usually microseconds. Cheap once; expensive in a loop.

### 4. Eager vs lazy deopt

**Eager deopt** is what we've described: a guard fails *right now*, on the running thread, and we reconstruct and resume immediately. It's local to the failing frame.

**Lazy deopt** handles a different situation: the runtime decides that some already-compiled code is *no longer valid* — but that code might be **running on the stack right now**, possibly on other threads, possibly several frames deep. You can't safely reach into another thread's mid-execution native frame and rewrite it from outside. So instead the runtime marks the compiled method **not entrant**: no *new* calls will use it, and each currently-active frame of it is patched so that **when control returns to it**, it deopts then. The invalidation is *scheduled* rather than *immediate*.

```text
EAGER:  guard fails  -> deopt this frame immediately, resume in interpreter.
LAZY:   runtime invalidates code -> mark "not entrant" -> existing frames
        deopt when reached -> new calls go to interpreter/recompile.
```

### 5. Class loading can invalidate running code (CHA)

This is the canonical lazy-deopt trigger on the JVM. Suppose at compile time HotSpot ran **Class Hierarchy Analysis** and found that `PaymentProcessor.process()` had **no overriding subclass** anywhere loaded. It then *speculatively devirtualized and inlined* `process()` into the caller — a big win — guarded only by the assumption "no override exists." This is recorded as a **dependency** on the class hierarchy.

Later, your app dynamically loads a plugin defining `class FraudProcessor extends PaymentProcessor { override process() {...} }`. The assumption is now **false**. HotSpot's class loader checks registered dependencies, finds the optimized code that bet on "no override," and **invalidates** it (lazy deopt: mark not entrant, deopt active frames on return). The next call recompiles, this time with a proper virtual dispatch or a polymorphic guard. The semantics were always correct; the runtime just had to give up the speculation the instant a new class made it untrue.

### 6. The optimizations this machinery unlocks

The whole deopt apparatus exists to make these *safe*:

- **Monomorphic inlining.** A call site that has only ever resolved to one target gets inlined directly, with a guard: *"is the receiver still the type I inlined for?"* Fail → deopt. Inlining is the single most valuable optimization because it exposes further optimizations across the call boundary.
- **Type specialization.** `a + b` is compiled as an integer add (or a string concat, or a double add) based on observed types, with type guards. Other types → deopt. This is what makes dynamic-language arithmetic fast.
- **Branch pruning (uncommon branches).** Profiling shows a branch (e.g. an error path, a rare slow case) is never taken. The compiler **omits compiling it** and puts an **uncommon trap** at its entry. If that branch is ever taken, the trap deopts and the interpreter handles it. You pay zero code-size/optimization cost for cold paths.

Every one of these is a *bet recorded as a deopt point with reconstruction metadata.*

---

## Code Examples

### Example 1: Forcing and reading a HotSpot deopt with scope info

```java
// Devirt.java
class Animal { String sound() { return "?"; } }
class Dog extends Animal { String sound() { return "woof"; } }

public class Devirt {
    static String speak(Animal a) {   // hot; HotSpot may speculate the target
        return a.sound();
    }
    public static void main(String[] args) throws Exception {
        Animal a = new Dog();
        long acc = 0;
        // Warm up: only Dog seen -> CHA may devirtualize/inline Dog.sound().
        for (int i = 0; i < 1_000_000; i++) acc += speak(a).length();

        // Introduce a new type AFTER warm-up to provoke deopt/invalidation.
        Animal b = new Animal() { String sound() { return "meow"; } };
        for (int i = 0; i < 1_000_000; i++) acc += speak(b).length();

        System.out.println(acc);
    }
}
```

Run with:

```bash
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintCompilation \
     -XX:+TraceDeoptimization Devirt
```

In the trace you'll see `speak` compiled, then deoptimization activity when the second, unseen receiver type shows up — the monomorphic-inlining bet on "always `Dog`" no longer holds, and the call site is recompiled as polymorphic.

### Example 2: Reading a V8 translation/bailout reason

```js
// specialize.js
function pick(o) {
  return o.value;     // V8 speculates on o's hidden class (shape)
}

const a = { value: 1 };          // shape S1
for (let i = 0; i < 1_000_000; i++) pick(a);   // monomorphic on S1

const b = { name: 'x', value: 2 };  // DIFFERENT shape S2 (extra field first)
console.log(pick(b));               // shape guard fails -> deopt
```

```bash
node --trace-deopt --trace-opt specialize.js
```

You'll see `pick` optimized, then a deopt with a reason like `wrong map` (the *map* is V8's hidden class). The optimized `pick` had a **map guard**; feeding a different shape failed it, and V8 rebuilt the interpreter frame from the translation data and resumed.

### Example 3: Branch pruning made visible

```js
// prune.js
function f(x) {
  if (x < 0) {
    // Cold path: never taken during warm-up.
    return slowPath(x);
  }
  return x * 2;          // hot path: only this is exercised at first
}
function slowPath(x) { return -x * 3; }

for (let i = 0; i < 1_000_000; i++) f(i);   // x >= 0 always

// Now take the pruned branch ONCE.
console.log(f(-5));      // entering the cold branch -> deopt
```

With `--trace-deopt` you'll observe a deopt when `f(-5)` first drives execution into the branch the compiler had treated as never-taken. The cold branch wasn't fully optimized; entering it triggered the trap, and execution fell back to handle it correctly (`f(-5)` returns `15`).

### Example 4: Inlining means one frame becomes two on deopt (conceptual)

```js
function inner(o) { return o.x; }       // will be inlined into outer
function outer(o) { return inner(o) + 1; }

// After warm-up, V8 inlines inner() into outer(): ONE optimized frame.
// If a shape guard inside the inlined inner() fails, the deoptimizer must
// reconstruct TWO interpreter frames (inner + outer) from that one frame,
// using the translation data that records both inlined scopes.
```

You can't "see" the two frames in a one-line trace, but `--trace-deopt`'s output references the inlining position, and a stack trace captured at the deopt resume point will show both `inner` and `outer` — proof the single physical frame was decompressed into two virtual ones.

---

## Coding Patterns

### Pattern 1: Keep call sites monomorphic to preserve inlining

```js
// ❌ Polymorphic call site: handler could be many shapes -> can't inline well.
function dispatch(handler, ev) { return handler.handle(ev); }

// ✅ If a site is hot, drive it with one concrete type so it stays
//    monomorphic and inlinable. Specialize separate sites for separate types.
```

### Pattern 2: Stabilize shapes before the loop, not inside it

```js
// ❌ Shape changes inside the hot loop -> repeated map-guard deopts.
function build(n) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const o = {};            // empty shape...
    o.i = i;                 // ...mutated each iteration
    out.push(o);
  }
  return out;
}

// ✅ Construct with the final shape so every object shares one map.
function buildFast(n) {
  const out = new Array(n);
  for (let i = 0; i < n; i++) out[i] = { i };   // one stable shape
  return out;
}
```

### Pattern 3: Route the rare case out of the hot function (keep branches prunable)

```js
// ✅ The hot function stays narrow; the rare/cold path lives elsewhere so the
//    optimizer can prune it and trap on entry instead of compiling it inline.
function handle(req) {
  if (req == null) return handleNull(req);   // cold, separate
  return fastHandle(req);                     // hot, monomorphic
}
```

### Pattern 4 (JVM): avoid surprise overrides of hot virtual methods

```java
// If a hot path calls a virtual method that CHA can prove monomorphic,
// it gets devirtualized/inlined. Loading a subclass that overrides it later
// forces invalidation. Mark methods final (or keep classes effectively
// final) when you know they won't be overridden, to make the speculation
// permanent rather than provisional.
```

---

## Best Practices

- **Treat warm-up deopts as normal; treat steady-state deopts as bugs.** The signal is *repetition on the same site*, not the mere presence of deopt lines.
- **Read the reason string.** `not a Smi`, `wrong map`, `not entrant`, `unstable map`, `insufficient type feedback` each point at a different broken assumption.
- **Keep inline-critical sites monomorphic.** Inlining is the optimization you most want to protect; polymorphism is its enemy.
- **Stabilize object shape at construction.** One construction path → one hidden class → stable map guards.
- **On the JVM, make intentionally-non-overridable methods `final`.** It turns a provisional CHA bet into a permanent fact, removing an invalidation risk.
- **Don't fight branch pruning.** Letting cold paths be cold (and separate) is *good*; it keeps the hot path lean. Don't merge rare error handling into hot loops.

---

## Edge Cases & Pitfalls

### Pitfall 1: Confusing eager and lazy deopt symptoms

A type guard failing is *eager* and local — you'll see it pinned to a specific site and value. A `made not entrant` after a class load is *lazy* and structural — the code wasn't wrong, the world changed. Misdiagnosing one as the other sends you fixing the wrong thing.

### Pitfall 2: Inlining hides the real deopt site

A deopt reason may point at a method that *got inlined into* the one you were profiling. The failing guard lives in the inlined callee, not the caller you were staring at. Always check whether inlining is in play.

### Pitfall 3: "It deopted once, so my code is broken"

A single deopt as the engine learns a new type is expected and cheap. Re-optimization usually folds the new type into a polymorphic version that then runs fast. Only sustained, repeated deopts indicate a real problem.

### Pitfall 4: Assuming devirtualization is permanent

CHA-based devirtualization is *provisional* — valid only until a class that breaks it loads. Dynamic class loading, plugin systems, and some frameworks (proxies, bytecode generation) can invalidate it at runtime. If a hot method must stay devirtualized, make it non-overridable.

### Pitfall 5: Forgetting the GC interaction

Deopt metadata also tells the GC which optimized-frame slots hold object references (OopMaps). This is why values can't be laid out *completely* arbitrarily — the compiler must always be able to describe, at every safepoint/deopt point, where the live references are. It's a constraint that quietly bounds optimization.

### Pitfall 6: Long-running frames delaying lazy deopt

If a method marked *not entrant* is sitting in a very long loop, it keeps running its now-invalid (but still semantically correct) compiled code until the loop exits or an OSR/safepoint lets the runtime intervene. Long loops can therefore delay the benefit of invalidation.

---

## Apply it

1. Find a real component where **Deoptimization & Speculation** affects an interface or dependency.
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

- Which boundary is most affected by Deoptimization & Speculation?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
