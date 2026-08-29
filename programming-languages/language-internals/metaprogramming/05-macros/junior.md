# Macros — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Macros** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A Macro Is Find-and-Replace, Run by the Compiler

Start with the simplest macro:

```c
#define PI 3.14159

double area = PI * r * r;
```

The preprocessor sees `PI` and replaces it — literally, like a text editor's find-and-replace — with `3.14159`. After the preprocessor runs, the compiler reads:

```c
double area = 3.14159 * r * r;
```

The compiler never knew `PI` existed. There is no variable named `PI` in the compiled program, no memory for it, no type. This is the entire idea: **the macro disappears, leaving only its expansion.**

Object-like macros like this are mostly harmless. The trouble starts when macros take arguments.

### 2. Function-Like Macros Paste Tokens, They Do Not Call

```c
#define SQUARE(x) x * x

int a = SQUARE(5);   // becomes  5 * 5  → 25, fine
```

This *looks* like a function call, but it is not. `SQUARE(5)` is replaced by `5 * 5`. No function exists. The argument `5` is pasted in wherever `x` appears in the body. So far so good — but watch what happens when the argument is not a simple number.

### 3. The Missing-Parentheses Bug

```c
#define SQUARE(x) x * x

int b = SQUARE(2 + 3);
```

You expect `25` (because `2 + 3` is `5`, and `5²` is `25`). You get **11**. Why? Because the macro pastes the *tokens* `2 + 3` in place of `x`, with no parentheses:

```c
int b = 2 + 3 * 2 + 3;   // = 2 + 6 + 3 = 11
```

The preprocessor does not evaluate `2 + 3` first — it does not evaluate *anything*. It copies the tokens, and now C's normal precedence rules apply to a garbled expression. The fix is to **parenthesize every parameter and the whole body**:

```c
#define SQUARE(x) ((x) * (x))

int b = SQUARE(2 + 3);   // becomes  ((2 + 3) * (2 + 3))  → 25, correct
```

Rule of thumb every C programmer learns: **wrap each argument in parentheses, and wrap the entire macro body in parentheses.** Forgetting either causes a precedence bug that the compiler will not warn you about.

### 4. The Double-Evaluation Bug

Parentheses fix precedence, but they do **not** fix this:

```c
#define SQUARE(x) ((x) * (x))

int i = 5;
int c = SQUARE(i++);
```

The macro expands to:

```c
int c = ((i++) * (i++));
```

The argument `i++` was pasted **twice**, so `i` is incremented *twice*, and the multiplication uses two different values. The result is unpredictable (and `i` ends at `7`, not `6`). A real function would have evaluated `i++` **once** before the call. A macro cannot, because it does not evaluate — it duplicates text.

This is **double evaluation**, and it is the single most dangerous macro bug, because the code looks completely innocent. The classic real-world example is:

```c
#define MAX(a, b) ((a) > (b) ? (a) : (b))

int m = MAX(i++, j++);   // both i++ and j++ may run twice — chaos
```

There is no general fix in C; you simply must never pass expressions with side effects to a function-like macro. (Languages with *hygienic, syntactic* macros solve this — see `senior.md`.)

### 5. The Multi-Statement Bug and `do { } while(0)`

Suppose a macro needs two statements:

```c
#define LOG_AND_RUN(x) printf("running\n"); run(x);

if (ready)
    LOG_AND_RUN(task);
```

Expands to:

```c
if (ready)
    printf("running\n"); run(task);
```

Only the `printf` is inside the `if`! `run(task)` runs **unconditionally**, because C attaches only the first statement to a braceless `if`. The standard idiom that fixes this is to wrap the body in a `do { ... } while(0)`:

```c
#define LOG_AND_RUN(x) do { printf("running\n"); run(x); } while(0)

if (ready)
    LOG_AND_RUN(task);     // both statements now inside the if
```

`do { } while(0)` is a single statement that runs its body exactly once, **and** it requires a trailing semicolon, so the macro call reads like a normal statement. This idiom looks bizarre the first time you see it; it exists entirely to make multi-statement macros safe inside `if`/`else`.

### 6. The Preprocessor Does Not Understand Scope

```c
#define INCREMENT(x) tmp = x; x = x + 1

int tmp = 0;     // the caller happens to have a 'tmp' too
int value = 10;
INCREMENT(value);
```

The macro silently clobbers the caller's `tmp`. The preprocessor has no idea that `tmp` inside the macro and `tmp` in the caller are "supposed" to be different — to a text substituter, a name is just a name. This is a **capture** bug. Hygienic macro systems (Scheme, Rust) make this *impossible*; C makes it a daily hazard, and the only defence is ugly conventions like naming internal variables `__macro_tmp_xyz`.

---

## Code Examples

### Seeing the expansion with `gcc -E`

This is the single most useful debugging tool for macros. It runs *only* the preprocessor:

```c
// file: demo.c
#define SQUARE(x) x * x
int main(void) {
    int b = SQUARE(2 + 3);
    return b;
}
```

```bash
$ gcc -E demo.c
# ... lots of header noise ...
int main(void) {
    int b = 2 + 3 * 2 + 3;   // <-- the bug is now visible
    return b;
}
```

The `-E` flag stops after preprocessing and prints the result. When a macro confuses you, *always* look at `-E` output. (Clang: `clang -E demo.c`. C++: `g++ -E`.)

### The full "safe macro" checklist applied

