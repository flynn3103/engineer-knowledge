# Allocation Profiling — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Allocation Profiling** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Profiling](../README.md) → Allocation Profiling
> *The junior page taught you that allocation rate, not live size, is usually the GC's real workload. This page is about turning that idea into a coordinate on a map: capturing an allocation profile, reading it down to the exact line that churns, and proving — with the escape analyzer — why that line reached the heap at all.*

---

## The Four Quadrants: alloc vs inuse × space vs objects

Go's heap profile is a single dataset with **four sample types**, formed by crossing two independent axes. Confusing them is the single most common allocation-profiling error, so anchor them first.

|              | **space** (bytes)                       | **objects** (count)                       |
|--------------|-----------------------------------------|-------------------------------------------|
| **alloc_**   | total bytes *ever* allocated here        | total *number* of allocations here         |
| **inuse_**   | bytes from here *still live* now         | live *objects* from here now               |

- **Axis 1 — `alloc_` vs `inuse_`.**
  - `alloc_*` is **cumulative since the program started** (or since counters were reset): it counts everything that passed through, *including what the GC already freed*.
  - `inuse_*` is a **snapshot of what is live right now**.
  - Allocation profiling is the `alloc_*` column — the *rate* of churn. `inuse_*` is retained-memory profiling, the subject of [memory-profiling](../02-memory-profiling/middle.md).
- **Axis 2 — `space` vs `objects`.** `*_space` weights each sample by **bytes**; `*_objects` weights by **count**. They rank call sites *differently*:
  - **`alloc_objects` finds many-small churn.** A function called 5M times allocating a 16-byte struct each call is invisible in `alloc_space` (80 MB total, modest) but screams in `alloc_objects` (5M allocations — 5M GC-scannable headers, 5M trips through the allocator fast path). High object *count* is what pressures the GC's mark phase and the allocator, regardless of bytes.
  - **`alloc_space` finds few-big.** One function allocating a 64 MB buffer ten times is trivial in `alloc_objects` (10 allocations) but dominates `alloc_space`. Big allocations blow your memory ceiling and trigger more frequent GC cycles by hitting the heap-growth trigger sooner.

> **Key insight:** Always read **`alloc_objects` and `alloc_space` side by side.** If a call site tops `alloc_objects` but not `alloc_space`, you have a high-frequency small allocation — fix it by *reducing the count* (reuse, pooling, avoiding per-iteration allocation). If it tops `alloc_space` but not `alloc_objects`, you have a few large allocations — fix it by *right-sizing or streaming*. The two columns prescribe two different cures.

---

## Capturing an Allocation Profile in Go

There are two entry points, and you'll use both.

**From a benchmark** — the cleanest signal, because the workload is isolated:

```bash
go test -run='^$' -bench=BenchmarkEncodeJSON -benchmem \
  -memprofile=mem.out -memprofilerate=1 ./...
```

- `-benchmem` adds `B/op` and `allocs/op` columns to the bench line — your first, cheapest allocation metric, no profile needed:

```
BenchmarkEncodeJSON-8   210148   5712 ns/op   4096 B/op   47 allocs/op
```

  - `47 allocs/op` is the headline number. If a fix drops it to `3 allocs/op`, you've succeeded *before* opening `pprof`.
- `-memprofilerate=1` records **every** allocation.
  - The default (`512*1024` bytes — one sample per ~512 KB) is fine for a long-running server but will *miss* small high-frequency allocations in a short benchmark.
  - For diagnosis, sample everything; for production, leave it at the default to keep overhead negligible.

**From a live server** — via `net/http/pprof`:

```go
import _ "net/http/pprof"           // registers handlers on the default mux
// ... run an http.Server on a debug port
```

```bash
# heap profile snapshot (defaults to the inuse_space view)
go tool pprof http://localhost:6060/debug/pprof/heap
```

- The HTTP heap profile is a *snapshot*: every counter is cumulative-since-start for `alloc_*` and live-now for `inuse_*`.
- To measure churn *over an interval* on a server, take two snapshots and diff them (`pprof -base old.out new.out`) — that isolates "what allocated during these 60 seconds" from the program's startup allocations.

> **Key insight:** `-memprofilerate=1` is for *diagnosis on a benchmark*, never for production. At rate 1 every allocation takes a stack trace; on a hot server that is enormous overhead. Diagnose at rate 1 on an isolated benchmark, then ship with the default sampling rate.

---

## Reading the Profile Down to a Call Site

A profile is useless until it points at a line. The path from "something allocates" to "*this* line allocates" is three commands.

**1. The flat top-list — who allocates the most.** Pick the sample type explicitly:

```bash
go tool pprof -alloc_objects mem.out
(pprof) top
```

