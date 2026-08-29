# Runtime ↔ GC Integration — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Runtime ↔ GC Integration** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The GC's Problem: "Which Of These Bits Are Pointers?"

When the GC starts, it wants to find every live object. Live means reachable from a **root**. The roots live in three places: thread stacks, CPU registers, and globals. Here is the catch. Imagine a thread's stack at the moment of a pause:

```text
stack slot 0:  0x00007f3a9c001020   <- could be a pointer... or an integer
stack slot 1:  0x0000000000000005   <- the number 5? or address 0x5?
stack slot 2:  0x00007f3a9c0010a0   <- a pointer to an object? or random data?
```

The raw bytes give no hint. A 64-bit value that happens to fall inside the heap's address range *might* be a live pointer — or it might be a coincidence: a hash code, a loop counter, a packed timestamp. **The GC cannot tell on its own.** This is the central problem of root finding, and there are two ways to solve it.

### 2. Conservative vs Precise Scanning

**Conservative scanning** says: "If a value *looks* like it could be a pointer into the heap, treat it as one." It scans every word on the stack and in registers, and for each, asks "does this point at a valid object?" If yes, it keeps that object alive — just in case. This needs *no help* from the compiler, which is why it was used by early systems like the Boehm GC (a drop-in collector for C/C++) and early versions of V8.

The downsides of conservative scanning:

- **Floating garbage.** An integer that happens to look like a pointer pins a dead object in memory. The object never gets collected. This is rare per-object but real.
- **You cannot move objects.** If you are not *sure* a value is a pointer, you dare not overwrite it with the object's new address — you might corrupt an innocent integer. So conservative collectors generally cannot **compact**.

**Precise (exact) scanning** says: "I will know *exactly* which slots are pointers, because the compiler told me." The compiler emits **stack maps** (called **oop maps** in HotSpot, where "oop" = ordinary object pointer). At each point where a GC could happen, the map records which stack offsets and which registers hold live object references. Now the GC scans only those, with zero ambiguity.

The benefits: no floating garbage from false pointers, and — crucially — the GC *can* move objects, because it knows precisely which slots to update with the new address. Nearly all modern managed runtimes (JVM, Go, .NET, modern V8) are precise.

### 3. The Catch: Maps Are Only Valid At Certain Points

You cannot ask "where are the pointers?" at a *random* machine instruction. Between two instructions, a value might be half-loaded into a register, or a pointer might be temporarily held in a form the map doesn't describe. Building a correct stack map for *every single instruction* would be enormous and slow.

So the compiler only generates maps at a chosen set of locations called **safepoints** (or **GC-safe points**). A safepoint is a place where the thread's state is clean and fully described. The GC is only allowed to inspect a thread that is sitting *at* a safepoint. This is the second half of the contract: the runtime must get every thread *to* a safepoint before it scans.

### 4. Getting Everyone To A Safepoint

Threads do not stop instantly when the GC asks. The runtime needs a cooperative mechanism. The common one:

- The compiler sprinkles tiny **safepoint polls** into the generated code — typically at **loop back-edges** (the jump back to the top of a loop) and at **method entries and returns**. A poll is a cheap check: "has the runtime asked me to stop?"
- When the GC wants to collect, it flips a global flag (or, cleverly, makes a special memory page unreadable so the next poll traps). The next time each thread executes a poll, it notices, parks itself at that safepoint, and waits.

The total time from "GC raised the flag" to "the *last* thread finally reached a poll and stopped" is the **time-to-safepoint (TTSP)**. In a healthy program this is microseconds. But if one thread is stuck in a giant tight loop with no poll, or blocked in a long native call, everyone else waits for it — and your "GC pause" is actually mostly *TTSP*, not collection.

### 5. Stop-The-World vs Concurrent — What The Runtime Must Promise

A **stop-the-world (STW)** collector pauses all mutators at safepoints, does its work, and resumes them. Simple, but the pause is visible as latency.

A **concurrent** collector runs *alongside* the mutator to shrink pauses. But now there is a problem: while the collector is scanning, the mutator keeps changing pointers. An object the collector already marked "dead" might suddenly become referenced by a fresh pointer the mutator just wrote. If the collector misses that, it frees a live object — a catastrophic bug. To prevent it, the runtime needs the mutator to *report* its pointer writes. That is the job of the **write barrier**.

### 6. Write Barriers, Gently

A **write barrier** is a small piece of code the compiler inserts so that *every* pointer store does a tiny bit of extra bookkeeping. Conceptually:

```text
// what you wrote:
obj.field = other;

// what the compiler actually emits (simplified):
obj.field = other;
write_barrier(obj, other);   // tell the GC "obj now points at other"
```

