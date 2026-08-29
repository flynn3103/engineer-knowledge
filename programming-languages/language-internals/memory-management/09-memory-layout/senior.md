# Memory Layout — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Memory Layout** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. AoS vs. SoA: the same data, two physical worlds

Consider a particle system with position `(x, y, z)`, velocity, and a color, processed by a physics step that only reads/writes positions and velocities.

**AoS:**

```c
struct Particle { float x, y, z, vx, vy, vz; uint32_t color; };
Particle particles[1_000_000];

for (auto &p : particles)        // update positions
    p.x += p.vx, p.y += p.vy, p.z += p.vz;
```

Each `Particle` is 28 bytes (→ 32 with padding). The physics loop touches 6 of 7 fields, so AoS wastes little here — and AoS is excellent when you operate on *whole records*.

**SoA:**

```c
struct Particles {
    float x[N], y[N], z[N];
    float vx[N], vy[N], vz[N];
    uint32_t color[N];
};
for (size_t i = 0; i < N; i++)
    P.x[i] += P.vx[i];   // ... etc
```

Now `x[]` is a dense contiguous array of floats. Three things happen:

- **SIMD becomes trivial.** `x[i] += vx[i]` over a contiguous float array vectorizes to one AVX instruction per 8 elements. The compiler (and you) can load 8 lanes at once. In AoS, `x` values are 32 bytes apart — a *gather*, which SIMD hates.
- **Cache lines carry only useful data.** A 64-byte line of `x[]` holds 16 positions, all of which you use. In AoS, a line holds 2 particles' worth of *all* fields, including `color` you didn't need.
- **Cold fields don't pollute hot scans.** If the physics pass never touches `color`, SoA never loads it.

The flip side: if you need *one whole particle* (e.g., to render a single picked entity), SoA forces 7 separate array accesses across 7 distant regions — 7 cache lines for one record, where AoS needed one.

> **The rule:** choose layout by access pattern. **Operate on one field across many records → SoA.** **Operate on many fields of one record → AoS.** Columnar scans, vectorized math, and bulk filters love SoA; transactional record-at-a-time access loves AoS.

This is exactly why **columnar databases** (Parquet, ClickHouse, DuckDB, Arrow) store data column-by-column: analytics queries scan one column across billions of rows, and SoA makes that bandwidth- and SIMD-optimal. Row stores (Postgres heap, MySQL InnoDB) are AoS, optimal for fetching whole rows in OLTP.

### 2. Pointer chasing vs. flat arrays

A linked list is the canonical cache-hostile structure:

```c
struct Node { int value; struct Node *next; };
```

Each `Node` is heap-allocated, potentially far from its neighbors. Traversal is a chain of dependent loads: you cannot prefetch `next->next` until `next` resolves. Every hop is a likely cache miss (~200 cycles), and the CPU's out-of-order machinery stalls because the address of the next load *depends on* the result of the current one. This is **pointer chasing**, and it is why a linked list can be 10–50× slower to traverse than a flat array holding the same values — despite identical Big-O.

A `vector`/slice/array stores elements contiguously. Traversal is a linear sweep the hardware prefetcher predicts perfectly; misses are amortized across a whole cache line of elements. The same logic indicts:

- **Node-based trees** (red-black trees, generic BSTs) vs. flat/array-backed structures (B-trees with large nodes, sorted arrays, implicit heaps).
- **Hash maps with separate-chaining** vs. open-addressing (Swiss tables / `hashbrown`, Go's bucketized map) which keep entries in flat arrays.
- **Graphs of heap-pointer nodes** vs. CSR (compressed sparse row) adjacency arrays.

The senior instinct: **prefer flat, index-based structures over pointer-based ones for hot traversals.** Replace `*next` pointers with array indices; replace heap-scattered nodes with a backing arena. You keep the algorithm and lose the cache misses.

### 3. Object-header overhead in managed runtimes

In C/Rust/Go (mostly), a struct *is* its fields. In managed runtimes, every heap object carries hidden metadata that dominates the layout of small objects.

**JVM (HotSpot):** each object has a header:
- **Mark word** (8 bytes): identity hash, GC age/mark bits, lock state (biased/lightweight/heavyweight).
- **Klass pointer** (4 bytes with compressed class pointers, else 8): points to the class metadata.
- Plus alignment to 8 bytes.

So an `Integer` wrapping a 4-byte `int` costs **16 bytes** (12-byte header + 4-byte value, padded to 16). A `Long[]` of boxed `Long`s is catastrophic: each element is a pointer (4–8 bytes) to a 16-byte heap object, scattered — pointer chasing plus header bloat. This is the entire reason for primitive arrays, `IntStream`, value types (Project Valhalla), and off-heap columnar storage in JVM data systems.

**Compressed oops** shrink this: on heaps ≤ 32 GB, the JVM stores references as 32-bit values scaled by the 8-byte alignment, so a reference is 4 bytes instead of 8 and the klass pointer is 4 bytes. Crossing the 32 GB heap threshold *disables* compressed oops and can make a larger heap hold *less* live data — a classic capacity-planning trap.

**Go:** objects have **no per-object header**. A struct on the heap is just its fields (the GC tracks metadata in separate span/bitmap structures, not inline). This is why Go structs are compact and why `[]Particle` is genuinely contiguous. The cost is paid elsewhere (the GC's side tables), but your layout is what you wrote.

**Other runtimes:** CPython objects are enormous (refcount + type pointer + per-type fields; a bare `int` object is ~28 bytes), which is why NumPy exists — to store numbers in flat C arrays outside the object model. .NET has an 8-byte object header (sync block + method table pointer) plus 8-byte alignment.

The senior takeaway: **in managed runtimes, the runtime's per-object overhead, not your field layout, often dominates** — and the cure is fewer, bigger objects (struct-of-arrays, primitive arrays, value types, off-heap buffers) rather than millions of tiny ones.

### 4. Data-oriented design as an architecture

DOD inverts OOP's starting question. OOP asks "what *is* this thing?" and bundles its data and behavior into an object. DOD asks "what *transformation* runs over this data, and how is it laid out for that transformation to be fast?" Layout follows access pattern, not conceptual taxonomy.

The flagship is the **ECS** in game engines (Unity DOTS, Bevy, EnTT, Overwatch's engine). Instead of `class Enemy { Transform t; Health h; AI ai; ... }` (AoS objects, virtual dispatch, pointer chasing), you store each **component** in its own SoA array. A *system* (e.g., movement) iterates the `Position` and `Velocity` arrays in lockstep — pure linear, SIMD-friendly, branch-predictable passes over hot data, with cold components never loaded. The same idea powers vectorized query engines and high-frequency trading hot paths.

DOD is not anti-abstraction; it is anti-*pessimistic-default-layout*. It says: for the small set of code that runs millions of times, design the memory layout deliberately and let the access pattern dictate the structure.

---

## Code Examples

### Rust — AoS vs. SoA, and SIMD-friendliness

```rust
// AoS: one whole record is contiguous; bulk single-field ops gather.
#[derive(Clone, Copy)]
struct ParticleAoS { x: f32, y: f32, z: f32, vx: f32, vy: f32, vz: f32 }

struct ParticlesSoA {
    x: Vec<f32>, y: Vec<f32>, z: Vec<f32>,
    vx: Vec<f32>, vy: Vec<f32>, vz: Vec<f32>,
}

impl ParticlesSoA {
    // This loop is auto-vectorizable: x and vx are dense f32 arrays.
    fn step(&mut self) {
        for i in 0..self.x.len() {
            self.x[i] += self.vx[i];
            self.y[i] += self.vy[i];
            self.z[i] += self.vz[i];
        }
    }
}
// The AoS equivalent strides by sizeof(ParticleAoS) — the loads are 24 bytes
// apart, defeating contiguous SIMD loads and wasting cache-line bandwidth
// on vx/vy/vz the position-only pass might not need.
```

### Go — flat indices instead of pointer chasing

```go
// Pointer-based tree: each node is a separate, scattered allocation.
type NodePtr struct {
    Value       int
    Left, Right *NodePtr // chasing these is a cache miss per hop
}

// Arena/flat tree: nodes live in one contiguous slice; "pointers" are indices.
type Arena struct {
    Value       []int
    Left, Right []int32 // -1 == nil; indices into the same arrays
}

func (a *Arena) sum(i int32) int {
    if i < 0 {
        return 0
    }
    // Children are nearby in the backing arrays -> prefetcher-friendly,
    // and traversal order can be made contiguous by build order.
    return a.Value[i] + a.sum(a.Left[i]) + a.sum(a.Right[i])
}
```

### Java — header overhead and the boxing trap

```java
// Each boxed Long: 12-byte header + 8-byte value + padding = 24 bytes,
// PLUS an 8-byte reference in the array, scattered across the heap.
Long[] boxed = new Long[1_000_000];   // ~32 MB + pointer chasing on iterate

// Primitive array: pure contiguous 8-byte longs, one allocation, no headers.
long[] flat = new long[1_000_000];    // exactly 8 MB, dense, SIMD-able

// On heaps <= 32 GB, compressed oops make references 4 bytes; cross 32 GB
// and references jump to 8 bytes — a bigger heap can hold less live data.
```

---

## Coding Patterns

- **Structure-of-arrays transform:** take a hot `[]Struct`, split each field into a parallel array, and rewrite hot loops to iterate one field at a time. Keep an AoS "view" for rare whole-record access.
- **Index-as-pointer (arena):** replace `*Node` with `int32` indices into shared backing arrays; `-1`/sentinel for null. Enables compact serialization and cache locality.
- **Component arrays (ECS):** store each component type in its own dense array; iterate the intersection of component sets in systems.
- **Off-heap / value-type escape hatch:** in managed runtimes, move bulk numeric data out of the object model entirely (primitive arrays, direct `ByteBuffer`, Arrow vectors) to dodge headers and chasing.
- **AoSoA tiling:** group records into tiles of `K` (e.g. SIMD width), SoA within a tile, AoS across tiles — when you need both SIMD and decent single-record locality.

---

## Best Practices

1. **Pick layout from the hottest access pattern, and write it down.** Document "this is SoA because the analytics scan dominates"; the next engineer will otherwise "fix" it into AoS.
2. **Default to flat, index-based structures in hot paths.** Reach for pointer-based structures only when insert/delete churn or stable addressing genuinely demands it.
3. **In managed runtimes, minimize object count for bulk data.** Prefer primitive arrays, value types, and off-heap buffers over millions of small objects.
4. **Keep AoS↔SoA reversible.** Encapsulate the layout behind an interface so you can switch when profiling demands, without rewriting callers.
5. **Watch the 32 GB JVM cliff.** Size heaps to stay under compressed-oops threshold, or accept the reference-size jump consciously.
6. **Validate with profiling, not theory.** Confirm cache-miss reduction and vectorization actually happened (covered in the professional tier).

---

## Edge Cases & Pitfalls

- **SoA hurts when you actually need whole records.** A mixed workload (bulk scans *and* record fetches) may need both representations or an AoSoA compromise — don't dogmatically pick one.
- **SoA mutation of record count is painful.** Inserting/removing a record means editing every parallel array consistently; a bug desyncs them silently.
- **"Linked lists are always bad" is too strong.** For small N, intrusive lists with good allocation locality, or workloads dominated by O(1) splice/move, lists can win. The indictment is about *cache-hostile traversal at scale*.
- **Auto-vectorization is fragile.** SoA enables SIMD but doesn't guarantee it; aliasing, non-contiguous access, or branches inside the loop can block the compiler. Check the generated assembly.
- **Compressed oops surprise across the heap cliff.** Increasing `-Xmx` past ~32 GB can *reduce* effective capacity and slow everything down.
- **Arena indices are not lifetime-safe.** A stale `int32` index outliving its slot (after compaction/reuse) is a use-after-free analog with no type-system protection.
- **False sharing returns in SoA.** Parallel writers each owning a *slice* of the same field array can false-share at slice boundaries; align partitions to cache lines.
- **Padding interacts with AoS strides.** A poorly ordered AoS struct inflates the stride, multiplying wasted bandwidth across the whole array — junior-tier ordering still matters here.

---

## Apply it

1. State the system invariant that **Memory Layout** must protect.
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

- Which invariant must remain true when Memory Layout fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
