# Object Model & Layout — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Object Model & Layout** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The JVM Object Header, Field by Field

On a 64-bit HotSpot JVM, every ordinary object instance begins with:

```
+0   mark word    (8 bytes)   -- hash, lock state, GC age, etc.
+8   class pointer (4 or 8 B)  -- 4 bytes if compressed oops on (the default)
+12  [your fields start here]  -- arrays add a 4-byte length here too
```

So before a single field you declared, you've spent **12 bytes** (8-byte mark word + 4-byte compressed class pointer), and the object is then padded up to an 8-byte boundary — so the minimum object size is **16 bytes**.

The **mark word** is a master of disguise. Its bits mean different things depending on the object's state:

- **Unlocked:** identity hash code (once computed), GC age bits, and a couple of tag bits.
- **Biased / thin-locked / fat-locked:** the same 64 bits get repurposed to hold a thread ID or a pointer to a lock record.
- **During GC:** the mark word can hold a forwarding pointer.

This is why it's called the *mark* word — it's a scratch space the runtime overloads. The key takeaway for now: **the JVM crams hash, locking, and GC metadata into one shared 64-bit slot per object**, and it only "spills" to a real lock object when there's actual contention.

### 2. CPython's PyObject: Refcount + Type, Then Payload

Every CPython object starts with `PyObject`:

```c
typedef struct {
    Py_ssize_t ob_refcnt;     // reference count  (8 bytes)
    PyTypeObject *ob_type;     // pointer to the type  (8 bytes)
} PyObject;                    // 16 bytes of header before any payload
```

Variable-sized objects (lists, strings, big ints) use `PyVarObject`, which adds an `ob_size`. After the header comes the type-specific payload. A Python `int` is a `PyLongObject`: the 16-byte header, a size/sign field, then the magnitude digits — which is why a small `int` weighs ~28 bytes.

Two consequences fall straight out of this:

- **Reference counting is per-object work.** Every time a reference is created or dropped, CPython writes to `ob_refcnt`. That's a memory write on operations that look free, and it's a reason the GIL exists and why free-threaded CPython is hard.
- **Everything is boxed.** There is no unboxed `int` in pure Python. A list of a million ints is a million pointers to a million ~28-byte objects. NumPy escapes this by storing a raw C array with *one* header for the whole array.

### 3. The C++ vtable Pointer

A C++ class with no virtual functions has **no hidden fields** — it's just its members, like a C struct. The moment you add a `virtual` method, the compiler inserts a hidden **vptr** (vtable pointer), almost always as the **first** member, at offset 0:

```cpp
struct Plain   { int x; };               // sizeof == 4, no vptr
struct Virtual { virtual ~Virtual(); int x; };  // sizeof == 16 on 64-bit:
                                          // 8-byte vptr + 4-byte x + 4 padding
```

The vptr points to the class's **vtable**, a static per-class array of function pointers. A virtual call `obj->foo()` becomes: load the vptr from offset 0, index into the vtable to find `foo`'s slot, call through that pointer. The *next* topic (method dispatch) covers the call mechanics; what matters here is **the vptr is a per-object header cost, placed first, that you pay for the entire object's life the moment any method is virtual.**

### 4. Hidden Classes: Making `obj.x` a Fixed Offset Again

Here's the central problem of dynamic languages. In JavaScript, `obj.x` can't be a compile-time offset — `obj` has no static type, properties can be added or deleted at runtime, and two objects called `obj` might have totally different shapes. The naive implementation is a **hash map per object**: every property access is a string hash and a bucket lookup. That's an order of magnitude slower than a `+offset` load.

V8's answer (and SpiderMonkey's, and JSC's) is the **hidden class** — V8 calls it a **Map**, SpiderMonkey a **Shape**, JSC a **Structure**. The idea: objects with the *same set of properties added in the same order* share one hidden class, and that hidden class records "property `x` is at offset 0, property `y` is at offset 1." So:

