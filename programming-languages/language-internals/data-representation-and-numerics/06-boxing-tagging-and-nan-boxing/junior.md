# Boxing, Tagging & NaN-Boxing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Boxing, Tagging & NaN-Boxing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Core Problem: One Slot, Two Possible Meanings

Imagine you are designing a list that can hold anything. Every element is one machine word — eight bytes. Sometimes that word should mean "the integer 42." Sometimes it should mean "a pointer to a `User` object at heap address `0x7fff...`." When you read a slot back, the *bits look the same* — eight bytes are eight bytes. So how do you know whether to treat them as a number or as an address to follow?

You have three broad strategies:

1. **Make everything a pointer (boxing).** Even the number 42 becomes a tiny heap object. Now every slot is uniformly "a pointer," and the object it points to carries a type tag. Simple, uniform, slow.
2. **Steal spare bits to tag (pointer tagging).** Numbers stay in the slot directly; use a couple of low bits to flag "this is a small int, not a pointer."
3. **Hide everything inside a float (NaN-boxing).** Exploit the fact that a 64-bit `double` has billions of unused bit-patterns (NaNs) and stuff non-float values into them.

This page focuses on strategy 1, because it's the one you meet first as a working programmer — Java and C# do it constantly, often without you asking.

### 2. Boxing: Wrapping a Primitive So It Can Be a Reference

A **box** is a heap object whose only job is to hold one primitive value. In Java:

```text
   int (primitive, 4 bytes, lives in a register or on the stack)
        │  boxing
        ▼
   Integer (object on the heap)
   ┌──────────────────────────┐
   │ object header (~12-16 B)  │
   │ int value: 5              │
   └──────────────────────────┘
        ▲
        │ the slot in your ArrayList holds a POINTER to this
```

The primitive `5` is 4 bytes. The boxed `Integer` holding 5 is a full heap object — an object header *plus* the value, often 16 bytes total, plus the 8-byte pointer that refers to it. You turned 4 bytes of data into ~24 bytes of memory traffic. That is the cost of boxing.

### 3. Why Boxing Is Slow

Boxing hurts in three compounding ways:

- **Allocation cost.** Each box is a heap allocation. Allocating is cheap individually but adds up fast in a loop.
- **GC pressure.** Every box is garbage the collector must eventually find, trace, and free. A loop that boxes a million integers creates a million pieces of short-lived garbage.
- **Cache misses from pointer chasing.** An `int[]` stores its numbers *contiguously* — the CPU can stream them. An `ArrayList<Integer>` stores *pointers* contiguously, and each pointer leads somewhere else in the heap. Reading the values means jumping all over memory, and each jump risks a cache miss. This is often the biggest cost of all.

### 4. The Canonical Comparison: `int[]` vs `ArrayList<Integer>`

This is the single most important practical takeaway of the whole topic:

```text
int[]                          ArrayList<Integer>
┌──┬──┬──┬──┬──┐                ┌──┬──┬──┬──┬──┐
│ 1│ 2│ 3│ 4│ 5│  ← values     │ •│ •│ •│ •│ •│  ← pointers
└──┴──┴──┴──┴──┘                └─┬┴─┬┴─┬┴─┬┴─┬┘
contiguous, cache-friendly        │  │  │  │  │
                                   ▼  ▼  ▼  ▼  ▼
                                  [1][2][3][4][5]  ← scattered boxes
```

The `int[]` is one tight block the CPU loves. The `ArrayList<Integer>` is an array of pointers to scattered boxes — more memory, more allocations, and a cache miss waiting at every element. In tight numeric loops, `int[]` can be **several times faster**. When you need performance, prefer primitive arrays (or specialized libraries like Eclipse Collections / fastutil in Java) over boxed collections.

### 5. Unboxing and Its Famous Trap: the Null Box

Unboxing pulls the primitive back out of the box. In Java, `int x = someInteger;` automatically unboxes. The trap: if the `Integer` is `null`, unboxing it means dereferencing null, which throws a `NullPointerException` — often in a surprising place:

```java
Integer a = null;
int b = a;        // NullPointerException! (autoboxing tries a.intValue())
```

You wrote what looks like a harmless assignment, but the compiler inserted a method call on `null`. This is one of the most common boxing-related bugs.

### 6. A First Look at the Alternatives

Boxing makes *everything* a pointer. The clever alternatives keep small values *in* the slot:

- **Pointer tagging.** Aligned heap pointers always end in a few zero bits (a pointer to an 8-byte-aligned object ends in `000`). Runtimes use those free bits as a tag: "ends in 0 → it's a small integer; ends in 1 → it's a real pointer." V8 (the JavaScript engine in Chrome and Node) calls its tagged small integers **SMIs**. Ruby tags its `Fixnum`, `nil`, `true`, `false`, and symbols this way. The cost: a tagged integer loses a bit of range (a 64-bit slot holds 63- or 62-bit ints, not full 64-bit).
- **NaN-boxing.** A 64-bit `double` has an enormous number of bit patterns that all mean "Not a Number." Runtimes hijack those spare patterns to encode integers, pointers, and `true`/`false`/`null` — so *every value is physically a double*, and arithmetic on real numbers runs at native speed. SpiderMonkey (Firefox), LuaJIT, and JavaScriptCore (Safari) use this.

