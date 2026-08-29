# Annotations & Decorators — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Annotations & Decorators** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Retention: the lifecycle knob that decides *who can read it*

A Java annotation's `@Retention` is the most important property you set, because it decides which readers can even see it:

| Retention | Survives to | Who can read it | Example |
|-----------|-------------|-----------------|---------|
| `SOURCE` | source only; discarded by `javac` | annotation **processors** at compile time; never available at runtime | `@Override`, Lombok's `@Getter` |
| `CLASS` | the `.class` file, but not loaded for reflection | bytecode tools, some weavers | default if unspecified; rarely used directly |
| `RUNTIME` | `.class` file *and* loadable via reflection | **frameworks** at runtime (Spring, JUnit, Jackson) | `@Test`, `@Entity`, `@JsonProperty` |

The rule of thumb: **`SOURCE` = "a compile-time tool will consume me and I'll vanish." `RUNTIME` = "a framework will reflect on me while the app runs."** If you write a custom annotation that a runtime framework must see, and you forget `@Retention(RUNTIME)`, the framework will silently find nothing — a notorious bug.

### 2. `@Target`: where an annotation may legally appear

`@Target` restricts the application sites: `TYPE`, `METHOD`, `FIELD`, `PARAMETER`, `CONSTRUCTOR`, `ANNOTATION_TYPE`, `TYPE_PARAMETER`, `TYPE_USE`, etc. Putting an annotation where its `@Target` forbids is a compile error. This is how `@Override` is rejected on a field — its target is `METHOD` only.

### 3. Meta-annotations: annotations on annotations

You configure an annotation by annotating *its definition*:

```java
@Retention(RetentionPolicy.RUNTIME)   // meta-annotation
@Target(ElementType.METHOD)           // meta-annotation
public @interface Benchmark { }
```

`@Retention` and `@Target` are themselves annotations applied to `@Benchmark`. Other meta-annotations: `@Inherited` (subclasses inherit the annotation), `@Documented` (appears in Javadoc), `@Repeatable` (apply more than once).

### 4. The two processing paths, concretely

This is the heart of the topic. An annotation becomes meaningful in exactly one of two ways:

**(a) Compile-time processing (APT).** During `javac`, registered `Processor`s receive the set of annotated elements in *rounds*. A processor may:
- **Generate code** — write new `.java` files (Dagger writes DI graphs; MapStruct writes mappers; AutoValue writes value classes). The generated code is compiled in a later round.
- **Validate** — raise compile errors/warnings (e.g., "an `@Entity` must have a no-arg constructor").

Lombok is a special, controversial case: it uses the annotation-processing hook but *mutates the AST in place* to inject getters/setters rather than generating separate files — relying on internal compiler APIs (more in `senior.md` and `professional.md`).

**(b) Runtime reflection.** With `RUNTIME` retention, a framework at startup or on demand scans classes and reacts:
```java
for (Method m : clazz.getDeclaredMethods())
    if (m.isAnnotationPresent(Test.class))
        runAsTest(m);
```
Spring's component scan, JUnit's test discovery, Jackson's field mapping, and Hibernate's entity mapping all do versions of this.

**Cost trade-off:** compile-time processing makes the *build* slower but the *runtime* free; runtime reflection makes the *build* untouched but adds *startup* cost (scanning) and per-call reflection cost. This trade-off is the through-line of the whole section.

### 5. Decorator factories: decorators that take arguments

A plain decorator takes a function and returns a function. But `@retry(times=3)` needs an argument. The trick: `retry(times=3)` is *called first*, and must *return a decorator*. So you need three nested layers:

```python
def retry(times):                       # 1. factory: takes the argument
    def decorator(func):                 # 2. the actual decorator
        @functools.wraps(func)
        def wrapper(*args, **kwargs):    # 3. the wrapper
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
        return wrapper
    return decorator
```

`@retry(times=3)` evaluates `retry(3)` → returns `decorator` → `decorator(func)` → returns `wrapper`. **Parentheses mean "factory."** No parentheses means "the name *is* the decorator." Mixing these up is the most common decorator error.

### 6. Class decorators

A decorator can wrap a *class*, receiving the class and returning a (possibly modified or replaced) class:

```python
def singleton(cls):
    instances = {}
    @functools.wraps(cls, updated=[])
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class Config:
    ...
```

Now `Config()` always returns the same instance. Class decorators are how `@dataclass` works: `@dataclass` reads the class's annotations and *generates* `__init__`, `__repr__`, `__eq__`. (Note `@dataclass` reads Python's *variable annotations* — `name: str` — which are Python's metadata feature; a neat case of a decorator consuming annotations.)

