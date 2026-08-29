# Stack Management & Unwinding — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Stack Management & Unwinding** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Stack Is a Stack

The "stack" in *call stack* is the same stack you meet in data structures: last-in, first-out. When `main` calls `a`, and `a` calls `b`, and `b` calls `c`, the stack looks like this (drawn with `main` at the bottom, the way most debuggers print it):

```text
    +---------------------+  <- top of stack (lowest address), current SP
    |  frame for c()      |   c is running right now
    +---------------------+
    |  frame for b()      |   b is paused, waiting for c to return
    +---------------------+
    |  frame for a()      |   a is paused, waiting for b
    +---------------------+
    |  frame for main()   |   main is paused, waiting for a
    +---------------------+  <- bottom of stack (highest address)
```

`c` must return before `b` resumes; `b` before `a`; `a` before `main`. You can never return into the *middle* of the stack — only the top frame is live. This is exactly why the most recent call is at the "top" of a stack trace.

### 2. What Is Inside One Frame

A single stack frame typically holds, from a junior's point of view, three things:

1. **The return address** — "when I'm done, jump back to *here* in my caller." Without this, the program could not find its way home.
2. **The saved frame pointer** — the previous frame's anchor, so we can restore it on return and so tools can walk the chain (more on this below).
3. **Local variables and temporaries** — the function's `int x`, its arrays, anything that doesn't fit in or got pushed out of registers.

```text
   higher addresses
   +------------------------+
   |  arguments / caller's  |
   |  stuff (above)         |
   +------------------------+
   |  return address        |  <- pushed by the `call` instruction
   +------------------------+
   |  saved frame pointer   |  <- the caller's FP, saved by the prologue
   +------------------------+  <- FP (rbp) points here
   |  local variable a      |
   |  local variable b      |
   |  ... temporaries ...   |
   +------------------------+  <- SP (rsp) points here (top)
   lower addresses
```

The exact layout depends on the platform's *calling convention*, which you'll meet in `middle.md`. For now the takeaway is: **a frame is just a small block of memory with a fixed structure, and the CPU has registers pointing at it.**

### 3. The Two Pointers: SP and FP

Two CPU registers track the stack:

- The **stack pointer** (`rsp` on x86-64) always points at the very top — the current edge. Every `push` decrements it; every `pop` increments it.
- The **frame pointer** (`rbp` on x86-64), when used, points at a *fixed* spot inside the current frame. Because the stack pointer moves around as the function pushes and pops temporaries, the frame pointer gives a *stable* reference: "local `x` is always `rbp - 8`, no matter what SP is doing."

The frame pointer also forms a **linked list**. Each frame saves the caller's frame pointer. So starting from the current `rbp`, you can follow the chain — `rbp` points at a slot that holds the *previous* `rbp`, which points at a slot holding the one before that — all the way down to `main`. Right next to each saved frame pointer sits the return address. **Following that chain is how a debugger draws a backtrace.** (In `middle.md` you'll learn that compilers sometimes drop the frame pointer to free up a register, which is why this simple chain-walk doesn't always work.)

### 4. `call` and `ret`

Two CPU instructions do the heavy lifting:

- `call foo` does two things atomically: it **pushes the return address** (the address of the instruction right after the `call`) onto the stack, then **jumps** to `foo`.
- `ret` does the reverse: it **pops the return address** off the stack into the program counter, so execution resumes in the caller.

Between them, the called function runs its **prologue** (set up its frame), its body, and its **epilogue** (tear the frame down), leaving the stack exactly as it found it so that `ret` lands cleanly.

### 5. A Stack Trace Is Just the Frame Chain, Printed

When your program crashes or you call something like Java's `Thread.dumpStack()` or Python's `traceback.print_stack()`, the runtime walks the live frames from the top down and prints, for each one, *which function it is* and *what source line it was at*. That's all a stack trace is: **the call stack, made readable.** The top line is where you are now; each line below is the caller that got you there.

---

## Code Examples

### Example 1: Recursion makes the stack visible

```python
# Python — every recursive call adds a frame; the trace shows them all.
import traceback

def countdown(n):
    if n == 0:
        traceback.print_stack()   # print the live call stack right here
        return
    countdown(n - 1)

def main():
    countdown(3)

main()
```

The printed stack will list, top to bottom: `print_stack` is called from `countdown(0)`, which was called from `countdown(1)`, from `countdown(2)`, from `countdown(3)`, from `main`, from module top-level. **Each recursive call is one frame.** This is exactly why deep recursion eventually overflows the stack — every call adds a frame and nothing is popped until the base case is hit.

### Example 2: Watching a stack overflow happen

```python
# Python caps recursion to protect you (default ~1000 deep).
import sys

def recurse(n):
    return recurse(n + 1)   # no base case — infinite recursion

try:
    recurse(0)
except RecursionError as e:
    print("Hit the recursion limit:", e)
    print("Python's safety net stops you before the real OS stack overflows.")
    print("Current limit:", sys.getrecursionlimit())
```

Python raises a *clean* `RecursionError` because it counts frames itself. Lower-level languages have no such net: in C, infinite recursion runs the *real* OS stack into its guard page and the program dies with a `SIGSEGV` ("segmentation fault"). Same root cause, different report.

### Example 3: A frame holds locals — and they vanish on return

