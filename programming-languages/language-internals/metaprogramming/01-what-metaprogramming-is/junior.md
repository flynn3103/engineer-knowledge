# What Metaprogramming Is — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **What Metaprogramming Is** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Code Is Just Data (If You Look At It Right)

The deepest idea in metaprogramming is this: **a program is data.** Your source file is a text file — a string. After parsing, it becomes a tree of objects describing functions, calls, and expressions. At runtime, a class is itself an object with a list of methods and fields. Once you see code as data, you can do to it everything you do to data: read it, search it, copy it, transform it, and produce more of it.

Ordinary programming:

```text
data  ──►  [your program]  ──►  result
```

Metaprogramming:

```text
code  ──►  [meta-program]  ──►  more code   (or)   behavior
```

The "data" flowing through a metaprogram *is itself a program*.

### 2. The Central Question: WHEN Does the Meta Level Run?

This is the single most useful thing to learn on this page. Every metaprogramming technique runs the meta level at one of two times:

- **Compile-time / build-time** — the meta-code runs *before* your program runs, while it is being built. The output is baked into the final program. Examples: macros, C++ templates, annotation processors, code generators (`go generate`, `protoc`), Rust's `#[derive]`.
- **Runtime** — the meta-code runs *while* your program is running. Examples: reflection, Python decorators that inspect at import time, metaclasses, dynamic proxies, monkeypatching, `eval`/`exec`.

```text
            BUILD                          RUN
  ┌────────────────────────┐   ┌──────────────────────────┐
  │ macros                 │   │ reflection / introspection│
  │ C++ templates          │   │ metaclasses               │
  │ annotation processors  │   │ dynamic proxies           │
  │ code generators        │   │ monkeypatching            │
  │ Rust #[derive]         │   │ eval / exec               │
  └────────────────────────┘   └──────────────────────────┘
      "decided already"            "decided as it runs"
```

Why does the *when* matter so much? Because it decides:

- **Speed:** Compile-time meta-code has zero runtime cost — the work is already done. Runtime meta-code costs you something on every call.
- **Safety:** Compile-time tools can catch mistakes before you ship. Runtime tools fail when the user is watching.
- **Flexibility:** Runtime tools can react to information you only have *while running* (the actual data, config, plugins loaded). Compile-time tools only know what was true at build.

Keep this axis in your head for the entire section.

### 3. Introspection vs Intercession (Look vs Change)

Two flavors of reflective metaprogramming:

- **Introspection** = *observe* the program's structure. "What type is `x`? What methods does this class have? Does this field have an annotation?" Read-only.
- **Intercession** = *change* the program's structure or behavior while it runs. "Add a method to this class. Replace this function. Intercept every call to this object."

Introspection is common and relatively safe (serializers, debuggers, test frameworks lean on it). Intercession is powerful and dangerous (monkeypatching, dynamic proxies) — you are editing the program *as it runs*.

### 4. Generative vs Reflective Metaprogramming

Another way to slice the field:

- **Generative** = *produce new code.* Macros, code generators, templates, `#[derive]`. The meta-code's output is more code.
- **Reflective** = *inspect/alter existing code or objects.* Reflection, metaclasses, proxies. The meta-code works on code that already exists.

Many tools mix both (a runtime framework might inspect your class *and* generate a proxy), but the distinction helps you classify what you are looking at.

### 5. Homoiconicity: The Purest Form

In most languages, code and data look different — code is special syntax, data is values. In the **Lisp** family, code is *written as lists*, the same structure used for data. A function call `(+ 1 2)` is literally a list of three things: the symbol `+`, the number `1`, the number `2`. Because code *is* a list, a Lisp program can build, take apart, and rewrite code using the exact same operations it uses on any list. This property is called **homoiconicity** ("same representation"), and it is why Lisp macros are considered the gold standard of metaprogramming — there is no gap between "code" and "data you can manipulate."

Most languages bolt metaprogramming on with special machinery (reflection APIs, macro syntax). Lisp gets it for free because of how the language is shaped.

### 6. The Frameworks You Already Use Are Built On This

You will rarely write a metaprogramming framework. You will *constantly use one*. A short, honest list of famous tools and the technique underneath them:

- **Spring / Hibernate (Java)** — reflection + annotations + dynamic proxies.
- **Django / Rails (Python / Ruby)** — metaclasses, dynamic method generation, decorators.
- **serde (Rust)** — `#[derive]` macros that generate serialization code at compile time.
- **gRPC / Protocol Buffers** — code generators that produce client/server stubs from a schema.
- **Mocking libraries (Mockito, unittest.mock)** — dynamic proxies and runtime class manipulation.

