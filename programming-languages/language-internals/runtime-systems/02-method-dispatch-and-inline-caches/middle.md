# Method Dispatch & Inline Caches — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Method Dispatch & Inline Caches** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Single-Inheritance vtable Layout (the clean case)

With single inheritance, the layout is beautifully simple and is what makes vtables fast. The rule: **a derived class's vtable starts with the base class's slots in the same order, then appends its own new methods.**

```text
class Base    { virtual void f(); virtual void g(); };
class Derived : Base { void g() override; virtual void h(); };

Base vtable:      [0]=Base::f   [1]=Base::g
Derived vtable:   [0]=Base::f   [1]=Derived::g   [2]=Derived::h
                   ^same slot     ^overridden      ^new
```

Because slot indices are preserved, code compiled against `Base*` can call `g()` at slot 1 and it works correctly on a `Derived` — the slot holds `Derived::g`. The `this` pointer needs no adjustment, because a `Derived` object *starts with* a `Base` sub-object at offset 0. One vptr, fixed slots, zero pointer math. This is why single inheritance is the fast, simple case in every implementation.

### 2. Multiple Inheritance: Two Bases, Two vptrs, and Pointer Adjustment

Now let a class inherit from two bases:

```cpp
struct A { virtual void fa(); int a; };
struct B { virtual void fb(); int b; };
struct C : A, B { void fa() override; void fb() override; };
```

A `C` object can't put both `A` and `B` at offset 0 — only one can be first. A typical layout:

```text
C object:
  offset 0:  [ A's vptr ][ a ]      <- the A sub-object
  offset N:  [ B's vptr ][ b ]      <- the B sub-object
```

So a `C` has **two vptrs** and two embedded sub-objects. Here's the problem. When some code holds a `B*` (pointing at the `B` sub-object, at offset N) and calls `fb()`, the actual `C::fb` method expects a `C*` (pointing at offset 0). The pointers differ by N bytes. Something must subtract N from the receiver before entering `C::fb`. That "something" is a **thunk**.

### 3. Thunks: The Glue for `this` Adjustment

A **thunk** is a tiny compiler-generated stub. The `B` sub-object's vtable doesn't point its `fb` slot directly at `C::fb`; it points at a thunk that does:

```text
thunk_for_C_fb:
    this -= N          ; adjust B*  ->  C*   (the "this adjustment")
    jmp C::fb          ; tail-call the real method
```

So calling `fb()` through a `B*` lands in the thunk, which fixes the pointer and jumps to the real `C::fb`. From the caller's side it's invisible — still "read the slot, call it" — but the slot points at glue, not the method. Thunks can also adjust the *return* pointer for covariant returns. The cost is a tiny extra jump and some pointer arithmetic on the multiple-inheritance path; single inheritance never pays it. Virtual inheritance (the diamond) adds further indirection (vtable-stored offsets) but the principle is the same: **adjust the receiver, then dispatch.**

### 4. Interface Dispatch Is a Different Problem

A class hierarchy gives every subtype a vtable that's a superset of its base's vtable, with stable slots. Interfaces break that. A type can implement `Comparable` (Java) or `io.Reader` (Go) regardless of where it sits in the class tree, and two unrelated types implementing the same interface won't have that interface's methods at the same vtable slot. So "interface method → fixed slot" doesn't hold the way "class method → fixed slot" does. Runtimes need a separate mechanism.

### 5. Java itables

In Java, a class that implements interfaces gets, for each interface, an **itable** (interface method table): a small array mapping that interface's methods to the class's concrete implementations. `invokevirtual` (class-method call) uses the simple, fixed-slot vtable. `invokeinterface` (interface call) is harder: the JVM must, given the object's class and the target interface, find the right itable and then the right method within it. Naively that's a search over the class's interface tables — more expensive than `invokevirtual`. HotSpot optimizes this with **inline caches on interface call sites**: the first call resolves the itable lookup, and subsequent calls with the same receiver class hit a cached target behind a class guard, just like other dispatch. So the *worst case* is the itable search, but the *common case* is a guarded direct call.

### 6. Go's itab (Interface Table)

Go has no classes, but interface dispatch is central. A Go **interface value** is two words: `(itab, data)`. The **itab** is a small header that ties a concrete type to an interface:

```text
itab:
   ├─ inter  : *interfacetype   (which interface, e.g. io.Reader)
   ├─ _type  : *_type           (the concrete dynamic type, e.g. *os.File)
   ├─ hash   : uint32           (type hash, for type switches)
   └─ fun[]  : [n]uintptr       (function pointers: the concrete methods
                                  implementing the interface, in interface order)
```

