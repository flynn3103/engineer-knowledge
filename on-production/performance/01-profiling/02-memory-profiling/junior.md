# Memory Profiling — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Memory Profiling** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Profiling](../README.md) → Memory Profiling
> *Your program's memory is a room full of objects. A heap profile is a photograph of that room: who's in it right now, and how much space each one takes. Most "memory bugs" are really one question — why is something still in the photo that should have left?*

---

## Core Concept 1 — A Heap Profile Is a Snapshot of What's Alive

Picture the heap as a room. Every object your program created and still uses is standing in that room. A heap profile walks in, photographs everyone, and hands you a list: *"4,000 `User` objects, 38 MB total. 1 big `[]byte` buffer, 64 MB. 200,000 `string`s, 12 MB."* That list is the snapshot.

Three things to internalize about the photograph:

**It only contains the living.** Objects your program created and then dropped — a temporary slice in a function that already returned — are *not* in the snapshot, because the GC either already collected them or is about to. The profile is not a history of allocation; it's a census of survivors.

**Survival means reachability.** An object stays in the room because something is still pointing at it: a global variable, a field of another live object, a closure captured by a running goroutine. Trace those pointers from the program's roots (globals, stacks) and everything you can reach is "live." Everything you can't is garbage. The snapshot is exactly the reachable set.

**Every language has this same picture, under different names.** The concept is universal; only the file format and tool differ:

| Runtime | How you capture it | What you open it with |
|---|---|---|
| **Go** | `pprof` heap profile (`-inuse_space`) | `go tool pprof` |
| **Java** | a heap dump, `.hprof` | Eclipse **MAT**, VisualVM |
| **Python** | `tracemalloc` snapshot | `tracemalloc` API / `snapshot.statistics()` |
| **Node.js / Chrome** | a `.heapsnapshot` | Chrome DevTools → Memory |

> **Key insight:** A heap profile answers *"what is alive right now and who allocated it,"* not *"what did my program ever allocate."* Allocation rate — how fast objects are born — is a *different* profile (`-alloc_space` in Go), covered in [Allocation Profiling](../03-allocation-profiling/junior.md). When you want to know *why memory is high*, you want the *in-use* (live) profile, every time.

In Go, the live view is the `-inuse_space` profile. It reports the bytes currently held by objects that are still reachable, grouped by the line of code that allocated them.

---

## Core Concept 2 — "Growing" vs "High": A Leak Is Not the Same as a Big Working Set

This is the single most important distinction at this level, and it's the one nobody explains.

Memory being **high** is a *level*. Memory being a **leak** is a *trend*. They look identical in a single screenshot and completely different over time.

Watch what healthy memory does. It saws up and down: it climbs as your program allocates, then drops sharply when the GC runs and reclaims the dead, then climbs again. That sawtooth is *normal*. The peaks can be high and the program is perfectly fine — the GC just hasn't felt enough pressure to run yet, so dead objects are sitting around waiting to be swept. **High peaks are not a leak.**

```
Healthy (sawtooth — GC reclaims):        Leak (ratchet — floor keeps rising):

MB                                       MB
 |      /|    /|    /|                    |              ___/
 |     / |   / |   / |                    |         ___/
 |    /  |  /  | _/  |                    |    ___/
 |   /   |_/   |/    |                    |_ /
 |__/_______________________ time        |________________________ time
   GC drops it back down each cycle         floor never returns to baseline
```

The signature of a real **leak** is that the *floor* rises. After every GC, memory should fall back to roughly the same baseline — the size of what's genuinely still needed. In a leak, the post-GC floor creeps upward run after run, because more objects are surviving every cycle than the cycle before. The GC is doing its job perfectly; the problem is that the objects are *still reachable*, so the GC is *correct* to keep them. The bug is in your code holding the reference, not in the collector.

And there's a third case that masquerades as both: a large but **stable** working set. A service holding a 2 GB in-memory cache will report 2 GB forever and never grow — that's not a leak, that's the feature working. The way you tell these three apart is not by staring at one number; it's by watching the post-GC floor over time, or by the diff technique in Concept 4.

> **Key insight:** Before you debug a "leak," answer one question: *does the post-GC floor keep rising, or is it just high-and-flat?* High-and-flat is a working set (or a lazy GC) — leave it alone or right-size the cache. A **rising floor** is a leak — now go find what's growing. Skipping this question is how engineers spend a day "fixing" memory that was never broken.

To see whether it's the GC just being lazy versus a true growing floor, you can force a collection right before you measure. In Go that's `runtime.GC()` before `runtime.ReadMemStats`; in Java, a heap dump triggers a full GC first, which is exactly why a `.hprof` shows the *reachable* set rather than the inflated pre-GC number.

---

## Core Concept 3 — Shallow Size vs Retained Size

Open any heap tool — MAT, Chrome DevTools, pprof's flame graph — and you'll see two size columns. Reading the wrong one is the most common mistake in memory profiling, so let's make it concrete.

