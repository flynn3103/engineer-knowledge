# Method Dispatch & Inline Caches — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Method Dispatch & Inline Caches** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Two Ways to Find a Method

Every method call is answered in one of two fundamental ways.

**Static dispatch.** The compiler already knows the exact target. A free function `sqrt(x)`, a `private` method, a `final` method, a non-virtual C++ method, a Go function call — all of these resolve to a fixed address at compile time. The generated machine code is essentially `call 0x4011a0`. This is as cheap as a call gets: one jump, and the CPU's branch predictor handles it beautifully because the target never changes.

**Dynamic dispatch.** The compiler does *not* know the target, because it depends on the runtime type of the receiver. `animal.speak()` where `animal` is declared as `Animal` but might actually be a `Dog` or a `Cat`. The machine must, at runtime, ask the object "what are you, really?" and then jump to the matching method. This is more expensive, and the rest of this topic is largely about *how* runtimes make it fast.

### 2. The vtable: How Compiled Languages Do It Fast

In C++, Java, C#, and similar languages, dynamic dispatch is implemented with a **vtable** — a virtual method table.

Here is the trick. Every class with virtual methods gets, at compile/link time, one shared table: an array of function pointers, one slot per virtual method. `Animal`'s vtable has a slot for `speak`. `Dog`'s vtable also has a slot for `speak` *at the same index*, but it points at `Dog::speak` instead of `Animal::speak`.

Every object carries a hidden pointer — the **vptr** — to its class's vtable. So a `Dog` object's vptr points at `Dog`'s vtable; a `Cat` object's vptr points at `Cat`'s vtable.

Now the magic. The call `animal->speak()` becomes, roughly:

```text
1. vptr   = animal->__vptr        // load the hidden pointer (one memory read)
2. target = vptr[INDEX_OF_speak]  // load the function pointer (one memory read)
3. call target                    // jump to it (one indirect call)
```

The compiler knows `speak` is, say, slot 0 in *every* `Animal`-family vtable — that index is fixed at compile time. So the only runtime work is: follow the vptr, read the slot, jump. Two memory loads and an indirect call. Fast, constant-time, and it works no matter how many subclasses exist. **This is the single most important mechanism in this whole topic.**

### 3. Why Dynamic Languages Are Different (and Slower by Default)

Python, JavaScript, and Ruby don't have a fixed vtable laid out at compile time, because their objects can change shape at runtime — you can add a method to a class, attach a field to a single object, or rewire inheritance on the fly. There's no compile step that can freeze a vtable.

So how do they find `obj.method()`? Naively, by **searching**:

- **Python** looks at the object, then walks its class's **MRO** (Method Resolution Order) — an ordered list of the class and all its parents — checking each one's dictionary for an attribute named `method`.
- **JavaScript** walks the **prototype chain**: it checks the object itself, then the object's prototype, then *that* prototype, and so on up the chain, looking for a property named `method`.
- **Ruby** walks its class's ancestor chain, checking each class's method table.

Each step is a hash-table (dictionary) lookup. A few of those per call, every single call, is slow — far slower than the vtable's "two loads and a jump." If you called `obj.method()` a million times in a loop, naively you'd do that whole search a million times, even though the answer is *the same every time*.

### 4. The Inline Cache: Remembering the Answer

Here's the key insight that makes dynamic languages fast: **at any given call site, the object is almost always the same type as it was last time.** The `obj.method()` on line 42 sees `Account` objects on iteration 1, iteration 2, iteration 3... essentially always `Account`.

So the runtime adds a tiny memo *at the call site* — an **inline cache** (IC). The first time the line runs, it does the slow search, finds the answer, and writes down: *"if the object's type is `Account`, the method is at address `0xABC`."* On every later run, it does a quick check — *"is this object still an `Account`?"* — and if yes (the common case), it jumps straight to `0xABC`, skipping the entire search.

That quick check is called the **guard**. The guard compares the object's runtime type descriptor (its **hidden class** or **shape**) against the cached one. A pointer comparison and a branch — cheap. If the guard passes, you've turned a multi-step dictionary search into something almost as fast as a vtable call. This is why modern JavaScript and Python are far faster than a naive interpreter would be.