```
Showing nodes accounting for 9876543, 98.21% of 10056789 total
      flat  flat%   sum%        cum   cum%
   4100000 40.77% 40.77%    4100000 40.77%  encoding/json.(*encodeState).string
   2500000 24.86% 65.63%    6600000 65.63%  myapp/api.(*Handler).marshalRow
   1800000 17.90% 83.53%    1800000 17.90%  fmt.Sprintf
    900000  8.95% 92.48%     900000  8.95%  strings.(*Builder).grow
```

- Read **flat vs cum** exactly as in a CPU profile: *flat* = allocations made *in this function's own body*; *cum* = allocations in this function **plus everything it calls**.
- A high-cum / low-flat frame (`marshalRow` above: cum 6.6M, flat 2.5M) is a *router* — the allocations happen downstream, in `json.string`. Chase the flat, not the cum, to find the actual allocating line.

**2. Annotate the source — which line in that function.** This is the command that ends the hunt:

```bash
(pprof) list marshalRow
```

```
ROUTINE ======================== myapp/api.(*Handler).marshalRow
   2500000    6600000 (flat, cum) 65.63% of Total
         .          .   41:func (h *Handler) marshalRow(r Row) []byte {
         .          .   42:    m := map[string]any{}
   2500000    2500000   43:        m["id"] = r.ID            // any boxing: int → interface
         .    4100000   44:        b, _ := json.Marshal(m)   // 4.1M allocs downstream
         .          .   45:        return b
         .          .   46:}
```

- Line 43 makes 2.5M allocations on its own (boxing `r.ID` into `any`).
- Line 44's allocations are all charged to `cum` because they happen inside `json.Marshal`.
- Now you have a *line number* and a *count next to it*.

**3. The visual view — `web` / flame.** For a wide call graph, `web` (opens an SVG; boxes sized by allocation) or the flame view in `go tool pprof -http=:8080 mem.out` shows the *shape* — which subtree owns the churn — faster than reading text. Use it to choose *which* function to `list`, then `list` to get the line.

> **Key insight:** `top` ranks functions; `list` indicts lines. Never stop at `top` — a function name is not a fix. The `list` output, with allocation counts in the left margin pointing at specific statements, is the artifact you act on.

---

## The Escape-Analysis Connection

Here is the conceptual core of the page. The profiler answers **"what reached the heap?"** It does **not** answer **"why couldn't this stay on the stack?"** — and without the why, your fix is a guess. The escape analyzer answers the why, at compile time, for free:

```bash
go build -gcflags='-m' ./...        # add a second -m for more detail: -gcflags='-m -m'
```

```
./handler.go:43:9: m["id"] = r.ID escapes to heap
./handler.go:42:7: map[string]any{} escapes to heap
./encode.go:88:21: ... argument does not escape
./encode.go:90:13: make([]byte, n) escapes to heap
```

- Escape analysis is the compiler's static proof of whether a value's lifetime can be bounded by its function's stack frame.
- If the compiler can't *prove* the value dies when the function returns, it must **heap-allocate** it (it "escapes").
- The profiler shows you the *consequence*; `-m` shows you the *cause*.

**The recurring causes:**

- **Interface boxing.** Assigning a concrete value to an `interface{}`/`any` (or passing it to a variadic `...any`, like `fmt.Println`) boxes it — the value is copied to the heap so the interface can hold a pointer to it. `m["id"] = r.ID` above escapes for exactly this reason.
- **Pointer escape (returning a pointer to a local).** `return &x` where `x` is a local forces `x` onto the heap — its address outlives the frame, so it can't live in the frame.
- **Closure capture.** A closure that captures a local *by reference* and outlives the function (stored, returned, or run in a goroutine) forces the captured variable to the heap.
- **Slice/map growth beyond a provable bound.** `make([]T, n)` with a non-constant `n` the compiler can't bound, or an `append` that may reallocate, escapes — the backing array's size isn't known at compile time.
- **Value too large for the stack**, or passed to a function the compiler can't see through (an indirect/interface call), so it conservatively assumes escape.

> **Key insight:** The profiler and the escape analyzer are a **diagnosis pair**. `pprof` finds the *hot allocating line*; `-gcflags=-m` on that exact line tells you *which* of the five causes applies, which tells you the fix (de-interface it, return a value not a pointer, hoist the closure variable, preallocate with a known size). Then you re-run `-m` to *confirm* the line no longer says "escapes to heap" — a verifiable success criterion the bench's `allocs/op` then corroborates.

---

## The Same Question in Other Languages

The "where/how-often do I allocate" question is universal; the tooling differs.

**Java — JFR allocation events / async-profiler `--alloc`.** The JVM records allocations via two JFR events:
- `jdk.ObjectAllocationInNewTLAB` — the object started a fresh thread-local allocation buffer (i.e. it triggered a slow-path TLAB refill).
- `jdk.ObjectAllocationOutsideTLAB` — the object was too big for a TLAB and went straight to the heap — your "few-big" signal.