```js
const a = { x: 1, y: 2 };   // hidden class C2: {x@0, y@1}
const b = { x: 5, y: 9 };   // SAME hidden class C2 — shared!
```

Now `obj.x` compiles (after JIT warm-up) to: check `obj`'s hidden class is C2, then load the in-object slot at offset 0. That check + fixed load is nearly as fast as a static struct. The per-site cache that remembers "(shape C2 → offset 0)" is the **inline cache**.

### 5. Shape Transitions and Why Order Matters

Objects gain their hidden class through a chain of **transitions**. Starting from the empty object:

```
{}  --add x-->  C1{x@0}  --add y-->  C2{x@0, y@1}
```

Each `add property` step moves to a new hidden class along a transition edge. Crucially, **the order of additions defines the path.** If you add `x` then `y`, you get C2. If you add `y` then `x`, you get a *different* hidden class C3 = `{y@0, x@1}` — same properties, different shape, different offsets.

```js
function f(a, b) {
  const p = {};
  if (cond) { p.x = a; p.y = b; }   // -> shape {x, y}
  else      { p.y = b; p.x = a; }   // -> shape {y, x}   DIFFERENT
  use(p.x);                          // this site now sees TWO shapes
}
```

The `use(p.x)` site is now **polymorphic** — it must handle both shapes. A few shapes are tolerable (the IC becomes a small list); too many and it goes **megamorphic**, falling back to the slow hash-map lookup and disabling key optimizations. **The fix is trivial and free: always initialize an object's properties in the same order, ideally all in the constructor.**

### 6. Monomorphic vs Polymorphic vs Megamorphic

A property-access site is rated by how many hidden classes it has seen:

| State | Shapes seen | Speed |
|-------|-------------|-------|
| **Monomorphic** | 1 | Fastest: single shape check + fixed offset load. |
| **Polymorphic** | 2–4 (engine-dependent) | A short list of (shape → offset) — still fast, slightly slower. |
| **Megamorphic** | many | Falls back to a generic hash lookup; the optimizing JIT may bail out of the function. |

Keeping hot sites monomorphic is one of the highest-leverage things a JS or Ruby or Python (PyPy) performance engineer does — and it's almost entirely a question of **object layout discipline**: same fields, same order, same types.

### 7. Python's `__slots__`: Opting Out of the Per-Object Dict

By default a CPython object stores its attributes in a `__dict__` — a per-instance hash map (so Python objects are "always megamorphic" by JS standards). Declaring `__slots__` tells CPython to lay the attributes out as **fixed offsets** in the object instead, removing the per-instance dict:

```python
class Point:
    __slots__ = ('x', 'y')   # x and y become fixed slots, no per-instance __dict__
    def __init__(self, x, y):
        self.x = x
        self.y = y
```

This is CPython's manual version of the hidden-class idea: trade dynamism (you can no longer add arbitrary attributes) for compact, fixed-offset layout. For a class instantiated millions of times, `__slots__` routinely cuts per-object memory by 30–50% and speeds attribute access.

### 8. AoS vs SoA, Now With Cache Numbers

The junior page introduced AoS vs SoA. The middle-level point is *quantitative*. A cache line is 64 bytes. Suppose a particle is 24 bytes (`float x,y,z; float vx,vy,vz` would be 24). In **AoS**, a 64-byte line holds ~2.6 particles — so a loop reading only `x` fetches 64 bytes to use 4, wasting ~94% of the bandwidth. In **SoA**, the `x` array is contiguous: a 64-byte line holds 16 `x` values, all of which your loop uses — near-100% useful, and the access pattern is a clean linear stream the hardware prefetcher and the auto-vectorizer both love. The same logic governs whether you split a hot field out of a cold struct (covered in `senior.md`).

---

## Code Examples

### Java — Measuring the header with JOL

