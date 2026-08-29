# Allocators — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Allocators** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Anatomy of a chunk: headers and boundary tags

The classic `dlmalloc` chunk layout interleaves user data and metadata. Each chunk stores its size in a header; the low bits of the size (which are always zero because sizes are aligned) are stolen as flags — most importantly **PREV_INUSE**, marking whether the *previous* chunk is allocated.

```
 Allocated chunk:                     Free chunk:
 +------------------+                 +------------------+
 | prev_size (maybe)|                 | prev_size        |
 +------------------+                 +------------------+
 | size | flags     | <-- header      | size | flags     |
 +------------------+                 +------------------+
 | user data ...    | <-- malloc      | fwd  (next free) |
 |                  |     returns      +------------------+
 |                  |     here         | bck  (prev free) |
 |                  |                  +------------------+
 |                  |                 | ... unused ...    |
 +------------------+                 +------------------+
                                       | size (boundary)  | <-- footer copy
                                       +------------------+
```

The genius of the **boundary tag**: when you free chunk C, you want to know if the chunk *physically before* C in memory is also free, so you can merge. Reading "backwards" in memory is normally impossible without knowing the previous chunk's size. The boundary tag stores that size in a footer at the end of each free chunk, so the previous chunk's size sits right before C's header — making the backward step O(1). (The `PREV_INUSE` flag lets the allocator skip even reading the footer when the previous chunk is in use.)

### Splitting and coalescing

These are the two operations that keep the heap from degenerating.

- **Splitting** happens on allocation: you ask for 32 bytes, the smallest available free chunk is 200 bytes. The allocator returns a 32-byte (plus header) piece and creates a new free chunk from the remaining ~160 bytes rather than wasting it.

- **Coalescing** happens on free: after marking a chunk free, the allocator checks its physical neighbors (using boundary tags / `PREV_INUSE`). Any neighbor that is also free gets merged so you end up with one large free chunk instead of two small ones.

Without coalescing, repeatedly allocating and freeing different sizes shreds the heap into unusable confetti — classic **external fragmentation**.

### Placement strategies: first/best/next fit

Given a request and a free list, *which* free chunk do you pick?

| Strategy | Rule | Trade-off |
|----------|------|-----------|
| **First-fit** | Take the first chunk that's big enough. | Fast; tends to leave usable big chunks at the end but pollutes the front with small leftovers. |
| **Next-fit** | Like first-fit but resume the search where the last one stopped. | Spreads allocations out; often *worse* locality and fragmentation in practice. |
| **Best-fit** | Take the smallest chunk that fits. | Minimizes leftover, but a naive scan is O(n) and creates many tiny unusable slivers. |
| **Worst-fit** | Take the largest chunk (split it). | Mostly academic; tries to keep leftovers large but exhausts big chunks. |

Real allocators rarely scan a single linear list. They use **segregated free lists** so the "search" is mostly a direct index, approximating best-fit at O(1) cost.

### Size classes and segregated free lists

Instead of one free list of all sizes, maintain *many* lists, one per **size class**. Round each request up to its class and index straight into the matching list.

```
 size classes (bytes):  16   32   48   64   80  ...  512  ...
 free lists:           [..] [..] [....] [.] [...]    [..]
                         |
   malloc(40) -> round up to class 48 -> pop head of the 48-list (O(1))
```

Benefits: allocation and free become O(1) list operations; objects of the same size cluster together (good cache behavior); fragmentation within a class is bounded (all chunks are interchangeable). The cost is **internal fragmentation**: a request for 40 bytes consumes a 48-byte slot, wasting 8 bytes. Allocators tune the class spacing to keep that waste — typically capped around 10–25% — acceptable.

### Bins: the dlmalloc/ptmalloc model

glibc's allocator (ptmalloc, derived from Doug Lea's dlmalloc) organizes free chunks into several kinds of **bins**:

