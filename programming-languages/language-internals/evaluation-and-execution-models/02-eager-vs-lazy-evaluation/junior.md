# Eager vs. Lazy Evaluation — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Eager vs. Lazy Evaluation** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Eager Is the Default — and You Never Noticed

When you write ordinary code, *everything runs in order, immediately*:

```python
def greet(name):
    print("computing greeting...")
    return "Hello, " + name

message = greet("Ada")   # "computing greeting..." prints RIGHT HERE
print("about to use it")
print(message)
```

Output:

```text
computing greeting...
about to use it
Hello, Ada
```

The greeting was computed the instant `greet("Ada")` was reached — *before* "about to use it" printed. That is eager evaluation. It is so natural you have never questioned it. The work happens where you wrote it.

### 2. Lazy Means "Build a Recipe, Not a Result"

Lazy evaluation changes the deal. Instead of *running* `greet("Ada")` immediately, the language stores a **recipe** for it — "to get this value, call `greet` with `'Ada'`" — and runs that recipe only the first time someone reads the value.

Most languages don't make whole expressions lazy by default, but they give you tools to *opt in*. In Python, the simplest opt-in is wrapping the work in a function and only calling it later:

```python
def lazy_greeting():
    print("computing greeting...")
    return "Hello, Ada"

# Nothing prints yet — we only have a recipe (the function).
recipe = lazy_greeting
print("about to use it")
message = recipe()   # NOW "computing greeting..." prints
```

Output:

```text
about to use it
computing greeting...
```

Notice the order flipped. With laziness, "about to use it" prints *first*, because the greeting work was deferred until we actually called `recipe()`. The function `lazy_greeting` (without parentheses) is a primitive **thunk**: a parked computation.

### 3. You Already Use Laziness: Short-Circuit Operators

Here is the most important point on this whole page, because it makes laziness concrete with code you have written a hundred times.

```python
def is_admin(user):
    print("checking admin (expensive!)")
    return user.role == "admin"

# If user is None, we must NOT call is_admin — it would crash.
if user is not None and is_admin(user):
    grant_access()
```

The `and` here is **lazy in its right operand**. If `user is not None` is `False`, Python never evaluates `is_admin(user)`. It can't — and it doesn't. This is **short-circuit evaluation**, and it is laziness in miniature. The same holds for:

- `a and b` — `b` runs only if `a` is truthy.
- `a or b` — `b` runs only if `a` is falsy.
- `cond ? x : y` (ternary) — only the chosen branch runs.

These operators are **non-strict** in their second/branch operands. Every mainstream language has them, which means *every language already ships with a little bit of laziness built in.* Lazy evaluation as a topic is just: "what if we could do that on purpose, everywhere, for whole data structures?"

### 4. The Thunk: a Parked Computation

A **thunk** is the unit of laziness. Picture an envelope. On the outside it says "I am a `string`." Inside is not a string — it is *instructions for making the string*. The first time someone opens the envelope (**forces** the thunk), the instructions run, the string is produced, and (in good implementations) the string is written back into the envelope so the next reader gets it for free. We will explore that "write it back" optimization — called **memoization** — in later levels. For now, hold this picture: a thunk is an IOU for a value.

### 5. Generators: Your First Real Lazy Tool

In Python, a function with `yield` becomes a **generator** — a lazy sequence that produces one value at a time, *only when pulled*:

```python
def naturals():
    n = 0
    while True:        # infinite loop — but this is FINE
        yield n
        n += 1

gen = naturals()       # nothing has run yet
print(next(gen))       # 0   (runs until the first yield, then pauses)
print(next(gen))       # 1   (resumes, runs to the next yield)
print(next(gen))       # 2
```

The `while True` loop would hang forever if it were eager. But a generator only advances when you call `next()`. It computes one value, pauses, and waits. This is how laziness lets you describe **infinite** data and still have a program that terminates — you simply never ask for all of it.

---

## Code Examples

### Eager: list comprehension computes everything immediately

```python
def square(x):
    print(f"squaring {x}")
    return x * x

# Square brackets = EAGER. All four squares compute right now.
squares = [square(x) for x in range(4)]
print("list is built")
print(squares[0])
```

Output:

```text
squaring 0
squaring 1
squaring 2
squaring 3
list is built
0
```

Every element was computed before "list is built" printed — even `squares[1]`, `[2]`, `[3]`, which we never used.

### Lazy: generator expression computes on demand

```python
def square(x):
    print(f"squaring {x}")
    return x * x

# Round brackets = LAZY generator. Nothing computes yet.
squares = (square(x) for x in range(4))
print("generator created")
print(next(squares))   # only NOW does 'squaring 0' run
```

Output:

```text
generator created
squaring 0
0
```

Same code shape — one bracket difference — and the behavior is completely different. We computed exactly one square: the one we asked for.

### Laziness avoids wasted work: "first match" in a big search

