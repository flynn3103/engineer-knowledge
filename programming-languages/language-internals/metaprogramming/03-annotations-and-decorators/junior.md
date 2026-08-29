# Annotations & Decorators — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Annotations & Decorators** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The `@` Is Just Syntax — The Meaning Is Per-Language

The `@Name` placed above a declaration is called the *decoration* or *annotation site*. The same shape compiles to different things:

- In **Java/C#**, it records metadata in the type system. No code runs.
- In **Python/TypeScript**, it (usually) runs a function and may replace the declared thing.

Whenever you see `@Something`, your first job is to ask **"which language family, and therefore which meaning?"**

### 2. A Java Annotation Does Nothing By Itself

This is the headline. Consider:

```java
@Override
public String toString() { return "hi"; }
```

`@Override` does not change `toString`. It does not run code. It is a *fact recorded on the method*: "the author claims this overrides a superclass method." That fact is **read by the compiler**, which then checks: *does a method with this signature actually exist in a parent class?* If not, the compiler errors. The *value* of `@Override` comes entirely from the compiler choosing to read it. Remove the compiler's check and `@Override` becomes a no-op comment.

The same is true of every annotation:

- `@Deprecated` — the compiler reads it and emits a warning when you use the thing.
- `@Test` (JUnit) — the test runner reads it at runtime and decides "this method is a test, run it."
- `@Entity` (JPA/Hibernate) — the ORM reads it and decides "this class maps to a database table."

**No reader, no effect.** An annotation is a question waiting for someone to ask it.

### 3. Who Reads Annotations, and When — The Two Paths

There are exactly two times an annotation can be read, and this split is the backbone of the entire topic:

- **Compile time:** an **annotation processor** runs *during the build*, sees your annotations, and reacts — usually by generating new source code or raising compile errors. Lombok, Dagger, and many code generators work this way. Nothing is "magic" at runtime; the code was simply written for you at build time.
- **Runtime:** a framework uses **reflection** to scan your loaded classes and react to annotations *while the program runs*. Spring scanning for `@Component`, JUnit scanning for `@Test`, Jackson reading `@JsonProperty` during serialization — all runtime.

Which path applies is controlled by the annotation's **retention** (covered properly in `middle.md`): an annotation can be discarded after compilation, kept in the class file, or kept available for runtime reflection.

### 4. A Python Decorator *Is* Code That Runs

Now the other family. In Python:

```python
@timer
def slow():
    ...
```

is *exactly equivalent* to:

```python
def slow():
    ...
slow = timer(slow)
```

Read that twice. The `@timer` line literally means "after defining `slow`, call `timer(slow)` and bind the result back to the name `slow`." So `timer` is a function that takes a function and returns something (usually a new wrapped function). After this runs, the name `slow` no longer points at your original function — it points at whatever `timer` returned.

That is why decorators *do* things: they are live code, executed at definition time, that can replace your function with a wrapper.

### 5. The Shape of a Python Decorator

A decorator that wraps a function to add behavior looks like this:

```python
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)   # call the original
        print(f"{func.__name__} took {time.time() - start:.3f}s")
        return result
    return wrapper                       # return the replacement
```

- `timer` receives the original function as `func`.
- It defines `wrapper`, which runs *extra* code (timing) around a call to `func`.
- It **returns** `wrapper`, which now stands in for the original.

`*args, **kwargs` is the idiom that lets `wrapper` accept *any* arguments and forward them, so the decorator works on any function.

### 6. TypeScript / Angular Decorators Sit In Between

TypeScript decorators (`@Component`, `@Injectable`, `@Input`) are runnable functions like Python's, but they are mostly used the *Java way*: to attach metadata that Angular or NestJS reads later. So `@Component({...})` runs a function at class-definition time, and that function's job is usually to *store metadata* about the class for the framework to find. It's a decorator (live code) being used to do an annotation's job (record metadata). This blend is why TypeScript is the bridge between the two worlds — and why it confuses people most.

### 7. C# Attributes Are Java Annotations With Different Syntax

C# `[Serializable]`, `[Obsolete]`, `[Required]` use square brackets instead of `@`, but they are the *same concept* as Java annotations: pure declarative metadata, inert until something reads them via reflection. If you understand Java annotations, you understand C# attributes — the only change is the bracket.

### 8. The One-Question Test

For any `@Something` you encounter, ask: **"If I delete the framework/processor/compiler that looks for this, does the code below still behave the same?"**

