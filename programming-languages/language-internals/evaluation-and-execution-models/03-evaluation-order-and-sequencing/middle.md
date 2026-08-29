# Evaluation Order & Sequencing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Evaluation Order & Sequencing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The sequence-point rule (C89 / C99 / C11)

The classic C rule, almost verbatim:

> Between the previous and next sequence point, an object shall have its stored value modified **at most once** by the evaluation of an expression. Furthermore, the prior value shall be read **only to determine the value to be stored**.

Two violations make a program undefined:

- **Modifying a scalar twice** between sequence points: `i = i++;`, `i++ + i++`, `++i + ++i`.
- **Reading a scalar for any purpose other than computing the value to store**, while also writing it: `a[i] = i++` (the read of `i` to index `a` is *not* "to determine the value stored into `i`").

Where are the sequence points in C? The important ones:

- At the **end of a full expression** (the `;` of a statement, the controlling expression of `if`/`while`/`for`, each clause of `for(;;)`).
- After the **left operand of `&&`, `||`, `?:`, and the comma operator `,`**.
- After **evaluating all function arguments and the function designator, but before the call** (entry to a function is a sequence point).
- At the `?` of the ternary and between the `?:` selected branch.

Everything *not* separated by a sequence point is, in old C terms, "indeterminately ordered" with no guarantee of single-modification — hence the traps.

### 2. The C++11 model: sequenced-before, unsequenced, indeterminately-sequenced

C++11 retired "sequence points" (they were too coarse to describe threads and finer optimizations) and replaced them with a *relation between evaluations*. For any two evaluations A and B, exactly one of:

- **A is sequenced-before B** — A fully completes (value computation *and* side effects) before B begins. Total order. Example: the left operand of `&&` is sequenced-before the right.
- **A and B are unsequenced** — no ordering at all, and they may even interleave. If both access the same scalar and at least one is a write (and they're not atomic), the behavior is **undefined**. Example (pre-C++17): the two `i++` in `f(i++, i++)`.
- **A and B are indeterminately-sequenced** — one is sequenced-before the other, but *which* is unspecified, and they do **not** interleave. Example: two full function-argument evaluations — each runs to completion, but in an unspecified order. This is *not* UB by itself (no overlap), it's merely *unspecified*.

The crucial split: **unsequenced** (overlap allowed → UB on conflicting access) vs **indeterminately-sequenced** (no overlap, just unknown order → merely unspecified). Function *arguments* are indeterminately-sequenced relative to each other; sub-expressions *within* an argument can be unsequenced.

### 3. Why `a[i] = i++` is undefined — traced precisely

```c
a[i] = i++;
```

There are two side effects / reads on `i` in one full expression with no sequence point (C) / sequenced-before edge (C++) between them:

- **Read of `i`** to compute the address `&a[i]` (left side).
- **Write of `i`** as part of `i++` (right side).

In the C model: between the surrounding sequence points, `i` is read *not* "to determine the value to be stored into `i`" (it's read to index `a`) while `i` is also modified → **UB**. In the C++ pre-17 model: the value computation of `a[i]`'s index and the side effect of `i++` are **unsequenced**, and they conflict on the scalar `i` → **UB**. Same verdict, two derivations.

> **The fix is mechanical:** introduce sequencing. `a[i] = i; i++;` puts a sequence point (the `;`) between the read and the write.

### 4. Assignment ordering and what C++17 changed

C++17 tightened several previously-unspecified or undefined cases. The most important:

- In an assignment `E1 = E2`, C++17 now sequences **E2 before E1** (the right-hand side is evaluated before the left-hand side's value computation, and the assignment's side effect is sequenced after both). Before C++17 the order of `E1` and `E2` was unsequenced — so `a[i] = i++` was UB. **In C++17, `a[i] = i++` becomes well-defined** (it uses the *old* `i` to index). C remains UB. This is a genuine, testable difference between C, C++14, and C++17.
- C++17 also made the operands of `<<`, `>>`, `[]`, `.`, `->*`, and several others *sequenced* left-to-right, fixing the infamous `std::cout << f() << g()` argument-order surprise.
- **Function arguments remain indeterminately-sequenced even in C++17** — argument order is *still* unspecified. C++17 did not fix `printf("%d %d", i++, i++)` argument order; that's still unspecified (and the conflicting writes are still UB because the two `i++` are unsequenced relative to each other).

So the era matters. Always know which standard you compile against.

### 5. Function-argument order is *unspecified*, and compilers really do differ

The standard never promised an order for evaluating function arguments. Historically:

- **GCC and Clang on x86-64** typically evaluate arguments **right-to-left** (matching the System V calling convention's push order, conceptually).
- **MSVC** has also commonly evaluated **right-to-left** for cdecl, but the standard does not require *any* order and you must not depend on it.
- Older toolchains and different ABIs flip this. The lesson is identical regardless of the exact direction: **never write code whose meaning depends on argument order.**

This is *unspecified* (the compiler picks one of several legal orders), which is much milder than the *undefined* status of `f(i++, i++)` — there, on top of the unspecified order, the two writes to `i` are unsequenced and conflict, pushing it from "unspecified result" all the way to "no defined meaning."

### 6. The guaranteed sequence points you rely on

These always impose order, in C and C++:

| Construct | Guarantee |
|-----------|-----------|
| `a && b` | `a` sequenced-before `b`; `b` skipped if `a` is false. |
| `a \|\| b` | `a` sequenced-before `b`; `b` skipped if `a` is true. |
| `c ? a : b` | `c` sequenced-before the selected branch; only one branch runs. |
| `a , b` (comma op) | `a` sequenced-before `b`; value is `b`. |
| End of full expression `;` | All side effects complete here. |
| Function entry | All arguments evaluated (in some order) before the body runs. |

These are your tools for *forcing* order when you need it.

---

## Code Examples

### Example 1 — Classifying expressions by the rule

```c
int i = 0, a[5];

i = i + 1;        // fine: read of i is to compute value stored into i
i = i++;          // UB in C/C++14: i modified twice (= and ++) with no sequencing
a[i] = i++;       // UB in C/C++14 (defined in C++17): read of i (index) conflicts with write
i++ + i++;        // UB: two unsequenced modifications of i
f(i++, i++);      // UB: arguments' i++ are unsequenced relative to each other
i++ , i++;        // OK: the comma operator sequences left-before-right
```

### Example 2 — The comma operator imposes order

```c
int x = (a = 5, a + 1);   // a = 5 sequenced-before a+1; x becomes 6. Defined.
```

Contrast with the *comma separator* in a function call — `f(a, b)` — which is **not** the comma operator and imposes **no** order between `a` and `b`.

### Example 3 — Short-circuit forces sequencing

```c
// p is read for the null check, sequenced-before reading p->len. Safe.
if (p != NULL && p->len > 0) { ... }

// Force evaluation order with comma when you genuinely need a side effect first:
int ok = (init(), ready());   // init() runs, result discarded, then ready() decides.
```

### Example 4 — Demonstrating unspecified argument order

```c
#include <stdio.h>
int log_and_return(int id) { printf("arg %d\n", id); return id; }

int main(void) {
    // The two arg evaluations are indeterminately-sequenced: order unspecified.
    printf("sum=%d\n", log_and_return(1) + log_and_return(2));
    // GCC/Clang on x86-64 often print "arg 2" then "arg 1" (right-to-left).
}
```

The *sum* is always `3`; the print order is implementation-defined. Don't ship code that depends on it.

### Example 5 — `i = i++` differs by language

```c
// C / C++14: UNDEFINED. Anything may happen.
int i = 0; i = i++;
```

```java
// Java: DEFINED. i ends up 0.
// Evaluation: read i (0) for the assignment's RHS value; i++ writes 1 to i;
// then the assignment stores the saved RHS (0) back into i, overwriting the 1.
int i = 0; i = i++;   // i == 0 afterward
```

Same characters, different worlds: C says "no meaning," Java says "definitely 0." This is the cleanest illustration of why pinning order (Java) versus leaving it loose (C) is a real semantic decision.

### Example 6 — Member-initialization order (C++ teaser)

```cpp
struct S {
    int a;
    int b;
    // Initializer list says b first, then a — but members initialize in
    // DECLARATION order (a then b), not init-list order. If a depends on b, bug.
    S(int x) : b(x), a(b + 1) {}   // a is initialized FIRST (declaration order), reading uninitialized b!
};
```

This declaration-order-not-init-list-order rule is a classic C++ trap; `senior.md` covers it and static-init order in full.

---

## Coding Patterns

**Pattern: Force order with a sequence point when you need it.**

```c
// Need a() before b()? Don't trust argument order; sequence explicitly:
int ra = a();
int rb = b();
use(ra, rb);
```

**Pattern: Beware multiple-expansion macros.**

```c
#define MAX(x, y) ((x) > (y) ? (x) : (y))
int m = MAX(i++, j);   // i++ expands twice on one path -> potential double modification
```

Prefer inline functions or `typeof`-based statement-expression macros that evaluate arguments once.

**Pattern: Split RHS/LHS when indices mutate.**

```c
int idx = i;
i++;
a[idx] = idx;   // unambiguous in every standard
```

---

## Best Practices

1. **State the standard before you state the verdict.** "UB in C++14, defined in C++17" is the correct shape of an answer.
2. **Apply the sequence-point rule as a checklist** when reviewing C: at most one modification per scalar per full expression, reads only to determine the stored value.
3. **Treat argument order as unspecified, always**, regardless of what your current compiler does.
4. **Never expand a side-effecting argument multiple times in a macro.**
5. **Reach for `&&`, `||`, `?:`, and the comma operator** when you genuinely need sequencing inside an expression — they're the standard-blessed ordering tools.
6. **Enable `-Wsequence-point` (GCC) / `-Wunsequenced` (Clang)** and treat them as errors.

---

## Edge Cases & Pitfalls

- **`f(i++, i++)`** — unsequenced writes to `i` → UB in C and C++ (even C++17 does not save this).
- **`cout << i++ << i++`** — before C++17, indeterminately-sequenced and the writes conflict → UB; C++17 sequences the `<<` operands left-to-right, removing the *ordering* surprise, but two unsequenced modifications of `i` within them are *still* a problem — confirm against the exact standard.
- **The comma *separator* vs comma *operator*** — `f(a, b)` separator imposes no order; `(a, b)` operator imposes left-then-right. Same character, opposite guarantees.
- **Function-call entry is a sequence point** — so `g(i++) + h(i++)` does *not* race inside each call, but the two calls are indeterminately-sequenced and the two `i++` conflict → still UB.
- **`volatile` does not buy you ordering between two writes in one expression** — it controls when accesses happen relative to the abstract machine, not whether `i = i++` is defined. (More in `professional.md`.)
- **Macros that re-expand arguments** silently turn `SQ(i++)` into UB.

---

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "C++17 fixed `f(i++, i++)`" | No. Function argument order is *still* unspecified and the conflicting writes are *still* UB. C++17 only sequenced *assignment* RHS-before-LHS and some operators. |
| "Unspecified means undefined" | No. Unspecified = legal-but-unknown choice (arg order). Undefined = no meaning. |
| "Sequence points and sequenced-before are the same" | They model the same idea but sequenced-before is finer and thread-aware. |
| "The comma separator orders arguments" | It does not; only the comma *operator* does. |
| "Member init follows the initializer list" | It follows *declaration* order. |

---

## Apply it

1. Find a real component where **Evaluation Order & Sequencing** affects an interface or dependency.
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

- Which boundary is most affected by Evaluation Order & Sequencing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
