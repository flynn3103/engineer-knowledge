# Runtimes (Language Runtime Support) — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Runtimes (Language Runtime Support)** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Memory Contract: Allocation Calls, Write Barriers, and Stack Maps

The compiler's relationship with memory management has three parts.

**(a) Allocation calls.** Whenever a value must live on the heap, the compiler emits a call into the allocator. In Go that's `runtime.mallocgc`; in Java the JIT emits a fast-path bump-pointer allocation with a slow-path call into the runtime; in C++ `new` lowers to `operator new`. **Escape analysis** decides *whether* a value escapes to the heap at all — if a value provably stays local, the compiler keeps it on the stack and emits **no** allocation call, saving both the allocation and the future GC work.

```go
func a() *int { x := 0; return &x } // x ESCAPES -> heap allocation (runtime call)
func b() int  { x := 0; return x  } // x stays on the stack -> no allocation
```

**(b) Write barriers.** A *concurrent* or *generational* garbage collector runs *while your program mutates the object graph*. If your code makes object A point to object B, and the GC has already scanned A but not B, it might wrongly conclude B is garbage. To prevent this, the compiler emits a **write barrier**: a tiny snippet around every pointer-into-heap write that informs the GC "this pointer changed." This is a direct compiler obligation — the GC algorithm only works if the compiler instruments pointer writes correctly.

```text
You write:        obj.field = ptr

Compiler emits:   gcWriteBarrier(&obj.field, ptr)   // when GC is in a phase that needs it
                  obj.field = ptr
```

**(c) Stack maps for roots.** To free garbage, the GC must know what's *reachable*, starting from **roots**: globals, and every pointer currently live on a thread's stack and in registers. The compiler emits **stack maps** — metadata that says, at each safepoint, "slot 3 holds a pointer, slot 4 is an integer." Without stack maps the GC couldn't distinguish a pointer from an integer that happens to look like an address. (This is precisely why *precise* GC requires compiler cooperation, while *conservative* GC — used when no stack maps exist — must guess.)

### 2. The Scheduler Contract: Spawn Calls and Safepoints

For a language with green threads, the compiler's job is twofold.

**(a) Spawn the task.** `go f()` lowers to a runtime call (`runtime.newproc`) that creates a goroutine struct with its own small stack and puts it on a run queue. The runtime's **scheduler** then runs it.

**(b) Make tasks preemptible.** Here's the subtle part. The scheduler must be able to **pause** a running goroutine — to run the GC (which needs all goroutines stopped at safepoints), or to give another goroutine a turn so one goroutine can't hog a thread. But you can't pause a thread at an arbitrary instruction safely (it might be mid-write, holding pointers in registers the GC can't decode). So the compiler arranges **safepoints** — places where pausing is safe — and historically emitted **cooperative preemption checks** (e.g. a check at function entry: "has the scheduler asked me to yield?"). Modern Go (1.14+) added **asynchronous preemption** using signals, but the runtime still needs compiler-provided stack maps to safely stop a goroutine at the signal point.

```text
Function prologue (conceptually):
  if g.stackguard triggered (preempt requested OR stack low):
      call runtime.morestack  // this path also handles preemption/GC requests
  ... function body ...
```

The same prologue check serves *two* runtime needs: **stack growth** and **preemption**. That's an elegant reuse — one check, two jobs.

### 3. M:N Scheduling and Work Stealing

Go's scheduler is the canonical example. It uses three entities, the **G-M-P** model:

- **G** — a goroutine (the task and its stack).
- **M** — a "machine", i.e. an OS thread.
- **P** — a "processor", a scheduling context that owns a local run queue of Gs and must be held by an M to run Go code.

The number of P's defaults to `GOMAXPROCS` (number of CPUs). Each P has a **local run queue** of goroutines; there is also a **global run queue**. When a P's local queue is empty, its M **steals** half the goroutines from another P's queue — **work stealing** — to balance load without a central bottleneck. When a goroutine makes a **blocking syscall**, the runtime can detach the M from the P and hand the P to another M, so the blocking goroutine doesn't freeze a whole CPU's worth of work.

The payoff: goroutines are *cheap* (a few KB of stack, created in nanoseconds) and you can have **millions** of them, because the runtime multiplexes them onto a handful of OS threads. The cost: the runtime must do bookkeeping, and the compiler must emit the safepoints/stack-growth checks that make it all work.

### 4. The Stack Contract: Growable Stacks and Prologue Checks

An OS thread has a large fixed stack (often 1–8 MB). A million goroutines with 1 MB stacks each would need a terabyte of memory — impossible. So green-thread runtimes give each task a **small** stack (Go starts at 8 KB) and **grow it on demand**.

How does the runtime know when to grow? The **compiler** emits a check in (almost) every function's prologue comparing the stack pointer against a guard. If the function's frame would exceed the current stack, the prologue calls `runtime.morestack`, which allocates a **bigger** stack, **copies** the old stack's contents over (Go uses *contiguous, copying* stacks since 1.4; older Go used *segmented* stacks), fixes up pointers into the stack, and resumes. Copying stacks is only possible because the compiler's **stack maps** tell the runtime which slots are pointers that must be relocated.

