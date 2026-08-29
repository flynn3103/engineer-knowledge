# Memory Layout — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Memory Layout** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The cache line is the real unit of cost

A modern CPU never reads one byte. When you touch a single `int`, the CPU loads the entire 64-byte cache line containing it. This has two consequences:

- **Spatial locality is free-ish.** The 63 neighboring bytes came along for the ride. If your next access is nearby, it's already in cache — a hit.
- **Layout decides hit rate.** If the fields you use together live in the same line, one fill serves them all. If they're scattered across many lines, you pay a fill per line, and you evict useful data to make room.

So "minimize padding" is really a proxy for "fit more useful data per cache line." A 12-byte struct means ~5 per line (with the line boundary cutting one in half); an 8-byte struct means exactly 8 per line, none split.

### 2. Packing: removing padding on purpose

Sometimes you *want* zero padding — typically to match a binary format (network packet, file header, hardware register block) byte-for-byte. You tell the compiler to pack:

```c
#pragma pack(push, 1)
struct WireHeader {
    uint8_t  version;   // offset 0
    uint32_t length;    // offset 1  (!! misaligned)
    uint16_t flags;     // offset 5
};                      // size 7, no padding
#pragma pack(pop)
```

Or per-struct in GCC/Clang:

```c
struct __attribute__((packed)) WireHeader { /* ... */ };
```

Rust:

```rust
#[repr(packed)]
struct WireHeader { version: u8, length: u32, flags: u16 } // size 7
```

**The trade-off is real and sharp:**

- **Win:** exact byte layout, smaller size, protocol/format compatibility.
- **Cost:** fields may be misaligned. On x86-64 a misaligned scalar read is *legal but slower*. On many ARM, MIPS, SPARC, and most embedded targets it is **undefined behavior** — it can fault and crash, or silently read the wrong bytes.
- **Worse trap (Rust/C):** taking a *reference or pointer* to a packed field is UB even on x86, because the reference type promises alignment the field doesn't have. `&packed.length` is a bug waiting to happen. Copy the field to a local first.

Pack only at trust boundaries (serialization), and read packed fields by **value**, never by pointer.

### 3. Hot/cold field splitting

Not all fields are equal. Consider a connection object touched on every request:

```c
struct Conn {
    int      fd;              // hot: every read/write
    uint64_t bytes_sent;      // hot: every write
    uint64_t bytes_recv;      // hot: every read
    char     peer_name[64];   // cold: logged once on error
    char     last_error[128]; // cold: only on failure
    time_t   created_at;      // cold: diagnostics
};
```

The hot fields total 20 bytes — they'd fit in one cache line. But interleaved with 200 bytes of cold data, the struct spans 4 cache lines, and a hot loop over many `Conn`s drags cold bytes into cache on every iteration, evicting useful data.

**Fix:** split hot from cold. Keep hot fields inline; move cold fields behind a pointer:

```c
struct ConnCold {
    char   peer_name[64];
    char   last_error[128];
    time_t created_at;
};
struct Conn {
    int          fd;          // all hot fields now
    uint64_t     bytes_sent;
    uint64_t     bytes_recv;
    struct ConnCold *cold;    // one pointer; followed only on the rare path
};
```

Now the hot struct is ~32 bytes, two per cache line, and a scan over connections touches only hot lines. The cold data still exists; you just don't pay to haul it on the common path.

### 4. False sharing: the scalability killer

This is the most important — and most surprising — concept in this tier.

Imagine two threads, each incrementing its own counter:

```c
struct Counters {
    uint64_t a;   // thread 1 writes this
    uint64_t b;   // thread 2 writes this
};
```

`a` and `b` are different variables; the threads never touch each other's. Logically there is **no contention**. But `a` and `b` sit in the *same 64-byte cache line*. Cache coherence works at line granularity: when thread 1 writes `a`, the protocol must give core 1 exclusive ownership of the whole line — which means **invalidating** core 2's copy. Then thread 2 writes `b`, stealing the line back and invalidating core 1. The line ping-pongs between cores on every write.

The result: code that should scale linearly with cores instead gets *slower* with more threads. This is **false sharing** — the cores share a cache line, not actual data, yet pay the full coherence cost.

**The fix** is to push each hot, per-thread field onto its own cache line with padding:

```c
struct Counters {
    alignas(64) uint64_t a;   // own line
    alignas(64) uint64_t b;   // own line
};
```

Now writes never collide. Each language has a blessed helper for this (covered in Coding Patterns). The cost is memory: you "waste" ~56 bytes per counter. For hot per-core data that is a trade you take every time — the speedup is often 5–10×.

---

## Code Examples

### Go — measuring false sharing