When you understand *what* metaprogramming is, these stop being magic and become "oh, it's reading my annotations and generating a proxy."

### 7. The Fundamental Trade

Metaprogramming buys you **power and DRY-ness**: write a rule once, apply it everywhere; eliminate boilerplate; let the machine generate what would be tedious or error-prone by hand. The price is **comprehensibility, debuggability, and tooling**: code that is generated or rewritten is harder to read, harder to step through in a debugger, and harder for your IDE to autocomplete or jump to. The whole rest of this section, ultimately, is about spending that power wisely.

---

## Code Examples

These are deliberately tiny. Each shows *one* technique and labels *when it runs*. Run them and watch what happens.

### Python — Reflection / Introspection (runtime)

```python
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def greet(self):
        return f"hi, I'm {self.name}"

u = User("Ada", 36)

# The program inspects ITSELF at runtime:
print(type(u).__name__)        # 'User'        -- what class is this?
print(vars(u))                 # {'name': 'Ada', 'age': 36}  -- its fields
print([m for m in dir(u) if not m.startswith("_")])  # ['age', 'greet', 'name']

# It can even decide what to call by a string computed at runtime:
method_name = "greet"
print(getattr(u, method_name)())   # 'hi, I'm Ada'
```

Nothing here was known when you wrote it — `method_name` could have come from a config file. This is **introspection** at **runtime**. A serializer turning any object into JSON works exactly this way.

### Python — Decorator (runtime, at import)

```python
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_calls            # this RUNS when the module is imported
def add(a, b):
    return a + b

print(add(2, 3))
# calling add
# 5
```

`@log_calls` is metaprogramming: it takes a function *as data*, wraps it, and replaces it. The decorator runs **once at import** (runtime), producing a new function. This is the same shape as `@app.route` in a web framework.

### Python — `exec` (runtime, the bluntest tool)

```python
source = "def square(x): return x * x"
exec(source)           # turns a STRING into a real function, right now
print(square(5))       # 25
```

`exec` takes source code *as a string* and runs it as code. Powerful, and almost always the wrong choice (slow, unsafe, invisible to tooling) — but it shows the idea in its rawest form: **a program writing and running a program at runtime.**

### Rust — Derive Macro (compile-time)

```rust
#[derive(Debug, Clone)]   // a MACRO runs at COMPILE time
struct Point {
    x: i32,
    y: i32,
}

fn main() {
    let p = Point { x: 1, y: 2 };
    let q = p.clone();              // Clone code was GENERATED for us
    println!("{:?}", q);            // Debug code was GENERATED: Point { x: 1, y: 2 }
}
```

You wrote zero lines of printing or cloning logic. The `#[derive(...)]` macro **generated** that code *before* the program was compiled. By the time the program runs, there is no "magic" left — just ordinary compiled functions. This is **generative**, **compile-time** metaprogramming.

### Go — `go generate` (build-time code generation)

```go
//go:generate stringer -type=Color
type Color int

const (
    Red Color = iota
    Green
    Blue
)
```

Running `go generate ./...` invokes the `stringer` tool, which **writes a new `.go` file** giving each `Color` a `String()` method (`Red.String() == "Red"`). Go deliberately has *no* macros; instead it leans on this explicit "generate a file you can read and check in" approach plus the `reflect` package at runtime. The generated file is real source you can open and step through.

### Java — Reflection + Annotation (runtime)

```java
import java.lang.annotation.*;
import java.lang.reflect.*;

@Retention(RetentionPolicy.RUNTIME)
@interface Test {}

class Suite {
    @Test public void checkA() { System.out.println("A ran"); }
    public void helper()       { System.out.println("not a test"); }
}

public class Runner {
    public static void main(String[] args) throws Exception {
        Suite s = new Suite();
        for (Method m : Suite.class.getDeclaredMethods()) {
            if (m.isAnnotationPresent(Test.class)) {   // INSPECT at runtime
                m.invoke(s);                           // CALL by reflection
            }
        }
    }
}
// prints: A ran
```

This is, in miniature, *how JUnit works*: it uses **reflection** at **runtime** to find every method tagged `@Test` and call it. The `@Test` annotation is data attached to your code; the framework reads that data and acts on it.

### Lisp — Homoiconic Macro (compile-time, code as data)