Different collectors use the barrier for different reasons (generational collectors use it to track old→young pointers via "card marking"; concurrent collectors use it to track marking work). The exact flavors are `middle.md` material. The junior takeaway: **the convenience of GC has a hidden cost — a few extra instructions on every pointer write — and the compiler is the one paying it on your behalf.** In store-heavy code this cost is measurable, and good compilers work hard to *remove* barriers they can prove are unnecessary.

### 7. Moving Collectors And The Register Problem

If the collector **moves** an object to a new address (to defragment the heap), every pointer to that object must be updated to the new address. The compiler's stack maps make the *stack and register* pointers updatable. But there is a subtle rule: the compiler **cannot keep a raw pointer in a register across a safepoint** if the object might move during a GC at that safepoint, *unless* the safepoint's map lets the GC find and rewrite that register. If it kept a stale address that the GC didn't know about, after the move the program would dereference freed or relocated memory. This is why moving GC and the compiler are so tightly bound: the compiler must declare every live pointer at every safepoint so the GC can fix them all up.

### 8. Allocation Is Part Of The Contract Too

The collector reclaims memory; allocation hands it out. To make `new` fast, runtimes give each thread a private slab of heap called a **TLAB** (thread-local allocation buffer). Allocating is then just: bump a pointer forward by the object's size; if it fits, you're done — no locks, just a couple of instructions inlined right into your compiled code (the **allocation fast path**). Only when the TLAB is full does the thread take the **slow path** and ask the runtime for a fresh TLAB (which may trigger a GC). So the runtime and compiler co-design allocation and collection together.

---

## Code Examples

The integration is mostly invisible in source code — that's the point. But we can *see its effects*. These examples are about observing the contract, not implementing it.

### Showing the allocation fast path (Java)

```java
public class AllocBench {
    static class Point { int x, y; }

    public static void main(String[] args) {
        long total = 0;
        for (int i = 0; i < 100_000_000; i++) {
            Point p = new Point();   // <- bump-pointer fast path in the TLAB
            p.x = i;
            total += p.x;            // keep p "used" so it isn't optimized away
        }
        System.out.println(total);
    }
}
```

Most of these `new Point()` calls compile down to a *pointer bump* inside the thread's TLAB — no lock, no call into the runtime. Only occasionally (when the TLAB fills) does a slow path run, possibly triggering a GC. Run with `-Xlog:gc` (modern JVMs) and you'll see GC events; run with `-verbose:gc` on older ones. The point: allocation is cheap *because* the compiler inlined the fast path the runtime designed.

### Provoking a long time-to-safepoint (the shape of the bug)

```java
public class CountedLoop {
    public static void main(String[] args) {
        // A huge "counted loop" over an int range.
        long sum = 0;
        for (int i = 0; i < Integer.MAX_VALUE; i++) {
            sum += i;     // no allocation, no method call inside
        }
        System.out.println(sum);
    }
}
```

Historically, the JVM omitted safepoint polls inside tight *counted* loops like this (loops with a known integer bound) as an optimization. If a GC was requested while this loop ran, *every other thread* could be stuck waiting for this one to finish — a long TTSP. Modern JVMs added "loop strip mining" and other fixes, but the shape of the bug is permanent: **a long-running loop with no safepoint poll can hold the entire program hostage.** You don't see it in source; you see it as a multi-hundred-millisecond pause in a GC log where the actual collection was tiny.

### Watching write barriers exist (Go, conceptually)

```go
package main

type Node struct {
    next *Node
    val  int
}

func link(a, b *Node) {
    a.next = b   // <- the Go compiler may emit a write barrier here
}

func main() {
    a := &Node{val: 1}
    b := &Node{val: 2}
    link(a, b)
    _ = a
}
```

The single line `a.next = b` is a pointer store. When Go's concurrent collector is in its marking phase, the compiler-inserted **write barrier** records that `a` now points at `b`, so the collector won't miss `b`. You wrote one assignment; the runtime contract added bookkeeping around it. You can inspect the generated assembly with `go build -gcflags=-S` and find the barrier call in the output — proof that the "simple" assignment is not so simple under a concurrent GC.

### Conservative vs precise, illustrated in pseudocode

```text
// CONSERVATIVE root scan (no compiler help):
for each word W on the stack and in registers:
    if W looks like an address inside the heap:
        treat the object at W as LIVE   // might be a false positive

// PRECISE root scan (compiler provided a stack map for this safepoint):
map = stackMapFor(currentInstructionPointer)
for each slot S that map marks as "holds a pointer":
    object = read(S)
    treat object as LIVE                // never a false positive
    // and, if moving: after relocation, write the new address back into S
```

The precise version is only possible because the compiler emitted `stackMapFor(...)` data alongside the code. That metadata *is* the runtime↔GC interface.