- **Yes** → it was an annotation (inert metadata). The effect lived in the *reader*.
- **No** → it was a decorator (active code). The effect lived in the `@` itself.

---

## Code Examples

### Java — `@Override`: the inert annotation that the compiler reads

```java
class Animal {
    public String speak() { return "..."; }
}

class Dog extends Animal {
    @Override                       // metadata: "I override a parent method"
    public String speak() { return "Woof"; }
}
```

If you misspell it as `spek()`, the `@Override` causes a **compile error** — because the compiler *read* the annotation and checked the claim. Delete `@Override` and the misspelling silently compiles into a brand-new unrelated method (a classic bug `@Override` exists to prevent). The annotation itself runs no code; the *compiler's check* is the value.

### Java — `@Deprecated`: read by the compiler to warn callers

```java
class OldApi {
    @Deprecated
    public void legacy() { /* ... */ }
}

// Elsewhere:
new OldApi().legacy();   // compiler emits: "legacy() is deprecated"
```

Again: `@Deprecated` performs nothing. The compiler reads it and warns. Pure sticky note.

### Java — a custom annotation that does *nothing*

```java
@interface Cool { }          // define an annotation

class Widget {
    @Cool
    public void doThing() { }   // marked... but nobody reads @Cool
}
```

This compiles fine and has **zero effect** anywhere. `@Cool` is metadata that no reader looks for. This is the purest demonstration of "an annotation does nothing by itself." To make it matter you'd need a processor (compile time) or reflection code (runtime) that searches for `@Cool` — covered in `middle.md`.

### Python — a decorator that *does* run

```python
import time
import functools

def timer(func):
    @functools.wraps(func)            # preserve func's name/docstring
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.perf_counter() - start:.4f}s")
        return result
    return wrapper

@timer
def add(a, b):
    return a + b

print(add(2, 3))   # prints the timing line, then 5
```

The moment Python reaches `@timer`, it runs `add = timer(add)`. Now calling `add(2, 3)` actually calls `wrapper`, which times and forwards to the real `add`. The decorator *did* something — unlike a Java annotation.

### Python — built-in decorators you already use

```python
class Circle:
    def __init__(self, r):
        self._r = r

    @property                  # makes radius() callable as an attribute
    def radius(self):
        return self._r

    @staticmethod              # a method that doesn't take self
    def unit():
        return Circle(1)

c = Circle(5)
print(c.radius)                # 5  — no parentheses, thanks to @property
print(Circle.unit().radius)    # 1
```

`@property`, `@staticmethod`, and `@classmethod` are decorators in the standard library. They *change how the method behaves* — that's behavior, not metadata.

### Python — `@functools.lru_cache`: behavior change you can feel

```python
import functools

@functools.lru_cache(maxsize=None)     # note: a decorator *factory* (takes an arg)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

print(fib(35))   # fast: results are memoized (cached) automatically
```

`lru_cache` wraps `fib` so repeated calls return a stored result instead of recomputing. The `(maxsize=None)` means `lru_cache(maxsize=None)` is *called first* to produce the actual decorator — that's a **decorator factory**, our first taste of decorators-with-arguments (full treatment in `middle.md`).

### Python — Flask routing: the framework-magic you've seen

```python
from flask import Flask
app = Flask(__name__)

@app.route("/hello")           # registers this function as the /hello handler
def hello():
    return "Hello!"
```

`@app.route("/hello")` runs at import time. It calls `app.route("/hello")` to get a decorator, which *registers* `hello` in Flask's URL map and returns `hello` (often unchanged). This is a decorator used partly for behavior (registration as a side effect) — the "magic" of web frameworks demystified.

### TypeScript / Angular — a decorator used to attach metadata

```typescript
import { Component } from '@angular/core';

@Component({
  selector: 'app-greeting',
  template: '<h1>Hello</h1>',
})
export class GreetingComponent { }
```

`@Component({...})` runs at class-definition time, but its job is to *store* that configuration object as metadata on `GreetingComponent`. Angular later reads that metadata to know how to render the component. So it's decorator *machinery* doing an annotation's *job*. (How it stores metadata — `reflect-metadata` — is in `senior.md`.)

### C# — an attribute: same as a Java annotation, square brackets

```csharp
public class User
{
    [Obsolete("Use FullName instead")]   // metadata, read by the compiler
    public string Name { get; set; }

    [Required]                            // metadata, read at runtime by validators
    public string Email { get; set; }
}
```

