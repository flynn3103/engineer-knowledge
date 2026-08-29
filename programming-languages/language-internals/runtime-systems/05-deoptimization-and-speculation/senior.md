# Deoptimization & Speculation — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Deoptimization & Speculation** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Escape analysis deletes objects — deopt must un-delete them

Consider, on the JVM:

```java
int dist2(Point a, Point b) {
    Vector v = new Vector(a.x - b.x, a.y - b.y);  // never escapes dist2
    return v.dx * v.dx + v.dy * v.dy;
}
```

Escape analysis proves `v` never leaves `dist2`. Scalar replacement **removes the allocation**: `v.dx` and `v.dy` become two register values, no `Vector` object is created, GC pressure drops, and the method is pure arithmetic. Excellent.

Now suppose `dist2` was inlined into a caller, and somewhere in that optimized region there's a **deopt point** whose reconstructed interpreter state references `v` as a live object (because in the un-optimized bytecode, `v` *is* a real object on the stack). When that deopt fires, the interpreter cannot be handed "two loose registers" — it needs an actual `Vector` reference. So the deoptimizer **materializes** `v`: it allocates a fresh `Vector` on the heap and writes the current register values into `dx` and `dy`, producing a reference that's indistinguishable from one the program would have created normally.

The deopt metadata therefore records not just "where values live" but also **"this scope held a scalar-replaced object of class `Vector` with fields {dx ← R8, dy ← R9} — reify it if you deopt here."** Reification is the most subtle reconstruction case: an object that *never existed at runtime* is conjured into existence precisely so the interpreter's worldview stays consistent. Semantics preserved, as always — the program behaves exactly as if the object had been there the whole time.

### 2. Safepoints make deopt (and GC) safe

The runtime cannot rewrite a thread's frames, move its objects, or reconstruct its state at an *arbitrary* machine instruction — it might be halfway through a multi-instruction sequence with values in transient registers and no recorded mapping. It can only do these things at **safepoints**: locations where the compiler guarantees a complete, accurate description of all live values and references exists.

Deopt points are placed at (or are kinds of) safepoints. This is why:

- **Eager deopt** can reconstruct: the guard sits at a point with full metadata.
- **Lazy deopt** works: when a *not entrant* frame returns (a safepoint), the runtime can correctly intervene.
- **GC and deopt share infrastructure:** both need "where is every live reference right now," recorded as OopMaps at safepoints. (This is also why escape-analysis materialization must know the class and fields — it's recorded alongside the safepoint metadata.)

A consequence: aggressive optimization is *bounded* by the requirement to keep a describable state at every safepoint. The compiler can't optimize so hard that it loses the ability to answer "where is everything" at a deopt/GC point.

### 3. On-stack invalidation across threads

When the runtime invalidates compiled code (CHA broken, a deopt-all on debugger attach, a profiling decision), that code may be executing on **many threads simultaneously**, at different depths. The protocol:

1. Mark the compiled method **not entrant** — atomically, so no new activation starts using it.
2. Patch the method's entry / return handling so any **currently active** frame will deopt **when it next reaches a safepoint** (typically on return, or at a loop back-edge safepoint).
3. Optionally request a **safepoint** (stop-the-world-ish) to expedite patching active frames' return addresses to the deopt handler.
4. Each thread, on hitting its safepoint, reconstructs its frame(s) and continues in the interpreter; the next call recompiles.

The key insight: you never reach into a *running* native frame on another thread from outside and mutate it mid-instruction. You **schedule** the deopt to occur when that thread is itself at a safe, describable point. This is why invalidation has latency and why long-running optimized loops (with back-edge safepoints) are important for responsiveness.

### 4. The overflow / range / packed-array speculations

These are the high-value, easy-to-break bets in dynamic numeric code:

- **No-overflow (SMI/int32) speculation.** V8 represents small integers as **SMIs** and HotSpot keeps ints in 32 bits. Arithmetic is compiled assuming the result stays in range. A guard checks for overflow; overflow deopts to a wider representation (double / boxed). A counter that finally exceeds the SMI range, or a multiply that overflows int32, deopts.
- **Packed-array / elements-kind speculation.** V8 tags each array with an **elements kind**. `[1,2,3]` is `PACKED_SMI_ELEMENTS` — extremely fast. Pushing a `3.14` transitions it to `PACKED_DOUBLE_ELEMENTS`; pushing an object transitions to `PACKED_ELEMENTS`; creating a hole transitions to a `HOLEY_*` kind. **These transitions are one-way and they deopt code specialized for the old kind.** Code that assumed `PACKED_SMI` must bail when the array becomes doubles or holey.
- **Bounds / range speculation.** A loop indexing an array can have its per-iteration bounds check hoisted or eliminated under a speculation that the index stays in range; an out-of-range access deopts to the checked form.
- **Null/undefined speculation.** If a field has only ever been non-null, the compiler may elide null checks and speculate non-null; a null deopts.

Each is a bet that the *value domain* stays narrow. Widening the domain (one overflow, one float in an int array, one hole, one null) pays a deopt and forces a more general recompile.

### 5. Inline caches and the mono → poly → mega slide

A call site (or property access) carries an **inline cache** recording observed receiver types/shapes:

```text
MONOMORPHIC:  one shape seen        -> fastest; inlinable; tight guard.
POLYMORPHIC:  2..N shapes seen      -> a small switch of guarded cases; still ok.
MEGAMORPHIC:  too many shapes       -> engine gives up specializing; generic
                                       dispatch; inlining lost; speculation
                                       largely abandoned at this site.
```

A site that slides to megamorphic loses inlining and most speculation — a frequent root cause of "this got slow and I don't know why." The transition is driven by *how many distinct shapes* flow through the site. Senior-level performance work is often about *keeping critical sites monomorphic or low-polymorphic* — by separating types, stabilizing shapes, or splitting a generic site into several specialized ones.

### 6. Loop-invariant hoisting and other "moved" computations

LICM hoists a computation out of a loop. If the hoist is only valid under a speculation (e.g. the hoisted load assumes the underlying object/field doesn't change shape), the loop carries a guard; a violation deopts back to the un-hoisted loop. The same pattern covers strength reduction, common-subexpression elimination across speculated invariants, and constant-folding of speculated constants. The mental rule: **any optimization that *moved* or *removed* a computation must leave behind a deopt route that restores the original computation if its enabling bet breaks.**

---

## Code Examples

### Example 1: Provoke and observe scalar-replacement + materialization (HotSpot)

```java
// Escape.java
public class Escape {
    static final class Vec { final int dx, dy; Vec(int a,int b){dx=a;dy=b;} }

    static int dist2(int ax,int ay,int bx,int by){
        Vec v = new Vec(ax-bx, ay-by);   // candidate for scalar replacement
        return v.dx*v.dx + v.dy*v.dy;
    }
    public static void main(String[] a){
        long acc=0;
        for(int i=0;i<2_000_000;i++) acc+=dist2(i,i+1,i-1,i);
        System.out.println(acc);
    }
}
```

Inspect with:

```bash
# Confirm EA eliminated the allocation; watch for deopts if any guard breaks.
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintEscapeAnalysis \
     -XX:+PrintEliminateAllocations -XX:+PrintCompilation Escape
```

`PrintEliminateAllocations` reports the `Vec` allocation removed. If you then introduce a path that makes `v` escape (e.g. store it in a static field under some branch), you'll see the elimination disappear — and any deopt in a version that *had* eliminated it would materialize the `Vec`.

### Example 2: SMI overflow deopt in V8

```js
// overflow.js
function acc(start) {
  let s = start;
  for (let i = 0; i < 50; i++) s = s * 31;   // grows fast; leaves SMI range
  return s;
}
for (let i = 0; i < 100000; i++) acc(1);   // optimized assuming SMI math
console.log(acc(1));                        // result far exceeds SMI -> deopt path
```

```bash
node --trace-deopt overflow.js
```

You'll see deopts with overflow-related reasons as the multiply leaves the small-integer range and V8 must widen to doubles — exactly the no-overflow bet breaking.

### Example 3: Elements-kind transition deopt

```js
// elements.js
function sum(arr) {
  let s = 0;
  for (let i = 0; i < arr.length; i++) s += arr[i];
  return s;
}

const a = [1, 2, 3, 4];        // PACKED_SMI_ELEMENTS -> fastest
for (let i = 0; i < 1_000_000; i++) sum(a);   // optimized for PACKED_SMI

a.push(3.14);                   // transition to PACKED_DOUBLE_ELEMENTS
console.log(sum(a));            // code specialized for SMI must deopt
```

`node --trace-deopt elements.js` shows the deopt when the array's elements kind changes under the optimized `sum`. The fix: keep the array homogeneous, or accept the double representation from the start (`[1.0, 2.0, ...]`).

### Example 4: Watch a call site slide to megamorphic

```js
// mega.js
function field(o) { return o.v; }   // property access -> inline cache here

function shape(extra) {
  const o = { v: 1 };
  // Give each call a structurally different object to blow up the IC.
  for (let k = 0; k < extra; k++) o['k' + k] = k;
  return o;
}

// Feed MANY distinct shapes through the same access site.
for (let n = 0; n < 30; n++) {
  const o = shape(n);
  for (let i = 0; i < 100000; i++) field(o);
}
```

With `--trace-ic` (in a debug build) or by profiling, you can observe `field`'s inline cache moving monomorphic → polymorphic → megamorphic as the shape count climbs, at which point specialization and inlining are abandoned. Keeping `field` fed with one shape keeps it monomorphic and fast.

### Example 5: Disable an optimization to confirm causation

```bash
# Confirm a slowdown is escape-analysis/deopt-related by toggling EA off.
java -XX:-DoEscapeAnalysis YourApp        # does the regression change?

# In V8, narrow down by allow-listing / observing a single function:
node --trace-deopt --trace-opt --print-opt-source app.js
```

Toggling an optimization is a legitimate *diagnostic* (not a fix): if behavior changes, you've localized the speculation involved.

---

## Coding Patterns

### Pattern 1: Keep allocations non-escaping so EA can delete them

```java
// ✅ Local, non-escaping temporary -> scalar replaced, no heap object.
double norm(double x, double y) {
    Complex c = new Complex(x, y);   // never stored, returned, or thrown
    return Math.hypot(c.re, c.im);
}
// ❌ Storing it anywhere global, returning it, or passing to a non-inlined
//    method that lets it escape defeats EA and forces a real allocation.
```

### Pattern 2: Choose one numeric domain for a hot loop

```js
// ✅ Stay in SMI range, integers only -> packed-SMI arrays, int32 math.
function histogram(samples) {        // samples: all small integers
  const bins = new Int32Array(256);  // typed array: fixed, packed, no deopt
  for (let i = 0; i < samples.length; i++) bins[samples[i] & 255]++;
  return bins;
}
// Typed arrays sidestep elements-kind transitions entirely.
```

### Pattern 3: Pre-size and densely fill arrays (avoid holey + reallocation)

```js
// ✅ Packed from the start; never holey.
const out = new Array(n);
for (let i = 0; i < n; i++) out[i] = compute(i);
// ❌ out = []; out[5] = x;  // creates holes -> HOLEY kind -> slower, deopt-prone
```

### Pattern 4: Split a megamorphic site into monomorphic ones

```js
// ❌ One generic site sees every shape -> megamorphic.
function render(node) { return node.draw(); }

// ✅ Dispatch by kind first so each call site sees one shape.
function render(node) {
  switch (node.kind) {
    case 'text':  return renderText(node);   // monomorphic site
    case 'image': return renderImage(node);  // monomorphic site
  }
}
```

### Pattern 5 (JVM): make hot virtual methods non-overridable

```java
// ✅ final removes the CHA-invalidation risk: the devirtualization/inlining
//    bet becomes permanent, not provisional.
public final int hash() { /* hot, must stay inlined */ }
```

---

## Best Practices

- **Optimize for *stability*, not just speed.** The valuable bets (EA, packed arrays, monomorphic inlining) pay off only if they *persist*. A fast path that keeps deopting is worse than a steady slower one.
- **Use typed arrays for numeric data in JS.** They have a fixed representation and sidestep elements-kind transitions and SMI/double churn entirely.
- **Keep objects local when you can.** Non-escaping objects get scalar-replaced; that's free allocation elimination.
- **Treat megamorphic sites as alarms.** If a hot dispatch site is megamorphic, restructure to make per-site shapes uniform.
- **Verify, don't assume.** Use `PrintEliminateAllocations`, `--trace-deopt`, `--trace-ic` to confirm a speculation is active and stable before relying on it.
- **Account for warm-up and re-opt.** Steady-state behavior, after tier-up settles, is what matters — benchmark past warm-up.

---

## Edge Cases & Pitfalls

### Pitfall 1: An object "escaping" through an un-inlined call

Escape analysis is often only effective *after inlining* exposes the object's full lifetime. If the method that would let an object escape isn't inlined (too big, megamorphic, behind a virtual call), EA conservatively assumes escape and keeps the allocation. A seemingly local object can still be heap-allocated because some callee wasn't inlined.

### Pitfall 2: Reification storms under bad speculation

If a hot region scalar-replaces objects *and* deopts frequently, each deopt re-materializes those objects — you get allocation churn at exactly the moments you were trying to avoid it. The cure is stabilizing whatever causes the deopts, not disabling EA.

### Pitfall 3: One value silently widening the whole loop

A single iteration producing a float, an overflow, a hole, or a null can deopt a loop that ran fast for a million iterations. These are *value-domain* breaks and they're easy to introduce accidentally (e.g. `arr.push(undefined)` deep in a helper).

### Pitfall 4: Typed-array vs regular-array confusion

`Int32Array` won't deopt on elements kind, but it also silently coerces/wraps values (e.g. assigning `3.7` truncates, out-of-range wraps). Choosing typed arrays for stability changes value semantics — make sure that's acceptable.

### Pitfall 5: Debugger / profiler attach causing mass deopt

Attaching certain debuggers or enabling some instrumentation forces a **deopt-all** (the runtime must present interpreter-level state to the debugger). Performance measured under a debugger is not representative — you're measuring de-optimized code.

### Pitfall 6: Assuming invalidation is instantaneous

After a CHA break or invalidation, optimized frames already on the stack keep running until they hit a safepoint/return. A long-running optimized loop may execute its now-invalid (but correct) code for a while; back-edge safepoints bound how long.

### Pitfall 7: Polymorphism reintroduced by frameworks

Proxies, decorators, ORMs, bytecode generators, and dynamic mixins inject extra shapes/types into call sites you thought were monomorphic, quietly pushing them toward megamorphic. The source looks clean; the runtime sees diversity.

---

## Apply it

1. State the system invariant that **Deoptimization & Speculation** must protect.
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

- Which invariant must remain true when Deoptimization & Speculation fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