```go
package main

import (
    "sync"
    "sync/atomic"
)

// Bad: two counters in adjacent slots -> same cache line.
type CountersBad struct {
    a uint64
    b uint64
}

// Good: pad each counter onto its own 64-byte line.
type CountersGood struct {
    a uint64
    _ [56]byte // 8 (uint64) + 56 = 64 bytes
    b uint64
    _ [56]byte
}

func hammer(p *uint64, wg *sync.WaitGroup) {
    defer wg.Done()
    for i := 0; i < 50_000_000; i++ {
        atomic.AddUint64(p, 1)
    }
}

func runBad() {
    c := &CountersBad{}
    var wg sync.WaitGroup
    wg.Add(2)
    go hammer(&c.a, &wg)
    go hammer(&c.b, &wg)
    wg.Wait()
}
// Benchmark runBad vs the padded version: the padded one is typically
// several times faster on a multi-core machine.
```

### C — packing trade-off, read by value

```c
#include <stdint.h>
#include <string.h>

#pragma pack(push, 1)
struct Packet { uint8_t type; uint32_t seq; uint16_t len; }; // 7 bytes
#pragma pack(pop)

uint32_t get_seq(const struct Packet *p) {
    uint32_t seq;
    memcpy(&seq, &p->seq, sizeof seq); // safe: byte copy, no misaligned deref
    return seq;
    // NOT: return p->seq;  -- on strict-alignment CPUs this can fault,
    //      and &p->seq is a misaligned pointer (UB) anywhere.
}
```

### Rust — explicit cache-line padding

```rust
#[repr(align(64))]
struct CachePadded<T>(T);

struct Counters {
    a: CachePadded<std::sync::atomic::AtomicU64>,
    b: CachePadded<std::sync::atomic::AtomicU64>,
}
// Each AtomicU64 now starts a fresh 64-byte line; writes don't collide.
// In real code, prefer crossbeam::utils::CachePadded.
```

---

## Coding Patterns

**Per-language false-sharing helpers** (memorize these):

- **Java:** `@jdk.internal.vm.annotation.Contended` (or the public `@Contended` with `-XX:-RestrictContended`) pads a field onto its own line.
- **Rust:** `crossbeam_utils::CachePadded<T>` wraps a value to occupy its own line.
- **Go:** manual padding — add a `_ [N]byte` filler, or use a `[64]byte`-sized wrapper. Go has no built-in attribute.
- **C/C++:** `alignas(64)` (C11/C++11) on the field, or `__declspec(align(64))` (MSVC), or pad with a `char _pad[64 - sizeof(field)]`.

**Hot/cold split pattern:** keep hot fields inline; move cold fields into a separately-allocated struct reached by one pointer, populated lazily.

**Pack-at-the-boundary pattern:** define a `#[repr(packed)]` / `#pragma pack` struct *only* for the wire/disk representation; parse it into a normal, well-aligned in-memory struct immediately. Never compute on packed structs.

---

## Best Practices

1. **Think in cache lines, not bytes.** The question is never "how big is this field" but "what shares its 64-byte line."
2. **Pad shared hot fields; never pad ordinary data.** Padding to prevent false sharing is targeted surgery, not a blanket policy.
3. **Pack only at trust boundaries**, and read packed fields by value (`memcpy`/local copy), never via reference or pointer.
4. **Split hot from cold when a struct is both fat and frequently scanned.** If it's small or rarely touched, don't bother.
5. **Always benchmark on the target hardware.** False-sharing and cache effects are invisible in source and depend on core count, cache size, and access pattern.

---

## Edge Cases & Pitfalls

- **Padding for false sharing must account for prefetching.** Some CPUs prefetch *pairs* of lines (128-byte spatial prefetcher). Padding to 128 bytes is sometimes needed; `crossbeam`'s `CachePadded` already handles this per-architecture.
- **Atomics don't prevent false sharing.** Using `atomic` makes operations correct, not contention-free. A contended atomic on a shared line still ping-pongs.
- **Packed + pointer = UB, even on x86.** The CPU might tolerate the read, but the *language* doesn't. `&packed_field` is undefined behavior in C and Rust regardless of architecture.
- **Slices of packed structs are dangerous.** Iterating a `[]PackedStruct` by reference produces misaligned references on every element.
- **The compiler can defeat your hot/cold split** by inlining and keeping cold data alive in registers/caches anyway. Profile to confirm the split actually helped.
- **`_ [56]byte` padding can be wrong after edits.** If you add a field before the pad, the math changes silently. Prefer language helpers or compute the pad from `sizeof`.
- **Sub-line false sharing within one struct.** Two hot fields of the *same* object written by two threads false-share even without arrays. The fix is the same: separate their lines.

---

## Apply it

1. Find a real component where **Memory Layout** affects an interface or dependency.
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

- Which boundary is most affected by Memory Layout?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