**Shallow size** is the bytes of the object *itself*: its own fields and the pointers it holds — but **not** the things those pointers point to. A struct with two `int` fields and a slice header is small *shallowly*, even if that slice points at a gigabyte.

**Retained size** is the bytes that would be **freed if you deleted this object** — the object itself **plus everything that would become unreachable once it's gone**. It answers the question you actually care about: *"if this thing went away, how much memory do I get back?"*

Consider a `Cache` struct:

```go
type Cache struct {
    name    string             // a few bytes
    entries map[string][]byte  // a header — but it OWNS megabytes of values
}
```

The `Cache` object's **shallow** size is tiny: a string header and a map header, maybe 50 bytes. But its **retained** size could be 500 MB, because the `entries` map — and every `[]byte` value inside it — is kept alive *only* by this one `Cache`. Delete the `Cache`, and all 500 MB becomes collectable. The retained size is 500 MB; the shallow size is 50 bytes.

> **Key insight:** **Shallow size** is "how big is this box?" **Retained size** is "how much falls off the truck if I remove this box?" When you're hunting what's eating memory, you sort by **retained** size — that's what tells you which object, if fixed, actually gives memory back. Sorting by shallow size points you at a thousand small strings and hides the one `Cache` holding them all.

Java's MAT exposes this directly, and adds a beautiful structure called the **dominator tree**: it groups every object under the single object that *exclusively* keeps it alive. The top of the dominator tree, sorted by retained size, is almost always your leak — "this `HashMap` retains 480 MB" is the headline you're looking for. (The dominator tree is a middle-level topic; for now, just know that *retained size* is the number that points at the real offender.)

---

## Core Concept 4 — The Leak-Hunting Move: Snapshot, Work, Snapshot, Diff

Here is the one technique that turns vague suspicion into a named culprit. It works in every language and it is the bread-and-butter move of memory debugging:

1. Let the program reach a steady state (warmed up, caches filled).
2. Take a heap snapshot. Call it **A**.
3. Do a chunk of representative work — serve 10,000 requests, run the import job, replay the user flow.
4. Force a GC, then take a second snapshot. Call it **B**.
5. **Diff B against A.** Whatever *grew* is your suspect.

The logic is airtight. After step 3's work is finished, every *temporary* object it created should be dead and collected — they were needed only during the work. So anything that's *larger in B than in A* is something the work created **and then failed to let go of**. That's the definition of a leak. The diff filters out all the steady, healthy memory and leaves only the things that accumulated.

In Go you capture the two profiles and let `pprof` compute the difference with `-base`:

```bash
# 1. capture a baseline after warm-up (from a running service with net/http/pprof)
go tool pprof -inuse_space -output=A.pb.gz http://localhost:6060/debug/pprof/heap

# 2. ... drive a load of representative traffic against the service ...

# 3. capture again
go tool pprof -inuse_space -output=B.pb.gz http://localhost:6060/debug/pprof/heap

# 4. DIFF: what grew from A to B?
go tool pprof -inuse_space -base=A.pb.gz B.pb.gz
(pprof) top
```

A leaking program produces a diff that screams the answer:

```
      flat  flat%   sum%        cum   cum%
   78.50MB 94.10% 94.10%    78.50MB 94.10%  myapp/cache.(*Store).Put
    2.01MB  2.41% 96.51%     2.01MB  2.41%  myapp/api.decodeRequest
       ...
```

`cache.(*Store).Put` accounts for 78.5 MB of *growth* between the two snapshots — it allocated objects during the work and they're all still alive in B. Your suspect is whatever data structure `Put` is appending to and never trimming.

Every other ecosystem has the identical move:

- **Java:** take two `.hprof` dumps and use MAT's **histogram comparison** (or its leak-suspect report) to see which classes gained instances.
- **Python:** `tracemalloc.take_snapshot()` before and after, then `after.compare_to(before, 'lineno')` — it prints, per source line, exactly how many bytes were added.
- **Node/Chrome:** take two `.heapsnapshot`s and use DevTools' **"Comparison"** view, which lists the delta in objects and size per constructor.

> **Key insight:** A single snapshot tells you what's *big*; a **diff of two snapshots across a unit of work** tells you what's *growing*. Growing-across-work is the fingerprint of a leak, because honest temporary objects die between the snapshots and only the leaked ones survive into the second. When in doubt: snapshot, work, snapshot, diff.

---

## Core Concept 5 — Your First Real Heap Profile

Let's capture and read one end to end in Go. Here is a program with a deliberate, classic leak — a package-level map that records every request and never forgets:

```go
package main

import (
	"os"
	"runtime"
	"runtime/pprof"
	"strconv"
)

// seen is a global, so everything it points to stays reachable FOREVER.
var seen = map[string][]byte{}

func handle(id int) {
	key := strconv.Itoa(id)
	seen[key] = make([]byte, 1024) // 1 KB per request, never removed
}

func main() {
	for i := 0; i < 200_000; i++ { // ~200 MB accumulates in `seen`
		handle(i)
	}

	runtime.GC() // force a collection so the profile shows only LIVE objects
	f, _ := os.Create("heap.pb.gz")
	defer f.Close()
	pprof.WriteHeapProfile(f) // write the in-use (live) heap snapshot
}
```