```c
#include <stdio.h>

int* dangerous(void) {
    int local = 42;
    return &local;   // BUG: returning a pointer into our own frame
}                    // <- frame is abandoned here; `local` is gone

int main(void) {
    int *p = dangerous();
    // *p now points into a frame that no longer exists.
    // The memory may still hold 42... or garbage... or the next call's data.
    printf("%d\n", *p);   // undefined behavior
    return 0;
}
```

This is one of the most important junior lessons about the stack: **local variables live in the frame, and the frame is gone the instant the function returns.** A pointer into a returned frame is a *dangling pointer*. The bytes might still read `42` right after the call (nothing has overwritten them yet), which makes this bug terrifyingly inconsistent.

### Example 4: Reading a real backtrace (the most useful skill here)

```text
Traceback (most recent call last):
  File "app.py", line 20, in <module>
    main()
  File "app.py", line 16, in main
    result = process(data)
  File "app.py", line 11, in process
    return transform(item)
  File "app.py", line 6, in transform
    return 100 / value       <-- the actual crash
ZeroDivisionError: division by zero
```

Read it from the **bottom**: the error (`ZeroDivisionError`) happened in `transform`, at line 6. `transform` was called by `process` (line 11), which was called by `main` (line 16), which was called by the top-level script (line 20). The chain of frames tells you the *exact path* the program took to reach the bug. (Note: Python prints oldest-first; many languages, including Java and Go, print innermost-first. Always check which end is the crash.)

### Example 5: A peek at the assembly (don't memorize — just see the shape)

```asm
; x86-64. A textbook function prologue and epilogue.
my_func:
    push  rbp           ; save the caller's frame pointer
    mov   rbp, rsp      ; set up OUR frame pointer
    sub   rsp, 16       ; reserve 16 bytes for local variables
    ; ... function body uses [rbp-8], [rbp-16] for locals ...
    mov   rsp, rbp      ; discard locals (epilogue)
    pop   rbp           ; restore caller's frame pointer
    ret                 ; pop return address, jump back to caller
```

This is the whole life of a frame in six lines. The first two instructions (the prologue) build the frame and chain the frame pointers together; the last three (the epilogue) tear it down and return. **Everything in this topic is variations on this pattern.**

---

## Coding Patterns

**Pattern: Return values, not pointers to locals.** If a function needs to produce data that outlives it, return the *value* (which gets copied into the caller's frame) or allocate on the heap and return that pointer — never return the address of a local.

```c
// BAD: pointer into a dead frame.
int* bad(void) { int x = 5; return &x; }

// GOOD: return the value (copied into the caller).
int good(void) { int x = 5; return x; }

// GOOD: heap-allocate if it must outlive the call (remember to free).
int* good_heap(void) { int *x = malloc(sizeof(int)); *x = 5; return x; }
```

**Pattern: Convert deep recursion to iteration when depth is unbounded.** If recursion depth depends on *input size* (a million-node linked list, a deeply nested JSON), you risk a stack overflow. Rewrite it as a loop with an explicit stack on the heap, which can grow far larger than the call stack.

**Pattern: Always look at the top frame first.** When triaging a crash, read the innermost frame — that's where it actually broke. Then walk outward to understand *why* the bad input arrived there.

---

## Best Practices

1. **Keep large data off the stack.** Don't put a giant array (e.g. `char buf[1_000_000]`) as a local — it can blow the stack in one shot. Heap-allocate big buffers.
2. **Bound your recursion.** If recursion depth scales with untrusted input, you have a denial-of-service waiting to happen. Add a depth limit or rewrite iteratively.
3. **Never hand out a pointer to a local.** It's the classic dangling-pointer bug. The frame dies on return.
4. **Learn to read backtraces fluently.** Practice on real crashes. Identify the crash frame, the caller chain, and the line numbers.
5. **Don't disable the safety nets carelessly.** Python's recursion limit and your language's stack-size defaults exist for a reason. Raise them deliberately, not reflexively.
6. **Prefer values and references with clear ownership.** Languages like Rust make the "no pointer to a dead frame" rule a *compile error* — lean on that.

---

## Edge Cases & Pitfalls

- **Returning a pointer/reference to a local.** The frame is gone; the pointer dangles. In C/C++ it's undefined behavior; in Rust the borrow checker rejects it at compile time. Always the same root cause.
- **Stack overflow from deep recursion.** No base case, or depth scaling with input. In managed languages you get a clean error (`StackOverflowError`, `RecursionError`); in C you usually get a raw segfault.
- **A huge local variable.** A multi-megabyte array declared as a local can overflow the stack on the *very first call*, before any recursion. Move it to the heap.
- **Misreading which end of the trace is the crash.** Python and Java/Go print in *opposite* orders. Find the actual error line first, then trace the callers.
- **Capturing a reference in a closure that outlives the frame.** In some languages a closure can accidentally capture a stack local; the runtime usually "boxes" it onto the heap to keep it alive, but in unsafe languages this is a real bug.
- **Assuming locals are zero-initialized.** A fresh frame is just *reused stack memory*. In C, an uninitialized local holds whatever the previous call left there — garbage. Always initialize.

---

## Apply it

1. Choose one small, known input for **Stack Management & Unwinding**.
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

- What problem does Stack Management & Unwinding solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
