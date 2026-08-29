# Runtime ↔ GC Integration — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Runtime ↔ GC Integration** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Precise Stack Maps Under Aggressive Optimization

The interpreter's stack maps are trivial: the operand stack and locals have known types. The JIT destroys that simplicity:

- **Register allocation** spreads a single logical reference across registers and spill slots over its lifetime. The map at each safepoint must name *wherever it currently lives*.
- **Inlining** collapses many source frames into one machine frame; the map must still allow reconstructing per-inlined-method liveness (for deopt) while listing all live oops (for GC).
- **Scalar replacement** turns an object into loose slots; if any slot holds a reference, the map must mark it — otherwise the GC misses a root.
- **Derived/interior pointers** proliferate (array iteration, field-address arithmetic); each needs a base recorded.
- **Speculative/uncommon-trap points** must also be safepoints, so the deoptimizer can rebuild frames.

The senior insight: **the precision of root scanning is bounded by the precision of the compiler's liveness and type tracking.** A bug here is silent until a moving GC relocates and the program dereferences a slot the GC didn't update (or updated wrongly). This is why moving collectors and aggressive optimizers are a hard marriage, and why engines invest enormous test effort (stress GC at every safepoint) to validate maps.

### 2. Deoptimization Shares The GC's Metadata

Deopt and GC root scanning both ask "what is the state of this optimized frame?" — and both answer with the same family of metadata. In HotSpot, a compiled method carries both an `OopMapSet` (for GC) and **debug info / scope descriptors** (for deopt) at safepoints. The interactions:

- A safepoint may be reached *because* of a GC, *or* because a speculative assumption failed and we must deopt. The runtime must handle "GC arrives while a thread is mid-deopt" and "deopt arrives at a GC safepoint."
- During deopt, the frame is being rewritten; a GC scanning that frame must see a consistent view. Engines serialize these or define a precise order (deopt completes to a known state that the GC map describes).
- Scalar-replaced objects must be **rematerialized** on deopt (re-allocated, possibly triggering GC) — a deopt that itself allocates and may provoke a collection. The metadata must let the deoptimizer reconstruct the object *and* let any triggered GC find roots in the half-built frame.

Seniors should know: deopt is not GC, but they are *co-tenants of the safepoint metadata*. Many "impossible" crashes live at their intersection.

### 3. Read/Load Barriers And Colored Pointers (ZGC, Shenandoah)

Generational/STW collectors mostly need **write barriers** (track stores). Concurrent **compaction** — moving objects while the mutator runs — needs the mutator to never observe a *stale* pointer to a moved object. The natural place to enforce that is the **load**: when the mutator loads a reference, a **load barrier** checks whether the object has moved and, if so, corrects the pointer.

**ZGC** encodes state in the pointer itself — a **colored pointer**. On a 64-bit address, ZGC uses several high bits as color (marked0/marked1/remapped/finalizable). The load barrier is, in the fast path, a test of those bits:

```asm
    mov    rax, (obj_field)        ; load the (colored) reference
    test   rax, (bad_color_mask)   ; are any "bad" color bits set?
    jnz    zgc_load_barrier_slow   ; rare: relocate/remap, self-heal the slot
```

The fast path is a load plus a test-and-not-taken-branch. The slow path relocates the object if needed, remaps the pointer to the new address, **self-heals** by writing the corrected pointer back into the source slot, and returns the good pointer. Because the color is *in the pointer*, the same physical object can be addressed through different colored pointers; ZGC uses **multi-mapping** so all colors alias the same memory. The payoff: concurrent relocation with sub-millisecond pauses, at the cost of a barrier on (almost) every load.

**Shenandoah** historically used a **Brooks forwarding pointer**: every object has an extra header word that points to itself, or to its new copy during relocation. Reads indirect through it (`obj = *(obj->fwd)`), so a stale pointer still reaches the current object. Later Shenandoah versions moved to a load-reference-barrier scheme closer to ZGC's to reduce the per-object word overhead. Either way: **the integration point moved from the store to the load**, which is the defining senior-level distinction between these collectors and generational ones.

### 4. Write-Barrier vs Read-Barrier Economics

The choice is an engineering tradeoff in *where you pay*:

- **Write barriers** tax pointer **stores**. Most programs load far more than they store, so write barriers are cheap on average — but they can't, by themselves, support concurrent *relocation* (a load could still see a stale pointer).
- **Read/load barriers** tax pointer **loads** (far more frequent) but enable concurrent compaction and self-healing. They make pauses tiny and independent of heap size — ZGC and Shenandoah target sub-millisecond pauses on huge heaps — at a throughput cost (often a few percent to low-double-digits depending on workload).