Run it, then open the live profile:

```bash
go run main.go
go tool pprof -inuse_space heap.pb.gz
```

The `-inuse_space` flag is the one that matters: it asks for **space currently in use by live objects** — exactly the snapshot we want. (Its siblings: `-inuse_objects` counts live *objects*; `-alloc_space` and `-alloc_objects` count *cumulative allocation* — the rate, not the live set.) Inside the interactive prompt:

```
(pprof) top
Showing nodes accounting for 195.31MB, 100% of 195.31MB total
      flat  flat%   sum%        cum   cum%
  195.31MB   100%   100%   195.31MB   100%  main.handle
```

The profile is blunt: `main.handle` is holding 195 MB of live memory. Now ask *where* it's allocated:

```
(pprof) list handle
         .          .     16:func handle(id int) {
         .          .     17:    key := strconv.Itoa(id)
  195.31MB   195.31MB     18:    seen[key] = make([]byte, 1024)
         .          .     19:}
```

Line 18 is your leak, annotated with the exact bytes it retains. The fix is conceptual (forget old entries, bound the map, use a cache with eviction) and belongs to [Memory Optimization](../../05-memory-and-allocation-profiling/junior.md) — but *finding* it took one snapshot and two commands. For a visual version, `go tool pprof -inuse_space -http=:8080 heap.pb.gz` opens a flame graph in your browser where the widest box is the biggest retainer.

> **Key insight:** `-inuse_space` = "what's alive now" (the leak hunt). `-alloc_space` = "what got created total" (the allocation-rate hunt). They answer different questions and will point at different lines. For *"why is memory high/growing,"* reach for `-inuse_space` first.

The same end-to-end story in other runtimes: Java's `jmap -dump:live,format=b,file=heap.hprof <pid>` then open in MAT and read "Leak Suspects"; Python's `tracemalloc.start()` then `snapshot.statistics('lineno')` to rank source lines by live bytes; Node's `--heapsnapshot-near-heap-limit` or a manual DevTools snapshot, sorted by Retained Size. Different buttons, identical picture: *who is alive, and who retains them.*

---

## Real-World Examples

**1. The unbounded cache that "wasn't a cache."** A service kept a `map[string]Result` to "remember recent lookups" — but with no size limit and no expiry. Under steady traffic, memory climbed for days and OOM-killed the pod every Tuesday. A snapshot-work-snapshot diff showed the map's `Put` site growing by ~30 MB per hour while everything else stayed flat. It was a leak dressed as a cache: every distinct key lived forever. (This is the textbook growing-map leak — a global or long-lived collection that only ever *adds*.)

**2. The 1.6 GB that was completely healthy.** A different team panicked at a 1.6 GB resident-memory alert and spent an afternoon hunting a leak. The post-GC floor told the real story: it was *flat* at 1.6 GB across hours — a deliberately large in-memory index, exactly the working set the service was designed to hold. There was no leak. The fix was to the *alert threshold*, not the code. Reading the trend (flat) instead of the level (high) would have saved the afternoon.

**3. The listener that never unsubscribed.** A Node dashboard registered an event listener on every WebSocket reconnect but never removed the old one. Each reconnect captured the previous page's data in a closure that stayed reachable through the listener list. Two `.heapsnapshot`s taken ten minutes apart, compared in DevTools, showed the listener-held `Detached` DOM and closure objects climbing steadily. The retained-size column pointed straight at the closure; the diff proved it was *growing*, not merely present.

---

## Common Mistakes

1. **Calling high memory a leak.** A high *level* is not a leak; a rising post-GC *floor* is. Check the trend before you debug. Large-and-flat is usually a working set (or a cache doing its job) — not a bug.

2. **Reading shallow size when you meant retained.** The small struct at the top of a shallow-sorted list is rarely the problem. Sort by **retained** size to find the object that actually holds the memory hostage.

3. **Profiling allocation rate to find a leak.** `-alloc_space` shows what got created over the whole run, including long-dead objects. To find *what's still alive*, use `-inuse_space` (Go) / a heap dump (Java) / a live `tracemalloc` snapshot. Wrong profile, wrong line.

4. **Forgetting to GC before the snapshot.** Without a forced collection, the snapshot includes dead-but-not-yet-swept objects and overstates live memory — making a healthy program look like a leak. Force a GC first (Go's `runtime.GC()`; a Java heap dump does it for you).

5. **Taking only one snapshot when hunting a leak.** A single snapshot shows what's *big*, not what's *growing*. A leak is defined by growth, so you need **two** snapshots across a unit of work and a diff. One snapshot can't distinguish a leak from a large working set.

6. **Profiling during warm-up.** Snapshots taken before caches fill and pools stabilize are noisy — everything looks like it's "growing" because the program is still filling its legitimate working set. Reach steady state first, *then* start the diff.

---

## Apply it

1. Choose one small, known input for **Memory Profiling**.
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

- What problem does Memory Profiling solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
