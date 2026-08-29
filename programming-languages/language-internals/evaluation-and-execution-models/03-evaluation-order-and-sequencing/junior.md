# Evaluation Order & Sequencing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Evaluation Order & Sequencing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Precedence is *grouping*. Order is *timing*. They are different.

This is the single most important idea on the page, so we lead with it.

Take `a + b * c`. **Precedence** says the `*` binds tighter than `+`, so this parses as `a + (b * c)`. That is a fact about the *shape* of the expression — its parse tree:

```
      +
     / \
    a   *
       / \
      b   c
```

Precedence built that tree. But the tree says **nothing** about *which leaf is visited first*. Does the program read `a` before `b`? Before `c`? That is **evaluation order**, and it is a *separate* decision the language makes (or refuses to make).

> **Mantra:** *Precedence shapes the tree. Order walks the tree.* You can have the same tree walked in many different orders.

If `a`, `b`, and `c` are plain numbers, you cannot tell the difference — `2 + 3 * 4` is `14` whatever the walk order. The difference only shows up when reading `a`, `b`, or `c` *does something* (a side effect) or *returns a different value each time* (an impure function).

### 2. A side effect is what makes order visible.

Consider:

```python
def f():
    print("f")
    return 1

def g():
    print("g")
    return 2

x = f() + g()
```