async-profiler renders these as an **allocation flame graph**:

```bash
asprof -e alloc -d 30 -f alloc.html <pid>     # flame graph weighted by bytes allocated
```

- The flame is weighted by *allocated bytes per stack*, the direct analog of Go's `alloc_space` flame.
- **TLAB vs outside-TLAB** is the JVM's own "many-small vs few-big" split: a tower of `InNewTLAB` events is high-frequency churn; `OutsideTLAB` frames are the large allocations.

**Python — `tracemalloc`.** Built in, no external tool:

```python
import tracemalloc
tracemalloc.start()
# ... run the workload ...
snap = tracemalloc.take_snapshot()
for stat in snap.statistics("lineno")[:5]:
    print(stat)        # file:line: size=12.3 MiB, count=45213, average=285 B
```

- `statistics("lineno")` is Python's flat top-list: `size` is the `alloc_space` analog, `count` the `alloc_objects` analog, both per source line.
- Diff two snapshots (`snap2.compare_to(snap1, "lineno")`) to find what allocated *between* two points — the leak/churn hunter's move.

**.NET — ETW allocation events.** `dotnet-trace` collects the `GCAllocationTick` ETW event (one event per ~100 KB allocated per type). `dotnet-trace collect --providers Microsoft-Windows-DotNETRuntime:0x1 ...` or the Visual Studio / PerfView allocation view attributes bytes-by-type-by-call-stack — the same bytes-weighted allocation graph as the others.

> **Key insight:** Every ecosystem gives you the *same two columns* — bytes-weighted and count-weighted allocations, attributed to a stack — under different names (`alloc_space`/`alloc_objects`, JFR TLAB events, `tracemalloc` size/count, ETW `GCAllocationTick`). Learn the shape once; the language only changes which command prints it.

---

## Common Culprits You Find This Way

These five account for the large majority of allocation findings in Go services. Each has a tell in `-m` and a one-line fix.

1. **Hidden interface boxing.** `any`/`interface{}` arguments, `map[string]any`, `fmt.Sprint(x)` of a non-string. `-m` says `x escapes to heap` on the boxing line. *Fix:* use a concrete type; avoid `any` containers on the hot path.
2. **`fmt.Sprintf` in a hot loop.** It allocates the result string *and* boxes every `%v` argument into `...any`. Often several `allocs/op` by itself. *Fix:* `strconv.AppendInt`/`AppendFloat` into a reused `[]byte`, or `strings.Builder` with `Grow`.
3. **`string([]byte)` / `[]byte(string)` conversions.** Each one **copies** — the language forbids sharing storage because strings are immutable. A hot conversion shows up clearly in `alloc_space`. *Fix:* keep one representation; convert once at the boundary, not per call.
4. **Intermediate slices.** `append`-building a temporary slice, `strings.Split` you immediately range over, a `filter` that allocates a new slice. *Fix:* range the source directly; reuse a scratch slice; preallocate with `make([]T, 0, n)` when `n` is known.
5. **Defensive copies & `append` growth.** Copying a slice "to be safe," or `append` repeatedly reallocating because capacity wasn't reserved. `append` growth is the classic `alloc_objects` tower (one allocation per growth step). *Fix:* preallocate capacity (`make([]T, 0, expectedN)`); copy only when ownership genuinely transfers.

> **Key insight:** Notice the pattern in the fixes — **reuse a buffer, preallocate to a known size, or remove an interface.** Almost every allocation fix is one of those three moves. The profile plus `-m` tells you *which* of the three the line needs.

---

## Worked Example — Profile to Fix

A log-ingestion endpoint formats each line. Throughput is fine until load, then GC `% CPU` climbs. Walk the full loop: **profile → top call site → escape-analysis confirm → fix → verify.**

**The code:**

```go
func formatEntry(e Entry) string {
    parts := []string{}                                   // intermediate slice
    for _, f := range e.Fields {
        parts = append(parts, fmt.Sprintf("%s=%v", f.Key, f.Val))  // Sprintf + boxing per field
    }
    return strings.Join(parts, " ")                       // result string
}
```

**1. Capture and rank by count** (we suspect many-small):

```bash
go test -bench=BenchmarkFormat -benchmem -memprofile=mem.out -memprofilerate=1 ./ingest
```

```
BenchmarkFormat-8   384210   3128 ns/op   1184 B/op   23 allocs/op
```

```bash
go tool pprof -alloc_objects mem.out
(pprof) top
```

```
      flat  flat%        cum   cum%
   3700000 47.4%     3700000 47.4%  fmt.Sprintf
   1900000 24.3%     5600000 71.7%  myapp/ingest.formatEntry
    900000 11.5%      900000 11.5%  runtime.growslice
```