So: throughput-sensitive batch workload with tolerable pauses → write-barrier collector (ParallelGC, G1). Latency-critical service with large heaps → load-barrier collector (ZGC, Shenandoah). This is a *codegen-cost* decision dressed as a "GC choice."

### 5. Go's Hybrid Write Barrier

Go's concurrent mark-sweep is *non-moving*, so it needs only write barriers — but it has a special problem: goroutine **stacks** can be huge and numerous, and re-scanning all stacks stop-the-world at the end of marking was a major pause source pre-Go-1.8. The fix is the **hybrid write barrier** (Go 1.8), which combines:

- a **Yuasa-style deletion barrier**: shade (mark grey) the *old* pointer being overwritten, and
- a **Dijkstra-style insertion barrier**: shade the *new* pointer being written.

```text
writePointer(slot, ptr):
    shade(*slot)        // deletion part: keep what we're erasing
    if current_stack_is_grey:
        shade(ptr)      // insertion part
    *slot = ptr
```

The key consequence: a goroutine's stack can be scanned **once**, marked black, and **never re-scanned**, because the barrier guarantees the marker won't miss an object even as the goroutine keeps mutating. This eliminates the STW stack re-scan and is the main reason Go's pauses are typically well under a millisecond. It's a textbook example of *the barrier design buying a pause-time property*.

Go also solved its own counted-loop/TTSP problem differently: **asynchronous preemption** (Go 1.14) uses an OS signal to stop a goroutine even inside a tight loop with no explicit poll. The signal handler checks the goroutine's PC against precise stack maps emitted for *every instruction that could be a preemption point*, so it can stop and scan safely. This is Go choosing signal-based preemption over cooperative-only polling to bound TTSP.

### 6. V8's Integration

V8 (JavaScript) is an instructive contrast:

- **Early V8 was conservative** on the stack (Crankshaft era), scanning the stack pessimistically. Modern V8 (Orinoco/Oilpan) moved toward precise scanning where possible, but JS's dynamic nature and the C++ heap (Blink DOM objects, managed by **Oilpan**) make root finding heterogeneous: precise stack maps for compiled JS, plus conservative stack scanning at the C++ boundary, plus handle scopes for C++ references into the heap.
- V8 uses **handle scopes** (`v8::HandleScope`, `Local<T>`) so C++ code holds references the GC can find and update across moves — the same handle pattern as JNI, by a different name.
- V8's **incremental and concurrent marking** uses write barriers; its **scavenger** (young-gen) moves objects, so the compiler/runtime must keep roots precise enough to update them.
- The lesson: a real engine often runs *multiple* root-finding strategies at once (precise for managed code, conservative at native frames), because the program crosses managed/native boundaries constantly.

### 7. .NET CLR Integration

The CLR is a precise, moving (compacting) collector and shows the contract cleanly:

- The JIT emits **GC info** (stack maps) per method, describing which registers/slots hold object references at each **GC-safe point**. There are two regimes: **fully-interruptible** code (safepoints almost everywhere, larger maps) and **partially-interruptible** code (safepoints only at call sites, smaller maps) — a size/latency tradeoff the JIT chooses per method.
- The CLR distinguishes **managed pointers** (`byref`, interior pointers) from object references; interior pointers are the derived-pointer case and the GC tracks them to update after compaction.
- **GCHandle** (and pinned handles) is the .NET handle/pinning mechanism for interop with native code, exactly the "raw pointers can't survive a move" cure.
- The CLR coordinates threads to GC-safe points via **hijacking** (rewriting a thread's return address so it traps into the runtime on return) in addition to polling — a third safepoint mechanism beyond flag and page-trap.

Across HotSpot, Go, V8, and .NET you see the *same contract* solved with different mechanisms: cooperative polls vs page-traps vs signals vs return-address hijacking; write barriers vs load barriers; precise vs hybrid-with-conservative-edges.

### 8. Engineering The Incidents

Two canonical senior incidents:

**Long TTSP.** Symptom: pause logs show large "time to safepoint," small collection time. Causes: a counted loop with no poll (pre-mitigation JVM, or machine-generated code), a thread stuck in a long JNI/native call (which may pin and block a moving GC), or a runaway loop the optimizer stripped of polls. Fixes: enable counted-loop safepoints / strip mining; bound native sections; in Go, ensure async preemption is active; sometimes restructure the hot loop. The diagnostic discipline: *attribute the pause to integration before touching GC tuning flags*.

**Write-barrier storm.** Symptom: a graph/tree mutation workload spends a surprising fraction of CPU in barrier code; throughput drops under a concurrent collector. Cause: many pointer stores per unit work, each paying the barrier; possibly card-table false sharing across cores. Fixes: batch mutations, prefer value/index representations in hot structures, enable conditional card marking, pad hot card-table regions, or choose a collector whose barrier is cheaper for the workload. The senior move: *read the disassembly, confirm the barrier shape, and measure barrier CPU directly* (perf annotate / flame graph) rather than guessing.

---

## Code Examples

### Recognizing a ZGC load barrier

```java
public class LoadBarrier {
    static class Node { Node next; }
    static Node follow(Node n) { return n.next; }   // a pointer LOAD
}
```

```bash
java -XX:+UseZGC -XX:+UnlockDiagnosticVMOptions -XX:+PrintAssembly \
     -XX:CompileCommand=print,LoadBarrier.follow LoadBarrier
```

Around the load of `n.next` you'll see a load followed by a test against a "bad mask" and a branch to a stub — the colored-pointer load barrier. Compare with a non-pointer-returning method, which has no such test. This is the senior-level "the barrier is on the *load* now" made concrete. (On ParallelGC the same method has *no* barrier on the load at all.)

### Go: hybrid write barrier and async preemption, observed

```go
package main

import "runtime"

type N struct{ next *N }

//go:noinline
func mutate(a, b *N) { a.next = b } // hybrid write barrier when marking

func spin() {
    // A tight loop with no function calls. Pre-Go-1.14 this could resist
    // preemption (bad TTSP). With async preemption, a signal can stop it.
    x := 0
    for i := 0; i < 1_000_000_000; i++ {
        x ^= i
    }
    _ = x
}

func main() {
    runtime.GC()
    a, b := &N{}, &N{}
    mutate(a, b)
    spin()
}
```

```bash
go build -gcflags=-S ./...                 # find runtime.gcWriteBarrier around a.next=b
GODEBUG=gctrace=1,asyncpreemptoff=0 go run .   # observe GC + preemption behavior
```

`go tool objdump` on `mutate` shows the write-barrier call; toggling `GODEBUG=asyncpreemptoff=1` and watching pause behavior demonstrates how signal-based preemption bounds TTSP for `spin`.

### Diagnosing TTSP vs collection (JVM)

```bash
# Separate "reaching safepoint" (TTSP) from "at safepoint" (collection).
java -Xlog:safepoint:stdout:tags,time \
     -XX:+UnlockDiagnosticVMOptions -XX:+PrintGCApplicationStoppedTime \
     -jar service.jar
```

If `Reaching safepoint` dominates, hunt for a non-yielding thread (counted loop, native call). If `At safepoint` dominates, it's genuine collection work — *now* GC tuning (heap size, collector choice, generation sizing) is the lever. A senior never tunes the collector before splitting these.

### A self-healing load barrier, in pseudocode

```text
load_barrier(slot):
    ref = *slot
    if color_is_good(ref):
        return ref                       // fast path: just a bit test
    // slow path:
    obj = remap(ref)                     // find current location (relocate if needed)
    good = recolor(obj)                  // pointer with current/good color
    CAS(slot, ref, good)                 // SELF-HEAL: fix the source slot
    return good
```

The self-heal means the *first* load through a stale slot pays; subsequent loads are fast. This is why ZGC's amortized load-barrier cost is lower than "a slow path on every load" would suggest.

### Why scalar replacement needs a precise map (deopt + GC)

```java
// If 'p' is scalar-replaced, its fields live in registers/slots. At a safepoint
// inside compute(), the map must still mark the slot holding 'p.ref' as an oop,
// AND the deopt metadata must be able to REMATERIALIZE 'p' (re-allocate it).
static Object compute(boolean cond, Object x) {
    var p = new Object[]{ x };     // may be scalar-replaced (non-escaping)
    if (cond) heavyCallThatMayDeopt();   // safepoint; possible deopt -> rematerialize p
    return p[0];
}
```

If the map omits the slot holding `x`, a moving GC frees or fails to update it. If the deopt metadata can't rebuild `p`, deopt corrupts the frame. Both consume the same safepoint metadata — the senior point about co-tenancy.

---

## Coding Patterns

### Pattern 1: Attribute before you tune

```text
1. Pull pause data with TTSP vs collection split (-Xlog:safepoint / gctrace).
2. If TTSP dominates -> find the non-yielding thread (loop/native), fix it.
3. If collection dominates -> consider collector choice / heap sizing.
4. If barrier CPU dominates (flame graph) -> restructure mutations / pick collector.
Never skip to step 3 or 4.
```

### Pattern 2: Keep native interop GC-friendly

```c
/* JNI: hold references via handles; keep critical (pinning) regions tiny. */
jobject g = (*env)->NewGlobalRef(env, obj);     /* survives moves */
/* ... long-lived use ... */
{
    jbyte* p = (*env)->GetPrimitiveArrayCritical(env, arr, 0); /* PINS, may block moving GC */
    memcpy(dst, p, n);                                          /* minimal work */
    (*env)->ReleasePrimitiveArrayCritical(env, arr, p, 0);
}
(*env)->DeleteGlobalRef(env, g);
```

### Pattern 3: Reduce load-barrier pressure under ZGC/Shenandoah

```text
// Loads of references pay the barrier; loads of primitives don't.
// In hot loops, hoist a reference load out of the loop where the algorithm allows,
// or iterate over primitive/value arrays rather than arrays of references.
ref = obj.field;          // pay the load barrier ONCE
for (i...) use(ref, i);   // not once per iteration
```

### Pattern 4: Make hot objects non-escaping to delete barriers and allocations

```java
// Escape analysis can scalar-replace this; no allocation, no barriers on its stores.
double dist(double x1, double y1, double x2, double y2) {
    var p = new double[]{x2 - x1, y2 - y1};   // likely scalar-replaced
    return Math.hypot(p[0], p[1]);
}
```

---

## Best Practices

- **Split TTSP from collection time in every pause investigation.** It is the single highest-leverage habit; it routes you to integration vs algorithm fixes.
- **Choose the collector by its barrier economics relative to your SLO**, not by reputation: write-barrier/throughput (ParallelGC, G1) vs load-barrier/latency (ZGC, Shenandoah).
- **Keep native critical/pinning windows minimal**, and prefer handles to raw pointers across any boundary where a GC can run.
- **Validate barrier and poll presence in disassembly** when chasing regressions; the optimizer's choices (elimination, strip mining) change the picture per method and per collector.
- **Respect deopt × GC co-tenancy** when writing intrinsics or runtime glue: anything that allocates during deopt (rematerialization) can trigger a GC mid-frame-rebuild.
- **Ensure preemptibility of generated/numeric loops** (counted-loop safepoints on the JVM; rely on Go's async preemption; avoid hand-rolled poll-free assembly).
- **Treat per-load/per-store cost as a design input** for hot data structures under concurrent-moving collectors.

---

## Edge Cases & Pitfalls

- **GC during deopt of scalar-replaced objects.** Rematerialization allocates; if that triggers a GC, the partially-rebuilt frame must still be root-scannable. A classic intersection bug; rare but catastrophic.
- **Stale colored pointers leaking past a barrier.** If any pointer load bypasses the load barrier (a hand-written intrinsic, a missed codegen path), the mutator can dereference a pre-move address under ZGC/Shenandoah — memory corruption. Engines audit every load path for this reason.
- **Address-bit exhaustion for colored pointers.** ZGC consumes high virtual-address bits for color; this constrains usable address space and interacts with ASLR, large pages, and certain platforms (and motivated generational ZGC's redesign).
- **Go pointer-passing rule violations.** Passing a Go pointer to C and retaining it across a GC can leave C holding a moved/invalid pointer; the cgo rules exist precisely because of the moving/scanning contract.
- **Hijacking vs tail calls / exception unwinding (.NET).** Return-address hijacking must cooperate with frames that don't return normally; mishandling corrupts control flow.
- **Conservative edges keeping garbage alive (V8/Oilpan, native frames).** Where an engine falls back to conservative stack scanning at native frames, integer-shaped values can pin objects — intermittent retention that looks like a leak.
- **Card-table / SATB-queue contention.** Under heavy multi-core mutation, the *shared* barrier state structures become the bottleneck, not the GC algorithm. False sharing on the card table is a real, measurable senior-level problem.
- **Partially-interruptible code lengthening TTSP (.NET).** Methods with safepoints only at call sites can have long call-free stretches that delay reaching a GC-safe point.

---

## Apply it

1. State the system invariant that **Runtime ↔ GC Integration** must protect.
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

- Which invariant must remain true when Runtime ↔ GC Integration fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
