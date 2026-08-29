# Method Dispatch & Inline Caches — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Method Dispatch & Inline Caches** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Polymorphic Inline Cache (PIC)

When a second shape arrives at a monomorphic site, the runtime upgrades the IC to a **polymorphic inline cache**: a short, ordered list of guards.

```text
PIC at call site `obj.foo()`:
   if shape == Map_A:  call target_A
   elif shape == Map_B: call target_B
   elif shape == Map_C: call target_C
   else:                miss -> resolve, maybe append, or go megamorphic
```

The PIC is still far faster than a generic lookup: each entry is a compare-and-branch, and a hit short-circuits the rest. Crucially, the entries are typically tried **in order of how recently/frequently they were seen**, so a 90/10 type split still hits on the first compare most of the time. A PIC with 2–4 entries is a perfectly healthy state for genuinely polymorphic code (think: an AST visitor that sees a handful of node types). The performance falls off when the *number* of distinct shapes outgrows the cache.

### 2. Megamorphic: The Cliff

Most engines cap the PIC at a small size (V8's classic limit is 4; details vary by engine and IC kind). When a site exceeds it, the engine declares the site **megamorphic** and stops trying to cache per-site. Now every call does a **generic lookup**: V8 consults a global megamorphic stub backed by a hash table keyed by shape; the JVM falls back to the vtable/itable; SpiderMonkey switches to a generic IC stub. This is slower for three compounding reasons:

1. **The lookup itself is longer** — a hash probe or table walk instead of one compare-and-branch.
2. **The call is now an unpredictable indirect branch** — the target genuinely varies, so the CPU mispredicts (see §6).
3. **The optimizer can't devirtualize or inline** a megamorphic call — there's no single target to bet on, so the body stays out-of-line and downstream optimizations (constant propagation across the call, escape analysis) are blocked.

That third point is the killer. A megamorphic call isn't just a slow call; it's an **optimization barrier**. The lost inlining often dwarfs the lookup cost.

### 3. Hidden Classes / Shapes as the Bet's Currency

Every guard and every cache entry is keyed on a hidden class / shape pointer (covered in topic 01 in prose). The senior insight: **shapes are the unit the whole speculation economy trades in.** Two objects that you think are "the same" but that the runtime gave different shapes (because fields were added in a different order, or one got a deleted property, or one was created via a different path) will appear as *two types* at a call site — silently doubling the PIC's entry count. A megamorphic site is frequently not "the code is genuinely polymorphic" but "the code accidentally manufactures many shapes for what is logically one type." Keeping shape count low is therefore as important as keeping the number of *logical* types low.

### 4. Devirtualization via CHA

In a closed-world or partially-closed setting, the compiler can sometimes *prove* a virtual call has exactly one target. **Class Hierarchy Analysis** scans the loaded classes: if `Animal.speak()` is called but only `Dog extends Animal` exists and `Dog` doesn't override... or if `Dog` is the *only* subclass that overrides and the receiver is provably `Dog`... then the call has a unique target and can be compiled as a *direct* call. The JVM does exactly this: if CHA finds a single implementor of a method at JIT time, it emits a direct (and inlinable) call.

The subtlety: the JVM is an *open* world — a new class can be loaded later that adds an override, invalidating the CHA conclusion. So CHA-based devirtualization is paired with a **dependency**: if a class is later loaded that breaks the assumption, the JIT *deoptimizes* the affected compiled methods. CHA is thus "prove it under the current world, and tear it down if the world changes." `final` and `sealed` make CHA's job trivial and its conclusions permanent.

### 5. Speculative Devirtualization and Guarded Inlining

When the world is genuinely open and CHA can't prove uniqueness, the JIT falls back to **speculation**: the profile says this call site is 98% `Dog`, so emit

```text
   if (receiver.klass == Dog) {
       <inlined body of Dog::speak>      // direct, inlined, fully optimizable
   } else {
       <generic virtual call>            // or: deoptimize
   }
```

This is **guarded inlining**. The common path is a guard plus inlined code — as fast as static dispatch and open to all downstream optimization. The cold path handles the rare other types. If the site is monomorphic enough, the JIT may even omit the generic fallback and **deoptimize** on guard failure, betting the other types essentially never occur. For a 2- or 3-type site, the JIT can emit a small "polymorphic inlining" structure — a couple of guarded inlined bodies plus a fallback. Beyond that, it's not worth it, and the call stays a real virtual call. This is the JIT-level mirror of the interpreter's PIC.

### 6. The Branch Predictor Interaction

A virtual/interface/megamorphic call compiles to an **indirect branch** — the target sits in a register or memory. The CPU's **BTB (Branch Target Buffer)** predicts the target from history so the pipeline can keep fetching past the call without stalling. For a *monomorphic* indirect call, the target is always the same, the BTB predicts it perfectly, and the indirect call costs almost nothing beyond the loads. For a *megamorphic* call, the target genuinely varies, the BTB's prediction is frequently wrong, and each misprediction flushes the pipeline — on the order of 15-20 cycles on a modern out-of-order core. So the cost of a polymorphic call site is not merely the lookup; it's the **mispredicted indirect branch** on top of it.

This is the hardware reason the source-level advice ("keep call sites monomorphic") pays off twice: monomorphic sites devirtualize and inline (no indirect branch at all), and even when they don't, a single-target indirect call is BTB-friendly. Megamorphic sites lose both.

### 7. Property Access Rides the Same Machinery

Everything above applies to **property/field access**, not just method calls. `point.x` is, in V8/SpiderMonkey, an inline-cached operation: monomorphic load from a fixed offset, polymorphic small set, megamorphic dictionary lookup. The same monomorphic-to-megamorphic slide degrades a hot field read exactly as it degrades a hot method call. In dynamic-language profiling, "this property access went megamorphic" is as common a finding as "this call went megamorphic," and the fix is the same: stabilize shapes.

### 8. The Whole Chain, End to End

The senior synthesis: **type stability at the source → fewer shapes at the call site → monomorphic IC → CHA/speculative devirtualization → guarded (or unguarded) inlining → constant folding/escape analysis across the call → a BTB-friendly or branch-free hot path.** Break the chain at the top (many types/shapes), and you lose every link below it. This is why "make the collection homogeneous" or "construct objects consistently" can yield order-of-magnitude speedups that look out of proportion to the change — you didn't just speed up a lookup, you re-enabled the entire optimization cascade.

---

## Code Examples

### Forcing a Site Through Mono → Poly → Mega (JavaScript)

```javascript
function dispatch(o) { return o.kind(); }   // one call site

class A { kind() { return 'A'; } }
class B { kind() { return 'B'; } }
class C { kind() { return 'C'; } }
class D { kind() { return 'D'; } }
class E { kind() { return 'E'; } }

// MONOMORPHIC: only A
for (let i = 0; i < 1e6; i++) dispatch(new A());

// POLYMORPHIC: A and B (and a couple more) — small PIC, still fast
const few = [new A(), new B()];
for (let i = 0; i < 1e6; i++) dispatch(few[i & 1]);

// MEGAMORPHIC: 5+ distinct shapes through one site — PIC overflows
const many = [new A(), new B(), new C(), new D(), new E()];
for (let i = 0; i < 1e6; i++) dispatch(many[i % 5]);
```

Run with `node --trace-ic` (or in d8) and you'll see the IC state for the `o.kind()` site transition `0 -> 1 (MONO) -> P (POLY) -> N (MEGA)`. The third loop is dramatically slower despite doing "the same amount of work" — that's the cliff.

### CHA Devirtualization in the JVM (conceptual)

```java
abstract class Shape { abstract double area(); }
final class Circle extends Shape {           // 'final' helps CHA enormously
    final double r;
    Circle(double r) { this.r = r; }
    double area() { return Math.PI * r * r; }
}

double totalArea(Shape[] shapes) {
    double sum = 0;
    for (Shape s : shapes) sum += s.area();   // virtual call...
    return sum;
}
```

If, at JIT time, `Circle` is the only concrete subclass of `Shape` that the classloader has loaded, HotSpot's CHA concludes `s.area()` has a single target, devirtualizes it, and inlines `Math.PI * r * r` directly into the loop — turning a virtual call into branch-free arithmetic. The JIT records a CHA dependency; if a second `Shape` subclass is later loaded, `totalArea` is deoptimized and recompiled. `final` on `Circle` makes the analysis trivial and the conclusion robust.

### Speculative Guarded Inlining (pseudo-IR)

```text
; profile says s.area() is 97% Circle at this site
loop:
    klass = load s.klass
    cmp   klass, Circle_klass
    jne   slow
fast:                                  ; GUARDED INLINE of Circle::area
    r     = load s.r
    area  = PI * r * r
    jmp   merge
slow:
    area  = virtual_call s.area()      ; or: deoptimize
merge:
    sum  += area
```

The guarded `Circle` path is straight-line, inlinable arithmetic with one well-predicted branch (the guard almost always falls through). The `slow` path catches the rare non-`Circle`. This is what "devirtualize + inline" physically produces.

### Stabilizing Shapes to Stay Monomorphic (JavaScript)

```javascript
// BAD: fields added in different orders -> different hidden classes -> polymorphic
function makeBad(a, b) {
  const o = {};
  if (a > 0) { o.a = a; o.b = b; }   // shape #1: {a, b}
  else       { o.b = b; o.a = a; }   // shape #2: {b, a}  (DIFFERENT Map!)
  return o;
}

// GOOD: same fields, same order, every time -> one hidden class -> monomorphic
function makeGood(a, b) {
  return { a, b };                   // always shape {a, b}
}
```

`makeBad` manufactures two shapes for what is logically one type; any hot site consuming its output starts polymorphic for no semantic reason. `makeGood` keeps shape count at one. This is the most common real-world cause of accidental polymorphism.

### Go: Avoiding Megamorphic Interface Sites in a Hot Loop

```go
// If a hot loop dispatches through io.Writer over MANY concrete writer types,
// the call site is effectively megamorphic: the indirect call target varies,
// the BTB mispredicts, and the call can't be inlined.

// When the concrete type is known and hot, prefer the concrete call:
func copyFile(dst *os.File, src *os.File) { /* dst.Write is a direct call */ }

// vs the general (sometimes necessary) interface path:
func copyAny(dst io.Writer, src io.Reader) { /* dst.Write is indirect */ }
```

The interface version is the right API; the concrete version is the right hot-path implementation when you have the type. Specializing the hot path is a legitimate, measured optimization — Go's compiler also does some devirtualization of interface calls when it can prove the concrete type.

---

## Coding Patterns

### Pattern 1: Split a megamorphic site into several monomorphic ones

```javascript
// Instead of one site seeing all node types:
function visit(node) { return node.accept(visitor); }   // megamorphic

// Dispatch by kind ONCE, then call type-specialized functions whose
// internal call sites each see one type:
function visit(node) {
  switch (node.type) {
    case 'num': return visitNum(node);   // visitNum's sites are monomorphic
    case 'add': return visitAdd(node);
    // ...
  }
}
```

Moving the polymorphism to a single `switch` and keeping the downstream call sites type-specialized often beats relying on one hot megamorphic site.

### Pattern 2: Make uniqueness provable (`final`/`sealed`)

Mark leaf classes `final` and hierarchies `sealed` so CHA can devirtualize permanently without deopt dependencies. This is a free, intent-revealing speedup for any genuinely-not-overridden method.

### Pattern 3: Construct objects on one shape path

Initialize all fields in a fixed order in the constructor; avoid conditionally adding fields, deleting properties, or mutating object shape after construction. One construction path → one hidden class → monomorphic consumers.

### Pattern 4: Specialize the hot path, keep the general API

Offer the polymorphic/interface API for flexibility, but provide (or let the compiler generate) a concrete-type fast path for the measured hot loop. Don't degrade the whole API for one loop; specialize the loop.

---

## Best Practices

- **Profile IC/inlining state, don't guess.** Use `node --trace-ic`/`--trace-opt`, `-XX:+PrintInlining`/`-XX:+PrintCompilation`, or `perf` for indirect-branch mispredicts. The runtime can tell you exactly which sites went mega.
- **Treat megamorphic hot sites as bugs, not facts of life.** Most are accidental (fragmented shapes, an over-general container), not essential polymorphism.
- **Keep shape count == logical type count.** Accidental shape fragmentation is the stealthiest cause of polymorphism; consistent construction fixes it.
- **Prefer `final`/`sealed`/concrete types on hot paths.** They turn speculation into proof and remove guards entirely.
- **Don't over-speculate.** Forcing a genuinely polymorphic site to mis-speculate causes deopt storms; let it be a healthy PIC instead.
- **Measure the inlining loss, not just the call cost.** The real damage of a megamorphic call is the optimizations it blocks downstream.

---

## Edge Cases & Pitfalls

- **One rare type can wreck a hot site.** A 99.9%-`Dog` site that occasionally sees a `Cat` may still inline `Dog` with a guard — but a site that drifts to 5+ types tips megamorphic and loses everything. The transition is a step function, not gradual.
- **Accidental shape fragmentation looks monomorphic in source.** Two `{x, y}` objects built by different code paths can have different Maps; the call site is polymorphic even though "it's all just points." Hard to spot without shape-level tooling.
- **`delete obj.prop` (JS) demotes objects to dictionary mode**, giving them a slow, non-cacheable shape and forcing nearby ICs to mega. Avoid `delete` on hot objects; set to `undefined` or design the field out.
- **Deopt storms from bad speculation.** If the JIT speculates on a type that flips frequently, every flip deoptimizes and recompiles — pathologically slow. Symptom: high recompilation counts. Fix: make the site honestly polymorphic.
- **CHA conclusions are revoked by class loading.** A plugin/classloader that introduces a new override at runtime can deoptimize hot code mid-run, causing a latency spike. Relevant for app servers and dynamic plugin systems.
- **Branch-predictor state is finite and shared.** Even a monomorphic indirect call can mispredict if BTB entries are evicted by surrounding code with many indirect branches. Locality of hot indirect calls matters.
- **Megamorphic property access is as costly as megamorphic calls.** Don't only audit method calls; a hot `obj[dynamicKey]` or a property read over many shapes degrades identically.

---

## Apply it

1. State the system invariant that **Method Dispatch & Inline Caches** must protect.
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

- Which invariant must remain true when Method Dispatch & Inline Caches fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
