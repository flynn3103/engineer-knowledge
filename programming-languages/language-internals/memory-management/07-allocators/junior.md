# Allocators — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Allocators** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### The allocator turns coarse OS memory into fine-grained blocks

This is the one-sentence summary of the whole topic. The OS gives megabytes; your program wants bytes. The allocator bridges that gap.

```
   Your program          Allocator (malloc/free)          Operating System
  ---------------        ----------------------          -----------------
  malloc(24)    -->   carve 24B from owned memory
  malloc(100)   -->   carve 100B from owned memory
                       (no syscall needed)
  malloc(8MB)   -->   not enough owned memory   --->   mmap() one big region
                       carve 8MB from it
```

### Every allocation needs bookkeeping

When you later call `free(ptr)`, you only pass the pointer — *not* the size. So how does the allocator know how big the block was? It stored that information itself, usually in a small **header** placed just before the memory it returned to you.

```
        header              what you get back from malloc
   +-------------+----------------------------------------+
   | size: 24    |  <-- malloc returns a pointer to here  |
   | in-use flag |                                         |
   +-------------+----------------------------------------+
   ^
   allocator looks here when you call free(ptr)
```

This is why `malloc(24)` may actually consume more than 24 bytes of memory — the header is overhead.

### The free list: remembering what's available

When you `free` a block, the allocator doesn't return it to the OS (usually). It puts that block onto a **free list** — a chain of available chunks — so the next `malloc` can reuse it. This reuse is the whole point: it's why heavy allocate/free workloads stay fast.

```
free list:   [chunk A] -> [chunk C] -> [chunk F] -> NULL
             (free)        (free)       (free)

malloc(size) walks this list, finds a chunk that fits, removes it, returns it.
free(ptr)    adds the chunk back to the front of the list.
```

### Why `free` is harder than `malloc`

`malloc` just finds space. `free` has to do something subtle: if two free chunks end up *next to each other* in memory, the allocator should **coalesce** (merge) them into one bigger chunk. Otherwise you'd end up with thousands of tiny free chunks and never be able to satisfy a large request — even though plenty of total memory is free. This problem is **external fragmentation**, and fighting it is most of what makes a real allocator complicated.

## Code Examples

### Using `malloc`/`free` correctly (C)

```c
#include <stdlib.h>
#include <string.h>

char *make_greeting(const char *name) {
    // length of "Hello, " + name + "!" + null terminator
    size_t len = strlen("Hello, ") + strlen(name) + 1 + 1;

    char *buf = malloc(len);     // ask the allocator for `len` bytes
    if (buf == NULL) {           // ALWAYS check — malloc can fail
        return NULL;
    }

    snprintf(buf, len, "Hello, %s!", name);
    return buf;                  // caller now owns this memory
}

int main(void) {
    char *msg = make_greeting("Ada");
    if (msg) {
        puts(msg);
        free(msg);               // hand the memory back to the allocator
        msg = NULL;              // avoid using a dangling pointer
    }
    return 0;
}
```

Three habits to absorb from this tiny example:

1. **Check the return value.** `malloc` returns `NULL` when it cannot satisfy the request. Dereferencing `NULL` crashes.
2. **Free exactly once.** The block belongs to whoever holds the pointer; ownership must be clear.
3. **Null the pointer after freeing.** A freed pointer that you accidentally use again is a *use-after-free* — one of the nastiest classes of bug.

### Seeing the overhead

```c
#include <stdio.h>
#include <stdlib.h>
#include <malloc.h>   // glibc-specific: malloc_usable_size

int main(void) {
    void *p = malloc(1);                    // ask for just 1 byte
    printf("requested: 1, usable: %zu\n",
           malloc_usable_size(p));          // often prints 24 or more!
    free(p);
    return 0;
}
```

On glibc this typically prints something like `usable: 24`. You asked for 1 byte and the allocator reserved a whole minimum-sized chunk. That gap is **internal fragmentation** — and it's why allocating millions of tiny objects one at a time is wasteful.

## Best Practices

- **Always pair `malloc` with `free`** (or use RAII / smart pointers in C++, or let the GC handle it in managed languages). Decide *who owns* each allocation.
- **Check `malloc` for `NULL`.** It is rare to fail on modern systems but catastrophic when unhandled.
- **Don't allocate in tight inner loops** if you can allocate once outside and reuse the buffer.
- **Prefer the stack for small, short-lived data.** Stack allocation is essentially free and auto-cleaned. Only reach for the heap when you need dynamic size or longer lifetime.
- **Set freed pointers to `NULL`** so accidental reuse fails loudly instead of silently corrupting memory.

## Edge Cases & Pitfalls

- **`malloc(0)`** is legal and may return either `NULL` or a unique non-null pointer you can safely `free`. Don't assume which.
- **Forgetting to free** → a *memory leak*. The program's memory grows until it's killed. Long-running servers are especially vulnerable.
- **Freeing twice** → *double free*. Corrupts the free list; often crashes later, far from the actual bug.
- **Using after free** → reading/writing memory that may have been handed to someone else. Silent data corruption or a security hole.
- **Off-by-one on size** → forgetting the `+1` for a string's null terminator is a classic buffer overflow.
- **Assuming `malloc` zeroes memory** → it does *not*. The bytes are garbage. Use `calloc` if you need zeroed memory.

---

## Apply it

1. Choose one small, known input for **Allocators**.
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

- What problem does Allocators solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
