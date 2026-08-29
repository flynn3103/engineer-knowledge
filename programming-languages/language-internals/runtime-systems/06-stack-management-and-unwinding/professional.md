# Stack Management & Unwinding — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Stack Management & Unwinding** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Guard Pages: Overflow Is a Page Fault

A thread's stack region ends in a **guard page** — one (or several) page(s) mapped with no access. As the stack grows toward lower addresses, the first instruction that reads or writes into the guard page triggers a hardware page fault → `SIGSEGV` on Linux, an access violation on Windows. The runtime installs a handler that recognizes "the faulting address is in/near the guard region of the current thread's stack" and reports **stack overflow** rather than a generic segfault.

Two subtleties bite professionals:

- **The guard page must be big enough to *catch* the overshoot.** A single function with a huge local array can skip *over* a one-page guard in one stack adjustment, writing into valid memory beyond the guard — silent corruption instead of a clean fault. Compilers emit **stack probes** (`-fstack-clash-protection`) that touch each page as the frame grows, guaranteeing the guard is hit. This is also a security feature (stack-clash attacks).
- **The overflow handler runs in a constrained context.** You can't grow the stack to handle the stack-overflow signal, so handlers use an **alternate signal stack** (`sigaltstack`). Without it, the overflow handler itself faults.

### 2. Thread Stack Size Is a Real Resource

Each OS thread reserves address space for its stack (Linux default ~8 MB, tunable via `ulimit -s` or `pthread_attr_setstacksize`; the reservation is mostly lazy/uncommitted until touched). This is fine for dozens of threads and ruinous for millions. The reservation alone (even uncommitted) consumes address space and bookkeeping. **This single fact is why runtimes with massive concurrency cannot use OS thread stacks per task** — and why growable user-space stacks exist.

### 3. Segmented vs Copying Growable Stacks — and the Hot Split

If you want a million goroutines, each stack must start tiny (Go: 8 KB historically, now ~2–8 KB) and grow only as needed. Two strategies:

- **Segmented stacks (Go ≤ 1.2, `-fsplit-stack`).** When a function's prologue detects the current segment is nearly full, it allocates a *new, separate* chunk and links it. The stack becomes a linked list of segments. Simple in principle — but it has the **hot split** pathology: imagine a function call that sits right at a segment boundary inside a hot loop. Each iteration grows (allocate a new segment), returns (free it), grows again — allocating and freeing a segment every iteration, a catastrophic, hard-to-predict slowdown. Performance became a cliff that depended on *exactly where* in the stack a hot call landed.

- **Contiguous copying stacks (Go ≥ 1.3).** When the stack is nearly full, the runtime allocates a **single larger contiguous block** (typically double the size), **copies the entire old stack into it**, fixes up pointers, frees the old block, and continues. Growth is amortized O(1) per byte (geometric doubling), and — crucially — there is *no boundary* for a hot call to straddle, so the hot-split cliff disappears. The cost is the copy itself and the requirement to **relocate pointers** (next concept).

Go's move from segmented to copying stacks (Go 1.3, 2014) is the canonical case study in this whole topic: the segmented design was *elegant* but had an unpredictable performance cliff, and the "just copy it" design was *simpler to reason about* and faster in practice.

### 4. Copying Means Relocating Every Pointer Into the Stack

When the stack moves to a new address, every pointer that pointed *into the old stack* is now dangling. The runtime must find and rewrite them all: pointers in stack slots that point to other stack slots, pointers stored in registers at the moment of the move, and (in Go specifically) interior pointers and pointers handed to other goroutines. This is only possible because the runtime has **precise stack maps**: at the safepoint where growth happens, it knows *exactly* which slots and registers hold pointers and which hold integers. It rewrites each by adding `(new_base − old_base)`.

This is why Go requires **precise** GC and stack maps, and why it imposes rules like "you can't take the address of a stack variable and stash it somewhere the runtime can't track" without the variable *escaping to the heap*. Go's escape analysis decides, at compile time, whether a value can live on the (movable) stack or must go on the heap precisely so that the set of stack-internal pointers is statically known and relocatable. **Stack copying and escape analysis are two sides of the same coin.**