### 7. Stacking order

```python
@a
@b
@c
def f(): ...
```

is `f = a(b(c(f)))`. Applied **bottom-up** (`c` first), but at call time executes **top-down** (`a`'s wrapper outermost). So if `@timing` is on top of `@cache`, timing measures the cached call (fast on hits); swap them and timing measures the real call always. Order encodes semantics — choose it deliberately.

### 8. `functools.wraps` — what it actually copies, and why

Without it, the wrapper *is* a different object: `f.__name__ == "wrapper"`, `f.__doc__ is None`, `help(f)` is useless, and tools relying on `inspect.signature` see `(*args, **kwargs)`. `functools.wraps(func)` copies `__module__`, `__name__`, `__qualname__`, `__doc__`, `__dict__`, and sets `__wrapped__ = func` so introspection can recover the original. Treat it as non-optional on any function-wrapping decorator.

---

## Code Examples

### Java — defining a RUNTIME annotation with members and reading it

```java
import java.lang.annotation.*;
import java.lang.reflect.Method;

@Retention(RetentionPolicy.RUNTIME)     // so reflection can see it
@Target(ElementType.METHOD)             // only on methods
@interface Benchmark {
    int warmups() default 0;            // a member with a default
}

class Service {
    @Benchmark(warmups = 2)
    public void compute() { /* ... */ }
}

class Runner {
    static void run(Class<?> c) throws Exception {
        for (Method m : c.getDeclaredMethods()) {
            Benchmark b = m.getAnnotation(Benchmark.class);   // the reader
            if (b != null) {
                for (int i = 0; i < b.warmups(); i++) m.invoke(c.getDeclaredConstructor().newInstance());
                // ... time the real run ...
            }
        }
    }
}
```

Note both halves: the `@Benchmark` definition (with `RUNTIME` retention so it survives) and the `Runner` that reflects to find and act on it. Drop `RUNTIME` and `getAnnotation` returns `null`.

### Java — a SOURCE annotation consumed at compile time (sketch)

```java
@Retention(RetentionPolicy.SOURCE)
@Target(ElementType.TYPE)
@interface GenerateBuilder { }
```

A registered annotation processor would, during `javac`, see every `@GenerateBuilder` class and *emit* a `XxxBuilder.java` file. At runtime the annotation is gone — only the generated builder remains. (Full processor code is in `senior.md`.) This is the Dagger/AutoValue model: zero runtime reflection, all work done at build time.

### Python — parameterized decorator (factory) with a registry side effect

```python
import functools

ROUTES = {}

def route(path, methods=("GET",)):
    def decorator(func):
        ROUTES[path] = (func, methods)        # side effect at definition time
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

@route("/users", methods=("GET", "POST"))
def users():
    return "user list"

# ROUTES now contains {"/users": (users, ("GET", "POST"))} — registered at import.
```

This is the skeleton of every micro-framework router (Flask, FastAPI). The factory captures `path` and `methods` in a closure, registers at import time, and returns the function.

### Python — class decorator that augments the class

```python
def add_repr(cls):
    def __repr__(self):
        fields = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{cls.__name__}({fields})"
    cls.__repr__ = __repr__       # mutate the class
    return cls

@add_repr
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

print(Point(1, 2))   # Point(x=1, y=2)
```

The decorator receives the class, attaches a `__repr__`, and returns it. This is a miniature `@dataclass`.

### Python — stacking order made visible

```python
import functools

def tag(name):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*a, **k):
            print(f"enter {name}")
            r = func(*a, **k)
            print(f"exit {name}")
            return r
        return wrapper
    return deco

@tag("outer")
@tag("inner")
def work():
    print("working")

work()
# enter outer / enter inner / working / exit inner / exit outer
```

Applied bottom-up (`inner` wraps first), executed top-down (`outer` runs first). The print order proves it.

### TypeScript — a decorator factory storing config (Angular/NestJS pattern)

```typescript
function Controller(prefix: string) {
  return function (target: Function) {
    Reflect.defineMetadata?.('prefix', prefix, target);   // store metadata
  };
}

@Controller('/users')
class UsersController {}
```

`Controller('/users')` is the factory; it returns the actual decorator that stores `'/users'` as metadata on the class. NestJS later reads that metadata to build routes. Same decorator-doing-annotation's-job pattern, now with arguments. (The `Reflect.defineMetadata` mechanism is detailed in `senior.md`.)

### C# — attribute with constructor arguments, read by reflection

```csharp
[AttributeUsage(AttributeTargets.Method)]   // the C# equivalent of @Target
class RetryAttribute : Attribute
{
    public int Times { get; }
    public RetryAttribute(int times) => Times = times;
}

class Job
{
    [Retry(3)]
    public void Run() { }
}

// Reading it:
var attr = typeof(Job).GetMethod("Run")!
    .GetCustomAttribute<RetryAttribute>();
int times = attr?.Times ?? 1;
```

`[AttributeUsage]` is C#'s `@Target`; the attribute carries data via its constructor; reflection reads it. Conceptually identical to the Java `@Benchmark` example.

---

## Coding Patterns

### Pattern 1: The factory-decorator-wrapper triple (Python)

```python
def deco_factory(config):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # use `config`
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

Memorize the three layers. The outer captures config; the middle is the real decorator; the inner forwards the call. Each layer has exactly one job.

### Pattern 2: Make a decorator work with *and* without arguments

```python
def smart(func=None, *, level=1):
    if func is None:                      # called as @smart(level=2)
        return functools.partial(smart, level=level)
    @functools.wraps(func)                # called as @smart
    def wrapper(*a, **k):
        return func(*a, **k)
    return wrapper
```

Both `@smart` and `@smart(level=2)` now work. This pattern handles the common "parentheses or not" ambiguity gracefully.

### Pattern 3: Annotation + reader as a pair (Java)

Always ship the annotation *and* its consumer together, and choose retention to match the consumer:

- Consumer is a build-time processor → `@Retention(SOURCE)`.
- Consumer is a runtime framework → `@Retention(RUNTIME)`.

Document which consumer reads it, right on the annotation's Javadoc.

### Pattern 4: Preserve the original for introspection

```python
@functools.wraps(func)
def wrapper(*a, **k): ...
# later, recover the unwrapped function:
original = wrapper.__wrapped__
```

`__wrapped__` lets debuggers, doc tools, and your own code reach the real function through the wrapper.

---

## Best Practices

- **Match retention to reader.** Runtime framework → `RUNTIME`. Compile-time processor → `SOURCE`. This is the #1 source of "my annotation is ignored" bugs.
- **Always set `@Target`.** Constrain where your annotation may go; let the compiler reject misuse.
- **Ship annotation and consumer as a unit.** A bare annotation is half a feature; document/test the reader alongside it.
- **Use `functools.wraps` on every wrapping decorator.** Non-negotiable for debuggable, introspectable code.
- **Support both bare and parameterized forms when ergonomics matter** (Pattern 2).
- **Be explicit about stacking order.** Comment *why* the order is what it is, especially for security-sensitive stacks (auth must be outermost over cache).
- **Prefer compile-time generation for hot paths.** If reflection scanning hurts startup or per-call latency, a code-gen approach (Dagger-style) removes it.
- **Keep decorators side-effect-aware.** Remember registration side effects fire at import; don't do expensive or order-dependent work there casually.

---

## Edge Cases & Pitfalls

- **Wrong retention.** A custom `@RUNTIME`-needing annotation left at the default `CLASS` retention is invisible to reflection — and there's no error, just silence.
- **Decorator-factory parentheses.** `@retry` vs `@retry(3)`: using the factory without calling it passes the function as the *first positional arg of the factory*, producing baffling errors.
- **Forgetting `@wraps`.** Logs show `wrapper`, `help()` is empty, `inspect.signature` is wrong, and frameworks that key off `__name__` (some routers, some caches) misbehave.
- **Stacking order bugs.** `@cache` above `@auth` can serve cached responses without re-checking authorization — a real security hole.
- **Import-time side effects.** A decorator that registers routes/handlers runs when the module is imported; conditional or lazy imports can mean handlers never register.
- **Mutating the function vs returning a new one.** A decorator that returns a *new* object breaks identity comparisons and any reference captured before decoration.
- **`@Inherited` only covers class annotations, not method annotations,** and only along the superclass chain, not interfaces — a frequent surprise in framework code.
- **Repeatable annotations need a container.** Before `@Repeatable`, you couldn't apply the same annotation twice; mixing old code with repeatable usage causes confusing `getAnnotation` vs `getAnnotationsByType` differences.
- **Reflection cost.** Reading annotations per call (rather than caching the lookup) can dominate a hot loop — cache the reflective lookups.
- **Class decorator replacing the class** can break `isinstance` checks and pickling if it returns a function instead of a class (as the naive `@singleton` above does).

---

## Apply it

1. Find a real component where **Annotations & Decorators** affects an interface or dependency.
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

- Which boundary is most affected by Annotations & Decorators?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
