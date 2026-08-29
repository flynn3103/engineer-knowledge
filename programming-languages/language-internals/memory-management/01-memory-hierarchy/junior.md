# The Memory Hierarchy — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **The Memory Hierarchy** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Why there is a hierarchy at all

Engineers would love one memory that is **fast, huge, and cheap**. Physics and economics forbid it:

- **Fast memory is expensive and small.** The circuits that respond in under a nanosecond (SRAM, used for caches) cost far more per byte and draw more power than the dense DRAM used for main memory.
- **Slow memory is cheap and huge.** Disk storage is pennies per gigabyte but takes thousands of times longer to reach.

So instead of one perfect memory, machines stack several imperfect ones and try to keep the data you need *now* in the fast ones. The hierarchy is a compromise that *behaves* almost as fast as the top level while being *almost as big and cheap* as the bottom level — **as long as your access pattern cooperates.**

### The levels, top to bottom

1. **Registers** — dozens of them per core, each 8 bytes. Sub-nanosecond. The CPU computes directly on these.
2. **L1 cache** — ~32–64 KB per core. About **1 ns** (~4 cycles). Split into instruction and data caches.
3. **L2 cache** — ~256 KB–1 MB per core. About **4 ns**.
4. **L3 cache** — a few to tens of MB, *shared* by all cores. About **12–40 ns**.
5. **Main memory (DRAM)** — gigabytes. About **60–100 ns**.
6. **SSD / NVMe** — hundreds of GB to TB. About **10–100 µs** — *thousands* of times slower than DRAM.
7. **Network / spinning disk** — milliseconds. A *million* times slower than a register.

### The crucial idea: it moves data for you automatically

You do **not** write code that says "copy this into L2." The hardware does it. When the CPU needs a byte that isn't in cache (a **cache miss**), it fetches the whole 64-byte cache line containing it from the next level down and keeps it around, betting you'll want it (or its neighbors) again soon. Your job is not to control the cache directly — it's to **write code whose access pattern makes those bets pay off.**

---

## The Latency Pyramid With Real Numbers

These are approximate, order-of-magnitude numbers for a typical modern server CPU. Memorize the *shape*, not the exact digits.

```
Level            Typical size      Latency        "If 1 cycle = 1 second"
---------------------------------------------------------------------------
Register         ~dozens × 8B      < 0.5 ns       instant
L1 cache         32–64 KB          ~1 ns          a few seconds
L2 cache         256 KB–1 MB       ~4 ns          ~15 seconds
L3 cache         8–32 MB           ~12–40 ns      ~1 minute
DRAM (RAM)       8–256 GB          ~60–100 ns     a few minutes
NVMe SSD         256 GB–4 TB       ~10–100 µs      hours to a day
Network (LAN)    —                 ~0.1–1 ms       a week+
```

The last column rescales time so one CPU cycle feels like one second. On that scale, going to RAM feels like waiting minutes, and going to SSD feels like waiting a *day*. This is why a single unnecessary trip to disk can dwarf millions of in-cache operations.

---

## Code Examples

### Row-major vs column-major traversal (the classic demo)

A 2D array in C, Go, or Java is stored **row by row** in memory. Reading it in row order touches consecutive addresses; reading it column-first jumps by a whole row each step.

```c
#define N 4096
int a[N][N];

// FAST: walks memory in order — each cache line fully used.
long sum = 0;
for (int i = 0; i < N; i++)
    for (int j = 0; j < N; j++)
        sum += a[i][j];

// SLOW: jumps N ints between accesses — one line per access, mostly wasted.
long sum2 = 0;
for (int j = 0; j < N; j++)
    for (int i = 0; i < N; i++)
        sum2 += a[i][j];
```

The two loops compute the same answer with the same number of additions. The second is commonly **5–10× slower** purely because it ignores the cache line. *Nothing in the language tells you this — it's all in the hierarchy.*

### The same pattern in Go

```go
const N = 4096
var a [N][N]int32

var sum int64
for i := 0; i < N; i++ {
    for j := 0; j < N; j++ {
        sum += int64(a[i][j]) // contiguous — cache-friendly
    }
}
```

Swap the loop order and Go suffers exactly the same slowdown. The hierarchy doesn't care which language emitted the loads.

---

## Pros & Cons of Each Level

| Level | Pro | Con |
|---|---|---|
| Registers | Fastest possible; no addressing | Almost none; compiler-managed |
| L1/L2 | ~1–4 ns, per-core | Tiny; thrashes if working set too big |
| L3 | MBs, shared across cores | Slower; contended by all cores |
| DRAM | Gigabytes, cheap | ~100 ns — a stall the CPU hates |
| SSD | Persistent, large | Microseconds; thousands× DRAM |
| Network/disk | Effectively unlimited capacity | Milliseconds; treat as a different planet |

---

## Best Practices

1. **Prefer contiguous, sequential access.** Arrays scanned front-to-back are the gold standard.
2. **Keep hot data small and together.** The less memory a loop touches, the more of it stays in fast cache.
3. **Don't fight the hardware.** You rarely "place" data in a cache; you *arrange access patterns* so the automatic machinery wins.
4. **Measure, don't guess.** Two loops with identical logic can differ 10× — you can't see that by reading the source.

---

## Edge Cases & Pitfalls

- **"It's all RAM, so it's all the same speed."** False. A cache hit and a cache miss to the same array can differ by ~100×.
- **Counting operations instead of accesses.** Beginners optimize the number of `+` operations; the hierarchy cares about the number of distinct cache lines touched.
- **Assuming small inputs reveal the truth.** A 1,000-element array fits entirely in L1, so a bad access pattern looks free. The penalty only appears when the data outgrows the cache — exactly when it matters in production.
- **Forgetting persistence is a level too.** A program that re-reads a file from SSD inside a loop pays microseconds *every iteration*; caching it in RAM once can be thousands of times faster.

---

## Apply it

1. Choose one small, known input for **The Memory Hierarchy**.
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

- What problem does The Memory Hierarchy solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