```java
// Using OpenJDK's JOL (Java Object Layout) tool:
import org.openjdk.jol.info.ClassLayout;

class Small { int x; }

public class Demo {
    public static void main(String[] args) {
        System.out.println(ClassLayout.parseClass(Small.class).toPrintable());
    }
}
```

JOL prints something like: 8 bytes mark word, 4 bytes class pointer, 4 bytes for `int x`, total 16. It will show you the exact offsets and any alignment padding the JVM inserted — the authoritative way to see a Java object's layout rather than guessing.

### Java — Boxed map overhead

```java
// A HashMap<Long, Long> with 10M entries stores, per entry:
//   - a Node object (~32 bytes: header + hash + key ref + value ref + next ref)
//   - a boxed Long key  (~16 bytes)
//   - a boxed Long value (~16 bytes)
// That's ~64 bytes of object overhead to store 16 bytes of actual longs.
Map<Long, Long> m = new HashMap<>();
```

The actual data is two longs (16 bytes); the structure around it is ~4x that. For dense integer-keyed data, a specialized primitive map (e.g. `long[]`-backed open addressing, or libraries like Eclipse Collections / fastutil) can cut memory several-fold.

### Python — `__slots__` shrinks instances

```python
import sys

class Loose:
    def __init__(self, x, y):
        self.x = x; self.y = y          # stored in a per-instance __dict__

class Tight:
    __slots__ = ('x', 'y')              # stored as fixed slots, no __dict__
    def __init__(self, x, y):
        self.x = x; self.y = y

# The Tight instance has no __dict__, so it's markedly smaller and faster
# to access. For millions of instances this is a major memory win.
print(hasattr(Loose(1, 2), '__dict__'))  # True
print(hasattr(Tight(1, 2), '__dict__'))  # False
```

### JavaScript — Monomorphic vs polymorphic construction

```js
// GOOD: every Point has the same shape, built in the same order.
class Point {
  constructor(x, y) { this.x = x; this.y = y; }  // always {x, y}
}

// BAD: shape depends on a branch -> two hidden classes for one logical type.
function makePointBad(x, y, flag) {
  const p = {};
  if (flag) { p.x = x; p.y = y; }   // {x, y}
  else      { p.y = y; p.x = x; }   // {y, x}  -> different shape!
  return p;
}

// ALSO BAD: adding a property later forks the shape.
const q = new Point(1, 2);
q.z = 3;   // q now has a different hidden class than every other Point
```

Use a `class` (or always the same object literal), set all fields up front, and don't tack on properties after construction. The optimizing compiler rewards you with monomorphic, inline-cached property access.

### C++ — Where the vptr lands

```cpp
#include <cstdio>

struct Plain   { int a; };
struct Virtual { virtual void f() {} int a; };

int main() {
    printf("Plain   = %zu\n", sizeof(Plain));    // 4
    printf("Virtual = %zu\n", sizeof(Virtual));  // 16: 8B vptr + 4B a + 4B pad
    return 0;
}
```

The vptr is added at offset 0, ahead of `a`. Every virtual object pays 8 bytes and a pointer-chase per virtual call — the cost of dynamic dispatch made visible in `sizeof`.

### Go — `unsafe` to inspect offsets and alignment

```go
package main

import (
    "fmt"
    "unsafe"
)

type T struct {
    a byte
    b int64
    c byte
}

func main() {
    var t T
    fmt.Println("size:", unsafe.Sizeof(t))                 // 24 (lots of padding)
    fmt.Println("off b:", unsafe.Offsetof(t.b))            // 8
    fmt.Println("align b:", unsafe.Alignof(t.b))           // 8
    // Reorder to {b, a, c} -> size shrinks to 16.
}
```

---

## Coding Patterns

### Pattern 1: Construct in one fixed shape (dynamic languages)

```js
class User {
  constructor(id, name, age) {
    this.id = id;        // always these three fields...
    this.name = name;    // ...in this order...
    this.age = age;      // ...set in the constructor. One shape forever.
  }
}
```

