# Evaluation Strategies (call-by-x) — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Evaluation Strategies (call-by-x)** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Question Every Function Call Answers

When you write:

```python
x = 10
f(x)
```

the language must decide what `f` gets. There are really only three everyday answers:

1. **A copy of the value** (`10`). `f` can do anything with it; your `x` stays `10`. This is **call-by-value**.
2. **A handle to your variable itself.** If `f` writes `x = 99`, *your* `x` becomes `99`. This is **call-by-reference** — relatively rare as a built-in (C++, Pascal, C#'s `ref`).
3. **A copy of a reference to the same object.** `f` cannot change which object your variable points to, but if the object is mutable, `f` can change its *contents*. This is **call-by-sharing**, and it is what Python, Java, JavaScript, Ruby, and C# (for class types) actually do.

Almost every junior bug comes from confusing #1 and #3.

### 2. Call-by-Value: The Function Gets a Copy

In a pure call-by-value language, the argument is copied into the parameter. The parameter is a brand-new variable that happens to start with the same value.

```c
void addOne(int n) {
    n = n + 1;      // changes the LOCAL copy only
}

int main() {
    int x = 5;
    addOne(x);
    // x is STILL 5. The function changed its own copy.
}
```

C passes everything by value. Even a struct is *copied* into the function. The mental rule: **assigning to a parameter in a call-by-value language never affects the caller.** Full stop.

### 3. Call-by-Reference: The Function Gets Your Variable

In a true call-by-reference language, the parameter is an *alias* for the caller's variable. There is no copy — both names refer to the same storage.

```cpp
void addOne(int& n) {   // C++: the & makes it call-by-reference
    n = n + 1;          // changes the CALLER's variable
}

int main() {
    int x = 5;
    addOne(x);
    // x is now 6. The function reached back and changed it.
}
```

The single `&` is the whole difference. This is powerful and occasionally exactly what you want (e.g. a function that returns two values by writing into two parameters), but it makes functions harder to reason about: you cannot tell from the call site `addOne(x)` whether `x` will survive unchanged.

### 4. Call-by-Sharing: The Confusing One (Python / Java / JS)

Here is the part that trips up everyone. Languages like Python, Java, and JavaScript do **not** give you call-by-reference for objects, and they do **not** give you a deep copy either. They give you a **copy of the reference**. Both the caller's variable and the parameter point at *the same object*.

```python
def mutate(lst):
    lst.append(99)      # changes the SHARED object — caller sees it
    lst = [1, 2, 3]     # REBINDS the local name only — caller does NOT see it

original = [1, 2]
mutate(original)
print(original)         # [1, 2, 99]  — the append leaked out; the rebind did not
```

Read that twice. Two operations look similar but behave completely differently:

- `lst.append(99)` **mutates the shared object** → visible to the caller.
- `lst = [1, 2, 3]` **rebinds the local parameter** to a new object → invisible to the caller.

The crisp way to say it: **Python passes the reference *by value*.** You get a copy of the arrow, not a copy of the box, and not the caller's variable slot itself.

### 5. Why Integers "Feel" Like Call-by-Value in Python

If you do:

```python
def addOne(n):
    n = n + 1
    print(n)      # 6

x = 5
addOne(x)
print(x)          # 5 — unchanged!
```

This looks like call-by-value, but it is the *same* call-by-sharing rule. `n = n + 1` is a **rebind**: `n + 1` makes a brand-new integer object, and `n` is pointed at it. Integers are **immutable** in Python — there is no `n.increment_in_place()` — so the only thing you *can* do is rebind, and rebinds never reach the caller. Mutability, not a different passing rule, is why numbers behave one way and lists another.

### 6. The Unifying Insight: It's All About What You Can and Can't Do

| Operation | Call-by-value | Call-by-reference | Call-by-sharing |
|-----------|---------------|-------------------|-----------------|
| Rebind the parameter (`p = other`) | local only | **affects caller** | local only |
| Mutate the object (`p.field = ...`) | local only (it's a copy) | affects caller | **affects caller** |

Notice call-by-sharing sits in between. You can't rebind the caller's variable, but you *can* reach into the shared object and change it. That single row is the source of nearly every "why did my list change?" bug.

---

## Code Examples

### Example 1: The Same Code, Three Languages, Watch the Difference

```python
# Python — call-by-sharing
def f(lst):
    lst.append(4)     # mutates shared object → leaks out

a = [1, 2, 3]
f(a)
print(a)              # [1, 2, 3, 4]
```

```java
// Java — call-by-sharing (same as Python for objects)
void f(List<Integer> lst) {
    lst.add(4);       // mutates shared object → leaks out
}
List<Integer> a = new ArrayList<>(List.of(1, 2, 3));
f(a);
// a is now [1, 2, 3, 4]
```

```c
// C — call-by-value, the struct is COPIED
struct Vec { int data[3]; };
void f(struct Vec v) {
    v.data[0] = 99;   // changes the COPY only
}
struct Vec a = {{1, 2, 3}};
f(a);
// a.data[0] is STILL 1 — C copied the whole struct
```

### Example 2: Rebinding vs Mutating in Python

```python
def rebind(lst):
    lst = [9, 9, 9]       # local rebind, caller unaffected

def mutate(lst):
    lst[0] = 9            # mutation, caller affected

a = [1, 2, 3]
rebind(a)
print(a)                  # [1, 2, 3]   — rebind didn't leak

b = [1, 2, 3]
mutate(b)
print(b)                  # [9, 2, 3]   — mutation leaked
```

### Example 3: How C "Fakes" Call-by-Reference With a Pointer

C only has call-by-value. To let a function change the caller's variable, you pass the *address* of the variable (a pointer). The pointer itself is copied (by value!), but following it reaches the original.

```c
void addOne(int* n) {     // pass a pointer
    *n = *n + 1;          // follow the pointer, change the original
}

int main() {
    int x = 5;
    addOne(&x);           // pass the ADDRESS of x
    // x is now 6
}
```

This is the universal trick: **"pass by reference" in C is just call-by-value where the value happens to be a pointer.** You manually take the address with `&` and manually follow it with `*`.

### Example 4: The Swap That Doesn't Swap

The classic beginner bug. This swap works in C++ (true reference) but silently fails in a copy-only setting:

```python
# Python — looks like a swap, does nothing to the caller
def broken_swap(a, b):
    a, b = b, a           # only rebinds the LOCAL parameters

x, y = 1, 2
broken_swap(x, y)
print(x, y)               # 1 2 — unchanged!
```

```cpp
// C++ — works, because & gives true call-by-reference
void swap(int& a, int& b) {
    int t = a; a = b; b = t;
}
int x = 1, y = 2;
swap(x, y);               // x == 2, y == 1
```

Same idea, opposite result, because of the passing strategy.

---

## Coding Patterns

**Pattern: Defensive copy at the boundary.** If a function should not change the caller's list, copy it on the way in.

```python
def process(items):
    items = list(items)      # make a private copy first
    items.sort()             # safe to mutate now — it's ours
    return items
```

**Pattern: Return a new value instead of mutating.** Prefer functions that *return* results over functions that mutate arguments. It removes the whole class of "did this leak?" questions.

```python
# Prefer this (pure)
def with_appended(lst, x):
    return lst + [x]         # new list, caller's list untouched

# Over this (mutating)
def append_in_place(lst, x):
    lst.append(x)            # changes the caller's list
```

**Pattern: Document mutation in the name.** If a function *does* mutate its argument, say so: `sort_in_place(items)`, `fill_buffer(buf)`. The name is the contract.

**Pattern: Use immutables for shared data.** Pass tuples instead of lists, `frozenset` instead of `set`, when the receiver has no business changing them.

---

## Best Practices

1. **Know your language's one rule.** For Python/Java/JS: "reference passed by value — mutation leaks, rebinding doesn't." For C/Go (non-pointer): "everything is copied." Say it out loud.
2. **Don't mutate arguments unless that's the explicit job.** A function named `calculate_total(items)` should not reorder `items`. Surprise mutation is rude and bug-prone.
3. **If you must mutate, name the function so callers know.** `clear()`, `sort()`, `_in_place` suffixes.
4. **Prefer returning new values over mutating.** Pure functions are easier to test and reason about.
5. **Reach for immutable types** (tuples, strings, frozensets) when you want sharing without risk.
6. **When you genuinely need to change the caller's variable, be explicit:** pointers in C/Go, `ref`/`out` in C#, references in C++ — and prefer returning a value when you can.

---

## Edge Cases & Pitfalls

**Pitfall 1: "I passed a list and it changed."** You shared the object. The function mutated it. This is call-by-sharing working as designed, not a bug in the language. Fix: copy at the boundary or don't mutate.

**Pitfall 2: The non-working swap.** `def swap(a, b): a, b = b, a` does nothing to the caller in Python/Java because it only rebinds local parameters. There is no built-in call-by-reference to make it work.

**Pitfall 3: Mutable default arguments (Python's most famous trap).**

```python
def add_item(item, bucket=[]):   # DANGER: one shared list
    bucket.append(item)
    return bucket

add_item(1)     # [1]
add_item(2)     # [1, 2]  — the SAME list persisted across calls!
```

The default `[]` is created *once* and shared across all calls. Fix:

```python
def add_item(item, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
```

**Pitfall 4: Thinking integers are passed differently from lists.** They aren't. The passing rule is identical (call-by-sharing). Integers just *look* like call-by-value because they're immutable, so rebinding is all you can do.

**Pitfall 5: A copy that isn't deep.** `new_list = list(old)` copies the *outer* list but the inner objects are still shared. Mutating an inner object leaks. (That is "shallow copy"; a "deep copy" recursively copies.)

---

## Common Mistakes

- **Saying "Python is pass-by-reference."** It isn't. It's call-by-sharing (pass-the-reference-by-value). The give-away test: the broken swap. If Python were pass-by-reference, the swap would work — it doesn't.
- **Saying "Python is pass-by-value."** Also wrong: then mutating a passed list couldn't leak — but it does.
- **Assuming a function won't touch your data.** In call-by-sharing languages, always assume a function *could* mutate a mutable argument unless you know otherwise.
- **Forgetting that copying a list is shallow.** Inner objects are still shared after a shallow copy.
- **Reusing a mutable default argument.** The mutable-default trap above.

---

## Apply it

1. Choose one small, known input for **Evaluation Strategies (call-by-x)**.
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

- What problem does Evaluation Strategies (call-by-x) solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
