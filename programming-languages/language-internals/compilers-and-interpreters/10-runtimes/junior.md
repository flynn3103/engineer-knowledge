# Runtimes (Language Runtime Support) — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Runtimes (Language Runtime Support)** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Compiler Cannot Do Everything In-Line

Imagine the compiler had to translate `append(list, x)` into raw machine code every time. It would have to inline the whole logic of "is there room? if not, find a bigger block of memory, copy the old contents, free the old block, then write x." That is dozens of instructions, and it depends on a memory allocator that itself is hundreds of lines. Inlining that into every `append` call would make programs enormous and impossible to maintain.

Instead, the language authors write that logic **once**, compile it into the **runtime library**, and the compiler simply emits a **call**: `call runtime.growslice`. The same idea applies to almost every "high-level" feature:

| You write | Compiler emits | Provided by the runtime |
|-----------|----------------|--------------------------|
| `new T` / `make(...)` | a call to the allocator | memory management |
| array/slice index `a[i]` | a bounds check + load | bounds-check helper / panic |
| `go f()` (Go) | a call to spawn a goroutine | scheduler |
| `throw` / `panic` | unwind metadata + a call | exception/panic machinery |
| `typeof x` / `x.(T)` | a metadata lookup | reflection / RTTI |
| string concatenation | a call to a string helper | string runtime + GC |

So a useful first definition: **the runtime is everything the compiler decided to *call* rather than *inline*.**

### 2. Your Program Has a Hidden Entry Point

You think your program starts at `main`. It does not. The *real* entry point on a native platform is a runtime function — `_start` (provided by `crt0` for C) or the language runtime's bootstrap (Go's `runtime.rt0_go`). This code runs **before** `main` and does setup:

1. Sets up the stack and reads command-line arguments and environment variables.
2. Initializes the runtime's own data structures (the heap, the GC, the scheduler).
3. Runs **static initializers** — global constructors in C++, package `init` functions in Go, static blocks in Java.
4. *Then* calls your `main`.
5. After `main` returns, runs cleanup and exits the process.

This is why people say "your program runs *on top of* a runtime." There is always a layer underneath `main` that you did not write.

### 3. The Standard Library Is Partly Runtime

When you call `println` or `fmt.Println` or `System.out.println`, you are calling into the **standard library**, which is shipped with the language. Some of the standard library is ordinary code (string formatting), but a lot of it leans on **runtime services**: printing needs a heap-allocated buffer (allocator), reading a file needs the runtime's I/O layer, spawning a thread needs the scheduler. So in practice "standard library" and "runtime" blur together; the runtime is the *core* services, the standard library is the broader toolbox built on top.

### 4. Fat Runtime vs Thin Runtime

Languages sit on a spectrum based on **how much** runtime they carry:

- **Fat runtime (Go, Java, C#, Erlang/Elixir):** every program carries a big runtime: a **garbage collector**, a **scheduler** for lightweight threads, **reflection** metadata, and more. You get convenience (no manual memory management, cheap concurrency) at the cost of bigger binaries, slower startup, and less control.
- **Thin runtime (C, Rust):** the program carries almost nothing — just startup glue and a minimal library. No GC, no built-in scheduler. You get small binaries, fast startup, and total control, but you manage memory yourself (or with compile-time rules, as Rust does).

The slogan to remember: **"you pay for a runtime."** A fat runtime gives you superpowers, but those superpowers ship in every binary and run on every CPU cycle. Rust markets *"no runtime"* as a feature precisely because that makes it usable on tiny embedded chips and inside other languages' runtimes.

### 5. Why "Hello World" Is Big

A C "hello world" is tiny because the runtime (`libc`) is usually *shared* — it's already on the machine, and your program just links to it dynamically. A Go "hello world" is a few **megabytes** because Go **statically** bundles its entire runtime — the GC, the scheduler, the reflection tables, the goroutine machinery — into the binary. You are not paying for your five lines; you are paying for the *services* those five lines could use. The binary is big because the runtime is big, and Go chose to staple it in for self-contained deployment.

---

## Code Examples

The point of these examples is not the code you write, but the **runtime calls hiding behind it.**

### Example 1 — Allocation is a runtime call (Go)

```go
package main

func makeThings() []int {
    s := make([]int, 0, 4) // compiler emits: call runtime.makeslice
    for i := 0; i < 100; i++ {
        s = append(s, i)   // when capacity runs out: call runtime.growslice
    }
    return s
}

func main() {
    _ = makeThings()
}
```

You wrote `make` and `append`. The compiler turned them into **calls into the Go runtime**, which finds memory (allocator) and, when needed, grows the backing array. You never see `runtime.makeslice` in your source, but it is what actually runs. The garbage collector — also part of the runtime — will later reclaim this slice when nothing points to it.

### Example 2 — Spawning a lightweight task is a runtime call (Go)

```go
package main

import "fmt"

func main() {
    done := make(chan bool)
    go func() {              // compiler emits: call runtime.newproc (create a goroutine)
        fmt.Println("hi from a goroutine")
        done <- true
    }()
    <-done                   // channel ops are runtime calls too (the scheduler may park us)
}
```

`go func()` is not an OS-thread spawn. The compiler emits a call to the runtime's **scheduler**, which creates a tiny goroutine and later runs it on some OS thread. The whole multiplexing — many goroutines, few OS threads — is the runtime's job. You only wrote two characters: `go`.

### Example 3 — Bounds checks the compiler inserts (Go-ish pseudocode)

```text
You write:        x := a[i]

Compiler emits:   if i >= len(a) {        // bounds check inserted by the compiler
                      call runtime.panicIndex(i, len(a))   // runtime reports the error
                  }
                  x = load a[i]
```

You wrote one indexing expression. The compiler inserted a **safety check** and, if it fails, calls a **runtime helper** that produces the panic / `IndexOutOfBoundsException`. The check and the helper are both part of how the language stays memory-safe — and both involve the runtime.

### Example 4 — A thin-runtime language hands you control (C)

```c
#include <stdlib.h>

int main(void) {
    int *p = malloc(10 * sizeof(int)); // YOU call the allocator explicitly
    if (!p) return 1;
    // ... use p ...
    free(p);                           // YOU free it — no GC will do it for you
    return 0;
}
```

In C (a thin runtime), there is no GC. The runtime (`libc`) *offers* `malloc`/`free`, but **you** decide when to call them. The compiler does not insert allocation or freeing on your behalf. This is the trade: more control, more responsibility, a tiny runtime.

### Example 5 — Seeing the runtime in a binary's size

```text
$ cat > hello.go
package main
import "fmt"
func main() { fmt.Println("hello") }

$ go build hello.go
$ ls -lh hello
-rwxr-xr-x  1 you  1.8M  hello      # ~1.8 MB for five lines!

# Compare a C hello world (dynamically linked to a shared libc):
$ cc hello.c -o hello_c
$ ls -lh hello_c
-rwxr-xr-x  1 you   16K  hello_c    # ~16 KB — libc lives outside the binary
```

The Go binary is large because the **entire runtime** (GC, scheduler, reflection tables) is stapled inside. The C binary is small because its runtime (`libc`) is shared by the whole system and loaded separately. Same "hello world", very different runtime cost.

---

## Coding Patterns

These are beginner-level habits that come directly from understanding the runtime.

### Pattern 1 — Reduce allocations to reduce runtime work

Every allocation is a runtime call and adds to GC pressure. Reusing memory means fewer runtime calls.

```go
// Allocates a new slice every call — more runtime + GC work.
func bad() []byte { return make([]byte, 1024) }

// Reuse a buffer — fewer allocations, less work for the runtime.
var buf = make([]byte, 1024)
func good() []byte { return buf } // (single-threaded use only)
```

### Pattern 2 — Let `defer`/RAII clean up so the runtime doesn't have to track it manually

```go
f, _ := os.Open("data.txt")
defer f.Close() // the runtime ensures Close runs when the function returns
```

### Pattern 3 — Prefer the standard library; it cooperates with the runtime correctly

Hand-rolling string building or concurrency is easy to get wrong. The standard library (e.g. `strings.Builder`, channels) is written by the people who wrote the runtime, so it cooperates with the GC and scheduler properly.

### Pattern 4 — In thin-runtime languages, pair every allocation with a free

```c
int *p = malloc(n);
if (!p) return;
/* ... */
free(p);   // no runtime will do this for you
```

---

## Best Practices

1. **Know whether your language has a fat or thin runtime.** It changes everything about memory, concurrency, and deployment.
2. **Don't fight the runtime.** If your language has a GC, use it; don't try to "outsmart" it with manual tricks until you measure a real problem.
3. **Measure before optimizing runtime overhead.** "The GC is slow" is rarely true until a profiler proves it. Look at the *right column* (runtime time) in a flame graph.
4. **Mind startup cost for short-lived programs.** A program that runs for 5 ms but spends 20 ms in runtime bootstrap is dominated by the runtime.
5. **Use the standard library for anything the runtime touches** — concurrency, I/O, allocation-heavy work. It's written to cooperate with the runtime.
6. **In thin-runtime languages, own your memory discipline.** Free what you allocate; the runtime won't.
7. **Treat binary size as a runtime question first.** Before stripping symbols, understand that the base size *is* the runtime.

---

## Edge Cases & Pitfalls

- **"My program is slow before it does anything."** That's runtime startup/bootstrap, plus static initializers running before `main`. Heavy global constructors or package `init` functions run *first*.
- **"Hello world is 2 MB."** Not a bug — the statically-linked runtime. (Go.)
- **"I never called `malloc` but the profiler shows allocation."** The compiler emitted allocation calls behind `make`, `append`, string concatenation, closures, and interface boxing.
- **"My `init`/static block has a side effect I didn't expect at startup."** Static initializers run during bootstrap, before `main`. Order can surprise you.
- **"I called `free` but the GC also reclaimed it" — wrong language model.** Don't mix manual free with a GC. In GC languages, you don't free; in C/C++, the runtime won't free for you.
- **"Why does my embedded target reject this language?"** Fat runtimes (GC, scheduler) often can't fit or aren't allowed on bare metal. You need a thin/`no_std` runtime.
- **A panic/exception you didn't catch crashes the process.** Unwinding is a runtime service; if no handler is found, the runtime terminates the program.

---

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "The compiler generates *all* the machine code my program runs." | No — a lot of what runs is the **runtime library**, called by your code. |
| "Programs start at `main`." | The runtime's `_start`/bootstrap runs *before* `main`. |
| "Big binary = bloated/badly written code." | Usually it's the **runtime** bundled in, not your code. |
| "GC means I never think about memory." | You still cause allocations; the runtime just reclaims them — reducing allocations still matters. |
| "C has no runtime." | C has a **thin** runtime (`crt` + `libc`). "No runtime" is relative. |
| "Rust has a GC because it's safe." | Rust has **no GC**; safety comes at compile time, keeping the runtime thin. |
| "Goroutines are OS threads." | They are **runtime-managed** green threads multiplexed onto OS threads by the scheduler. |

---

## Tricky Points

- **The runtime is not the OS.** The OS gives raw resources (memory pages, threads, CPU time). The runtime is *your language's* layer built on top of the OS, providing language-level services (GC, goroutines, exceptions). Both sit under your code, but they are different layers.
- **"Runtime" is overloaded.** It can mean (1) "the time when the program runs" (as in "runtime error"), or (2) "the runtime *system* / library". This page is about meaning (2). A "runtime error" is just an error that happens during meaning (1) — sometimes raised by meaning (2).
- **The standard library and the runtime overlap.** There's no sharp line. Core services (allocator, scheduler, GC) are clearly "runtime"; higher-level utilities are "standard library"; many things straddle both.
- **The compiler and runtime are co-designed.** They are a matched pair. The compiler emits exactly the calls and metadata *this* runtime expects. You usually can't mix one language's compiler with another's runtime.

---

## Apply it

1. Choose one small, known input for **Runtimes (Language Runtime Support)**.
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

- What problem does Runtimes (Language Runtime Support) solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
