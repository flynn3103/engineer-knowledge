# Runtimes (Language Runtime Support) — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Runtimes (Language Runtime Support)** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Write Barriers and the Tri-Color Invariant

A concurrent mark-sweep GC colors objects white/gray/black and must preserve the **strong tri-color invariant**: *no black object holds a pointer to a white object* (a black object is "done", so the GC won't revisit it; if it points to an untracked white object, that object would be freed while live). Mutator pointer writes can violate this, so the compiler emits a **write barrier** on heap pointer stores.

Two classic shapes:

- **Dijkstra insertion barrier:** when you store `slot = ptr`, shade `ptr` gray (push it onto the GC work list). Now no black-to-white edge can be created unseen.
- **Yuasa deletion barrier (snapshot-at-the-beginning):** when you overwrite `*slot`, first remember the *old* value so the collector still scans what was reachable at the cycle's start.

Go uses a **hybrid (Yuasa + Dijkstra)** barrier so it can avoid re-scanning stacks (stacks are scanned once and stay black). The barrier is *conditional*: it only does real work while the GC is in the mark phase. Conceptually the compiler emits:

```text
store of pointer p into heap slot s:
    if writeBarrier.enabled {           // a global flag the GC flips on at mark start
        runtime.gcWriteBarrier(s, p)    // record old/new for the marker
    }
    *s = p
```

The cost is a predicted-not-taken branch on the fast path (GC off) and a buffered record on the slow path. This is the price the *compiler* pays so the *GC* can run concurrently. Crucially, **only heap pointer writes are barriered** — stack writes are not, which is why stacks must be re-scanned at a safepoint (or kept black via the hybrid barrier).

### 2. Safepoints: How You Actually Stop a Thread

The GC's mark/sweep and the scheduler's preemption both need threads stopped at points where stack maps are valid. There are two strategies:

- **Cooperative / polling safepoints (HotSpot, older Go):** the compiler inserts **polls** at loop back-edges and method entries/exits. To trigger, the runtime makes a special **poll page** unreadable; the next poll faults, the signal handler parks the thread. This guarantees every thread reaches a safepoint quickly without per-poll cost in the common case (the page is readable, the poll is a cheap load).
- **Asynchronous preemption (Go 1.14+):** the runtime sends a signal (`SIGURG`) to a running goroutine. The signal handler checks whether the interrupted PC is at an **async-safe point** (one with a valid register map); if so it preempts there, otherwise it sets a flag and lets the goroutine reach a cooperative point. This solved the "tight loop never yields" problem — but it *still* requires the compiler to have emitted register maps broadly enough that most instructions are async-safe.

The senior insight: **"stop the world" is never instantaneous.** It's "ask all threads to reach a safepoint and wait for the last one." A thread stuck in a long syscall, in barrier-free C code (cgo), or in a region with no safepoint can lengthen the pause. Safepoint *latency* is a real tail-latency contributor.

### 3. Exception Handling: Zero-Cost EH and the Personality Routine

Modern C++/Rust use **table-driven (zero-cost) exceptions**: the *happy path* has no overhead — no flags pushed, no setjmp. Instead, the compiler emits **metadata**:

- **Unwind tables** (`.eh_frame`, DWARF CFI) describing, for each PC range, how to restore callee-saved registers and find the return address — enough to walk *up* the stack.
- **LSDA** (Language-Specific Data Area, `.gcc_except_table`) describing which call sites are inside `try`/have cleanups, and which handlers (`catch`/landing pads) apply.

When an exception is thrown (`throw`/`panic!`), the runtime's **unwinder** (`_Unwind_RaiseException`) walks frames using the unwind tables and, **for each frame, calls that language's personality routine** (`__gxx_personality_v0` for C++, the Rust equivalent). Two phases:

1. **Search phase:** the unwinder asks each personality routine "do you handle this?" *without* modifying state, until a handler is found. If none, terminate (and you can inspect the full stack — nothing has been run yet).
2. **Cleanup phase:** unwind again, this time the personality routine runs **cleanup landing pads** (C++ destructors, Rust `Drop`, `finally`) in each frame, until control transfers to the handler.

The compiler's obligation is to emit the tables and the landing pads; the runtime provides the unwinder and you (or the language) provide the personality routine. This is why "zero-cost" means *zero cost when no exception is thrown* — the cost is all in metadata size and in the slow throw path. (Go's `panic`/`recover` is a *different*, simpler mechanism layered on `defer` chains, not Itanium unwinding — a deliberate runtime design choice.)