```python
def expensive_check(x):
    print(f"checking {x}")
    return x % 7 == 0 and x > 50

# Eager: builds the ENTIRE list of matches, then takes the first.
def find_first_eager(nums):
    matches = [x for x in nums if expensive_check(x)]  # checks ALL nums
    return matches[0]

# Lazy: stops at the first match. Checks far fewer.
def find_first_lazy(nums):
    return next(x for x in nums if expensive_check(x))  # stops early

print(find_first_lazy(range(1000)))
```

The lazy version stops the instant it finds `56` (the first multiple of 7 over 50). The eager version checks all 1000 numbers first. Same answer; the lazy one did a fraction of the work.

### Short-circuit operators (the laziness you already use)

```python
data = None

# Without short-circuit, this would crash on data.value (None has no .value).
# 'and' is lazy in its right operand, so data.value is never touched.
if data is not None and data.value > 10:
    print("big")
else:
    print("safe — no crash")   # prints this
```

### Generator exhaustion (the #1 beginner trap)

```python
gen = (x * x for x in range(3))

print(list(gen))   # [0, 1, 4]  — consumes the whole generator
print(list(gen))   # []         — it's EXHAUSTED, not refilled!
```

A generator is a *one-shot* stream. Once consumed, it is empty forever. If you need to iterate twice, either store the results in a list, or create a fresh generator each time.

### `itertools`: a toolbox of lazy building blocks

```python
import itertools

# itertools.count(0) is an INFINITE lazy sequence: 0, 1, 2, 3, ...
evens = (n for n in itertools.count(0) if n % 2 == 0)

# islice pulls just the first 5 — laziness lets us slice an infinite stream.
print(list(itertools.islice(evens, 5)))   # [0, 2, 4, 6, 8]
```

---

## Coding Patterns

**Pattern: lazy generate, eager consume.** Build a lazy pipeline, then collect exactly what you need at the end.

```python
import itertools

squares = (n * n for n in itertools.count(1))    # lazy, infinite
first_ten = list(itertools.islice(squares, 10))  # eager snapshot of 10
```

**Pattern: defer the work, pass the recipe.** Hand a *function* (a thunk) instead of a *value*, so the caller decides when (or whether) to run it.

```python
def log_if_enabled(level, make_message):
    if level >= CURRENT_LEVEL:
        print(make_message())   # only build the (expensive) string if we'll log it

# The lambda is a thunk — the f-string isn't built unless logging is enabled.
log_if_enabled(DEBUG, lambda: f"state dump: {expensive_dump()}")
```

**Pattern: convert to a list when you need to iterate twice.**

```python
gen = (x * x for x in range(5))
results = list(gen)          # materialize once
print(sum(results))          # iterate
print(max(results))          # iterate again — works because it's a list
```

---

## Best Practices

- **Know which bracket you wrote.** `[...]` is an eager list; `(...)` is a lazy generator. This one character changes everything.
- **Materialize before iterating twice.** If you'll loop over a generator more than once, `list(gen)` it first — or it'll be empty the second time.
- **Don't hide side effects inside lazy code.** A `print` or a DB write inside a generator runs at consumption time, which is rarely where you expect. Keep generators pure (no side effects) when you can.
- **Use `itertools` instead of hand-rolling.** `islice`, `takewhile`, `chain`, `count`, `cycle`, `repeat` are battle-tested lazy tools.
- **Force the result at the boundary.** Inside a function, laziness is fine; before you *return* to a caller who expects data, `list(...)` it so they get values, not a one-shot stream.
- **Name lazy things clearly.** `user_stream`, `lines_gen`, `lazy_results` — signal that the value is a stream, not a list.

---

## Edge Cases & Pitfalls

**Pitfall 1: "My code never ran."** You built a generator (or a LINQ query, or a JS iterator) and nothing happened. There was no bug in the logic — you simply never *consumed* it. Laziness does nothing until forced. Fix: consume it (`list()`, a `for` loop, `next()`).

**Pitfall 2: Generator exhaustion.** After consuming a generator once, it is empty. `list(gen)` then `list(gen)` again gives `[]` the second time. Fix: materialize to a list, or rebuild the generator.

**Pitfall 3: Late binding of variables.** A subtle one — a lazy value can capture a variable that *changes* before the value is forced:

```python
funcs = []
for i in range(3):
    funcs.append(lambda: i)      # each lambda captures the SAME i
print([f() for f in funcs])      # [2, 2, 2] — not [0, 1, 2]!
```

By the time the lambdas run (forced lazily), the loop has finished and `i` is `2`. This is the classic "modified closure" trap, and it bites in many languages. Fix: bind the value eagerly, e.g. `lambda i=i: i`.

**Pitfall 4: Infinite loop instead of infinite sequence.** A generator with `while True` is safe *only if* every consumer is bounded. `list(naturals())` will hang forever — you asked for *all* of an infinite stream. Always pair an infinite generator with something that stops (`islice`, `takewhile`, a `break`).

**Pitfall 5: Surprising side-effect timing.** Print statements inside generators fire when consumed, interleaved with the consumer's code, not at definition. This makes logs confusing. Keep generators free of side effects.

---

## Apply it

1. Choose one small, known input for **Eager vs. Lazy Evaluation**.
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

- What problem does Eager vs. Lazy Evaluation solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