A call site that always sees one type is called **monomorphic** — "one shape." That's the case inline caches love.

### 5. Putting It Together

Static dispatch is the fastest (no lookup at all). The vtable makes dynamic dispatch in compiled languages nearly as fast (a couple of loads). And the inline cache lets dynamic languages *approach* vtable speed for the common case where a call site keeps seeing the same type. The whole field is a story of **turning a search into a jump** — and the more predictable your types are at each call site, the better that trick works. The reverse — call sites that see many different types — is where things get slow, which is a major theme of the senior and professional pages.

---

## Code Examples

### Static vs Dynamic Dispatch in C++

```cpp
#include <cstdio>

struct Animal {
    // NOT virtual: statically dispatched. Always calls Animal::name.
    const char* name() { return "animal"; }
    // virtual: dynamically dispatched through the vtable.
    virtual void speak() { printf("...\n"); }
    virtual ~Animal() = default;
};

struct Dog : Animal {
    void speak() override { printf("Woof\n"); }
};

void make_it_speak(Animal* a) {
    a->speak();   // DYNAMIC: vtable lookup. Could be Dog::speak or Animal::speak.
    a->name();    // STATIC: always Animal::name, even for a Dog. Bound at compile time.
}

int main() {
    Dog d;
    make_it_speak(&d);   // prints "Woof" — speak() found Dog via the vtable
}
```

`speak()` is `virtual`, so the call goes through `d`'s vtable and finds `Dog::speak`. `name()` is *not* virtual, so even though `d` is really a `Dog`, the compiler statically binds to `Animal::name`. This single example shows the whole static/dynamic split in one function.

### What the vtable Call Becomes (pseudo-assembly)

```text
; a->speak()  where speak is virtual method at slot 0
mov  rax, [rdi]          ; rax = a->vptr        (load the hidden pointer)
mov  rax, [rax + 0]      ; rax = vptr[0]        (load slot 0 = the speak target)
call rax                 ; jump to it           (indirect call)
```

Two loads and an indirect `call`. Compare with a static call, which is a single `call <fixed address>`. That extra indirection is the entire runtime cost of a virtual call in C++ — usually a handful of cycles when the branch predictor cooperates.

### Dynamic Lookup in Python (conceptual)

```python
class Animal:
    def speak(self): return "..."

class Dog(Animal):
    def speak(self): return "Woof"

d = Dog()
print(d.speak())   # "Woof"

# What Python does, roughly, to resolve d.speak:
#   1. Is "speak" an attribute on the instance d's __dict__?  No.
#   2. Walk type(d).__mro__ = [Dog, Animal, object]
#   3. Is "speak" in Dog.__dict__?  Yes -> use Dog.speak
print(Dog.__mro__)   # (<class 'Dog'>, <class 'Animal'>, <class 'object'>)
```

`Dog.__mro__` is the **Method Resolution Order**: the exact ordered list Python searches. For `speak`, it stops at `Dog`. For a method only defined on `Animal`, it would search `Dog` (miss), then `Animal` (hit). Each step is a dictionary lookup. Without caching, this search happens on *every* call.

### Why Naive Lookup Is Slow (and why caching helps)

```python
class Account:
    def balance(self): return 100

# A hot loop calling the same method on the same type a million times.
acc = Account()
total = 0
for _ in range(1_000_000):
    total += acc.balance()   # SAME type, SAME method, every iteration
```

Naively, every one of the million iterations re-walks `Account`'s MRO to find `balance`. But the answer never changes! A modern Python (3.12+ has specializing adaptive interpreter ICs) or a JIT like PyPy will cache the resolved method at this call site after the first iteration, guard on "is the object still an `Account`?", and skip the search. That's the inline cache earning its keep.

### Monomorphic vs Polymorphic in JavaScript (conceptual)