- **Fast bins:** Singly linked LIFO lists for small chunks (≤ ~128 bytes). Freed chunks go here *without coalescing* for maximum speed; they're "consolidated" later in bulk.
- **Small bins:** Doubly linked lists, one exact size per bin, for sizes below 512 bytes. Coalescing applies.
- **Large bins:** Each holds a *range* of sizes, kept sorted, for big requests — approximate best-fit.
- **Unsorted bin:** A temporary holding area. Recently freed/split chunks land here first; the next `malloc` sorts them into small/large bins as a side effect (a "lazy" amortized sort).
- **Top chunk:** The wilderness — the unallocated tail of the arena, grown via `sbrk`/`mmap` and shrunk back to the OS when large enough.

Very large requests (above `mmap` threshold, ~128 KiB by default) bypass the bins entirely and get their own `mmap` region, freed directly back with `munmap`.

## Specialized Allocators

General-purpose allocators handle *any* size and *any* free order. If you know more about your workload, you can do far better.

### Bump / arena / region allocator

Allocate by simply **incrementing a pointer**. There is no free list, no header search, no coalescing — allocation is a few instructions.

```
 region: [###############.................................]
                          ^ bump pointer
 alloc(n): ptr = bump; bump += align(n); return ptr;   // that's it
```

The catch: **you cannot free individual objects.** You free *everything at once* by resetting the bump pointer to the start of the region. This is perfect for **request-scoped** or **frame-scoped** work: build up a pile of objects whose lifetimes all end together (one web request, one game frame, one compiler pass), then reset in O(1). Sometimes called a *region*, *arena*, or *linear* allocator.

### Pool / slab allocator (fixed-size objects)

When you allocate many objects of *one* size — network packets, `task_struct`s, AST nodes — a **pool** (a.k.a. **slab** or **object cache**) is ideal. Pre-carve a slab of memory into fixed-size slots, thread a free list through the empty slots, and allocate/free by popping/pushing that list — O(1), zero fragmentation *within* the pool, no per-object header needed (the size is implicit).

The Linux kernel's **slab/slub** allocator is the canonical example: it keeps per-type caches (`kmalloc-64`, `inode_cache`, etc.), so allocating an inode is a free-list pop. SLUB also keeps recently freed objects "hot" in cache and pre-initialized (constructor reuse), which is why object pools dramatically cut allocation churn.

### Buddy allocator (power-of-two)

The **buddy** system manages memory in blocks whose sizes are powers of two. To satisfy a request, find the smallest power-of-two block ≥ the request; if only larger blocks are free, **split** one repeatedly in half, each half being the other's "buddy." On free, if a block's buddy is also free, **merge** them back — and recursively up. Buddies have addresses differing in exactly one bit, so finding a buddy is a single XOR — merging is cheap. The cost is internal fragmentation: a 33 KiB request rounds up to a 64 KiB block. Linux uses a buddy allocator at the *page* level (and slab on top of it).

### Stack allocator

A bump allocator with a twist: you can free in **strict LIFO order** (last allocated, first freed) by saving and restoring a marker. Allocate moves the pointer up; free moves it back down to a saved marker, reclaiming everything above. It models nested scopes perfectly and is common for scratch/temporary memory in games and parsers.

## Code Examples

### A bump (arena) allocator in C

```c
#include <stddef.h>
#include <stdint.h>
#include <assert.h>

typedef struct {
    uint8_t *base;   // start of the region
    size_t   cap;    // total bytes
    size_t   off;    // bump offset (bytes used)
} Arena;

static size_t align_up(size_t n, size_t a) {  // a must be a power of two
    return (n + (a - 1)) & ~(a - 1);
}

void arena_init(Arena *a, void *backing, size_t cap) {
    a->base = (uint8_t *)backing;
    a->cap  = cap;
    a->off  = 0;
}

void *arena_alloc(Arena *a, size_t size) {
    size_t off = align_up(a->off, 16);        // 16-byte alignment
    if (off + size > a->cap) return NULL;      // region exhausted
    void *p = a->base + off;
    a->off = off + size;
    return p;                                  // no header, no free list
}

void arena_reset(Arena *a) {
    a->off = 0;                                // frees EVERYTHING in O(1)
}
```

