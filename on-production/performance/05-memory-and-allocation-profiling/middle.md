# Memory and Allocation Optimization — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Memory and Allocation Optimization** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Memory and Allocation Optimization
> *The junior page taught you to read a heap profile. This page is about doing something with it: why a value lands on the heap in the first place, how to keep it on the stack, when pooling pays off and when it quietly backfires, and how allocation rate — not heap size — is the dial that controls how often the GC steals your CPU.*

---

## Escape Analysis — Why a Value Goes to the Heap

The compiler would *prefer* to put everything on the stack: stack allocation is a pointer bump, and the whole frame is freed for free when the function returns — the GC never sees it. A value is forced onto the heap only when the compiler can't prove its lifetime ends with the function. That proof is **escape analysis**, and you can read its verdict directly:

```bash
go build -gcflags='-m' ./...
# ./main.go:12:9: &User{...} escapes to heap
# ./main.go:20:14: leaking param: cfg
# ./main.go:31:23: make([]byte, n) does not escape
```

`-m` once shows decisions; `-m -m` (or `-gcflags='-m=2'`) shows the *reasoning chain*. The common reasons a value escapes:

- **Returning a pointer to a local.** `func New() *User { u := User{}; return &u }` — `u` must outlive the frame, so it's heap-allocated. (Returning the *value* `User` instead keeps it on the stack until the caller decides.)
- **Storing a pointer in something that outlives the call** — a field of a longer-lived struct, an element of a heap slice, a channel.
- **Interface boxing.** Assigning a concrete value to an `interface{}` (or any interface) boxes it: the value is copied to the heap and the interface holds a pointer. `fmt.Println(x)` escapes `x` for exactly this reason — `...interface{}` boxes every argument.
- **Closures capturing by reference.** A closure captures variables *by reference*, not by value. If the closure escapes (returned, stored, run in a goroutine), every captured variable escapes with it.
- **Size or shape unknown at compile time.** `make([]int, n)` with a non-constant `n` large enough, or anything the compiler can't bound, goes to the heap.

```go
// Escapes: pointer to local is returned.
func NewUser(name string) *User { return &User{Name: name} }

// Does NOT escape: value returned, lives in caller's frame.
func MakeUser(name string) User { return User{Name: name} }
```

> **Key insight:** Escape analysis is *interprocedural but conservative* — the compiler heap-allocates whenever it *can't prove* a value stays local, not only when it's certain it escapes. So small, leaf-ish functions and avoiding "pointer to local out the door" are what keep values on the stack. Don't guess; run `-gcflags=-m` and read the verdict for the exact line.

---

## The Allocation-Rate → GC-Frequency Loop

Here is the relationship that reframes the whole topic. A tracing GC like Go's runs roughly when the live heap has grown by a set fraction since the last collection. So the *frequency* of GC is governed not by how big your heap is, but by **how fast you allocate**:

```
GC interval ≈ (GOGC% × live_heap) / allocation_rate
```

Two services with an identical 200 MB live heap behave completely differently if one allocates 50 MB/s and the other 2 GB/s — the second triggers GC ~40× more often, and each cycle burns CPU on marking and steals cache. This is why allocation-heavy code shows up in the *CPU* profile as `runtime.mallocgc` and `gcBgMarkWorker`, not as a memory problem at all. The bytes get reclaimed fine; you're paying in **throughput**, not in residency.

The practical consequence: **reducing allocations/op is a CPU optimization as much as a memory one.** A loop that drops from `42 allocs/op` to `3` doesn't just save memory — it cuts the GC's workload by an order of magnitude, often recovering more wall-clock time than the allocation savings alone would suggest.

> **Key insight:** Heap *size* is a tuning knob (GOGC). Allocation *rate* is a code property — and it's the one that determines how often the GC interrupts your hot path. Optimize the rate in code; tune the size last.

---

## Preallocation and Growth Amortization

Slices and maps grow by **reallocation**: when capacity runs out, the runtime allocates a larger backing array (Go roughly doubles for small slices, then grows ~1.25× for large ones) and **copies** the old contents over. A slice that grows to N elements one `append` at a time performs O(log N) reallocations and copies a total of ~2N elements along the way — all of it garbage the moment it's superseded.

