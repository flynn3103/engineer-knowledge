# Manual Memory Management — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Manual Memory Management** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### The four primitive functions

C gives you a tiny toolkit in `<stdlib.h>`:

| Function | What it does |
|----------|--------------|
| `malloc(n)` | Reserve `n` bytes, return a pointer to them. The bytes are **uninitialized** (garbage). |
| `calloc(count, size)` | Reserve `count * size` bytes and **zero them out**. |
| `realloc(p, n)` | Resize an existing block to `n` bytes, possibly moving it to a new address. |
| `free(p)` | Return the block at `p` to the allocator. |

### The contract

Manual memory management is a *contract* between you and the allocator. The allocator promises:

- If `malloc` succeeds, you own a usable block of at least the size you asked for.
- The block stays valid and untouched until *you* call `free` on it.

In return, *you* promise:

- You will call `free` exactly **once** per successful `malloc`.
- After you call `free`, you will **never touch that pointer again**.
- You will not read or write past the end of the block.

Every bug in this topic is a broken clause of that contract.

### `malloc` can fail

`malloc` returns `NULL` when it cannot satisfy the request (out of memory). Real code checks for this:

```c
int *p = malloc(sizeof(int) * 100);
if (p == NULL) {
    // handle the failure — do NOT use p
}
```

Skipping the check means that on failure you dereference `NULL`, which crashes (or worse).

### "Freed" does not mean "erased"

A crucial mental shift: `free(p)` does **not** clear the memory or change `p`. The bytes are still there, and `p` still points at them. You have simply told the allocator *"I'm done; you may give this region to someone else."* The pointer is now a **dangling pointer** — a loaded gun pointing at memory that may belong to another part of your program at any moment.

---

## Code Examples

### The happy path

```c
#include <stdlib.h>
#include <string.h>

void example(void) {
    // 1. Allocate room for 10 integers.
    int *numbers = malloc(10 * sizeof(int));
    if (numbers == NULL) {
        return;  // allocation failed — bail out
    }

    // 2. Use the memory.
    for (int i = 0; i < 10; i++) {
        numbers[i] = i * i;
    }

    // 3. Free it exactly once when done.
    free(numbers);

    // 4. numbers is now dangling. Do not touch it.
    // Defensive habit: null it so accidental use crashes loudly.
    numbers = NULL;
}
```

### `calloc` vs `malloc`

```c
int *a = malloc(4 * sizeof(int));  // contents: GARBAGE
int *b = calloc(4, sizeof(int));   // contents: 0, 0, 0, 0

// Reading a[0] before writing it is an UNINITIALIZED READ — a bug.
// b[0] is guaranteed to be 0.
```

### Growing a buffer with `realloc`

```c
int *buf = malloc(4 * sizeof(int));
// ... later we need more room ...
int *bigger = realloc(buf, 8 * sizeof(int));
if (bigger == NULL) {
    free(buf);   // realloc failed; original buf is STILL valid, free it
    return;
}
buf = bigger;    // realloc may have moved the block — always reassign
```

Note the careful pattern: **never write `buf = realloc(buf, ...)` directly.** If `realloc` returns `NULL`, you would overwrite your only pointer to the original block and leak it.

---

## Best Practices

1. **Always check `malloc`'s return for `NULL`** before using the pointer.
2. **Match every `malloc` with exactly one `free`** — make it a reflex.
3. **Set pointers to `NULL` after freeing** so accidental reuse crashes immediately instead of silently corrupting.
4. **Free in the reverse order you allocated** when blocks depend on each other.
5. **Allocate and free in the same "owner."** If function A allocates, prefer that function A (or its clear successor) frees. Don't scatter ownership.
6. **Prefer `calloc` when you need zeroed memory** instead of `malloc` + a manual loop.

---

## Edge Cases & Pitfalls

- **Forgetting to free → memory leak.** The program runs fine, then slowly grows until the machine runs out of memory hours later.
- **Using after free → use-after-free.** The classic source of crashes and security holes. The bug may not show up where you wrote it.
- **Freeing twice → double-free.** Corrupts the allocator's internal bookkeeping; usually crashes.
- **Forgetting `malloc` can return `NULL`.** On failure you dereference a null pointer.
- **`realloc` may move your block.** Any old pointers into the original block are now dangling. Always use the returned pointer.
- **Uninitialized read.** `malloc` gives you garbage bytes; reading them before writing is a bug. Use `calloc` or initialize first.
- **Off-by-one writes.** `malloc(10 * sizeof(int))` gives indices `0..9`. Writing to index `10` is a **buffer overflow** — it scribbles on memory you don't own.

---

## Apply it

1. Choose one small, known input for **Manual Memory Management**.
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

- What problem does Manual Memory Management solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