This is a deep compiler-runtime cooperation: the language's cheap-concurrency superpower (millions of goroutines) depends on the compiler instrumenting *every function* with a stack check. The deep mechanics of stack copying and pointer fixup are covered in the runtime-systems section; the key middle-level fact is **the compiler pays a small per-call tax so the runtime can keep stacks tiny.**

### 5. Bootstrap: What Runs Before `main`

When the OS loads your binary, control goes to the runtime's entry, not `main`:

1. **`_start` / `rt0`** — set up the initial stack, read `argc`/`argv`/`envp`.
2. **Runtime init** — initialize the **heap** and allocator, set up the **GC**, create the initial **P/M/G** (for Go), set `GOMAXPROCS`, parse `GODEBUG`/`GOGC` environment knobs.
3. **Static initializers** — run global constructors / package `init` functions. On ELF these are collected in `.init_array` and run in order; in Go, package-level `var` initializers and `init()` functions run after dependency ordering.
4. **Call `main`** — finally, your code runs.
5. **Exit** — after `main` returns, the runtime tears down and calls `exit`.

A heavy static initializer (e.g. building a big lookup table, opening a connection) runs in step 3 and *delays* the start of your `main` — a real source of startup latency.

---

## Code Examples

### Example 1 — Escape analysis decides allocation (Go)

```go
package main

type Point struct{ X, Y int }

//go:noinline
func makeLocal() int {
    p := Point{1, 2}     // does NOT escape -> stack, no runtime allocation
    return p.X + p.Y
}

//go:noinline
func makeEscaping() *Point {
    p := Point{1, 2}     // address returned -> escapes -> runtime.newobject (heap)
    return &p
}

func main() { _ = makeLocal(); _ = makeEscaping() }
```

Run `go build -gcflags='-m' .` and the compiler tells you: `p escapes to heap` for the second function. The first emits no allocation; the second emits a runtime allocation call and creates future GC work.

### Example 2 — Cheap goroutines vs OS threads

```go
package main

import (
    "fmt"
    "sync"
)

func main() {
    var wg sync.WaitGroup
    for i := 0; i < 1_000_000; i++ { // a MILLION goroutines is fine
        wg.Add(1)
        go func(n int) { defer wg.Done(); _ = n * n }(i)
    }
    wg.Wait()
    fmt.Println("done")
}
```

A million OS threads would exhaust memory and the kernel's thread limits. A million goroutines is routine: each starts with an 8 KB stack the runtime grows only if needed, and the scheduler multiplexes them onto `GOMAXPROCS` OS threads. This is the scheduler + growable-stack contract paying off.

### Example 3 — A goroutine that never yields (pre-1.14 problem)

```go
package main

import "runtime"

func main() {
    runtime.GOMAXPROCS(1)
    go func() {
        for {           // tight loop, no function calls, no allocations
        }               // pre-Go-1.14: this could starve the scheduler forever
    }()
    select {}           // would never run other goroutines before async preemption existed
}
```

Before Go 1.14, preemption was **cooperative** — it only happened at function-call safepoints. A loop with no calls hit no safepoint and could monopolize the only P. Go 1.14 added **asynchronous preemption** (signal-based), so the scheduler can interrupt even a tight loop. This example shows *why* safepoints matter and what happens when a goroutine never reaches one.

### Example 4 — Forcing stack growth (Go)

```go
package main

import "fmt"

func recurse(depth int) int {
    var big [4096]byte // each frame is large; stacks must grow as we recurse
    big[0] = byte(depth)
    if depth == 0 {
        return int(big[0])
    }
    return recurse(depth-1) + int(big[1])
}

func main() {
    fmt.Println(recurse(2000)) // the runtime grows (copies) this goroutine's stack several times
}
```

Each call's prologue checks the stack guard; as the deep recursion with fat frames consumes the 8 KB initial stack, `runtime.morestack` allocates a bigger stack and copies the old one over — transparently, thanks to compiler-emitted prologue checks and stack maps.

### Example 5 — Static initializer runs before `main` (Go)

```go
package main

import "fmt"

var table = buildTable() // runs during bootstrap, BEFORE main

func buildTable() map[int]int {
    fmt.Println("building table (before main!)")
    m := make(map[int]int)
    for i := 0; i < 5; i++ {
        m[i] = i * i
    }
    return m
}

func init() { fmt.Println("init() runs before main too") }

func main() { fmt.Println("main:", table[3]) }
```

Output order proves it: the table build and `init()` print *before* `main`. Heavy work here is paid at startup — a real consideration for short-lived or serverless programs.

---

## Coding Patterns

### Pattern 1 — Keep hot allocations on the stack

```go
// Returning a pointer forces a heap allocation (escape).
func newBuf() *[256]byte { var b [256]byte; return &b } // escapes

// Pass a buffer in; it can stay on the caller's stack.
func fill(b *[256]byte) { b[0] = 1 }                     // no new allocation here
```

### Pattern 2 — Pool reusable objects to cut allocator/GC traffic

