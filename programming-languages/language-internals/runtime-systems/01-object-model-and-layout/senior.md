# Object Model & Layout — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Object Model & Layout** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Compressed Oops: 64-bit References in 32 Bits

A 64-bit pointer is 8 bytes. In a heap full of reference-heavy objects, *most of the heap can be pointers*. The JVM's **compressed oops** optimization stores references as **32-bit** values, halving the cost of every reference field and the klass pointer.

The trick exploits alignment. Objects are 8-byte aligned, so every real object address has its low 3 bits zero. A 32-bit "narrow oop" is therefore an **object index**, decoded as:

```
real_address = heap_base + (narrow_oop << 3)
```

With a 3-bit shift, 32 bits of index addresses `2^32 × 8 = 32 GB` of heap. This is the famous **compressed-oops cliff**: below ~32 GB heap (precisely, when the heap fits the encodable range, often up to ~32 GB), references are 4 bytes; cross it and the JVM disables compressed oops and **every reference field doubles to 8 bytes**. The result is the well-known paradox: a 31 GB heap can hold *more live data* than a 33 GB heap, because the 33 GB heap wastes the savings on fat pointers. Senior tuning lesson: **don't size a heap just over 32 GB** — either stay comfortably under, or go large enough that the extra raw size outweighs the lost compression. (`ObjectAlignmentInBytes` can be raised to push the cliff to 64 GB at the cost of more per-object padding.)

When `heap_base` can be zero (heap mapped low), decoding is just a shift — no add — which is why the JVM tries to reserve low virtual addresses.

### 2. The Mark Word as a State Machine

The mark word's 64 bits are interpreted by a tag in the low bits. The classic states (pre-JDK-15, with biased locking):

```
state          (low bits)   contents
-----------------------------------------------------------------
unlocked       01           identity hash (if computed) | age | 01
biased         101          thread ID | epoch | age | 101
thin-locked    00           pointer to lock record on a thread stack
inflated       10           pointer to the heavyweight ObjectMonitor
GC-marked      11           forwarding pointer (during GC)
```

Two senior-critical consequences:

- **The identity hash and locking compete for the same bits.** When a thread thin-locks an object, the original mark word (which may hold the hash) is **displaced** into a lock record on the stack; the mark word now points there. If you call `System.identityHashCode()` on a biased object, the JVM must *revoke the bias* (it has nowhere to put the hash otherwise). So a seemingly innocent hash request can trigger lock revocation — a real, measurable cost.
- **Lock inflation is a layout event.** A contended lock "inflates": the mark word stops encoding a stack pointer and instead points to a separately allocated `ObjectMonitor`. Inflated monitors are heavier and were a GC/memory concern; modern JDKs added monitor deflation to reclaim them.

### 3. Biased Locking: History and Removal

**Biased locking** assumed most locks are only ever taken by one thread. The first thread to lock an object "biases" it (writes its thread ID into the mark word); thereafter that thread re-enters the lock with *no atomic operation at all* — just a check that the bias still holds. Cheap when right.

But it was expensive when wrong: another thread touching a biased object forces **bias revocation**, a stop-the-world-ish operation. As workloads shifted (thread pools, lots of short-lived contention, modern hardware where uncontended CAS is cheap), the average case stopped favoring bias. **JDK 15 disabled biased locking by default (JEP 374); JDK 18 removed it.** The senior point isn't nostalgia — it's that *the mark word's encoding changed across JDK versions*, so any tool, agent, or off-heap trick that reads mark-word bits is version-fragile. Newer JDKs are also exploring a *compact* object header (Project Lilliput) that shrinks the header further, again rewriting these bit layouts.

### 4. vtable Placement and Virtual Dispatch

For a C++ class with virtual methods, the compiler:

1. Builds one **vtable** per class — a static array of function pointers, one slot per virtual method, in a fixed order, with derived-class overrides replacing base entries.
2. Stores a **vptr** in every object, conventionally at **offset 0** (so the base subobject's vptr is found first).

A virtual call `p->foo()` compiles to roughly:

```
load  vptr   <- [p + 0]          ; fetch the object's vtable pointer
load  fn     <- [vptr + slot*8]  ; fetch foo's entry (slot fixed at compile time)
call  fn     (p, args...)        ; indirect call, `this` = p
```

Two dependent loads then an indirect call. The indirect call is the part that hurts: it's hard to inline, mispredicts on the branch predictor when the target varies, and pollutes the I-cache when many targets are live. This is *exactly* what the next topic (method dispatch) and JITs work to optimize — via inline caches, devirtualization, and speculative inlining.

**Multiple inheritance** complicates layout: an object with two polymorphic bases has *two* vptrs (one per base subobject), and calling a method through the second base requires a **`this`-pointer adjustment** (a fixed offset, or a thunk in the vtable) so `this` points at the right subobject. Virtual inheritance adds vbase offsets. The senior takeaway: **the simple "vptr at offset 0" picture holds for single inheritance; multiple/virtual inheritance multiplies vptrs and inserts adjustment thunks** — a reason layout-sensitive code prefers single inheritance or composition.

### 5. Hot/Cold Field Splitting

A common production object is large but has a tiny **hot set** — a few fields touched in the inner loop — surrounded by **cold** fields (debug info, rarely read metadata, audit timestamps). If hot and cold fields share cache lines, every hot-loop access drags cold bytes into cache, and you fit fewer hot sets per line.

**Hot/cold splitting** separates them:

- *Within an object:* order so the hot fields cluster at the front (one cache line), cold fields after.
- *Across objects:* move cold fields into a separate "extension" object reached by a pointer, so the common object stays one or two cache lines.
- *Structurally:* the SoA move — keep a dense array of hot fields and a parallel array (or sidecar map) of cold ones.

The win is "useful bytes per cache line" in the hot loop, often a multiple-x speedup with zero algorithmic change. This is the same instinct as SoA, applied at field granularity.

### 6. False Sharing of Hot Fields

Two fields can be logically independent yet physically share a 64-byte cache line. If two cores each write *their own* field on the same line, the coherence protocol treats every write as a conflict: the line ping-pongs between cores, invalidating each other's copy. This **false sharing** can make a "perfectly parallel" per-thread counter array scale *negatively*.

The fixes are layout fixes:

- **Pad to a cache line.** `alignas(64)` in C++; `_ [56]byte` filler in Go; `@Contended` in Java (which actually pads with 128 bytes to defeat adjacent-line prefetch). Note the *real* unit is often **two** cache lines because of the hardware's adjacent-line prefetcher — hence 128, not 64.
- **Don't co-locate hot, independently-written fields.** Two atomics that different threads hammer should not be neighbors.
- **Per-thread / per-CPU sharding** so each writer owns its own line outright.

False sharing is a *correctness-silent* performance bug: the program is correct, just mysteriously slow, and it only appears under true parallelism. `perf c2c` (cache-to-cache) is the tool that pinpoints the offending line.

### 7. Hidden-Class Deopt, Mechanically

The middle page said "inconsistent shapes deoptimize." Here's the mechanism. The optimizing JIT compiles a hot function under **speculative assumptions** baked from observed behavior: "this argument is always shape C2, so I'll emit a fixed-offset load for `.x` guarded by a shape check." When a new shape arrives, the guard fails, triggering a **deopt**: the optimized frame is discarded, execution resumes in the interpreter, and the function may be recompiled — now polymorphic, with weaker assumptions and slower code. Enough shape variety and the site goes **megamorphic**: the engine stops specializing entirely and uses a generic, hashed lookup, and the optimizing compiler may refuse to optimize the function at all.

So a deopt is not a one-time hiccup. A site that keeps seeing new shapes can enter a deopt loop (compile → deopt → recompile) that's worse than never optimizing. The senior fix is the same shape discipline, but now *measured*: run under `--trace-deopt`/`--trace-ic`, find the exact site, and identify the construction path that forks the shape.

### 8. Tagged vs Boxed, and Where the Header Goes Away

A boxed small integer pays a full header. The escape is **tagged representation**: steal the low bits of a machine word for a type tag (pointer tagging) or hide a payload in the unused bits of a NaN double (NaN-boxing in JS engines). A "Smi" (small integer) in V8 is a tagged 31-bit int stored *inline in the pointer slot* — no heap object, no header. The senior connection to layout: **whether a field is tagged-inline or boxed-out-of-line changes the object's footprint and the cache behavior of every loop over it.** When you control representation (Rust enums with niche optimization, C unions with a discriminant, custom NaN-boxing), you're doing object-model engineering — covered in depth by the data-representation topic, but you must recognize it here because it determines whether a "field" costs 0 extra bytes or a pointer plus a header.

---

## Code Examples

### Java — Seeing the compressed-oops cliff

```bash
# Below the cliff: compressed oops on, references are 4 bytes.
java -Xmx30g -XX:+PrintFlagsFinal -version | grep UseCompressedOops   # true

# Above ~32g: the JVM turns it off; references become 8 bytes.
java -Xmx40g -XX:+PrintFlagsFinal -version | grep UseCompressedOops   # false

# Force the alignment knob to push the cliff out (costs more padding):
java -Xmx40g -XX:ObjectAlignmentInBytes=16 ...   # narrow oops now reach 64g
```

The practical rule: a heap a hair over 32 GB can hold *less* live data than one just under, because every reference field doubled. Size around the cliff deliberately.

### Java — Inspecting the mark word and forcing hash/lock interaction

```java
import org.openjdk.jol.info.ClassLayout;
import static org.openjdk.jol.vm.VM.current;

public class MarkWord {
    public static void main(String[] args) {
        Object o = new Object();
        // Fresh object: mark word shows the "unlocked, no hash" pattern.
        System.out.println(ClassLayout.parseInstance(o).toPrintable());

        o.hashCode();   // computes identity hash -> now stored in the mark word
        System.out.println(ClassLayout.parseInstance(o).toPrintable());

        synchronized (o) {
            // Locked: the mark word now holds a lock-record pointer;
            // the previously-stored hash is "displaced" into the lock record.
            System.out.println(ClassLayout.parseInstance(o).toPrintable());
        }
    }
}
```

JOL prints the raw header bytes at each step; you can literally watch the mark word change meaning as you compute a hash and then lock.

### Java — `@Contended` to kill false sharing

```java
// Requires -XX:-RestrictContended to use @Contended outside the JDK.
import jdk.internal.vm.annotation.Contended;

class Counters {
    @Contended volatile long a;   // padded onto its own (pair of) cache line(s)
    @Contended volatile long b;   // ...so two threads writing a and b don't collide
}
```

Without `@Contended`, `a` and `b` likely share a 64-byte line; two threads each writing one of them ping-pong the line. `@Contended` pads each to ~128 bytes of isolation.

### C++ — vtable layout under single vs multiple inheritance

```cpp
struct A { virtual void f(); int a; };          // vptr_A, a
struct B { virtual void g(); int b; };          // vptr_B, b
struct C : A, B { void f() override; void g() override; int c; };
// C's layout (typical Itanium ABI):
//   [vptr_A][a]   <- A subobject; vtable here has C::f
//   [vptr_B][b]   <- B subobject; vtable here has C::g + a `this`-adjusting thunk
//   [c]
// Calling g() through a B* must add the offset to reach the C from the B subobject.
```

### C++ — Hot/cold split

```cpp
// Before: one fat object; the hot loop touches only `pos`, but every line
// it fetches also carries `name`, `created_at`, `audit` -> wasted bandwidth.
struct Entity {
    Vec3 pos;                       // HOT: touched every frame
    Vec3 vel;                       // HOT
    std::string name;               // cold
    std::chrono::time_point created_at; // cold
    AuditLog audit;                 // cold
};

// After: hot fields in a dense array; cold fields in a sidecar keyed by index.
struct HotEntity { Vec3 pos, vel; };          // 24 bytes, tight -> >2 per line
std::vector<HotEntity> hot;                    // the inner loop streams this
std::vector<ColdEntity> cold;                  // touched rarely, off the hot path
```

### Go — Padding to prevent false sharing

```go
type PaddedCounter struct {
    v   uint64
    _   [56]byte   // pad to 64 bytes so neighbors don't share a line
}

var counters [NumCPU]PaddedCounter   // each core writes its own line
```

### Rust — niche optimization removes the tag

```rust
// Option<&T> is the same size as &T: the compiler uses the
// impossible null pointer as the `None` "niche" -- no extra tag byte, no padding.
assert_eq!(std::mem::size_of::<Option<&u8>>(), std::mem::size_of::<&u8>());
// This is layout-level tagged representation done for free by the compiler.
```

---

## Coding Patterns

### Pattern 1: Cluster hot fields, exile cold ones

```cpp
struct Object {
    // hot first, packed into the leading cache line:
    uint64_t key; uint32_t flags; float score;
    // cold after (or behind a pointer):
    ColdExtras* extras;   // name, debug info, audit -> allocated lazily
};
```

### Pattern 2: Per-line isolation for contended counters

```java
@Contended long perThreadCounter;     // Java
```
```go
type C struct { v uint64; _ [56]byte } // Go
```
```cpp
struct alignas(64) Counter { std::atomic<uint64_t> v; };  // C++
```

### Pattern 3: Devirtualize hot polymorphism

```cpp
// Instead of a vtable call per element, use a closed set + std::variant:
using Shape = std::variant<Circle, Square, Triangle>;
for (auto& s : shapes)
    std::visit([](auto& shp){ shp.area(); }, s);   // compiler can inline each arm
```

### Pattern 4: Keep heap sizing off the cliff

```bash
# Prefer this...
-Xmx31g       # compressed oops ON, dense references
# ...over a heap a hair above 32g that silently fattens every pointer.
```

### Pattern 5: One shape per logical type (JS), enforced and tested

```js
class Vec3 { constructor(x,y,z){ this.x=x; this.y=y; this.z=z; } }
// Lint/test that no code path adds/deletes properties on Vec3 instances.
```

---

## Best Practices

- **Treat the 32 GB heap boundary as a real constraint.** Verify `UseCompressedOops` is on; size deliberately around the cliff or raise `ObjectAlignmentInBytes` knowingly.
- **Don't read raw mark-word bits without pinning a JDK version.** The encoding changed with biased-locking removal and will change again under compact-header projects.
- **Hunt false sharing with the right tool.** `perf c2c` (Linux), Intel VTune, or JFR; don't pad blindly — padding the wrong field just wastes memory.
- **Pad to 128 bytes, not 64,** when defeating false sharing, to account for adjacent-line prefetch.
- **Hot/cold split only measured-hot objects.** Profile first; the indirection to cold data is a cost you only want where the hot win pays for it.
- **Prefer composition or `variant`/CRTP over deep polymorphism** on hot paths to enable devirtualization and inlining.
- **Make shape discipline a tested invariant** in dynamic-language hot paths; trace deopts in CI-style perf runs, not just by eye.
- **Remember `identityHashCode` has side effects** under locking; avoid calling it on hot locked objects.

---

## Edge Cases & Pitfalls

- **The "bigger heap holds less" trap.** Bumping `-Xmx` from 31 GB to 34 GB can *reduce* effective capacity by disabling compressed oops. Always check the flag.
- **`identityHashCode` forcing revocation.** On JDKs with biased locking, hashing a biased object revokes the bias; in tight loops this surfaces as unexplained jitter.
- **Padding that the JIT/compiler removes.** A "padding" field with no uses can be elided; ensure the padding is real (e.g. `volatile`, or the language's contended annotation) or it won't survive optimization.
- **`@Contended` ignored.** It requires `-XX:-RestrictContended` (or being in the JDK) to take effect on user classes; silently does nothing otherwise.
- **Multiple inheritance vptr surprises.** `sizeof` jumps by *two* pointers, and a `static_cast` between base subobjects shifts `this` by a nonzero offset — pointer identity is not preserved across the cast.
- **Megamorphic deopt loops.** A site that keeps seeing new shapes can compile/deopt repeatedly, performing *worse* than the interpreter. The fix is to remove the shape variety, not to "warm it up more."
- **NaN-boxing and the float that isn't.** In NaN-boxed engines, certain bit patterns of a `double` are reserved for tags; naive bit-twiddling on doubles can collide with the tagging scheme.
- **Cross-version off-heap layout assumptions.** Code that mmaps objects or parses headers (agents, profilers, serializers) breaks when the runtime's header layout changes between releases.
- **False sharing inside arrays of small atomics.** `std::atomic<int> flags[64]` packs 16 atomics per line; threads hammering different indices still false-share. Pad each, or use one atomic with bit operations only if single-writer.

---

## Apply it

1. State the system invariant that **Object Model & Layout** must protect.
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

- Which invariant must remain true when Object Model & Layout fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