---

## Coding Patterns

These are application-level habits informed by how the integration works.

### Pattern 1: Reduce pointer churn in hot paths

```go
// Barrier-heavy: rewires pointers every iteration.
for i := range items {
    cache.head = &items[i]   // pointer store -> write barrier each time
}

// Lighter: store indices or values, not pointers, where possible.
for i := range items {
    cache.headIndex = i      // plain integer store -> no write barrier
}
```

A pointer store may carry a write barrier; an integer store does not. In genuinely hot code, preferring value/index storage can shave barrier cost. (Measure — don't contort readable code on a guess.)

### Pattern 2: Don't build pathological uninterruptible loops

```java
// Risky shape historically: a giant tight loop with no calls inside.
for (long i = 0; i < HUGE; i++) { acc += i; }

// Friendlier: chunk the work; method boundaries are safepoints.
for (long start = 0; start < HUGE; start += CHUNK) {
    processChunk(start, Math.min(start + CHUNK, HUGE)); // call = safepoint
}
```

Method entries/returns carry safepoint polls, so chunking gives the runtime regular chances to stop you, improving TTSP for the whole process.

### Pattern 3: Keep native/critical sections short

```text
// In any language with a native boundary (JNI, cgo, P/Invoke):
acquire native critical region
... do the MINIMUM ...
release native critical region
```

While a thread is in a long native call or a "GC-critical" region (where the GC promises not to move objects), the collector may be blocked or forced to back off. Short native sections keep the collector unblocked.

### Pattern 4: Let allocation be cheap — allocate small and local

```text
// Tiny, short-lived objects ride the TLAB fast path and die young.
// Generational GCs reclaim young garbage almost for free.
tmp := small.New()   // fast bump allocation; collected cheaply
use(tmp)
```

Short-lived local allocations are friendly to the integration: fast to allocate, cheap to collect, and they exercise fewer barriers.

---

## Best Practices

- **Read the pause, not just the GC count.** When latency spikes, separate *time-to-safepoint* from *collection time*. A long TTSP points at a thread that wouldn't stop, not at the collector.
- **Be suspicious of giant tight loops.** A loop with no method calls and no allocation may have no safepoint poll. If you have one over millions of iterations, consider chunking it.
- **Keep native calls short.** Long native sections can stall the whole collector. Copy out what you need and return.
- **Don't fight the write barrier with micro-tricks first.** Most code is fine. Reach for index/value storage only in a *profiled* hot path.
- **Prefer many small short-lived objects over a few churned long-lived ones** when it fits — generational integration handles youth death almost for free.
- **Trust the compiler's barrier elimination.** Modern compilers remove provably-unneeded barriers (e.g., stores into a freshly allocated object that nothing else can see yet). Write clear code and let them.
- **Learn your engine's flags.** `-Xlog:gc*`, `-Xlog:safepoint` (JVM), `GODEBUG=gctrace=1` (Go), and .NET's GC events expose exactly the integration behavior described here.

---

## Edge Cases & Pitfalls

- **The "pause" that isn't collection.** A GC log line says the pause was 200 ms but the marking/sweeping took 5 ms. The other 195 ms was *time-to-safepoint*: one thread took forever to reach a poll. Beginners blame the GC algorithm; the real fix is the slow thread.
- **The counted-loop trap.** A loop with a fixed integer bound and no calls inside historically had no safepoint poll. Inside it, the whole VM cannot pause. Even with modern mitigations, machine-generated tight loops can reproduce this.
- **Native calls and the collector.** A thread blocked in a long native call may be treated as "already at a safepoint" (so the GC proceeds) — but a native *critical* section that pins objects can *block* a moving collector until it ends. Both directions matter; both reward short native sections.
- **Conservative scanning pins junk.** If you ever use a conservative collector (e.g., Boehm in C), an integer that looks like a pointer can keep a dead object alive. Memory "leaks" that aren't real leaks.
- **You cannot hold a raw pointer across a safepoint under a moving GC** if the runtime doesn't know about it. In native extension code, you must use **handles** (indirection the GC can update), not raw addresses, across any point where a GC could run.
- **Barriers cost in store-heavy code.** Tight code that rewires many pointers per iteration pays the barrier repeatedly. It's usually fine; occasionally it's a measurable hotspot.
- **"It's just an integer" can be a pointer.** Under conservative scanning, the GC can't tell. Under precise scanning, the compiler *must* get the map right, or the GC frees live memory — a runtime-implementer's nightmare, not yours, but it's why precise maps are so carefully engineered.

---

## Apply it

1. Choose one small, known input for **Runtime ↔ GC Integration**.
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

- What problem does Runtime ↔ GC Integration solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
