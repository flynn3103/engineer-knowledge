# Escape Analysis — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Escape Analysis** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Stack is cheap, heap is expensive

Allocating on the stack is essentially free: the function already has a frame, and the variable lives in it. When the function returns, the whole frame disappears — no cleanup work, no GC.

Allocating on the heap costs more in three ways:
1. The allocator must find space.
2. The GC must later track and reclaim it.
3. More heap traffic means the GC runs more often, which can pause or slow your program.

So **fewer heap allocations → less GC work → smoother, faster programs.** Escape analysis is one of the main tools that keeps allocations off the heap.

### 2. The rule: a value escapes if it can outlive its function

The compiler's job is to be *safe*. A value can only stay on the stack if the compiler can **prove** it won't be used after the function returns. The moment a value might "leak out," it must go to the heap.

Common ways a value escapes:

- **It's returned** as a pointer/reference to the caller.
- **It's stored in something that outlives the function** — a global variable, a field of a long-lived object, a slice/map that survives.
- **Its address is taken and handed to something that keeps it.**
- **It's captured by a closure** (an inner function) that outlives the current call.
- **It's passed to a function the compiler can't see into** (so it conservatively assumes the worst).

If none of these happen, the value does not escape.

### 3. "I can't prove it's safe" means "escape"

Escape analysis is **conservative**. When the compiler is unsure — for example, you call a method through an interface and it can't tell which concrete code runs — it assumes the value escapes. Being conservative keeps your program correct; the cost is a few extra heap allocations.

---

## Code Examples

> Go is the easiest language to *see* escape analysis, because the compiler will literally print its decisions. We use it for the examples; the ideas are the same in Java and other languages.

### Example 1 — A value that does NOT escape

```go
package main

func sumLocal() int {
    x := 10        // local int
    y := 20        // local int
    return x + y   // we return the VALUE, not a pointer
}
```

Here `x` and `y` are used only inside `sumLocal`. We return their *sum* (a copy of a number), not a reference to them. Nothing leaks out. The compiler keeps them on the stack. **No heap allocation.**

### Example 2 — A value that DOES escape

```go
package main

type User struct {
    Name string
}

func newUser(name string) *User {
    u := User{Name: name} // local struct
    return &u             // we return a POINTER to it
}
```

We return `&u` — a pointer to a local variable. The caller will use that pointer *after* `newUser` returns, so `u` must outlive the function. It **escapes to the heap**.

> Note: In some languages (C/C++), returning the address of a local is a **bug** (dangling pointer). In Go and Java this is safe — the compiler simply *promotes* the value to the heap so it stays alive. Escape analysis is what makes this safe automatically.

### Example 3 — See the decision yourself

Run Go's compiler with a flag that prints escape decisions:

```bash
go build -gcflags='-m' main.go
```

For the code above you'll see lines like:

```
./main.go:10:2: moved to heap: u
```

`moved to heap: u` is the compiler telling you `u` escaped. For Example 1 you'll see no such message — those values stayed on the stack.

---

## Best Practices

- **Write clear code first; measure later.** Don't contort code to avoid escapes until profiling shows allocations matter.
- **Prefer returning values over pointers for small data.** A small struct returned by value often stays on the stack; returning a pointer frequently forces a heap allocation.
- **Learn to read the compiler's report** (`go build -gcflags=-m`). It's the only reliable source of truth about what escaped.
- **Don't assume — verify.** "This should stay on the stack" is a guess until the tool confirms it.

---

## Edge Cases & Pitfalls

- **Returning a pointer almost always escapes.** If a function returns `&something`, expect a heap allocation.
- **Passing to "print" functions escapes.** In Go, `fmt.Println(x)` often forces `x` to the heap because of how those functions accept arbitrary types. You'll learn why in the middle tier (it's called "boxing").
- **Closures can capture and leak.** If an inner function uses a local variable and that inner function outlives the call, the variable escapes.
- **"Stack allocation" is not guaranteed by the language.** Go and Java *do not promise* a given value stays on the stack. It's an optimization, not a contract. Never write code whose **correctness** depends on stack placement.

---

## Apply it

1. Choose one small, known input for **Escape Analysis**.
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

- What problem does Escape Analysis solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