### 5. The Same Stack Maps Scan GC Roots

A tracing garbage collector starts from **roots**: global variables, registers, and *every live pointer on every thread's stack*. To scan a stack root-set precisely (without conservatively treating any integer-that-looks-like-a-pointer as one), the GC reads the **stack map** at each frame's safepoint PC: "slot +16 is a pointer, slot +24 is an int, slot +32 is a pointer." It walks frames (via frame pointers, CFI, or runtime-specific frame info), and at each one consults the map. Conservative collectors (e.g. Boehm) skip the map and scan everything that *might* be a pointer — simpler, but they can retain garbage (false pointers) and *cannot move objects* (they daren't rewrite a maybe-pointer). Precise stack maps are what enable a *moving*, *compacting* collector. (Full GC mechanics live in the garbage-collection topic; here the point is that **root scanning is a stack-walking problem solved with stack maps**.)

### 6. Green-Thread / Coroutine Stacks

Lightweight concurrency comes in two flavors with very different stack stories:

- **Stackful** (Go goroutines, traditional fibers, `ucontext`): each task owns a real, switchable stack. A context switch saves/restores SP and registers and swaps stacks. These can suspend *anywhere* (deep in a call chain) because the whole physical stack is preserved. Cost: each task needs a stack (hence growable/small stacks matter).
- **Stackless** (Rust `async`, C#/JS `async`, Python coroutines): the compiler transforms an `async fn` into a **state machine**; suspension points become states, and locals that live across an `await` are stored in a heap-allocated future object, not on a stack. There's no separate task stack at all — when the future runs, it runs on the *caller's* (executor's) stack. This is extremely memory-efficient (no reserved stacks) but means a task can only suspend at explicit `await` points, and the *physical* stack at any moment reflects the executor, not the logical async caller chain.

### 7. Async Loses the Natural Stack — and Runtimes Rebuild a Logical One

In a stackless async program, when you `await`, your function returns to the executor; the chain of "who awaited whom" is *not* on the physical stack anymore — it's encoded in the linked futures/continuations on the heap. So a crash or a profile inside an async continuation shows a physical backtrace that bottoms out at the **event loop / poll function**, not at the request handler that logically initiated the work. This is the infamous "useless async stack trace."

Runtimes fight this with **async logical stacks**: by recording the chain of awaiting tasks (parent continuation pointers), they can splice together a *logical* backtrace that crosses suspension points — e.g. Rust's `tracing`/task-dump facilities, .NET's async stack-trace reconstruction, Node's `async_hooks`/async stack traces, Python's `asyncio` task stacks. The physical unwinder gives you one segment; the runtime stitches the rest from continuation metadata. Designing observable async systems means *deliberately* capturing this context (trace/span propagation) rather than relying on physical backtraces.

### 8. Tail-Call Elimination Reuses the Frame

A **tail call** — a call in the return position — can reuse the current frame instead of pushing a new one: the callee returns directly to *our* caller. This makes deep tail recursion run in O(1) stack space (essential in functional languages; mandated in Scheme, opportunistic in LLVM/`musttail`, and explicit in WebAssembly's tail-call proposal). The consequence for *this* topic: the eliminated frame is genuinely **not on the stack**, so backtraces and unwinding correctly skip it. This is correct, but it surprises debugging ("my caller vanished") and can make some stack-overflow bugs *disappear* when optimization kicks in — and reappear at `-O0`.

### 9. Fleet-Scale Profilability: Why Frame Pointers Came Back

Operationally, the dominant pain is the senior-level `[unknown]` flame graph multiplied across thousands of machines. DWARF-based sampling is expensive (it copies and interprets the stack at every sample) and fragile in signal handlers; LBR is shallow and hardware-specific. Frame-pointer walking is cheap, deep, and signal-safe — at a ~1–2% steady-state cost. For continuous, always-on, fleet-wide profiling (the modern norm), that trade flipped: **major distributions and large operators re-enabled `-fno-omit-frame-pointer` by default** (Fedora and others, early 2020s) because *being able to profile every machine all the time* is worth more than 1%. This is the practical climax of the whole topic: a decade-old optimization was reverted because *observability* became the dominant concern.

---

## Code Examples

### Example 1: Watch a Go stack grow (and the runtime copy it)

```go
package main

import "fmt"

// Deep recursion forces the goroutine stack to grow repeatedly.
// Each growth copies the whole stack to a 2x block and relocates pointers.
func depth(n int, acc *int) int {
    var local [128]byte // pin some frame size so growth happens sooner
    _ = local
    if n == 0 {
        return *acc
    }
    *acc++
    return depth(n-1, acc)
}

func main() {
    acc := 0
    fmt.Println(depth(100000, &acc))
    // Run with: GODEBUG=gctrace=1 go run main.go     (see GC)
    // Inspect growth with the runtime/debug + pprof, or read runtime.morestack.
}
```

Each time a goroutine's prologue (`runtime.morestack`) sees the stack near full, the runtime doubles it, **copies**, and **relocates the `*acc` pointer** to point into the new stack location. The program is correct only because Go's stack maps let the runtime find and rewrite that pointer.

### Example 2: Demonstrate guard-page overflow vs a clean error

```go
// Go turns goroutine stack exhaustion into a clean fatal error,
// because it controls growth and can detect the limit (default 1 GB).
package main

func boom(n int) int { return boom(n + 1) } // unbounded recursion

func main() {
    boom(0)
    // fatal error: stack overflow
    // runtime: goroutine stack exceeds 1000000000-byte limit
}
```

```c
// C has no growable stack: unbounded recursion runs into the guard page
// and dies with a raw segfault — no nice message.
int boom(int n) { return boom(n + 1); }
int main(void) { return boom(0); } // Segmentation fault (core dumped)
```

Same root cause (unbounded recursion), radically different reporting: Go's managed stack gives a precise message; C's fixed stack gives a `SIGSEGV` from the guard page.

### Example 3: Set up an alternate signal stack to even *report* an overflow

```c
#include <signal.h>
#include <stdlib.h>
#include <unistd.h>

static char altstack[SIGSTKSZ];

// Without sigaltstack, a SIGSEGV from stack overflow can't be handled —
// the handler itself needs stack space the overflowed thread doesn't have.
void install_overflow_handler(void (*h)(int, siginfo_t*, void*)) {
    stack_t ss = { .ss_sp = altstack, .ss_size = sizeof altstack, .ss_flags = 0 };
    sigaltstack(&ss, NULL);
    struct sigaction sa = {0};
    sa.sa_sigaction = h;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK; // <-- run handler on altstack
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, NULL);
}
```

This is exactly how runtimes (and ASan, and crash reporters) manage to report a stack overflow instead of recursing the handler into oblivion.

### Example 4: The "useless" async backtrace, and fixing it with context

```python
import asyncio

async def deepest():
    raise ValueError("boom")          # crash inside an awaited coroutine

async def middle():
    await deepest()

async def handler():
    await middle()

asyncio.run(handler())
# The traceback DOES chain here because asyncio/Python rebuilds it.
# In many runtimes the *physical* stack at the throw would bottom out at
# the event loop's `poll`/`run` — the logical caller chain (handler->middle->
# deepest) lives in task/continuation metadata, not the physical stack.
```

The lesson: physical backtraces in async code are only as good as the runtime's logical-stack reconstruction. For production, propagate explicit trace/span context across `await`s rather than trusting the backtrace.

### Example 5: Make the fleet profilable

```bash
# The modern default for profilable production binaries:
gcc -O2 -fno-omit-frame-pointer -fasynchronous-unwind-tables svc.c -o svc
# now continuous profilers (perf, parca, pyroscope, async-profiler) get
# full, signal-safe, low-overhead call graphs across every host.

# Verify before you ship — flame graph should NOT be a sea of [unknown]:
perf record -g ./svc && perf report --stdio | head
```

---

## Coding Patterns

**Pattern: Bound recursion on untrusted input.** Unbounded recursion on user data (deeply nested JSON/XML, attacker-controlled depth) is a stack-overflow DoS. Convert to iteration with a heap stack, or enforce an explicit depth limit. This is true even in Go (1 GB goroutine limit is still a crash).

**Pattern: Keep large buffers off the (growable) stack.** A giant local array forces immediate stack growth (Go) or can jump the guard page (C). Heap-allocate big buffers; in Go this also avoids triggering early stack copies in hot paths.

**Pattern: Install an alternate signal stack in any process that catches `SIGSEGV`.** Crash reporters, sanitizers, and overflow-detecting servers all need `sigaltstack` + `SA_ONSTACK`, or the handler can't run when the stack is exhausted.

**Pattern: Propagate logical context across `await`.** Don't rely on async physical backtraces. Thread a trace/span/request ID through the call chain (or use the runtime's structured async-context facility) so you can reconstruct *who* triggered work.

**Pattern: Build production binaries for profilability by default.**

```bash
# A sane default trio for server binaries:
-O2 -fno-omit-frame-pointer -fasynchronous-unwind-tables
```

Decide once, fleet-wide; don't discover at 3 a.m. that you can't profile the hot host.

**Pattern: Be aware of escape analysis when you measure Go stack behavior.** `go build -gcflags=-m` shows what escapes to the heap (and thus can't be relocated as part of a stack). Unexpected escapes change allocation and GC pressure.

---

## Best Practices

1. **Treat unbounded recursion on input as a security bug.** Cap depth or iterate. Fuzz the depth.
2. **Always pair `SIGSEGV` handling with `sigaltstack`.** Otherwise you can't even report a stack overflow.
3. **Enable stack-clash protection** (`-fstack-clash-protection`) for code with large frames or hostile input, so big allocations can't skip the guard page.
4. **Default production builds to frame pointers + async unwind tables** for fleet-wide, low-overhead, signal-safe profiling.
5. **Don't trust async physical backtraces; design observability in.** Propagate trace context across suspension points.
6. **Mind escape analysis in copying-stack runtimes.** Know what lives on the (movable) stack vs the heap; keep large/long-lived data on the heap.
7. **Size OS-thread stacks deliberately.** For thread-pool-heavy native services, default 8 MB × N threads can exhaust address space; tune `pthread_attr_setstacksize` to real need.
8. **Verify profilability and backtraces in CI/staging**, not in an incident. A `[unknown]`-free flame graph is a shippable artifact check.

---

## Edge Cases & Pitfalls

- **Huge local frame jumps the guard page.** A single multi-MB local array can write *past* a one-page guard into valid memory — silent corruption, not a fault. Needs stack probes / clash protection.
- **Overflow handler without `sigaltstack` recurses.** The `SIGSEGV` handler needs stack the overflowed thread doesn't have; it faults again. Symptom: a process that vanishes with no crash report.
- **Pointer into a Go stack handed to C / stored opaquely.** If the runtime can't track it, a stack copy invalidates it. cgo rules forbid passing Go pointers to Go pointers across the boundary precisely because the stack can move. Violations are crashes that reproduce only under stack growth.
- **Conservative GC can't move objects.** If any "maybe pointer" might be an integer, you can't rewrite it, so you can't compact. Mixing conservative scanning with a moving collector is a design contradiction.
- **Async backtrace bottoms out at the executor.** Crash inside a continuation shows the event loop, not the logical caller. Without logical-stack reconstruction you can't tell which request failed.
- **Tail-call elimination removes frames from backtraces.** Correct, but it makes "where's my caller?" debugging confusing, and `-O0` vs `-O2` can change whether deep tail recursion overflows.
- **Stack growth at an inopportune time.** In Go, stack growth happens at function prologues (safepoints). Code that assumes addresses of stack locals are stable across a call that triggers growth is wrong — another reason such addresses must escape to the heap if shared.
- **`ulimit -s unlimited` masks bugs.** It doesn't make recursion safe; it just delays the crash and can cause the stack to collide with the heap/mmap region in confusing ways.
- **Mismatched stack size between thread creator and library.** A library that recurses deeply on a thread someone else created with a tiny stack overflows unexpectedly. Document stack-depth needs.

---

## Apply it

1. Define the user or business outcome that **Stack Management & Unwinding** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Stack Management & Unwinding?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