```go
var bufPool = sync.Pool{New: func() any { return make([]byte, 0, 4096) }}

func handle() {
    buf := bufPool.Get().([]byte)
    defer bufPool.Put(buf[:0])
    // ... use buf without allocating a fresh slice each time ...
}
```

### Pattern 3 — Don't spawn unbounded goroutines; bound concurrency

```go
sem := make(chan struct{}, 100) // at most 100 concurrent tasks
for _, job := range jobs {
    sem <- struct{}{}
    go func(j Job) { defer func() { <-sem }(); process(j) }(job)
}
```

Goroutines are cheap, but each still has a stack and scheduler bookkeeping; unbounded fan-out can still exhaust memory.

### Pattern 4 — Keep `init`/static initializers light

```go
// Prefer lazy initialization over heavy work at startup.
var table map[int]int
var once sync.Once

func getTable() map[int]int {
    once.Do(func() { table = buildExpensiveTable() }) // paid on first use, not at startup
    return table
}
```

---

## Best Practices

1. **Use escape analysis as a guide, not a religion.** Check `-gcflags=-m`, reduce obvious escapes in hot paths, but don't contort code for micro-gains.
2. **Bound your goroutines.** Cheap is not free; use semaphores or worker pools for fan-out.
3. **Watch GC with the runtime's own tools.** `GODEBUG=gctrace=1`, `runtime.ReadMemStats`, pprof's heap profile — measure allocation pressure rather than guessing.
4. **Keep startup work lazy.** Heavy static initializers delay `main`; defer them to first use when possible.
5. **Respect safepoints in tight loops.** On older runtimes (or in other languages with cooperative scheduling), insert a yield in a long compute loop; on modern Go async preemption handles it.
6. **Don't assume goroutine = thread.** Blocking inside a goroutine on a C call or a busy loop has different effects than blocking an OS thread; know your scheduler's behavior.
7. **Tune `GOMAXPROCS`/`GOGC` deliberately** when profiling shows scheduler or GC limits, and document why.

---

## Edge Cases & Pitfalls

- **Tight compute loop with no calls starves other tasks (cooperative schedulers).** Mitigated by async preemption in modern Go, but still a classic trap in green-thread systems.
- **A blocking C call (cgo) pins an OS thread.** The runtime can't preempt code running in C; a long C call holds an M and can reduce effective parallelism. (Foreign-runtime interop is covered in the FFI/interop section.)
- **Escape analysis is conservative.** It heap-allocates when in doubt; a small refactor (avoid returning a pointer, avoid interface boxing) can flip a value back to the stack.
- **Interface boxing allocates.** Assigning a concrete value to an `interface{}` may allocate to store the value — a hidden runtime allocation.
- **Deep recursion triggers repeated stack copies.** Each growth copies the stack; pathological recursion can spend real time in `morestack`.
- **Heavy package `init` ordering bugs.** Initialization order across packages can surprise you; a global depending on another package's not-yet-run `init` is a bug.
- **GC pauses correlate with latency tails.** A request that lands during a stop-the-world phase sees added latency; this is a p99 problem, not an average problem.

---

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "Goroutines are free." | They're cheap, not free — stack + scheduler bookkeeping per goroutine. |
| "The GC handles everything; allocations don't matter." | Allocations create GC work; reducing them improves throughput and latency. |
| "Spawning a goroutine starts a thread." | It enqueues a task on a P; the scheduler runs it on an existing M. |
| "A `for {}` loop is harmless." | On cooperative schedulers it can starve everything; even modern runtimes only fixed this recently. |
| "Stacks are fixed-size." | Green-thread stacks grow (and Go copies them); the compiler emits the checks. |
| "Static init is part of `main`." | It runs during bootstrap, *before* `main`. |
| "Write barriers are optional optimization." | They're a correctness requirement for concurrent/generational GC; the compiler must emit them. |

---

## Tricky Points

- **One prologue check, two jobs.** The Go function prologue's stack-guard comparison handles *both* stack growth *and* preemption requests (the guard is set to an impossible value to force entry into `morestack`, which then notices a preemption request). Elegant overloading of a single check.
- **Precise vs conservative GC is a compiler question.** Precise GC needs stack maps (compiler-emitted). Languages without that metadata (or C extensions) fall back to conservative scanning, which can keep garbage alive by accident.
- **Work stealing avoids a central scheduler lock.** The genius of per-P local queues + stealing is that the common case (run from your own queue) needs no global synchronization; stealing is the rare, slow path.
- **Async preemption needs cooperation even when it's "asynchronous."** A signal interrupts the goroutine, but the runtime still needs a valid stack map *at the interrupted instruction* to safely stop it — so the compiler still does the heavy lifting.
- **Stacks moving breaks naive pointers-into-stack.** Because Go *copies* stacks, you cannot hold a raw pointer into a goroutine's stack across a potential growth point and expect it to stay valid — the runtime fixes up known pointers, but cgo/unsafe code can be caught off guard.

---

## Apply it

1. Find a real component where **Runtimes (Language Runtime Support)** affects an interface or dependency.
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

- Which boundary is most affected by Runtimes (Language Runtime Support)?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
