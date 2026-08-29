# Object Pinning & Movable Heaps — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Object Pinning & Movable Heaps** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Objects can move

A **moving GC** does not just free dead objects; it slides the surviving ones together to one end of the heap. Picture a bookshelf with gaps where books were removed. A moving GC pushes all the remaining books to the left so the empty space forms one big block on the right. After this **compaction**, the shelf has no gaps, and allocating a new "book" is trivial — you just place it at the boundary.

This is why many managed runtimes allocate so fast: with a compact heap, allocation is little more than "advance a pointer by N bytes." That speed is a *direct payoff* of being allowed to move objects.

### 2. The GC fixes managed references for you

When the GC moves an object from address `A` to address `B`, it walks all live references and rewrites every one that pointed to `A` so it now points to `B`. Because it does this atomically (while your code is paused or carefully coordinated), your program never sees a half-updated state. From your code's view, the object simply *is* where it is.

### 3. The GC cannot fix what it cannot see

Here is the crux. If you take an object's address and hand it to:

- a **C library** that stores it in its own variable,
- the **operating system** during a file or network read that writes into your buffer,
- a **hardware device** doing DMA into your buffer,

then the GC has no idea those copies exist. If it moves the object, those external addresses become **dangling** — they point at memory that has moved or been reused. Corruption or a crash follows.

### 4. Pinning = "do not move this"

**Pinning** marks an object as immovable for a window of time. While pinned, the GC skips it during compaction. Now its address is stable, and you can safely give that address to native code. When the native work is done, you **unpin**, and the object is free to move again on the next GC.

The golden rule, even at this level: **pin for the shortest time possible, and pin as few objects as possible.** A pinned object is a rock the GC must compact around — too many rocks, held too long, make the GC's job harder.

## Code Examples

The cleanest beginner-level illustration is C#'s `fixed` statement, which pins an array for the duration of a block and gives you a raw pointer.

```csharp
// C# — the `fixed` keyword pins `data` only inside the block.
byte[] data = new byte[1024];

unsafe
{
    fixed (byte* p = data)        // <-- object pinned here
    {
        // `p` is a STABLE raw address while we are inside this block.
        // Safe to pass `p` to a native function that fills the buffer.
        NativeFill(p, data.Length);
    }                             // <-- object UNPINNED here (block exits)
}

// After the block, the GC may move `data` again on the next collection.
```

What to notice:

- The pin is **scoped**: it begins at `fixed` and ends when the block closes. Short and automatic — exactly the recommended pattern.
- Inside the block, `p` is safe to hand to native code. Outside, it must not be used.

A conceptual sketch of what goes wrong *without* pinning:

```text
1. You take the address of object X  -> 0x1000
2. You hand 0x1000 to a C function and return to managed code
3. A GC runs and compacts the heap; X moves to 0x4000
4. The C function later writes to 0x1000  -> CORRUPTION
   (0x1000 may now be unused, or hold a DIFFERENT object)
```

## Best Practices

- **Pin the shortest possible time.** Open the window, do the native work, close it.
- **Prefer scoped pins** (`fixed`-style) over manual pin/unpin you must remember to release.
- **Pin as little as possible** — one buffer, not a whole graph of objects.
- **If sharing is long-lived, copy the data** into native/off-heap memory instead of holding a pin indefinitely (you'll learn this in higher tiers).
- **Never use a pinned address after unpinning.** Treat it as instantly invalid once the pin ends.

## Edge Cases & Pitfalls

- **Forgetting to unpin.** With manual APIs (not the scoped `fixed`), a forgotten unpin leaves the object stuck forever — a quiet performance leak.
- **Using the pointer outside the pinned region.** The classic bug: capturing the address, then using it after the block closes.
- **Assuming "Go and Java don't move objects, so I'm safe."** They move things too — Go moves goroutine *stacks*, and many JVMs compact the heap. The hazard is real across runtimes.
- **Pinning when a copy would be cheaper and safer.** For small data, copying is often the right call; pinning is for avoiding copies of large buffers.

---

## Apply it

1. Choose one small, known input for **Object Pinning & Movable Heaps**.
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

- What problem does Object Pinning & Movable Heaps solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