```lisp
;; `unless` does not exist as a built-in here; we WRITE it as a macro.
;; The macro receives code AS A LIST and returns new code.
(defmacro my-unless (condition body)
  (list 'if condition nil body))

(my-unless nil (print "this prints, because condition is nil"))
;; expands, before running, into:  (if nil nil (print "..."))
```

The macro `my-unless` receives its arguments *as lists of code* and builds new code with `list`. Because Lisp code *is* a list, "writing code that writes code" is just "writing a function that builds a list." This is **homoiconicity** — the purest metaprogramming there is.

---

## Coding Patterns

### Pattern 1: Classify before you touch — *which technique, run when?*

When you meet unfamiliar "magic," answer two questions before anything else:

```text
1. Generative or reflective?  (does it make code, or inspect/alter existing code?)
2. Compile-time or runtime?   (did it finish at build, or is it live now?)
```

Those two answers locate any feature on the map and tell you how to debug it.

### Pattern 2: Prefer the earliest stage that works

If a job can be done at **build time** (codegen, macro) instead of **runtime** (reflection, `eval`), prefer build time: it's faster and safer. Only move to runtime when you genuinely need information that doesn't exist until the program runs.

### Pattern 3: Read the generated output

For any code generator (`go generate`, `protoc`, macro expansion via `cargo expand`), *open the generated file or the expansion.* The single best way to demystify metaprogramming is to see the boring, ordinary code it produced.

### Pattern 4: Treat annotations as data, not behavior

An annotation/decorator/attribute is just a *label*. By itself it does nothing — some tool must read it. When you see `@Foo`, ask "who reads `@Foo`, and when?" The label and the reader are two separate things.

### Pattern 5: Start without metaprogramming

Write the boring version first (one explicit function, one explicit registration). Introduce metaprogramming only when the boilerplate genuinely repeats and hurts. Cleverness is a tool of last resort, not first.

---

## Best Practices

- **Default to ordinary code.** Reach for metaprogramming only when the repetition is real and the payoff clearly beats the loss of clarity.
- **Know *when* your meta-code runs.** Build-time and runtime have completely different costs and failure modes. Never confuse the two.
- **Make generated code visible.** Check generated files into the repo (or make them trivially regenerable) and mark them "DO NOT EDIT." Hidden code is the enemy of debuggability.
- **Never `eval`/`exec` untrusted input.** That is arbitrary code execution. If you think you need it, you almost certainly don't.
- **Prefer the language's blessed mechanism.** Use the standard reflection API, the standard macro system, the standard codegen tool — not a clever hack.
- **Document the magic.** If a class behaves differently because of a decorator, metaclass, or annotation, say so in a comment. The next reader cannot see the mechanism.
- **Keep base level and meta level separate.** Don't tangle "the code that does work" with "the code that generates code." Reviewers should be able to read each alone.

---

## Edge Cases & Pitfalls

- **"It works by magic" is a smell, not a feature.** If you can't explain *what read your code and when*, you don't understand it yet — and you can't debug it under pressure.
- **Debuggers struggle with generated/rewritten code.** A stack trace may point at code you never wrote, or at a generated file with no helpful names. Know how to view expansions (`cargo expand`, generated `.go`/`.java` files).
- **Runtime reflection is slow.** A reflective call can be orders of magnitude slower than a direct one. Fine in startup/config; bad in a hot loop.
- **`eval`/`exec` are security holes by default.** Running a string as code means whoever controls the string controls your program.
- **Compile-time errors point at the wrong place.** A macro or template that generates broken code produces an error in the *generated* code, far from your `#[derive(...)]` line. The mapping back is the hard part.
- **Annotations do nothing on their own.** Adding `@Cacheable` without the framework that reads it is a no-op. Many "why isn't my annotation working?" bugs are "nothing is reading it."
- **Metaprogramming concentrates knowledge.** A clever metaprogram replaces a whole team's worth of boilerplate — and becomes a single point of "only one person understands this." That's an organizational risk, not just a technical one.
- **Self-modifying code is (almost) never what you want today.** Historically, programs literally rewrote their own machine instructions to save memory. On modern CPUs this fights caches and security defenses and is essentially banned outside niche JITs. When people say "self-modifying" now, they almost always mean ordinary runtime metaprogramming, not literal instruction rewriting.

---

## Apply it

1. Choose one small, known input for **What Metaprogramming Is**.
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

- What problem does What Metaprogramming Is solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
