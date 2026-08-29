# Object Model & Layout — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Object Model & Layout** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Footprint Is a First-Class Production Metric

For a population of N objects, footprint is `N × (header + fields + padding + per-object-structure)`. At scale, the per-object *constants* dominate: 16 bytes of JVM header times 10 billion objects is 160 GB of pure overhead, independent of your actual data. The professional habit is to **budget footprint per record** like a latency budget: enumerate the header, the padding (from field order), the boxing (every boxed field is +pointer +header), and the structural overhead (map nodes, list backing arrays, reference indirection).

This budget drives architecture. It's why high-cardinality systems flatten objects, intern repeated values, choose primitive-specialized collections, and frequently abandon the object model entirely for **off-heap** or **columnar** storage where there are *no per-object headers at all* — one header amortized across millions of rows.

### 2. Layout Drives GC Behavior

The object model and the garbage collector are coupled. Layout affects GC three ways:

- **Allocation rate.** Boxing and short-lived wrapper objects (autoboxed integers, iterator objects, lambda captures) flood the young generation, driving minor-GC frequency. Flattening and primitives cut allocation rate directly.
- **Object count and graph shape.** The GC's mark cost scales with the number of objects and references it must trace. Ten million tiny linked objects are far more expensive to trace than one array of values, even at equal bytes — pointer-chasing defeats the GC's prefetch just as it defeats yours.
- **Survivor footprint and promotion.** Larger objects (from padding/boxing) fill survivor spaces faster and promote sooner, raising old-gen pressure and full-GC risk.

So a layout change that looks local ("I boxed this field") can show up as a global GC-pause regression. Professionals reason about layout and GC together, and validate with GC logs, not intuition.

### 3. On-Heap vs Off-Heap vs Columnar

Three regimes, chosen by scale and access pattern:

- **On-heap objects.** Natural, GC-managed, ergonomic. Pays headers/boxing per object. Correct default until footprint or GC pauses say otherwise.
- **Off-heap (native) buffers.** You allocate a flat region (`MemorySegment`, `Unsafe`, `mmap`, native malloc) and lay records out by hand — no per-object header, no GC tracing of the contents, full layout control, and the data can be memory-mapped or shared between processes. The cost is manual lifetime management, no type safety, and the engineering burden of a hand-rolled layout. This is how caches (e.g. large LRUs), columnar stores, and message buffers dodge GC entirely.
- **Columnar / SoA at storage scale.** Store each field as a contiguous column. One schema (one "header") describes millions of rows. Enables vectorized scans, aggressive compression (run-length, dictionary, bit-packing per column), and SIMD. This is the layout of Arrow, Parquet, ClickHouse, and every modern analytical engine — the object model dissolved into columns because analytical loops read one field across all rows.

The decision is access-pattern-driven: random whole-record access favors on-heap/off-heap row layout; scan-and-aggregate-one-field favors columnar.

### 4. ABI-Stable Wire and FFI Layouts

The moment a struct crosses a trust boundary — network, file, shared memory, FFI to another language — its layout becomes a **contract**, and the compiler's freedom to reorder fields or pick padding becomes a liability. Professionals **pin** these layouts:

- **`repr(C)` in Rust, `#pragma pack`/explicit padding in C, no field reordering** — the layout must match the spec exactly and never change with compiler version.
- **Define endianness explicitly.** A multi-byte field's byte order must be specified (network byte order / little-endian) and converted on read/write; never assume the writer and reader share endianness.
- **Version the schema.** Use a format with defined evolution rules (Protobuf field numbers, FlatBuffers vtables, Cap'n Proto) rather than a raw C struct if the schema will change — raw structs have *no* evolution story and break the instant you add a field.
- **Distinguish in-memory from on-wire.** The fast in-memory layout (reordered, padded for the CPU) is usually *not* the wire layout (packed, endianness-fixed). Convert at the boundary; don't let the wire format dictate your hot-path layout, or vice versa.

A layout drift here is a silent data-corruption incident, not a slowdown. It is treated with the rigor of an API contract.

### 5. Guarding Layout in CI

Layout regressions are invisible in normal tests — the program is *correct*, just bigger or slower. So professionals make layout an **asserted, version-controlled invariant**:

- **Size assertions.** `static_assert(sizeof(T) == 32)` in C++, `const _ = [...]` size checks in Rust/Go, JOL-based size tests in Java. A field addition that bloats the struct fails the build.
- **Offset assertions** for ABI structs: pin each field's offset so a reorder is caught.
- **Allocation-profile gates.** A perf test that fails if allocation rate or object count regresses past a threshold catches accidental boxing.
- **Deopt/shape monitoring** in JS/TS perf suites: assert hot functions stay optimized (no `--trace-deopt` output for the hot path).

The principle: **a layout property the system depends on must be encoded as a test**, because nothing else will catch its regression until production metrics move.

### 6. Value Types: Removing the Object Tax by Construction

The cleanest fix for header overhead is to not have a header. Languages provide **value types**:

- **C, C++, Go, Rust** structs are values by default — inline, header-free, embeddable. Composing them flattens naturally.
- **Java Project Valhalla** introduces **value classes** (and primitive classes) that the JVM can flatten — an array of value-class points becomes a dense block of `x,y` pairs with no per-element header or indirection, closing the gap with C structs while keeping Java semantics.
- **C# structs** are inline value types; an array of structs is contiguous and header-free, unlike an array of classes.

Designing with value types where identity isn't needed is the highest-leverage footprint decision available, because it removes the per-object overhead at the type level rather than fighting it object by object.

### 7. NUMA, Page Locality, and Large Pages

At the largest scale, *where* memory physically lives matters. On a multi-socket box, accessing memory attached to another socket (cross-NUMA) is markedly slower. Layout interacts with NUMA: per-thread/per-socket data structures (the sharding from the senior page) should be **allocated on the accessing socket's node** (first-touch policy, `numactl`, `mbind`). Huge/large pages reduce TLB pressure for big contiguous structures (off-heap buffers, large arenas). These are production realities for low-latency and high-throughput systems where the object model's *placement*, not just its *shape*, determines performance. They're out of scope to detail here but in scope to recognize: a perfectly laid-out object on the wrong NUMA node is still slow.

### 8. Cross-Runtime Trade-off Decisions

In a design review you'll be asked to justify a representation. The professional answer is quantified and context-aware:

- **"Box or flatten?"** Flatten when the field is on a hot path or the object count is high; tolerate boxing for low-cardinality, cold, or nullable-by-design fields where ergonomics win.
- **"Row or columnar?"** Columnar when the dominant access is scan/aggregate over few fields; row when access is whole-record and random.
- **"On-heap or off-heap?"** Go off-heap when GC pauses or footprint from a large, long-lived, simply-structured dataset (a cache, a buffer pool) dominate, and you can afford manual lifetime management.
- **"Polymorphism or closed set?"** Keep vtables for open, extensible hierarchies; use closed sets (`variant`, sealed types, enums) on hot paths to enable devirtualization.

Each is a trade between ergonomics/flexibility and footprint/speed, decided by *measured* importance, not dogma.

---

## Code Examples

### Java — Size and offset assertions as a layout gate

```java
import org.openjdk.jol.info.ClassLayout;
import static org.junit.jupiter.api.Assertions.assertEquals;

class Record { long id; int a, b; }   // expect: 16 hdr + 8 + 4 + 4 = 32, padded

@Test void layoutIsStable() {
    long size = ClassLayout.parseClass(Record.class).instanceSize();
    // Lock the size: adding a field or reordering carelessly fails the build.
    assertEquals(32, size, "Record layout changed — review footprint impact");
}
```

### Java — Off-heap record store with the Foreign Memory API

```java
import java.lang.foreign.*;
import static java.lang.foreign.ValueLayout.*;

// One contiguous off-heap block; no per-record header, no GC tracing.
MemoryLayout REC = MemoryLayout.structLayout(
    JAVA_LONG.withName("id"),
    JAVA_INT.withName("a"),
    JAVA_INT.withName("b"));            // 16 bytes/record, exact, header-free

try (Arena arena = Arena.ofConfined()) {
    long n = 100_000_000;
    MemorySegment seg = arena.allocate(REC.byteSize() * n);
    var idAt = REC.varHandle(MemoryLayout.PathElement.groupElement("id"));
    // 100M records = 1.6 GB flat; the on-heap object version would add
    // ~16 bytes/record of header (+1.6 GB) plus GC tracing cost.
}
```

### Rust — Pinned ABI layout with compile-time assertions

```rust
#[repr(C)]                    // stable field order + C padding; no reordering
pub struct WireHeader {
    pub magic: u32,           // offset 0
    pub version: u16,         // offset 4
    pub flags: u16,           // offset 6
    pub length: u64,          // offset 8
}

// CI gate: any layout drift fails to compile.
const _: () = assert!(std::mem::size_of::<WireHeader>() == 16);
const _: () = assert!(std::mem::offset_of!(WireHeader, length) == 8);

impl WireHeader {
    pub fn length_le(&self) -> u64 { u64::from_le(self.length) } // fix endianness at boundary
}
```

### C++ — `static_assert` on size and offset for an FFI struct

```cpp
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)
struct Packet {              // wire layout: exact, no padding, must not drift
    uint8_t  type;           // 0
    uint32_t length;         // 1  (misaligned on purpose: it's a wire format)
    uint16_t crc;            // 5
};
#pragma pack(pop)

static_assert(sizeof(Packet) == 7, "Packet wire layout changed");
static_assert(offsetof(Packet, crc) == 5, "Packet field moved");
```

### Go — Columnar (SoA) store for a scan workload

```go
// Row store (AoS): scanning one field hops 64 bytes per record.
type Trade struct { Px float64; Qty float64; Ts int64; Sym [8]byte }

// Columnar store (SoA): "sum of Px" streams one contiguous slice.
type Trades struct {
    Px  []float64
    Qty []float64
    Ts  []int64
    Sym [][8]byte
}
// Aggregations over Px now vectorize and stay cache-resident.
```

### Java — Allocation-rate guard (sketch)

```java
// In a perf test: run the workload, sample allocation via JFR/async-profiler,
// and fail if bytes-allocated-per-op exceeds a budget. Catches accidental boxing
// (autoboxing in a stream, Optional in a loop) before it ships.
assertThat(allocatedBytesPerOp).isLessThan(BUDGET_BYTES);
```

---

## Coding Patterns

### Pattern 1: Separate interior and boundary representations

```rust
struct Trade { px: f64, qty: f64 }          // interior: CPU-optimized, may reorder
#[repr(C)] struct TradeWire { px: u64, qty: u64 }  // boundary: pinned, endianness-fixed
// explicit to_wire()/from_wire() conversions at the edge
```

### Pattern 2: Lock layout with a compile-time/CI assertion

```cpp
static_assert(sizeof(HotRecord) == 32, "footprint regression — review");
```
```rust
const _: () = assert!(std::mem::size_of::<HotRecord>() == 32);
```

### Pattern 3: Off-heap arena for a large, simply-typed dataset

```java
try (Arena arena = Arena.ofShared()) {
    MemorySegment data = arena.allocate(recordSize * count);
    // bump-allocate records; free the whole arena at once; zero GC tracing
}
```

### Pattern 4: Columnar layout for scan-heavy data

```go
type Cols struct { a []int64; b []float64; c []byte }  // one column per field
```

### Pattern 5: Prefer value types / flattening where identity isn't needed

```rust
struct Line { start: Point, end: Point }  // Point flattened inline, no Box, no header
```

---

## Best Practices

- **Budget footprint per record and multiply by N** before choosing a representation; revisit when N changes by an order of magnitude.
- **Validate layout against GC, not intuition.** Confirm boxing/flattening changes with GC logs and allocation profiles.
- **Keep interior and boundary layouts separate,** connected by an explicit, tested conversion; define endianness at the boundary.
- **Pin ABI layouts with size/offset assertions** and use a schema'd format (Protobuf/FlatBuffers/Cap'n Proto) when the schema will evolve.
- **Gate layout in CI:** size assertions, allocation-rate budgets, and (for JS/TS) deopt-free hot-path checks.
- **Reach for off-heap or columnar deliberately,** only when footprint/GC/scan-pattern justify the loss of ergonomics and safety.
- **Use value types and flattening** as the structural fix for header overhead where identity and nullability aren't required.
- **Treat NUMA/large-page placement as the last 10%** — measure first; it matters only at the top of the performance curve.
- **Document the *why*** of every non-obvious layout choice; the next engineer will otherwise "clean it up" and reintroduce the regression.