```c
// BAD: precedence bug + multi-statement bug + capture bug all at once
#define BAD_SWAP(a, b) tmp = a; a = b; b = tmp

// GOOD: parenthesized, single-statement, and we accept its limits
#define SWAP(type, a, b) do {        \
        type swap_tmp_ = (a);        \
        (a) = (b);                   \
        (b) = swap_tmp_;             \
    } while (0)

int x = 1, y = 2;
SWAP(int, x, y);   // x == 2, y == 1; even an outer 'tmp' is untouched
```

Notes on the "good" version:
- The body is wrapped in `do { } while(0)` so it is one statement.
- Backslashes (`\`) continue the macro across lines — a macro is logically one line.
- The internal variable is named `swap_tmp_` to reduce collision risk (still not *guaranteed* safe — true hygiene needs a different language; see `senior.md`).
- Each parameter use is parenthesized.

### Object-like macros for configuration

```c
#define MAX_CONNECTIONS 1024
#define ENABLE_LOGGING  1

char pool[MAX_CONNECTIONS];

#if ENABLE_LOGGING
    log_init();          // compiled in only when ENABLE_LOGGING is non-zero
#endif
```

`#if` / `#ifdef` / `#endif` are **conditional compilation** — the preprocessor deletes whole blocks of code before the compiler sees them. This is how one source file targets Linux, Windows, and macOS, or how "debug" and "release" builds differ.

### A macro vs. the function that should have replaced it

```c
#define SQUARE_MACRO(x) ((x) * (x))     // pastes text, risks double-eval

static inline int square_fn(int x) {     // evaluates the argument ONCE
    return x * x;
}

int main(void) {
    int i = 5;
    int a = SQUARE_MACRO(i++);   // i++ runs TWICE; a is garbage
    i = 5;
    int b = square_fn(i++);      // i++ runs ONCE; b == 25, i == 6
    return a + b;
}
```

Modern C and C++ have `static inline` functions that the compiler can inline for the same speed as a macro, *without* the textual hazards. **If a macro could be a function, make it a function.** This is one of the most important practical lessons here.

---

## Coding Patterns

**Pattern: parenthesize everything.**

```c
#define ADD(a, b) ((a) + (b))   // not  a + b
```

**Pattern: `do { } while(0)` for multi-statement bodies.**

```c
#define CHECK(cond, msg) do { if (!(cond)) fail(msg); } while (0)
```

**Pattern: include guard (every header you write).**

```c
#ifndef MYLIB_WIDGET_H
#define MYLIB_WIDGET_H
/* declarations */
#endif /* MYLIB_WIDGET_H */
```

**Pattern: stringize for debugging.**

```c
#define SHOW(expr) printf(#expr " = %d\n", (expr))
SHOW(x + y);   // prints:  x + y = 7
```

`#expr` turns the *tokens* `x + y` into the string literal `"x + y"`. This only a macro can do — a function never sees the source text of its argument.

---

## Best Practices

- **Prefer functions, `const`, `enum`, and (C++) `constexpr`.** Reach for a macro only when no language feature can do the job (conditional compilation, stringizing, token pasting).
- **Parenthesize each parameter and the whole body.** Always. No exceptions.
- **Wrap multi-statement bodies in `do { } while(0)`.**
- **NAME macros in `UPPER_SNAKE_CASE`** by long-standing convention, so readers know "this is a macro; arguments may be evaluated oddly."
- **Never pass side-effecting expressions** (`i++`, function calls with effects) to a function-like macro.
- **When confused, run `gcc -E`** and read the real expansion.
- **Keep macros short.** A long macro is a debugging nightmare; extract logic into a real function the macro merely calls.

---

## Edge Cases & Pitfalls

- **`#define SQUARE(x) x*x`** → `SQUARE(a+b)` becomes `a+b*a+b`. Missing parentheses.
- **`SQUARE(i++)`** → `i` incremented twice. Double evaluation.
- **`#define MAX(a,b) a>b?a:b`** used as `MAX(x,y)*2` → expands to `x>y?x:y*2`, which means `x > y ? x : (y*2)`. Missing outer parentheses turn this into a different operator-precedence expression entirely.
- **Trailing semicolons.** `#define F() do {...} while(0)` is called as `F();` — the macro body should *not* end in a semicolon, or you get a double `;;` that breaks `if/else`.
- **Macro argument with a comma.** `SQUARE(a, b)` confuses the preprocessor: `MyMacro(std::pair<int, int>{})` — the comma inside `<...>` is read as an argument separator. Wrap such arguments or use variadic macros.
- **Recursive macros do not recurse.** `#define A A + 1` does *not* loop forever; the preprocessor refuses to expand a macro inside its own expansion. The result is literally `A + 1` (with `A` left un-expanded). Beginners expect infinite expansion; it does not happen.
- **A macro shadowing a real name.** `#define max somethingElse` will break `std::max` and any variable named `max` in scope, because the preprocessor replaces *every* occurrence of the token. This is why `<windows.h>` defining `min`/`max` macros is infamous.

---

## Common Mistakes

1. **Treating a macro like a function.** It does not evaluate arguments; it pastes them. The mental switch from "value" to "text" is the whole battle.
2. **Forgetting parentheses** and blaming the compiler for a "math bug."
3. **Passing `i++` or any side effect** into a macro.
4. **Multi-statement macros without `do { } while(0)`** silently dropping statements out of an `if`.
5. **Using a macro where a `const` or `inline` function would be safer and clearer.**
6. **Not looking at `gcc -E`** when a macro misbehaves, and instead guessing for an hour.

---

## Apply it

1. Choose one small, known input for **Macros**.
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

- What problem does Macros solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