A call `r.Read(buf)` where `r` is an `io.Reader` becomes: load the itab from the interface value, load `fun[index_of_Read]`, and call it with the `data` pointer as the receiver. itabs are built lazily and **cached** in a global hash table keyed by (interface type, concrete type), so the expensive "does this type satisfy this interface, and where are its methods?" computation happens once per (interface, type) pair, not per call. After that, an interface call in Go is essentially "load a function pointer from a 2-word value and call it" — close to a C++ virtual call in cost.

### 7. C++ Interface-Like Dispatch

C++ has no `interface` keyword; the idiom is an abstract base class (all pure-virtual). Calling through such a base is just ordinary virtual dispatch — *unless* the abstract base is one of several base classes, in which case you're back in multiple-inheritance territory with its extra vptr and thunks. So in C++, "interface dispatch" is a special case of multiple-inheritance vtable dispatch, paid for with the same thunks.

### 8. The Guard, Concretely

An inline cache's **guard** is mechanically simple: it compares the receiver's type descriptor against the cached one. Physically:

- **V8 / SpiderMonkey:** compare the object's hidden-class/shape pointer (the **Map** / **Shape**) against the cached pointer. A pointer compare + a conditional branch.
- **HotSpot:** compare the object's class pointer (`klass`) against the cached `klass`.
- **Go/C++ vtable calls** don't need a guard at all — the vtable *is* the dispatch; there's no speculation to verify.

The guard's whole job is to make speculation safe: *we bet the type is X; the guard confirms it before we trust the cached target.* On success, jump to the cached method. On failure (a **cache miss**), re-resolve and update the cache. A monomorphic IC is just `{ cached_type, cached_target }` plus this compare-and-branch. The next page generalizes one entry to several (a PIC).

---

## Code Examples

### Single-Inheritance Layout in Action (C++)

```cpp
#include <cstdio>

struct Base {
    virtual void f() { printf("Base::f\n"); }
    virtual void g() { printf("Base::g\n"); }
    virtual ~Base() = default;
};

struct Derived : Base {
    void g() override { printf("Derived::g\n"); }  // overrides slot 1
    virtual void h() { printf("Derived::h\n"); }    // new slot 2
};

int main() {
    Base* p = new Derived();
    p->f();   // slot 0 -> Base::f      (inherited)
    p->g();   // slot 1 -> Derived::g   (overridden, same slot)
    // p->h() won't compile: Base has no slot 2. The slot exists, the static type doesn't expose it.
    delete p;
}
```

The receiver `p` needs no adjustment: a `Derived` begins with its `Base` sub-object at offset 0, so `Base*` and the real `Derived*` are the same address.

### Multiple Inheritance and the Hidden Thunk (C++)

```cpp
#include <cstdio>

struct A { virtual void fa() { printf("A::fa\n"); } int a = 1; };
struct B { virtual void fb() { printf("B::fb\n"); } int b = 2; };

struct C : A, B {
    void fa() override { printf("C::fa\n"); }
    void fb() override { printf("C::fb\n"); }
};

int main() {
    C c;
    A* pa = &c;   // points at offset 0   (A sub-object)
    B* pb = &c;   // points at offset N   (B sub-object) — DIFFERENT address!

    printf("%p vs %p\n", (void*)pa, (void*)pb);  // not equal

    pb->fb();     // goes through B's vtable slot -> THUNK -> adjusts this -> C::fb
}
```

`pa` and `pb` print different addresses even though both refer to the same `c`. The call `pb->fb()` enters `C::fb` only because B's vtable slot for `fb` points at a compiler-generated thunk that subtracts the offset to recover the real `C*`.

### Go Interface Dispatch and the itab (conceptual)

```go
package main

import "fmt"

type Speaker interface{ Speak() string }

type Dog struct{ name string }
func (d Dog) Speak() string { return "Woof" }

func main() {
    var s Speaker = Dog{"Rex"}   // s is (itab(Speaker, Dog), &Dog{"Rex"})
    fmt.Println(s.Speak())       // load itab.fun[0] -> Dog.Speak; call with data
}

// Mentally, s.Speak() is:
//   itab   := s.tab               // the cached (Speaker, Dog) itable
//   target := itab.fun[0]         // Dog.Speak
//   data   := s.data
//   target(data)
```

The first time a `Dog` is assigned to a `Speaker`, Go builds (or fetches from the global cache) the `(Speaker, Dog)` itab. Every later call just reads `fun[0]`. A type switch (`switch v := s.(type)`) uses `itab._type` / `itab.hash`.