`fmt.Sprintf` tops `alloc_objects` (flat) and `formatEntry` is the high-cum router. `runtime.growslice` in the list is the `append` reallocating — a second, independent allocation source.

**2. `list` to the lines:**

```bash
(pprof) list formatEntry
```

```
   1900000    5600000 (flat, cum)
         .          .   1:func formatEntry(e Entry) string {
    400000     400000   2:    parts := []string{}
    500000     500000   3:        for _, f := range e.Fields {
   1000000    4100000   4:            parts = append(parts, fmt.Sprintf("%s=%v", f.Key, f.Val))
         .          .   5:    }
         .     600000   6:    return strings.Join(parts, " ")
}
```

Line 4 owns the churn: the `append` growth (flat 1.0M, charged to `growslice`) *and* the `Sprintf` (its 3.7M is in `cum`).

**3. Confirm the *why* with escape analysis:**

```bash
go build -gcflags='-m' ./ingest
```

```
./format.go:2:14: []string{} escapes to heap
./format.go:4:42: f.Key escapes to heap          ← boxed into Sprintf's ...any
./format.go:4:49: f.Val escapes to heap          ← boxed into Sprintf's ...any
./format.go:4:24: ... argument does not escape
```

Three confirmed causes: the intermediate `parts` slice escapes, and `Sprintf` boxes both `f.Key` and `f.Val` into `...any`. This matches culprits #1, #2, and #4 exactly.

**4. Fix — apply the three moves (preallocate, drop the interface, reuse a buffer):**

```go
func formatEntry(e Entry, buf []byte) []byte {     // caller passes a reused buffer
    buf = buf[:0]
    for i, f := range e.Fields {
        if i > 0 {
            buf = append(buf, ' ')
        }
        buf = append(buf, f.Key...)                // no boxing — Key is a string
        buf = append(buf, '=')
        buf = strconv.AppendInt(buf, f.Val, 10)    // no Sprintf, no boxing, no temp string
    }
    return buf
}
```

**5. Verify both numbers:**

```bash
go build -gcflags='-m' ./ingest      # the "escapes to heap" lines for 2 and 4 are GONE
go test -bench=BenchmarkFormat -benchmem ./ingest
```

```
BenchmarkFormat-8   2148630   546 ns/op   0 B/op   0 allocs/op
```

`23 allocs/op → 0`, `3128 ns/op → 546`. The escape report no longer flags the lines (static proof) and `allocs/op` is zero (runtime proof). That is a complete, *verified* allocation fix — diagnosis, cause, cure, confirmation.

---

## Common Mistakes

1. **Reading `inuse_space` when you meant `alloc_space`.** The default heap view is often `inuse_space` (retained), which answers a *different question*. For allocation rate, pass `-alloc_space`/`-alloc_objects` explicitly. People "optimize allocation" off the retained view and fix the wrong thing.

2. **Looking at only one of objects/space.** Ranking by `alloc_space` alone hides a 5M-count, 16-byte churn that's hammering the GC; ranking by `alloc_objects` alone hides a 200 MB buffer. The two columns are not redundant — read both.

3. **Stopping at `top`.** A function name isn't a fix. `list <fn>` to get the *line* and the per-line count, or you'll "optimize" the wrong statement inside a busy function.

4. **Profiling at the default sample rate on a short benchmark.** The default (~one sample per 512 KB) under-counts small high-frequency allocations. Set `-memprofilerate=1` for diagnosis; reset it for production.

5. **Acting on the profiler without `-gcflags=-m`.** You see a line allocates and guess the cause — often wrong (you blame `append` when it's actually interface boxing two lines up). Let `-m` name the cause, then fix *that*.

6. **Chasing `cum` instead of `flat`.** A high-cum frame just *calls* the allocator-heavy code; the fix lives at the high-`flat` frame downstream. Follow flat to the real allocating line.

7. **Declaring victory off `ns/op` alone.** Speed can improve for unrelated reasons. The allocation success metric is `allocs/op` (and the disappearance of the `escapes to heap` line), not nanoseconds.

---

## Apply it

1. Find a real component where **Allocation Profiling** affects an interface or dependency.
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

- Which boundary is most affected by Allocation Profiling?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
- A site tops `alloc_space` but barely registers in `alloc_objects`, and another is the reverse — how do the fixes differ?
- Why does per-call-site attribution matter, and how do flat vs cumulative views differ?
- `allocs/op` from a benchmark and a production allocation profile tell different stories — how do you reconcile them?
- How do you see *why* a specific allocation escaped, and how do you confirm a fix removed it?
- Is stack allocation always better than heap allocation, and what can defeat escape analysis even when it "should" work?
- What does async-profiler's `--alloc` mode do, and how does it differ from a CPU profile of the same program?