The *value* of `x` is `3` regardless of order. But the *printed output* depends on whether `f()` or `g()` runs first. In Python (and Java, C#, JavaScript) the answer is guaranteed: `f` then `g`, because these languages evaluate **left to right**. In C, the order is **unspecified** — a conforming compiler may print `g` then `f`.

So: **pure expressions hide evaluation order; side-effecting expressions expose it.** The practical lesson writes itself — *if you don't want order to matter, don't put side effects where order matters.*

### 3. Some languages pin the order. Some refuse.

Languages fall into roughly three buckets:

| Language | Operand / argument order | Notes |
|----------|--------------------------|-------|
| **Java** | Strict **left-to-right**, guaranteed by the spec | Operands, then the operation. |
| **C#** | Strict **left-to-right**, guaranteed | Same model as Java. |
| **JavaScript** | Strict **left-to-right**, guaranteed | Including object/array literals and arguments. |
| **Python** | **Left-to-right**, with a few documented exceptions (assignment) | Mostly predictable. |
| **C** | **Unspecified** for function arguments and most operands | Different compilers differ; not portable. |
| **C++** | **Unspecified** for function arguments (pre-C++17 even more so) | The land of "sequenced-before." |
| **Go** | Mostly left-to-right with specified rules; some function-call ordering subtleties | Specified, but read the spec. |
| **Rust** | Left-to-right, well-defined | No UB here, by design. |

The headline: **C and C++ deliberately leave function-argument order unspecified**, so the compiler can optimize. Everyone else mostly pins it left-to-right. Memorize which bucket your language is in.

### 4. Short-circuit operators *do* guarantee order — everywhere.

There is one place where *every* mainstream language guarantees order: the logical operators `&&` and `||` (and their null-coalescing cousins like `??`).

```c
if (p != NULL && p->value > 0) { ... }
```

`&&` evaluates its **left** operand first. If the left is false, the right is **not evaluated at all** ("short-circuit"). That is why the code above is safe: if `p` is `NULL`, `p->value` is never touched. This is a *guaranteed* left-to-right ordering, and you lean on it constantly. The same holds for `||` (stops on the first true) and `??` (stops on the first non-null).

> **Key insight:** `&&` and `||` are the one corner where C/C++ *do* promise order. Function arguments are not. Don't confuse the two.

### 5. The classic trap: reading and writing the same variable in one expression.

This is where C and C++ stop being merely "unspecified" and become **undefined** — meaning the standard says your program has *no meaning whatsoever*.

```c
int i = 1;
a[i] = i++;     // UB in C/C++ (before C++17 for this specific form)
```

The problem: this expression both **writes** `i` (via `i++`) and **uses** `i` (to index `a`) with no sequencing between them. The compiler is allowed to assume that never happens, so the result is undefined — it might use the old `i`, the new `i`, set fire to your stack, or appear to work for ten years and break after an upgrade. We will return to exactly why in `middle.md`. For now: **never read and modify the same variable in a single expression in C/C++.**

---

## Code Examples

### Example 1 — Precedence vs. order, made visible (Python, guaranteed L-to-R)

```python
def tag(name, value):
    print(f"evaluating {name}")
    return value

result = tag("A", 1) + tag("B", 2) * tag("C", 3)
print("result =", result)
```

Output (Python is left-to-right):

```
evaluating A
evaluating B
evaluating C
result = 7
```

Note two separate facts: the *result* is `1 + (2 * 3) = 7` because of **precedence**, but the *print order* is `A, B, C` because of **left-to-right evaluation order**. Precedence did not make `B*C` print first — order is independent of grouping.

### Example 2 — The same code in C, where order is unspecified

```c
#include <stdio.h>

int tag(const char *name, int value) {
    printf("evaluating %s\n", name);
    return value;
}

int main(void) {
    int result = tag("A", 1) + tag("B", 2) * tag("C", 3);
    printf("result = %d\n", result);
}
```

The *result* is still `7` (precedence is the same everywhere). But the **order in which `A`, `B`, `C` print is unspecified** — GCC and MSVC may differ, and even a flag change can flip it. Never write code whose correctness depends on this print order in C.

### Example 3 — Short-circuit as a safety guarantee (C, Java, JS, Go — all the same)

```c
// Safe: '&&' guarantees the left runs first, and skips the right if left is false.
if (node != NULL && node->next != NULL) {
    use(node->next);
}
```

If you wrote `if (node->next != NULL && node != NULL)` you would dereference `node` *before* the null check — a crash. The ordering of `&&` is what makes the correct version correct. This guarantee holds in every mainstream language.

### Example 4 — The undefined-behavior trap (C/C++)

```c
int i = 0;
int a[3];

a[i] = i++;     // UNDEFINED in C (and pre-C++17 C++): read and write of i, unsequenced
i = i++;        // UNDEFINED: also reads and writes i
int x = i++ + i++;  // UNDEFINED in C: two unsequenced modifications of i
```

A linter (or `-Wsequence-point` / `-Wunsequenced`) will flag these. The fix is always to split the side effect out:

```c
a[i] = i;
i++;
```

### Example 5 — Function arguments: defined in Java, unspecified in C

Java (guaranteed left-to-right):

```java
int i = 0;
System.out.println(consume(i++) + ", " + consume(i++) + ", " + consume(i++));
// Always prints arguments built from i = 0, 1, 2 in that order.
```

C (unspecified — do NOT do this):

```c
int i = 0;
printf("%d %d %d\n", i++, i++, i++);   // order of the three i++ is UNSPECIFIED
// GCC and MSVC famously evaluate arguments in different orders.
```

### Example 6 — Making order *not matter* (the fix, any language)

```python
# Instead of relying on order:
result = next(it), next(it)   # depends on left-to-right; fine in Python, risky habit

# Prefer explicit sequencing:
first  = next(it)
second = next(it)
result = (first, second)
```

The second version says *exactly* what you mean and survives a port to a language with different rules.

### Example 7 — Comma operator (C/C++): evaluate left, throw it away, keep right

```c
int x = (printf("side effect\n"), 42);
// prints "side effect", then x = 42.  The comma *guarantees* left-then-right.
```

The comma operator is one of the few C operators that *does* impose order (left fully evaluated, result discarded, then right). It's rarely needed; don't reach for it.

---

## Coding Patterns

**Pattern: Hoist side effects out of expressions.**

```python
# Instead of:
process(get_next(), get_next())

# Do:
first = get_next()
second = get_next()
process(first, second)
```

**Pattern: Use short-circuit ordering intentionally, and document it.**

```java
// cheap-first: never call expensiveValidate() unless quickValidate() passed.
if (quickValidate(x) && expensiveValidate(x)) { ... }
```

**Pattern: One mutation per statement.**

```c
a[i] = value;
i++;            // not  a[i] = value, i++  crammed together with a read of i
```

**Pattern: Prefer pure expressions in arithmetic.** Keep `i++`, `print()`, and assignments *out* of arithmetic expressions, so order can never change the result.

---

## Best Practices

1. **Never read and write the same variable in one expression** — especially in C/C++, where it is undefined behavior.
2. **Don't rely on the evaluation order of function arguments** unless your language *guarantees* it (and even then, prefer clarity).
3. **Keep at most one side effect per statement.** This makes order irrelevant.
4. **Lean on `&&` / `||` ordering deliberately** — it's the one ordering guarantee you have everywhere — but keep the cheap/safe test on the left.
5. **Know your language's bucket:** left-to-right (Java/C#/JS/Python/Rust) or unspecified (C/C++ args).
6. **Turn on warnings:** `-Wsequence-point`, `-Wunsequenced`, or a linter catches the classic traps automatically.
7. **When in doubt, split it out:** two clear statements beat one clever expression.

---

## Edge Cases & Pitfalls

- **`i = i++;`** — Looks like it should leave `i` incremented (or unchanged). In C/C++ it's **undefined**. In Java it's *defined* and surprisingly leaves `i` **unchanged** (the old value is stored back over the increment). Same syntax, totally different fates.
- **`f() + g()` where both print** — works, but the print order is unspecified in C. Don't depend on it.
- **`arr[i++] = arr[i]`** — reads and writes around the same `i`; UB in C/C++.
- **Logging in a short-circuit** — `if (ok && logAndReturnTrue())` only logs when `ok` is true. Easy to misread.
- **Assuming precedence implies order** — `a() + b() * c()`: the `*` groups tighter, but `a()` may still run first. Grouping ≠ timing.
- **Ternary `cond ? a() : b()`** — only one branch runs; that's an ordering/short-circuit guarantee, not "both evaluated."
- **Increment in array index** — `data[index++] = index;` reads `index` after modifying it; in left-to-right languages the right side is evaluated before the assignment target's index in some, after in others — read your spec, or just split it.

---

## Common Mistakes

| Mistake | Why it's wrong | Fix |
|---------|----------------|-----|
| Believing precedence sets order | Precedence only groups; order is separate | Memorize: tree shape ≠ walk order |
| `printf("%d %d", i++, i++)` in C | Argument order is unspecified | Split into separate statements |
| `a[i] = i++;` in C/C++ | Undefined behavior (read+write of `i`) | `a[i] = ...; i++;` |
| Assuming all languages are left-to-right | C/C++ args are unspecified | Check your language's spec |
| Relying on `&&` to *not* matter | It absolutely matters: it controls whether the right side runs | Put the guard/cheap test on the left |
| Cramming side effects into arithmetic | Makes results order-dependent | Hoist side effects to their own lines |

---

## Apply it

1. Choose one small, known input for **Evaluation Order & Sequencing**.
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

- What problem does Evaluation Order & Sequencing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