```go
// Bad: starts at cap 0, reallocates ~log2(10000) times, copying as it goes.
var out []int
for i := 0; i < 10000; i++ { out = append(out, f(i)) }

// Good: one allocation, zero growth copies.
out := make([]int, 0, 10000)
for i := 0; i < 10000; i++ { out = append(out, f(i)) }
```

The fix is to tell the runtime the size up front when you know (or can estimate) it: `make([]T, 0, n)` for slices, `make(map[K]V, n)` for maps (the hint sizes the bucket array so it doesn't rehash repeatedly). You don't need an exact count — even a rough upper bound collapses many reallocations into one.

> **Key insight:** Doubling makes *amortized* append O(1), but "amortized cheap" still produces real garbage on every doubling step. Preallocation converts O(log N) allocations-plus-copies into exactly one. When the final size is knowable, there is no reason not to.

A subtlety: a slice and its backing array are different things. `s = s[:0]` resets the length but **keeps the capacity** — the backing array is reused, zero new allocation. This is the foundation of buffer reuse (next sections).

---

## Value Semantics, In-Place Ops, and the `[]byte`↔`string` Tricks

Many allocations come from creating *new* objects when you could mutate or reuse existing ones.

**Value semantics keep things on the stack.** Passing and returning small structs *by value* (rather than `*T`) often avoids the heap entirely — the value rides in the caller's frame. The instinct that "pointers are cheaper" is wrong for small values: a pointer can *force* an escape that a value wouldn't.

**In-place operations reuse backing storage.** `strings.Builder` and `bytes.Buffer` grow one backing array and write into it, instead of `+`-concatenating which allocates a fresh string per step:

```go
// Allocates a new string every iteration — O(n²) bytes of garbage.
s := ""
for _, p := range parts { s += p }

// One amortized buffer; reuse it across calls with b.Reset().
var b strings.Builder
b.Grow(estimatedLen)            // preallocate the backing array
for _, p := range parts { b.WriteString(p) }
s := b.String()
```

**The `[]byte`↔`string` conversions normally copy.** `string(b)` and `[]byte(s)` each allocate and copy, because Go strings are immutable and the runtime must guarantee the string can't be mutated through the original slice. In hot paths this copy is pure overhead. The standard library already avoids it in the right places — `m[string(keyBytes)]` is special-cased by the compiler to *not* allocate, since the temporary string can't escape the lookup. For your own code, the safe modern tool is `unsafe.String`/`unsafe.Slice` (Go 1.20+):

```go
// Zero-copy view: NO allocation, but the []byte MUST NOT be mutated afterward,
// and the string MUST NOT outlive the backing slice.
s := unsafe.String(unsafe.SliceData(b), len(b))
```

> **Key insight:** The zero-copy `[]byte`↔`string` trick removes a real allocation but **breaks Go's immutability guarantee**. It is correct *only* when you can prove the bytes won't change and the alias won't outlive its source. Reach for it in measured hot paths, never by default — a mutated "immutable" string is a memory-safety bug that corrupts silently.

---

## Object Pooling — `sync.Pool` and When It Hurts

When an object is large, frequently created, and short-lived, recreating it each time is pure allocation pressure. A pool lets you reuse instances across calls. Go's `sync.Pool` is the standard tool:

```go
var bufPool = sync.Pool{
	New: func() any { return new(bytes.Buffer) },
}

func handle(w io.Writer, data []byte) {
	buf := bufPool.Get().(*bytes.Buffer)
	buf.Reset()                 // critical: clear stale state before use
	defer bufPool.Put(buf)
	buf.Write(data)
	// ... use buf ...
	w.Write(buf.Bytes())
}
```

`sync.Pool` is designed for exactly this: a per-P (per-processor) free list that the GC drains on each cycle. But it is sharp, and pooling helps far less often than people assume:

- **It helps** when the pooled object is meaningfully expensive (large buffers, parsers, gzip writers, `bytes.Buffer` reused thousands of times/sec) and the churn is real. The win shows up as a drop in `allocs/op` *and* in GC CPU.
- **It hurts** when objects are small or cheap — the pool's own bookkeeping, the type assertion, and the `Get`/`Put` synchronization can cost more than the allocation you avoided. Pooling a `struct{ x, y int }` is almost always a net loss.
- **Pool churn** is the classic trap: `sync.Pool` is cleared on *every* GC cycle, so objects you `Put` may be gone before the next `Get`. If your get/put rate doesn't comfortably exceed the GC frequency, the pool acts like a cache with a near-zero hit rate — you pay the overhead and still allocate.
- **Variable-size objects fragment the pool.** Pooling slices of wildly different sizes means `Get` often returns one too small, forcing a fresh allocation anyway. Cap the size you put back, or the pool's average payload bloats.

The cardinal correctness rule: **always reset pooled state before use.** A `bytes.Buffer` from the pool still holds the previous caller's bytes. Forgetting `Reset()` leaks data between requests — a real, exploitable bug class.

> **Key insight:** A pool replaces allocation cost with synchronization + bookkeeping + a GC-driven eviction risk. It's a win only when the object is expensive *and* reuse rate dwarfs GC frequency. Benchmark with `-benchmem` before *and* after; a pool that doesn't move `allocs/op` and `ns/op` together is just added complexity.

---

## Reading an Allocation Profile to Find the Worst Site

A heap profile has three lenses, and choosing the wrong one sends you optimizing the wrong line:

| View | `pprof` flag | Measures | Use it to find |
|---|---|---|---|
| **In-use space** | `-inuse_space` | bytes *live now* | leaks, oversized caches, retained working set |
| **In-use objects** | `-inuse_objects` | object *count* live now | many tiny live objects (map/pointer overhead) |
| **Alloc space** | `-alloc_space` | bytes *ever allocated* (cumulative) | sites producing the most GC byte-pressure |
| **Alloc objects** | `-alloc_objects` | objects *ever allocated* (cumulative) | sites producing the most *allocation count* — the GC-frequency driver |

For cutting GC pressure, `-alloc_objects` is usually the right starting lens: GC cost scales with the *number* of allocations more than their total bytes, and `allocs/op` is what `benchmem` reports. A site allocating ten million 24-byte objects hurts more than one allocating a single 200 MB buffer, even though `-alloc_space` ranks the latter higher.

```bash
go test -bench=. -benchmem -memprofile=mem.out
go tool pprof -alloc_objects mem.out
(pprof) top10            # worst call sites by allocation count
(pprof) list MyFunc      # annotated source: allocations per line
```

`list` is the payoff — it shows allocations attributed to each *line*, so you go from "this function allocates a lot" to "*this exact `append`/conversion/closure* is the cost." That line-level attribution is what turns a profile into a fix.

> **Key insight:** `-inuse_*` answers "what's holding memory?" (leaks, residency). `-alloc_*` answers "what's *generating* garbage?" (GC pressure). They diagnose different diseases; reaching for `-inuse_space` when your problem is GC CPU will point you at the wrong code every time.

---

## GC Tuning Basics — GOGC and the Heap Target

`GOGC` (default `100`) sets the heap-growth target: GC triggers when the live heap has grown by `GOGC%` since the last cycle. `GOGC=100` means "run when the heap has doubled"; `GOGC=200` means "wait until it triples." Higher GOGC → fewer, larger collections → less GC CPU but more memory; lower GOGC → the reverse.

```bash
GOGC=200 ./server     # trade RAM for throughput: GC half as often
GOGC=off ./batch      # disable entirely for a short-lived batch job
```

For services with a hard memory ceiling (containers, especially), Go 1.19+ added `GOMEMLIMIT` — a **soft memory limit** that makes the GC run *more aggressively* as the heap approaches the limit, regardless of GOGC. The modern pattern is `GOMEMLIMIT` set near your container limit (with headroom) plus a generous `GOGC`: you get throughput in the common case but avoid the OOM kill when the heap spikes.

The order of operations matters and is constantly inverted:

1. **First, reduce allocation rate in code** (the sections above). This shrinks GC cost *and* memory, and it's the only lever that doesn't trade one resource for another.
2. **Then tune GOGC/GOMEMLIMIT** to dial the remaining memory-vs-CPU trade for your environment.

> **Key insight:** GOGC and GOMEMLIMIT *redistribute* the cost between RAM and CPU; they don't remove it. Tuning them before cutting allocations is treating the symptom. Cut the rate first, then tune the residual trade-off to fit the box you run on.

---

## Worked Example — Escape Output and a benchmem Before/After

A JSON-ish formatter that builds a response line per record. The naive version:

```go
func format(recs []Record) []string {
	out := []string{}                       // cap 0 → grows by reallocation
	for _, r := range recs {
		s := fmt.Sprintf("%s=%d", r.Key, r.Val)  // Sprintf boxes args → escapes
		out = append(out, s)
	}
	return out
}
```

Run escape analysis and the benchmark:

```bash
$ go build -gcflags='-m' .
./format.go:3:9:  []string{} escapes to heap
./format.go:5:23: ... argument does not escape    # but Sprintf's interface boxing does
./format.go:5:24: r.Key escapes to heap
./format.go:5:31: r.Val escapes to heap

$ go test -bench=Format -benchmem
BenchmarkFormat-8    52143    22841 ns/op    14208 B/op    402 allocs/op
```

402 allocs for 100 records: one growing `out`, one boxed `Key` and `Val` each (200), plus the per-call `Sprintf` machinery. Rewrite with preallocation and a builder, dropping `Sprintf`:

```go
func format(recs []Record) []string {
	out := make([]string, 0, len(recs))      // one allocation for the slice
	var b strings.Builder
	for _, r := range recs {
		b.Reset()
		b.WriteString(r.Key)
		b.WriteByte('=')
		b.WriteString(strconv.Itoa(r.Val))   // no interface boxing
		out = append(out, b.String())
	}
	return out
}
```

```bash
$ go test -bench=Format -benchmem
BenchmarkFormat-8   214905    5436 ns/op    4816 B/op    101 allocs/op
```

`402 → 101 allocs/op`, `22.8µs → 5.4µs` (~4.2× faster), and a third the bytes. The remaining 101 are the one slice plus the 100 result strings — irreducible without changing the API (the caller wants `[]string`). The `strconv.Itoa`-vs-`Sprintf` swap alone removed the interface boxing that `-gcflags=-m` flagged on lines `Key`/`Val`. Note the throughput win exceeds the byte win — that's the allocation-rate-to-GC effect from earlier, cashed out as real wall-clock time.

---

## Common Mistakes

1. **Returning `*T` "for efficiency" on small values.** A pointer to a local often *forces* an escape that returning the value by copy would avoid. For small structs, value semantics are frequently cheaper. Check with `-gcflags=-m`.

2. **Optimizing `-alloc_space` when the problem is GC frequency.** Total bytes ranks the one giant buffer first; GC cost is driven by allocation *count*. Use `-alloc_objects` to find the line spraying millions of tiny objects.

3. **Pooling cheap or rarely-reused objects.** `sync.Pool` overhead can exceed the allocation it replaces, and pool churn (cleared every GC) makes a low-reuse pool a near-zero-hit cache. Benchmark before *and* after; if `allocs/op` doesn't drop, remove the pool.

4. **Forgetting to reset pooled objects.** A `bytes.Buffer` from the pool still holds the last caller's data. No `Reset()` → cross-request data leakage, a genuine security bug, not just a perf nit.

5. **`append`-ing in a loop without preallocating.** Known final size and still `var s []T` then `append`? You're paying O(log N) reallocations and copies for nothing. `make([]T, 0, n)` collapses it to one.

6. **Reaching for the zero-copy `unsafe.String` trick by default.** It breaks immutability. Correct only when you can prove the bytes are stable and the alias won't outlive its backing array. Default to the safe copy; use `unsafe` only in a measured, contained hot path.

7. **Tuning GOGC before cutting allocations.** GOGC trades CPU for RAM; it doesn't reduce the work. Cut the allocation rate in code first, then dial GOGC/GOMEMLIMIT for the residual trade-off.

---

## Apply it

1. Find a real component where **Memory and Allocation Optimization** affects an interface or dependency.
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

- Which boundary is most affected by Memory and Allocation Optimization?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