---

## Edge Cases & Pitfalls

- **The "it's only 8 bytes" dismissal.** Multiply by N before dismissing. Eight bytes across ten billion objects is 80 GB.
- **Wire format leaking into the hot path** (or vice versa). A packed, endianness-fixed wire struct used directly as the in-memory hot object is misaligned and slow; a CPU-reordered struct shipped raw over the wire corrupts data.
- **Raw structs as a wire format with no schema evolution.** Adding a field to a raw C struct breaks every existing reader. Use a format with defined evolution if the schema can change.
- **Off-heap lifetime bugs.** No GC means use-after-free, leaks, and double-frees return; an off-heap cache needs rigorous lifetime ownership (arenas, RAII, confined/shared arenas).
- **Endianness assumed, not specified.** Works in dev (same architecture), corrupts in production across heterogeneous hosts (x86 writer, ARM reader).
- **CI gates too strict or never updated.** A size assertion that's "always tweaked to pass" provides no protection; an intentional layout change must consciously update the gate, with review.
- **Columnar updates and point lookups.** Columnar is brilliant for scans and brutal for "update record 5's three fields" or "fetch one whole record"; don't force a transactional workload into it.
- **Valhalla/value-type identity loss.** Flattening removes reference identity — `==`, locking on the object, and nullability semantics change; not a drop-in for every class.
- **NUMA first-touch surprises.** Memory is placed on the node that *first writes* it, not the one that allocates it; initialize per-thread data from the thread that will use it.
- **GC interactions you didn't model.** Reducing object size can change promotion timing and survivor occupancy in non-obvious ways; always re-measure pauses after a layout change.

---

## Apply it

1. Define the user or business outcome that **Object Model & Layout** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Object Model & Layout?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