```javascript
function getX(point) {
  return point.x;          // property access — also uses an inline cache!
}

// MONOMORPHIC: every call sees the same shape {x, y}. Fast.
for (let i = 0; i < 1e6; i++) {
  getX({ x: i, y: 0 });
}

// POLYMORPHIC / MEGAMORPHIC: many different shapes through one call site. Slow.
const shapes = [{ x: 1 }, { x: 1, y: 2 }, { a: 0, x: 3 }, { x: 4, z: 9 }, /* ... */];
for (const s of shapes) {
  getX(s);                 // the IC at `point.x` keeps missing -> degrades
}
```

The first loop keeps the `point.x` call site **monomorphic** — one shape — so V8's inline cache nails it every time. The second loop feeds many object shapes through the same site, so the cache can't settle on one answer and the access gets slow. Note that **property access** (`point.x`), not just method calls, is cached this way.

---

## Coding Patterns

### Pattern 1: Keep a hot call site type-stable (monomorphic)

```javascript
// GOOD: the array holds one shape, so `p.x` stays monomorphic.
const points = makePoints();           // all {x, y}
let sum = 0;
for (const p of points) sum += p.x;    // IC stays happy

// RISKY: mixing many object shapes through the same hot access defeats the IC.
```

The junior takeaway: **in hot loops, feed one type through a given call site.** Type-stable collections keep inline caches monomorphic.

### Pattern 2: Mark methods non-overridable when they truly are

```java
public final class Money {           // final class -> methods can be devirtualized
    public final long cents() { ... } // final method -> compiler may bind statically
}
```

`final` is a hint that the compiler and JIT can use to skip dynamic dispatch and even inline the call. Use it when a method genuinely shouldn't be overridden — it's both clearer and faster.

### Pattern 3: Don't fear virtual calls — fear *unpredictable* ones

A virtual call that always lands on the same target is cheap (the branch predictor and inline cache handle it). The expensive case is the call site that jumps all over the place. Design for predictability, not for zero virtual calls.

---

## Best Practices

- **Default to clear code; optimize dispatch only where it's hot.** A virtual call in cold code costs nothing meaningful. Profile first.
- **Keep hot call sites monomorphic.** If a loop calls `x.foo()` a million times, try to make sure `x` is the same type each time. This is the single biggest inline-cache lever you control.
- **Use `final`/`sealed`/non-virtual when a method shouldn't be overridden.** It documents intent *and* unlocks the fast path.
- **Prefer homogeneous collections in hot paths.** A `List<Dog>` iterated and `.speak()`-ed is faster than a `List<Animal>` holding a wild mix, because the call site stays type-stable.
- **Don't prematurely de-virtualize by hand.** Don't replace clean polymorphism with `if/else` type switches "for speed" without measuring — modern runtimes optimize the polymorphism for you, and your manual version is often slower *and* uglier.

---

## Edge Cases & Pitfalls

- **"Virtual is always slow" is a myth.** A predictable virtual call is only a few cycles more than a static one, and the JIT often inlines it away entirely. The real cost is *unpredictable* dispatch.
- **Calling a virtual method in a constructor/destructor.** In C++, during construction the object's vptr points at the *base* class's vtable, so a virtual call in a constructor does *not* reach the derived override. This surprises everyone once.
- **Non-virtual methods don't dispatch dynamically — even on a derived object.** In the C++ example, `a->name()` calls `Animal::name` even when `a` is really a `Dog`. If you expected the override, you forgot `virtual`.
- **The hidden vptr costs a word per object.** Tiny objects with virtual methods carry an extra pointer. Usually negligible, occasionally relevant for huge arrays of tiny objects.
- **Adding a method to a class at runtime (Python/JS/Ruby) can invalidate inline caches.** It's flexible, but it forces caches to be thrown away and rebuilt — a hidden cost of monkey-patching in a hot path.
- **A single "weird" object can pollute a hot call site.** In JS, feeding even occasionally-different shapes through a hot property access can knock its inline cache out of the fast monomorphic state.

---

## Apply it

1. Choose one small, known input for **Method Dispatch & Inline Caches**.
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

- What problem does Method Dispatch & Inline Caches solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