### 4. Async/Await → State Machine: The Coroutine Transform

This is the marquee senior topic. An `async fn` looks like sequential code with suspension points (`.await`), but there are **no OS threads to block on** and the function must be able to **suspend and resume**. The compiler solves this with a **coroutine lowering**: it rewrites the function into a **state machine**.

Consider conceptual Rust:

```rust
async fn fetch_two(a: Url, b: Url) -> (Resp, Resp) {
    let ra = get(a).await;   // suspension point 1
    let rb = get(b).await;   // suspension point 2
    (ra, rb)
}
```

The compiler generates (conceptually) a struct and a `poll`:

```rust
enum FetchTwo {
    Start { a: Url, b: Url },
    AwaitingA { fut: GetFut, b: Url },        // saved: in-flight future + locals still needed
    AwaitingB { fut: GetFut, ra: Resp },      // saved: ra crosses the second await
    Done,
}

impl Future for FetchTwo {
    type Output = (Resp, Resp);
    fn poll(self: Pin<&mut Self>, cx: &mut Context) -> Poll<(Resp, Resp)> {
        loop {
            match *self {
                Start { a, b }       => { let fut = get(a); *self = AwaitingA { fut, b }; }
                AwaitingA { fut, b }  => match fut.poll(cx) {
                    Pending     => return Poll::Pending,     // SUSPEND: state preserved in self
                    Ready(ra)   => { let fut2 = get(b); *self = AwaitingB { fut: fut2, ra }; }
                },
                AwaitingB { fut, ra } => match fut.poll(cx) {
                    Pending     => return Poll::Pending,
                    Ready(rb)   => { let out = (ra, rb); *self = Done; return Poll::Ready(out); }
                },
                Done                  => unreachable!(),
            }
        }
    }
}
```

The key mechanics:

- **The discriminant** (the enum tag) records *which `.await` we last suspended at* — i.e., where to resume.
- **The variant's fields** are exactly the **locals live across that suspension point** (the compiler's liveness analysis determines this — the same kind of analysis used for register allocation). Locals *not* live across an await don't need saving.
- **Suspension is just returning `Pending`**; the state (the struct) is preserved by the *caller* who owns it. **Resumption is just calling `poll` again**; the `match` jumps straight back to the right state.
- **No stack is captured.** Unlike a green thread (which suspends a whole call stack), an async state machine captures only the live locals into a flat struct — that's why async tasks can be far cheaper in memory than goroutine stacks, and why this is sometimes called **stackless** coroutines (vs. **stackful** green threads).
- **The executor** (Tokio in Rust, the .NET thread pool + synchronization context in C#) owns the loop: it `poll`s the top-level future; on `Pending` it parks the task and, via the `Waker` in `cx`, the I/O reactor wakes it when the awaited resource is ready, then `poll`s again.

C# `async/await` does the same thing — the compiler builds a struct implementing a state machine (`IAsyncStateMachine`) with a `MoveNext()` method and an `int _state` field. JavaScript engines lower `async`/`await` (and generators) similarly. The transform is the same idea across languages: **straight-line code with suspension points becomes a struct + a resumable method.**

**Self-reference and `Pin`.** A saved local can be a *reference to another saved local* (e.g., a buffer and a slice into it both live across an await). Then the state machine is **self-referential** — moving it in memory would dangle the internal pointer. Rust's answer is `Pin<&mut Self>`: a contract that the future won't be moved after polling begins. This is the deepest consequence of the stackless transform leaking into the type system.

### 5. Stackless vs Stackful: Two Runtime Strategies for "Cheap Concurrency"

There are two ways a runtime gives you cheap concurrency, and the compiler's job differs:

- **Stackful (green threads / goroutines, Go, Erlang):** each task has a real (growable) stack; suspension saves the *whole* stack and the scheduler swaps in another. The compiler emits stack-growth checks and stack maps; suspension is transparent (you write blocking-looking code, e.g. `<-ch`).
- **Stackless (async/await state machines, Rust, C#, JS):** no per-task stack; suspension is a `return Pending` from a generated state machine. The compiler does the coroutine transform; suspension is *visible* in the type (`Future`, `Task`) and at call sites (`.await`).

The trade: stackful is ergonomic ("everything looks synchronous", any function can yield) but stacks cost memory and the runtime is heavier; stackless is memory-lean and runtime-light (you can run it with *no* GC) but "colors" functions (async vs sync) and leaks `Pin`/`Send` complexity into types. Rust chose stackless precisely so async needs **no runtime baked into the language** — you bring your own executor.

### 6. Runtime Startup, In Detail

The senior view of bootstrap:

```text
_start (crt0 / runtime rt0)
  └─ set up initial stack, read argc/argv/envp, align stack
  └─ TLS setup (thread-local storage base)
  └─ runtime init:
        heap/arena reservation, allocator init
        GC init (set GOGC/heap goal), spawn background GC worker
        scheduler init (allocate P's = GOMAXPROCS, create m0/g0)
        signal handlers installed (incl. async-preempt SIGURG, fault handlers)
  └─ __libc_csu_init / .init_array  → run static constructors in order
        (C++ global ctors, Go package init() after dependency topo-sort)
  └─ call main()
  └─ on return: run atexit/finalizers, flush, _exit(code)
```

Two senior implications: (1) **static initializers run single-threaded, before the scheduler is "open for business,"** so heavy or ordering-sensitive init is risky and slow; (2) **the GC and a background worker may already be running before `main`**, which is why even an idle program shows runtime threads.

---

## Code Examples

### Example 1 — A hand-written future shows what the compiler generates (Rust)

```rust
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};

// This is roughly what `async { delay(); 42 }` compiles to.
struct Delay { polls: u32 }

impl Future for Delay {
    type Output = i32;
    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<i32> {
        if self.polls < 3 {
            self.polls += 1;
            cx.waker().wake_by_ref(); // ask the executor to poll us again
            Poll::Pending             // SUSPEND: our state (polls) lives in the struct
        } else {
            Poll::Ready(42)           // RESUME to completion
        }
    }
}
```

The `polls` field is a saved local that survives across suspensions — exactly what the coroutine transform does automatically for every cross-`.await` local.

### Example 2 — Why locals across an await get saved (Rust, conceptual)

```rust
async fn example(buf: Vec<u8>) -> usize {
    let header = &buf[0..4];      // borrows buf
    let n = read_more().await;    // SUSPEND here: `buf` AND `header` are live across the await
    header.len() + n              // both must have been saved in the state machine
}
```

Because `buf` and `header` (a slice into `buf`) are both live across `.await`, the generated state machine stores both — and since `header` points into `buf`, the future is **self-referential**, which is why polling requires `Pin`.

### Example 3 — The barrier is conditional on GC phase (Go, conceptual asm)

```text
; obj.next = newptr   compiles roughly to:
    MOVB    runtime·writeBarrier(SB), AX   ; load the global "barrier on?" byte
    TESTB   AX, AX
    JEQ     fast                            ; common case: GC not marking -> skip
    ; slow path: record the write for the marker
    LEAQ    obj_next(SP), DI
    MOVQ    newptr, SI
    CALL    runtime·gcWriteBarrier(SB)
fast:
    MOVQ    newptr, obj_next(SP)            ; do the actual store
```

The fast path is one load + one branch (predicted not-taken). The barrier "turns on" only while the GC marks. This is the compiler funding concurrent GC.

### Example 4 — Exceptions cost nothing until thrown (C++)

```cpp
int hot_path(int* a, int n) {
    int s = 0;
    for (int i = 0; i < n; ++i) s += a[i]; // NO unwind code here on the happy path
    return s;                              // exception metadata lives in .eh_frame, off to the side
}

void with_cleanup() {
    std::vector<int> v(1000);   // destructor is a cleanup landing pad in the unwind table
    might_throw();              // if it throws, the unwinder runs ~v via the personality routine
}                              // happy-path return: just the normal destructor call
```

The loop pays nothing for exception support. The cost is the `.eh_frame`/`.gcc_except_table` metadata (binary size) and the slow throw path that invokes the unwinder.

### Example 5 — Go panic/recover is a different mechanism (not Itanium unwinding)

```go
func risky() {
    defer func() {
        if r := recover(); r != nil { // recover walks the defer chain, not DWARF unwind tables
            fmt.Println("recovered:", r)
        }
    }()
    panic("boom")
}
```

Go deliberately does **not** use table-driven C++-style unwinding. `panic` unwinds the **`defer` chain** the runtime maintains per goroutine. It's simpler, integrates with goroutine stacks, and avoids the LSDA/personality machinery — a conscious runtime design choice with different trade-offs (no zero-cost happy path for `defer`, but much simpler model).

---

## Trade-offs

| Axis | Stackful (green threads) | Stackless (async state machines) |
|------|--------------------------|----------------------------------|
| **Per-task memory** | A growable stack (KBs+) | A flat struct sized to live locals |
| **Ergonomics** | Synchronous-looking; any fn can yield | Function "coloring" (async vs sync); `.await` visible |
| **Runtime weight** | Needs scheduler + stack machinery (fat) | Can run with *no* GC; bring-your-own executor (thin-friendly) |
| **Compiler work** | Stack checks, stack maps | Coroutine transform, liveness, `Pin`/self-ref handling |
| **Suspension cost** | Save/restore stack context | Return `Pending`; state already in struct |
| **Type-system leakage** | Minimal | `Future`/`Task`, `Pin`, `Send`/`Sync` bounds |

| Axis | Table-driven EH (C++/Rust) | Defer/panic (Go) | Return-value errors (Go errors, Rust `Result`) |
|------|----------------------------|------------------|-----------------------------------------------|
| **Happy-path cost** | Zero (metadata only) | Small per-`defer` bookkeeping | Explicit branch, but local and predictable |
| **Throw/propagate cost** | Slow (unwinder + personality) | Walk defer chain | Cheap, explicit `?`/`if err` |
| **Binary size** | Large unwind tables | Small | Small |
| **Reasoning** | Invisible control flow | Visible at defers | Fully explicit |

---

## Coding Patterns

### Pattern 1 — Minimize locals live across `.await` (smaller futures)

```rust
// BAD: a large buffer is held across the await -> the future struct is huge.
async fn bad(data: [u8; 65536]) -> usize { let n = io().await; data.len() + n }

// BETTER: drop/scope the big value before the await so it isn't saved in the state machine.
async fn good() -> usize {
    { let data = [0u8; 65536]; let _ = use_locally(&data); } // dropped before await
    io().await
}
```

The future's size is the max set of locals live across *any* suspension point; shrinking that shrinks every task allocation.

### Pattern 2 — Keep cgo/native calls short to avoid stretching safepoints

```go
// A long-running C call holds an M and can't hit a safepoint -> lengthens stop-the-world.
// Prefer chunking native work or doing it off the hot GC path.
```

### Pattern 3 — Don't hold pointers into a future's locals across moves (respect `Pin`)

In Rust, never construct a self-referential future and then move it; pin it (`Box::pin`, `pin!`) before polling.

### Pattern 4 — Prefer explicit error returns in size/latency-critical code

When unwind tables or GC overhead matter (embedded, hot loops), `Result`/error returns give predictable cost the compiler lowers to plain branches.

---

## Best Practices

1. **Reason in lowerings.** When debugging async or EH, picture the generated state machine or unwind tables, not the source syntax.
2. **Keep futures small.** Audit cross-await live locals; large saved state inflates every task and hurts cache behavior.
3. **Measure safepoint latency, not just GC CPU.** Tail latency often comes from the last thread reaching a safepoint, not from marking cost.
4. **Choose your concurrency model deliberately.** Stackful for ergonomics and uniform yielding; stackless for memory-lean, runtime-light, embedded-friendly async.
5. **Respect `Pin` and `Send`/`Sync` as consequences, not annoyances** — they encode real invariants of the state-machine transform.
6. **Treat metadata as a cost.** Unwind tables and reflection data are part of "you pay for a runtime"; account for them in binary-size budgets.
7. **Don't put heavy work in static initializers.** They run single-threaded before `main`, before the scheduler is fully live.

---

## Edge Cases & Pitfalls

- **Self-referential futures moved after polling = UB without `Pin`.** The whole `Pin` apparatus exists to make this a compile error.
- **`.await` inside a held lock can deadlock or block the executor thread.** Suspension returns control to the executor while the lock is held; a non-async-aware mutex must not be held across `.await`.
- **A future that never returns `Pending` and never completes starves an executor thread** (busy-poll). Mirror of the "tight loop never yields" problem, in stackless land.
- **Long syscalls / cgo extend stop-the-world** because that thread can't reach a safepoint; pure-Go preemption can't reach into C.
- **Forgetting the write barrier in hand-written assembly / unsafe code corrupts the heap** — manual stores of heap pointers must replicate the barrier or use runtime helpers.
- **Throwing across an FFI boundary is undefined** unless both sides agree on the unwinder; C++ exceptions must not propagate into C frames lacking unwind info. (FFI/interop section covers this boundary.)
- **`panic` across a cgo boundary** is similarly unsafe — Go's defer-chain unwinder doesn't understand C frames.

---

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "Async means threads under the hood." | Stackless async is a compiler-generated state machine; threads are optional and driven by an executor. |
| "`.await` blocks the thread." | It *suspends the task* and returns control to the executor; the thread runs other tasks. |
| "Exceptions are slow, so avoid `try`." | Table-driven EH is *zero-cost on the happy path*; only throwing is slow. |
| "The GC just magically knows what's live." | It needs compiler-emitted stack maps and write barriers to be correct and precise. |
| "Stop-the-world is instantaneous." | It's bounded by the slowest thread reaching a safepoint. |
| "Go uses the same unwinding as C++." | Go uses a defer-chain panic mechanism, not Itanium/DWARF unwinding. |
| "`Pin` is bureaucratic noise." | It encodes the real hazard of self-referential generated state machines. |

---

## Tricky Points

- **Liveness analysis decides future size.** The same dataflow analysis used for register allocation determines which locals cross a suspension point and thus what the async struct must store. Two source-equivalent rewrites can yield different future sizes.
- **The hybrid write barrier lets Go avoid re-scanning stacks.** By combining deletion + insertion barriers and keeping stacks black after one scan, Go shortens stop-the-world stack re-scanning — a barrier-design choice with direct latency consequences.
- **Async coloring is a consequence of stacklessness, not a fashion.** Because a stackless suspension only saves the *current* function's state, the *caller* must also be a state machine to propagate suspension — hence `async` propagates up the call chain ("function coloring").
- **Zero-cost EH isn't zero binary cost.** The happy path is free in time, but `.eh_frame`/LSDA tables can be a large fraction of a binary; size-constrained builds sometimes disable EH entirely.
- **Two-phase unwinding lets you get a clean stack trace before destructors run.** Phase 1 finds the handler without touching state, which is why a debugger/`std::terminate` can show the throw site intact when no handler exists.

---

## Apply it

1. State the system invariant that **Runtimes (Language Runtime Support)** must protect.
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

- Which invariant must remain true when Runtimes (Language Runtime Support) fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
