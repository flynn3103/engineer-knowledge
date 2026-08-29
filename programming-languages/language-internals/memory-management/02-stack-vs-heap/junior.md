# Stack vs Heap — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Stack vs Heap** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Two regions, one job: hold your data

Every running program has a layout in memory. A simplified picture:

```
high addresses
┌──────────────────────────┐
│   Stack (grows DOWN ↓)    │   ← function calls live here
│                          │
│            ⋮             │
│                          │
│   Heap (grows UP ↑)      │   ← new/malloc'd objects live here
├──────────────────────────┤
│   Global / static data   │
├──────────────────────────┤
│   Program code           │
└──────────────────────────┘
low addresses
```

The two regions grow toward each other from opposite ends. This is a layout convention, not a law of physics, but it is what almost every system you will touch does.

### The stack follows your function calls

The stack exists to make function calls work. Here is the key idea: **every time you call a function, the program pushes a new frame onto the stack. Every time a function returns, that frame is popped off.**

A frame holds everything a single call needs:

- The **parameters** passed in.
- The function's **local variables**.
- The **return address** — where to jump back to when this function finishes.
- Sometimes **saved registers** the function must restore before returning.

Because calls finish in the reverse order they started (the function you called most recently returns first), the stack is **LIFO**: last in, first out. That is exactly why it is called a stack — like a stack of plates.

Trace this:

```
main() calls greet()        → push greet's frame
greet() calls format()      → push format's frame
format() returns            → pop format's frame
greet() returns             → pop greet's frame
```

When `format()` returns, its locals vanish instantly. Nobody had to "clean them up." Moving the stack pointer back *is* the cleanup.

### Stack allocation is almost free

How does the program reserve space for a function's locals? It just moves the stack pointer. To give a frame 64 bytes, the CPU subtracts 64 from the stack pointer (the stack grows down, so reserving means subtracting). To release them, it adds 64 back. That is one arithmetic instruction.

There is no searching, no bookkeeping, no list of free blocks. This is why people say stack allocation is "nearly free."

### The heap is for data that outlives a function

Sometimes a value must live longer than the function that created it. Say you build a list of users and return it to your caller. If that list lived on the current frame, it would be destroyed the instant you returned — useless. So it goes on the **heap** instead.

Heap memory is requested explicitly or implicitly:

- In **C**, you call `malloc(size)` and later `free(ptr)`.
- In **Go, Java, Python**, you create an object (`new`, `make`, `[]`, a class instance) and a **garbage collector** later reclaims it when nothing points to it anymore.

The heap's superpower is **arbitrary lifetime**: data lives until you (or the GC) decide it is done, independent of any function's start and end.

Its cost is that *somebody has to keep track*. The allocator must find a free chunk of the right size, hand it out, and later remember the chunk is free again. That bookkeeping is why heap allocation is meaningfully slower than bumping the stack pointer.

### Lifetime is the real distinction

Beginners often think "small = stack, big = heap" or "primitive = stack, object = heap." Those are rough rules of thumb, but the *real* rule is **lifetime**:

- If a value's life begins and ends inside one function call → it can live on the **stack**.
- If a value must survive past the function that made it → it must live on the **heap**.

Hold on to that. Almost everything else follows from it.

## Code Examples

### Go — a value that escapes to the heap

```go
package main

import "fmt"

// stays on the stack: x lives and dies inside this function
func sumLocal() int {
    x := 41   // local, used here, then gone
    return x + 1
}

// escapes to the heap: the caller keeps a pointer to p,
// so p must outlive newUser, so Go puts it on the heap.
func newUser(name string) *string {
    p := name
    return &p   // returning the address of a local
}

func main() {
    fmt.Println(sumLocal())       // 42
    fmt.Println(*newUser("ada"))  // ada
}
```

In Go, returning `&p` is *safe*. The compiler notices the pointer outlives the function and quietly moves `p` to the heap. You can see this decision with `go build -gcflags=-m`.

### C — the same pattern is a bug

```c
#include <stdio.h>

int* broken(void) {
    int x = 42;
    return &x;     // BUG: x lives on broken's frame, which is gone after return
}

int main(void) {
    int *p = broken();   // p points at reclaimed stack memory
    printf("%d\n", *p);  // undefined behavior: garbage, crash, or "works" by luck
}
```

C does *not* rescue you. The frame holding `x` is popped on return, and `p` points into reclaimed memory. To return data that outlives the function in C, you must put it on the heap with `malloc` and free it later.

### Python — names are references to heap objects

```python
def make_list():
    data = [1, 2, 3]   # the list object lives on the heap
    return data        # we return a reference; the object survives

nums = make_list()
print(nums)            # [1, 2, 3] — perfectly fine
```

In Python you almost never think about stack vs heap directly: essentially every object lives on the heap, and variable names are just references to it. There is no `&x` footgun here.

## Best Practices

- **Prefer the stack when you can.** It is faster and self-cleaning. Many languages do this automatically; do not fight them by allocating on the heap "just in case."
- **In C, never return the address of a local.** If the data must outlive the function, `malloc` it (and document who frees it).
- **Match every `free` to exactly one `malloc`.** Freeing twice or never are both bugs.
- **Don't put huge arrays on the stack.** A `char buf[10*1024*1024]` local can overflow the stack instantly. Heap-allocate large buffers.
- **In managed languages, let the runtime decide.** Trust Go's escape analysis and Java's/Python's heap model; optimize only when a profiler points you there.

## Edge Cases & Pitfalls

- **Dangling pointer:** keeping a pointer to data that has been freed or to a popped stack frame. Reading it is undefined behavior.
- **Stack overflow:** the stack runs out of room — usually from infinite or very deep recursion, or a giant local array. The program crashes (often with a `SIGSEGV` or `StackOverflowError`).
- **Memory leak:** heap data that is never freed and never collected because something still (mistakenly) references it, or the pointer was lost. Memory usage grows until the process dies.
- **"It works on my machine":** dangling-pointer code in C may *appear* to work because the reclaimed memory has not been overwritten yet. That is luck, not correctness.

---

## Apply it

1. Choose one small, known input for **Stack vs Heap**.
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

- What problem does Stack vs Heap solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