You don't need the bit-level details yet — `middle.md` and `senior.md` cover them. For now, hold the shape: **boxing puts the value behind a pointer; tagging and NaN-boxing keep the value in the slot and use spare bits to remember its kind.**

### 7. Where You Meet This Daily

- **Java:** `List<Integer>`, `Map<String, Long>`, generics over primitives — all box. `int`, `long`, `double` are primitives; `Integer`, `Long`, `Double` are boxes.
- **C#:** Putting an `int` into an `object` or a non-generic collection boxes it. Generics (`List<int>`) avoid it — a key difference from Java.
- **Python:** *Everything* is an object, including the number `5`. CPython caches small integers (−5 to 256) so they aren't re-allocated.
- **JavaScript:** Engines use SMIs (tagged small ints) or NaN-boxing under the hood, but you never see it — all numbers are conceptually doubles.

---

## Code Examples

We'll see boxing's cost and its traps across languages.

### Java — Boxing happens automatically (autoboxing)

```java
import java.util.ArrayList;
import java.util.List;

public class Boxing {
    public static void main(String[] args) {
        List<Integer> list = new ArrayList<>();
        for (int i = 0; i < 5; i++) {
            list.add(i);   // AUTOBOXING: int i -> Integer.valueOf(i), a heap object
        }
        int sum = 0;
        for (Integer n : list) {
            sum += n;      // AUTO-UNBOXING: n.intValue()
        }
        System.out.println(sum); // 10
    }
}
```

Every `list.add(i)` silently calls `Integer.valueOf(i)` and stores a pointer to a heap object. Every `sum += n` silently calls `n.intValue()`. The convenience hides the cost.

### Java — The Integer cache and the `==` trap

```java
public class IntegerCache {
    public static void main(String[] args) {
        Integer a = 127, b = 127;
        System.out.println(a == b);        // true  -- same cached object

        Integer c = 128, d = 128;
        System.out.println(c == d);        // false -- two different objects!

        System.out.println(c.equals(d));   // true  -- compares VALUES
    }
}
```

`Integer.valueOf` caches the boxes for −128..127 and hands out the *same* object each time, so `==` (reference identity) is `true`. Outside that range it allocates fresh objects, so `==` is `false`. **Always use `.equals()` to compare boxed values; `==` compares pointers, not numbers.**

### Java — The null-unboxing NullPointerException

```java
import java.util.HashMap;
import java.util.Map;

public class NullUnbox {
    public static void main(String[] args) {
        Map<String, Integer> counts = new HashMap<>();
        int n = counts.get("missing");  // get() returns null -> auto-unbox null -> NPE
        System.out.println(n);
    }
}
```

`counts.get("missing")` returns `null` (the key is absent). Assigning it to `int n` auto-unboxes, which calls `.intValue()` on `null` — a `NullPointerException`, thrown by a line that *looks* like it can't fail.

### C# — Boxing a value type into `object`

```csharp
using System;

class Program {
    static void Main() {
        int x = 42;
        object boxed = x;      // BOXING: int copied onto the heap, boxed holds a reference
        int y = (int)boxed;    // UNBOXING: copy back out

        Console.WriteLine(y);  // 42

        // Boxed copies are independent of the original:
        x = 99;
        Console.WriteLine((int)boxed); // still 42 -- the box has its own copy
    }
}
```

In C#, a `struct` (value type) is boxed when stored in an `object` or a non-generic collection. Critically, **generics avoid this**: `List<int>` stores ints directly, no boxing — unlike Java, where `List<Integer>` always boxes.

### Python — Everything is an object, and small ints are cached

```python
a = 256
b = 256
print(a is b)    # True  -- CPython caches small ints (-5..256)

c = 257
d = 257
print(c is d)    # often False in the REPL -- separate objects

print(c == d)    # True  -- compares VALUES, always correct
```

In CPython, even `5` is a heap object (`PyLongObject`). The interpreter pre-creates the small integers −5 to 256 and reuses them, so `is` (identity) is `True` for those. Outside the cache, identity is not guaranteed. As in Java: **compare values with `==`, never identity with `is`.**

### Go — No autoboxing, but `interface{}` boxes

```go
package main

import "fmt"

func main() {
    var i int = 42
    var any interface{} = i // boxing-like: int stored in an interface value (heap if it escapes)
    n := any.(int)          // type assertion = unboxing
    fmt.Println(n)          // 42
}
```

Go has no Java-style autoboxing, but putting a value into an empty interface (`interface{}` / `any`) is the same idea: the value gains a type tag and may be heap-allocated. Type assertions pull it back out. Same trade-off, different syntax.