### Pattern 2: `__slots__` for high-count Python classes

```python
class Node:
    __slots__ = ('value', 'next')   # millions of these? slots saves big.
```

### Pattern 3: Initialize all fields even when "unknown"

```js
// Bad: leaving `parent` unset until later forks the shape on assignment.
// Good: declare it up front with a stable type.
class TreeNode {
  constructor(v) {
    this.value = v;
    this.left = null;     // declared now, stable shape
    this.right = null;
    this.parent = null;
  }
}
```

### Pattern 4: Prefer primitive/typed arrays for bulk numbers

```js
const xs = new Float64Array(n);   // contiguous, unboxed doubles
```
```java
double[] xs = new double[n];      // not Double[] / List<Double>
```

### Pattern 5: SoA for field-at-a-time hot loops

```cpp
struct Bodies {           // instead of struct Body{...} bodies[N];
    std::vector<float> x, y, z, vx, vy, vz;
};
// integrate(): loop over x[]/vx[] contiguously — streams cache, vectorizes.
```

---

## Best Practices

- **Use a layout/inspection tool, don't guess.** JOL for Java, `unsafe.Sizeof`/`Offsetof` for Go, `std::mem::size_of` for Rust, `sys.getsizeof` and `__sizeof__` for Python, `--print-bytecode`/DevTools for V8 shapes.
- **In dynamic languages, lock object shape:** all fields set in the constructor, same order, stable types, no late `delete` or ad-hoc property tacking.
- **Reach for `__slots__`** on any Python class you create in large numbers.
- **Avoid boxing in hot paths.** Primitive/typed arrays over boxed collections; specialized primitive maps for dense integer keys.
- **Keep hot property-access sites monomorphic.** If a function processes objects of several shapes, consider splitting it per shape so each site sees one.
- **Order struct fields largest-alignment-first** (carries over from junior; still true here).
- **Measure deopts.** In Node, `--trace-deopt` and `--trace-ic` reveal which sites went polymorphic and why.
- **Don't store small integers as objects** when an unboxed/tagged representation exists — connect this to the data-representation topic.

---

## Edge Cases & Pitfalls

- **Conditional property assignment forks the shape.** `if (c) o.a = 1;` followed by `else o.b = 2;` makes two shapes. Set all properties unconditionally; use `null`/`undefined` as a placeholder value, not a missing field.
- **`delete obj.prop` in JS** drops the object to dictionary (slow) mode in most engines. Set to `null` instead of deleting if you need the fast path.
- **Adding properties in a loop, in data-dependent order,** generates a fan of shapes. Build the object fully, then mutate values, never the shape.
- **Mixed-type fields.** A field that is sometimes an `int` and sometimes a `string` (in JS) or that starts boxed and becomes unboxed forces the engine to widen its representation — a hidden deopt.
- **Java `Optional`, autoboxing, and varargs** silently allocate boxed objects in hot loops. `for (int i : list)` over a `List<Integer>` unboxes a million times.
- **Python's default `__dict__`** means every attribute access is a dict lookup; without `__slots__` you never get fixed-offset speed.
- **The mark word is volatile state.** Don't assume an object's identity hash is "stored somewhere fixed" — it may not be computed until first requested, and locking can temporarily displace it. (Details in `senior.md`.)
- **Arrays of objects are arrays of references** (Java, JS, Python). Iterating them is pointer-chasing across scattered heap memory, defeating prefetch — unlike a primitive/typed array.
- **`sizeof` lies about deep cost.** `sizeof` (or `getsizeof`) reports the object's *own* bytes, not the boxed objects it points to. A list's `getsizeof` doesn't include the elements.

---

## Apply it

1. Find a real component where **Object Model & Layout** affects an interface or dependency.
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

- Which boundary is most affected by Object Model & Layout?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