`[Obsolete]` is read by the C# compiler to warn callers; `[Required]` is read at runtime by validation frameworks via reflection. Inert until read — identical in spirit to Java annotations.

---

## Coding Patterns

### Pattern 1: The simple wrapping decorator (Python)

```python
import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

The canonical shape: take `func`, define `wrapper` that does extra work and forwards via `*args, **kwargs`, return `wrapper`. **Always** add `@functools.wraps(func)` — without it, `wrapper.__name__` becomes `"wrapper"` and you lose the original's identity.

### Pattern 2: The marker annotation + a reader (Java, conceptual)

```java
@interface Loggable { }       // 1. the inert marker
```

The marker is useless until *something reads it*. At junior level, know that the reader is either an annotation processor (build time) or reflection code (runtime). The pattern is always **two halves**: the annotation, and the code that looks for it. Writing only the first half is the #1 beginner mistake.

### Pattern 3: Use the built-in decorators, don't reinvent them

```python
class Account:
    @property
    def balance(self):           # read like an attribute: account.balance
        return self._balance

    @staticmethod
    def currency():              # no self needed
        return "USD"
```

Reach for `@property`, `@staticmethod`, `@classmethod`, `@functools.lru_cache`, `@functools.cached_property` before writing your own. They are battle-tested and signal intent clearly.

### Pattern 4: Rewrite-to-understand

When a decorated function misbehaves, rewrite the `@` lines as explicit calls:

```python
@auth
@cache
def handler(): ...
# means:
handler = auth(cache(handler))
```

Then reason about it as plain function composition. This is the fastest way to debug decorator order bugs.

---

## Best Practices

- **First, classify it.** Before touching any `@Something`, decide: metadata (annotation/attribute) or behavior (decorator)? Everything else follows.
- **For annotations, always identify the reader.** An annotation with no processor or reflection reading it is dead code. Find the half that acts on it.
- **For Python decorators, always use `functools.wraps`.** It preserves `__name__`, `__doc__`, and the signature for debuggers and docs. Forgetting it is the most common decorator bug.
- **Keep decorators thin.** A decorator should do one cross-cutting thing (time, log, cache, authorize). Don't bury business logic in a wrapper.
- **Prefer standard-library decorators.** `@property`, `@staticmethod`, `@lru_cache` over hand-rolled versions.
- **Don't stack five decorators blind.** Each one rewires the call. If order matters (and it often does), comment why.
- **Use `@Override` everywhere it applies (Java).** It's free safety: the compiler catches signature mistakes for you.
- **Read the framework docs for what a magic annotation actually does.** `@Transactional`, `@Autowired`, `@app.route` each have surprising rules; don't guess.

---

## Edge Cases & Pitfalls

- **Writing a custom annotation and expecting it to *do* something.** It won't. Without a processor or reflection reading it, `@Cool` is inert. This trips up nearly every beginner.
- **Forgetting `functools.wraps`.** Your wrapped function reports its name as `wrapper`, breaks logging that uses `__name__`, hides its docstring, and confuses tools that introspect signatures.
- **Confusing a decorator with a decorator factory.** `@lru_cache` (no parens) is wrong; it must be `@lru_cache(maxsize=None)` or `@lru_cache` only if you're on a Python version that allows bare usage. A factory needs to be *called* to produce the decorator. Getting the parentheses wrong is a classic error.
- **Decorator order.** `@a` over `@b` means `a(b(f))`. If `@auth` must run before `@cache`, the order on the page matters. Reversing them can leak unauthorized cached results.
- **Assuming `@Override` does work at runtime.** It's a *compile-time-only* annotation; it's gone by the time the program runs.
- **Assuming a `@Test` method just runs.** It only runs because a test runner (JUnit, pytest) *scans* for it. Run the class with a plain `main` and nothing happens.
- **Mutating shared state inside a decorator at import time.** Decorators run at definition time — if your decorator has side effects (registering routes, opening files), they happen when the module is *imported*, not when functions are called. Surprising if you don't expect it.
- **`@property` on the wrong thing.** Accessing `c.radius()` with parentheses after using `@property` calls the *returned value*, not the method — a common "object is not callable" error.
- **C# attributes look different but behave the same.** Don't treat `[Required]` as if it actively validates; a validator must read it. Same inert-metadata rule as Java.

---

## Apply it

1. Choose one small, known input for **Annotations & Decorators**.
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

- What problem does Annotations & Decorators solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