### Watching an Inline Cache Form (JavaScript, conceptual)

```javascript
function area(shape) {
  return shape.width * shape.height;   // two property-access ICs: .width and .height
}

// First call: ICs are empty -> slow generic lookup, then they record the shape.
area({ width: 3, height: 4 });

// Subsequent calls with the SAME shape {width, height}:
//   guard: shape's Map == cached Map ?  yes
//   -> read width at cached offset, read height at cached offset (no dictionary search)
area({ width: 5, height: 6 });  // monomorphic, fast
```

After the first call, V8's IC for `.width` records "for objects of this Map, `width` lives at field offset k." The guard checks the Map pointer; on a hit it loads from the fixed offset — no name search. The same machinery serves both property reads and method calls.

### A Cache Miss in Slow Motion

```text
call site: shape.width

iter 1:  IC empty
         -> generic lookup finds width at offset 8 for Map_M1
         -> IC := { Map_M1 -> offset 8 }                      (now MONOMORPHIC)

iter 2:  shape has Map_M1
         -> guard hit -> load [shape + 8]                     (fast)

iter 3:  shape has Map_M2 (different shape!)
         -> guard MISS
         -> generic lookup finds width at offset 16 for Map_M2
         -> IC must now hold two cases -> becomes POLYMORPHIC   (senior.md)
```

One stray shape is enough to push a monomorphic site toward polymorphic. That transition is the central performance story of the next level.

---

## Coding Patterns

### Pattern 1: Prefer single inheritance + interfaces over deep multiple inheritance

```text
Instead of: class C : public Drawable, public Serializable, public Comparable { ... }
            (three vptrs, thunks, fatter objects)
Prefer:     compose, or use one base + lightweight interface-style mixins.
```

Multiple inheritance isn't wrong, but each extra base adds a vptr and thunked calls. Reach for it deliberately.

### Pattern 2: Keep interface method sets small and stable

In Go and Java, a smaller interface means a smaller itab/itable and fewer call sites that can go megamorphic across many implementations. `io.Reader` (one method) is cheap to dispatch and easy to keep monomorphic per call site.

### Pattern 3: Don't box into an interface inside a hot loop unnecessarily

```go
// Each assignment to an interface variable may require an itab (cached, but still).
// In a hot loop over concrete Dogs, call the concrete method directly when you can.
```

If you already hold the concrete type, calling it directly is a static dispatch — strictly cheaper than going through an interface value.

---

## Best Practices

- **Know which call is which.** `invokevirtual`/non-virtual-call = vtable or static; `invokeinterface`/Go-interface-call = itable/itab. They have different costs.
- **Treat multiple inheritance as a tool with a footprint.** Extra vptrs and thunks are real; use composition or interfaces when you only need the contract, not the storage.
- **Keep object shapes stable.** In dynamic languages, initialize all fields in the constructor in a consistent order so objects share one hidden class — this keeps property-access ICs monomorphic.
- **Don't compare base pointers from different bases for identity.** Under multiple inheritance, `(A*)&c != (B*)&c`. Compare typed pointers or compare addresses of the most-derived object.
- **Let the runtime cache interface dispatch; design for type stability, not manual caching.** Hand-rolling your own dispatch table rarely beats the runtime's itab/IC.

---

## Edge Cases & Pitfalls

- **`(A*)&c` and `(B*)&c` are different addresses** under multiple inheritance. Code that assumes "same object → same pointer value" breaks. Identity must compare most-derived pointers.
- **Calling through the wrong base after a `reinterpret_cast`** skips the thunk and lands you at the wrong offset — undefined behavior. Use `static_cast`/`dynamic_cast`, which apply the offset.
- **An empty/zero interface value in Go** has a nil itab; calling a method on a nil interface panics, while a non-nil interface wrapping a nil pointer does *not* (the itab is present). This nil-vs-nil-interface trap bites everyone once.
- **Adding a field or method late (dynamic langs) splits hidden classes.** Two objects you think are "the same shape" may have different Maps if their fields were added in different orders — silently making a call site polymorphic.
- **itable/itab lookups are only cheap after the cache is warm.** A microbenchmark that measures the first interface call measures the resolution cost, not the steady state.
- **Covariant return types add return-adjusting thunks** in C++. The slot points at glue that fixes the returned pointer, not just `this`.

---

## Apply it

1. Find a real component where **Method Dispatch & Inline Caches** affects an interface or dependency.
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

- Which boundary is most affected by Method Dispatch & Inline Caches?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