---

## Coding Patterns

### Pattern 1: Prefer primitive arrays in hot paths (Java)

```java
// Slow: boxed
List<Integer> values = new ArrayList<>();
// Fast: primitive
int[] values2 = new int[n];
```

When a collection is large and numeric and you control its shape, a primitive array eliminates every box.

### Pattern 2: Always compare boxed values with `.equals` / `==value`, never identity

```java
if (a.equals(b)) { ... }   // Java: correct
```

```python
if c == d:   # Python: correct (value compare)
    ...
# never `if c is d` for number equality
```

### Pattern 3: Guard against null before unboxing (Java)

```java
Integer v = map.get(key);
int n = (v != null) ? v : 0;   // safe; or map.getOrDefault(key, 0)
```

### Pattern 4: Use C# generics to avoid boxing

```csharp
List<int> nums = new();   // no boxing
// not: ArrayList nums (non-generic) -> boxes every int
```

### Pattern 5: Stream primitives, not boxes (Java)

```java
int sum = IntStream.rangeClosed(1, 100).sum();  // IntStream, no boxing
// not: Stream<Integer> ... .reduce(0, Integer::sum)  -> boxes
```

---

## Best Practices

- **Know which of your types box.** In Java, capital-letter wrapper types (`Integer`, `Long`, `Double`) box; lowercase primitives (`int`, `long`, `double`) don't. In C#, `struct → object` boxes; generics don't.
- **Use specialized primitive APIs.** `IntStream`/`LongStream` over `Stream<Integer>`; `int[]` over `List<Integer>`; fastutil / Eclipse Collections for primitive collections.
- **Never rely on `==` / `is` for boxed-number equality.** Use `.equals` (Java) or `==` (Python value compare). The small-int caches make identity *sometimes* work, which is worse than always failing.
- **Treat every auto-unbox as a possible NPE.** Any `int x = someInteger;` where the `Integer` could be null is a latent crash. Prefer `getOrDefault`, `Optional`, or explicit null checks.
- **Measure before assuming boxing matters.** In glue code it's free. In a 10-million-iteration loop it can dominate. Profile, don't guess.
- **Understand your runtime's number representation.** If you write JavaScript, Lua, or Ruby, knowing whether the engine uses SMI tagging or NaN-boxing explains why integer-heavy code is fast and why huge integers or weird values can fall off a fast path.

---

## Edge Cases & Pitfalls

- **The `Integer` cache boundary at 128.** `Integer a = 127, b = 127; a == b` is `true`; at `128` it's `false`. Pure identity accident; never depend on it.
- **`Long` has a cache too.** Java caches `Long.valueOf(−128..127)` exactly like `Integer`. Same trap.
- **Null unboxing throws.** `int x = nullableInteger;` is a `NullPointerException` factory. The most surprising NPE in Java for beginners.
- **`==` between `Integer` and `int` unboxes the `Integer`.** Mixing the two in a comparison silently unboxes — which can *also* NPE if the boxed side is null.
- **Boxed values copy in C#.** `object boxed = x;` makes an independent copy; later changes to `x` don't affect `boxed`. Surprises people who expect reference semantics.
- **Python's `is` on small ints "works" then mysteriously stops.** `256 is 256` → `True`, `257 is 257` → often `False`. The cache boundary, not a language guarantee.
- **Hidden boxing in generics/streams.** `Stream<Integer>`, `Map<Integer, ...>`, lambdas capturing primitives — boxing sneaks in where you didn't write it.
- **Tagged small ints have reduced range (preview).** A runtime using 1-bit tagging stores 63-bit, not 64-bit, integers. Numbers near the limit may silently promote to a boxed "big" representation.

---

## Common Mistakes

1. **Comparing boxed numbers with `==` (Java) or `is` (Python).** Works for small cached values, fails for large ones. A classic intermittent bug.
2. **Assigning a possibly-null `Integer` to an `int`.** Auto-unboxing null → NPE.
3. **Using `ArrayList<Integer>` for a large numeric workload.** Boxing tax in memory and speed where `int[]` would fly.
4. **Assuming C# collections box like Java's.** They don't — `List<int>` is unboxed. Carrying Java intuition to C# misleads.
5. **Thinking Python `int` is a primitive.** It's a full heap object; the small-int cache is the only reason identity ever holds.
6. **Mutating after boxing in C# and expecting the box to change.** The box is a snapshot copy.
7. **Ignoring boxing in hot lambdas/streams.** A `Stream<Integer>` in a critical loop quietly allocates millions of boxes.
8. **Believing all of this is "just an optimization detail."** The identity and null traps are *correctness* bugs, not just performance ones.

---

## Apply it

1. Choose one small, known input for **Boxing, Tagging & NaN-Boxing**.
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

- What problem does Boxing, Tagging & NaN-Boxing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