Note what's *missing*: no `arena_free(ptr)`. Individual frees don't exist. You allocate a burst of objects, use them, then `arena_reset` reclaims all of them at once.

### A fixed-size pool allocator in C

```c
#include <stddef.h>
#include <stdint.h>

typedef struct FreeNode { struct FreeNode *next; } FreeNode;

typedef struct {
    FreeNode *free_list;
    size_t    block_size;
} Pool;

// Carve `backing` into N blocks of block_size and thread a free list.
void pool_init(Pool *p, void *backing, size_t block_size, size_t count) {
    p->block_size = block_size;                // must be >= sizeof(FreeNode)
    p->free_list  = NULL;
    uint8_t *cur = (uint8_t *)backing;
    for (size_t i = 0; i < count; i++) {
        FreeNode *node = (FreeNode *)cur;
        node->next   = p->free_list;           // push onto free list
        p->free_list = node;
        cur += block_size;
    }
}

void *pool_alloc(Pool *p) {
    FreeNode *node = p->free_list;
    if (!node) return NULL;                     // pool empty
    p->free_list = node->next;                  // pop -> O(1)
    return node;
}

void pool_free(Pool *p, void *ptr) {
    FreeNode *node = (FreeNode *)ptr;
    node->next   = p->free_list;                // push -> O(1)
    p->free_list = node;
}
```

The free list lives *inside* the free blocks themselves — a freed block's first bytes become the `next` pointer. Zero metadata overhead, O(1) alloc/free, no fragmentation as long as every object is the same size.

## Coding Patterns

- **Arena-per-scope.** Tie an arena's lifetime to a logical scope (request, frame, pass). Reset at the scope boundary; never `free` inside.
- **Pool-per-type.** Give each hot fixed-size type its own pool to kill allocation churn and fragmentation.
- **Bulk back the specialized allocator with the general one.** Get the big backing region from `malloc`/`mmap` once, then sub-allocate with your bump/pool allocator.
- **Fallback chains.** A pool that overflows can fall back to a general allocator for the rare oversized case.

## Best Practices

- **Match the allocator to the lifetime pattern**, not to convenience. Same-lifetime burst → arena. Many same-size objects → pool. Arbitrary → general-purpose.
- **Respect alignment** when bump-allocating; misaligned pointers crash on some CPUs and slow others.
- **Make `block_size >= sizeof(pointer)`** in pools — the free list reuses the block's storage for its `next` link.
- **Keep size-class spacing tight enough** to bound internal fragmentation but loose enough to limit the number of classes.
- **Don't hand-roll a general allocator** for production unless you must; the specialized ones above are where custom allocators actually pay off.

## Edge Cases & Pitfalls

- **Freeing into the wrong allocator.** Passing an arena-allocated pointer to `free()` corrupts the heap — the allocator that made a pointer must be the one that releases it.
- **Pool block too small for the free-list node.** If `block_size < sizeof(FreeNode)`, the embedded `next` pointer overwrites adjacent blocks.
- **Forgetting to coalesce** (in a hand-rolled general allocator) guarantees external fragmentation.
- **Buddy rounding surprise.** A 65 KiB request in a buddy system grabs a 128 KiB block — nearly 50% wasted. Watch power-of-two boundaries.
- **Arena over-retention.** Because an arena frees nothing until reset, one long-lived object pins the *entire* region. Keep long-lived data out of short-lived arenas.
- **Next-fit's hidden cost.** It often fragments worse and trashes cache locality compared to first-fit despite seeming "fairer."

---

## Apply it

1. Find a real component where **Allocators** affects an interface or dependency.
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

- Which boundary is most affected by Allocators?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
