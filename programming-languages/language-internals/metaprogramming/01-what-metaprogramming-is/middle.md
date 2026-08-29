# What Metaprogramming Is — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **What Metaprogramming Is** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Full Taxonomy of Techniques

Every metaprogramming feature you'll meet is one of these. The grouping is by *what it does*; the stage (when it runs) is noted because that's the dominant property.

| Technique | What it does | Typical stage | Generative/Reflective |
|-----------|--------------|---------------|-----------------------|
| **Reflection / introspection** | Inspect types, fields, methods at runtime | Runtime | Reflective |
| **Intercession** | Modify structure/behavior at runtime | Runtime | Reflective |
| **Annotations / attributes** | Attach machine-readable data to code | Read by build *or* runtime tools | (data; enabler) |
| **Decorators** | Wrap/replace functions or classes | Runtime (Python: at import) | Reflective + generative |
| **Code generation** | Emit source from a schema/spec | Build-time | Generative |
| **Macros (textual)** | Token substitution before compile | Pre-compile (C preprocessor) | Generative |
| **Macros (syntactic/hygienic)** | Transform the AST before compile | Compile-time (Lisp, Rust) | Generative |
| **Metaclasses** | Control how classes are constructed | Runtime (class-creation time) | Reflective + generative |
| **Dynamic proxies** | Runtime stand-ins intercepting calls | Runtime | Generative + reflective |
| **`eval` / `exec`** | Run a string as code | Runtime | Generative |
| **Template metaprogramming** | Compute with types/values | Compile-time (C++) | Generative |
| **`constexpr` / `comptime`** | Run normal code at compile time | Compile-time (C++, Zig) | Generative |
| **AST manipulation** | Walk/rewrite the syntax tree | Build-time *or* runtime | Both |

Notice that **annotations are not a technique by themselves** — they are *data attached to code*, made meaningful only by something that reads them (an annotation processor at build time, or reflection at runtime). This is a common source of confusion: the `@Annotation` is inert; the reader gives it power.

### 2. Stages Are Finer Than "Compile vs Run"

Junior level used two stages. In reality there is a chain, and metaprogramming can hook into any link:

```text
 read-time  →  macro-expand  →  type-check  →  compile  →  link  →  load  →  runtime
   (C pp)       (Lisp/Rust)      (C++ TMP)                          (class    (reflection,
                                                                    loaders)   eval, proxies)
```

The earlier a stage, the cheaper (at runtime) and the safer (errors caught sooner), but the less it knows about the actual world the program will run in. The later a stage, the more it knows (real data, real config, loaded plugins) but the more it costs and the later it fails. This is the **earliness/knowledge trade-off**, and it underlies every design decision in the field.

### 3. The Language Spectrum

Languages can be placed on a line from "metaprogramming is forbidden/minimal" to "metaprogramming is the language."

```text
 minimal ◄───────────────────────────────────────────────────► maximal
   Go        C        Java        C++        Rust      Python       Lisp
   │         │         │           │          │          │          │
 reflect   text     reflection   templates  hygienic   runtime    code IS
 + go      pre-      + annotation + constexpr macros    everything  data;
 generate  processor processors   (compile-  (compile-  (classes,   macros are
 (no       (no AST,  + dynamic    time TMP)  time)      metaclasses, native
 macros    just      proxies      static     mostly     monkey-
 by        tokens)   (runtime,    typing     compile-   patch,
 design)             dynamic)                time       eval)
```

The crucial observation: **position on this line is a design choice, not an accident.** Each language traded something:

- **Go** chose *readability and tooling* over expressive power. No macros means "what you read is what runs" — a non-trivial productivity and onboarding benefit at scale. It accepts more boilerplate in exchange.
- **Rust** chose *zero-cost abstraction*: do the metaprogramming at compile time so the running binary pays nothing, and keep it hygienic and type-checked so it stays safe.
- **Python** chose *maximal runtime flexibility*: everything is an object you can inspect and mutate, enabling extraordinarily expressive frameworks (Django, SQLAlchemy) at the cost of speed and "spooky action."
- **C++** chose *compile-time computation through the type system*, which is enormously powerful but historically produced famously inscrutable errors.
- **Lisp** chose *homoiconicity*, making metaprogramming the native idiom rather than a feature.
- **Java** chose a *middle path*: strong static types, reflection and dynamic proxies at runtime, annotation processing at build time — enough power for Spring and Hibernate, with guardrails.
- **C** chose *only a textual preprocessor* — the bluntest, least safe form (no understanding of types or scope), kept for simplicity and portability.

### 4. Quoting and Quasiquotation

To manipulate code as data, you need a way to say "don't run this — treat it as a value." That's **quoting**. In Lisp, `'(+ 1 2)` is the *list* `(+ 1 2)`, not the number `3`. **Quasiquotation** adds holes you can fill with computed pieces: in Lisp, ``` `(+ 1 ,x) ``` is "the code `(+ 1 ...)` with the value of `x` spliced in." Rust's `quote!` macro and template literals in some languages serve the same role. Quoting is the bridge between "code" and "data you can build and transform"; every macro system has some form of it.

### 5. Introspection vs Intercession, Sharpened

- **Introspection** is *almost always safe*: reading type names, field lists, annotations. Serializers, DI containers (at scan time), test runners, and debuggers rely on it.
- **Intercession** is *powerful and risky*: adding methods to a live class (monkeypatching), swapping a function, generating a proxy that wraps every call. It breaks the assumption that code is fixed once written, which is exactly what makes it both useful (AOP, mocking) and dangerous (action-at-a-distance bugs).

A practical rule: introspection scales to large teams; intercession needs strict discipline and clear ownership, because it can change behavior anywhere.

### 6. Multi-Stage Programming, Introduced

**Multi-stage programming (MSP)** is the explicit, principled version of "do work earlier to make later work fast." You annotate which computations happen at an earlier stage to *generate* the code that runs at a later stage. C++ template metaprogramming, Rust's `const fn` and macros, Zig's `comptime`, and research languages like MetaML/MetaOCaml are points on this continuum. The mental model: a *staged* program is one where some of the program's job is "write the rest of the program." You'll see this idea formalized in the compile-time-vs-runtime trade-offs topic of this section; here, just hold the concept that staging is metaprogramming with the *stages made explicit and type-checked*.

### 7. Self-Modifying Code: Mostly History

Classic **self-modifying code** literally rewrote its own machine instructions in memory — to save space, to patch jumps, to implement early JITs. On modern hardware this is hostile to instruction caches, branch predictors, and security hardening (`W^X`: memory is writable *or* executable, not both). Today, "self-modifying" in practice means *runtime metaprogramming* (a program reshaping its own objects/classes), and genuine instruction rewriting is confined to JIT compilers and a few specialized runtimes that take great care. Know the term and its history; don't reach for the literal version.

---

## Code Examples

Each example highlights *stage* and *taxonomy slot*. Run them and locate each on the map.

### Java — Annotation Processor vs Runtime Reflection (same annotation, two stages)

```java
// The SAME annotation can be consumed at DIFFERENT stages.
import java.lang.annotation.*;

@Retention(RetentionPolicy.SOURCE)   // visible only to the COMPILER / APT
@interface GenerateBuilder {}

@Retention(RetentionPolicy.RUNTIME)  // survives into the running program
@interface Endpoint { String path(); }
```

`RetentionPolicy.SOURCE` means an **annotation processor** (build-time) reads it and generates code; it's gone by runtime. `RetentionPolicy.RUNTIME` means **reflection** (runtime) reads it. The *retention policy is literally a declaration of which stage will consume this label.* This single example captures the whole "when does the meta level run?" axis.

### Rust — Compile-Time `const fn` (computation moved to build)

```rust
const fn factorial(n: u64) -> u64 {
    let mut acc = 1;
    let mut i = 2;
    while i <= n {
        acc *= i;
        i += 1;
    }
    acc
}

const TABLE_SIZE: u64 = factorial(5);   // computed AT COMPILE TIME → 120

fn main() {
    let buf = [0u8; TABLE_SIZE as usize]; // size known before the program runs
    println!("{}", buf.len());            // 120, zero runtime computation
}
```

This is multi-stage programming in miniature: ordinary-looking code runs at compile time to produce a constant the runtime simply uses. Rust pushes work to the build stage to make the binary pay nothing.

### Python — Metaclass (intercession at class-creation time)

```python
class AutoRepr(type):                 # a metaclass: the "class of a class"
    def __new__(mcs, name, bases, ns):
        cls = super().__new__(mcs, name, bases, ns)
        def __repr__(self):
            fields = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
            return f"{name}({fields})"
        cls.__repr__ = __repr__       # INJECT a method into the class
        return cls

class Point(metaclass=AutoRepr):
    def __init__(self, x, y):
        self.x, self.y = x, y

print(Point(1, 2))   # Point(x=1, y=2)  -- __repr__ was generated for us
```

The metaclass runs *when the `Point` class is created* (a distinct runtime stage) and *injects* a method — this is **intercession**, top-right of our map. Django's models and SQLAlchemy's declarative base work on exactly this mechanism.

### Java — Dynamic Proxy (generate a stand-in at runtime)

```java
import java.lang.reflect.*;

interface Service { String run(String in); }

public class ProxyDemo {
    public static void main(String[] args) {
        Service real = in -> "result:" + in;
        Service proxied = (Service) Proxy.newProxyInstance(
            Service.class.getClassLoader(),
            new Class<?>[]{Service.class},
            (proxy, method, mArgs) -> {          // intercepts EVERY call
                System.out.println("calling " + method.getName());
                return method.invoke(real, mArgs);
            });
        System.out.println(proxied.run("x"));
        // calling run
        // result:x
    }
}
```

`Proxy.newProxyInstance` *generates a class at runtime* that implements `Service` and routes every call through your handler. This is how Spring adds transactions/logging "around" your beans without you writing wrapper code — generative *and* runtime (top-right).

### Go — `reflect` for Generic Struct Inspection (runtime introspection)

```go
package main

import (
    "fmt"
    "reflect"
)

type User struct {
    Name string `json:"name"`
    Age  int    `json:"age"`
}

func describe(v any) {
    t := reflect.TypeOf(v)
    for i := 0; i < t.NumField(); i++ {
        f := t.Field(i)
        fmt.Printf("%s (%s) tag=%q\n", f.Name, f.Type, f.Tag.Get("json"))
    }
}

func main() {
    describe(User{})
    // Name (string) tag="name"
    // Age (int) tag="age"
}
```

Go intentionally gives you *introspection* (`reflect`) but *no macros* — so when you need to generate code rather than inspect at runtime, the idiomatic answer is `go generate` writing a real `.go` file you can read. The language nudges you toward visible, debuggable generation.

### Lisp — Quasiquotation (build code from a template)

```lisp
;; `swap!` writes code that swaps two place values, using quasiquote/unquote.
(defmacro swap! (a b)
  `(let ((tmp ,a))     ; backquote = template; comma = splice in the argument
     (setf ,a ,b)
     (setf ,b tmp)))

;; (swap! x y) expands BEFORE running into:
;;   (let ((tmp x)) (setf x y) (setf y tmp))
```

The backquote builds a code *template*; the commas splice in the actual arguments. This is quasiquotation, the core mechanism of nearly every macro system — Rust's `quote!` is the same idea with different syntax.

---

## Coding Patterns

### Pattern 1: Place every feature on the 2×2 map

For any magic: *generative or reflective?* × *compile-time or runtime?* That single placement predicts speed, failure mode, and debug strategy. Make it a reflex.

### Pattern 2: Match the stage to the information you have

If everything you need is known at build time, generate at build time. Only push to runtime the parts that genuinely depend on runtime-only information (loaded plugins, config, actual data shapes).

### Pattern 3: Annotations + a named reader

When designing your own annotation-driven feature, make the reader explicit and discoverable: a documented annotation processor, or a documented startup scan. Don't bury the reader so deep that nobody can find why `@Foo` "works."

### Pattern 4: Prefer hygienic/syntactic macros over textual ones

If your language offers AST-level (hygienic) macros, prefer them to textual substitution. Textual macros (C preprocessor) don't understand scope or types and produce subtle capture bugs; syntactic macros (Lisp, Rust) respect both.

### Pattern 5: Keep introspection at the boundary, not in hot loops

Reflection at startup/config time is fine. Reflection on every request is a performance bug. Cache reflective lookups (resolved methods, field accessors) once, reuse the cheap handle.

---

## Best Practices

- **Name the stage out loud in design docs and code comments.** "This is a build-time codegen step" vs "this is a runtime reflection scan" changes everything about how it's reviewed and debugged.
- **Use the language's blessed mechanism, not a workaround.** A proc-macro in Rust, an annotation processor in Java, `go generate` in Go — these have tooling support; ad-hoc string munging does not.
- **Make generated code first-class.** Check it in (or make regeneration trivial and CI-verified), mark it "DO NOT EDIT," and ensure stack traces can point into it meaningfully.
- **Respect the language's bargain.** Don't fight Go by simulating macros with codegen hacks where a plain function would do; don't fight Python by avoiding all runtime flexibility when it's the idiomatic solution.
- **Cache runtime reflection.** Resolve once at startup; never repeat per-call.
- **Treat intercession (monkeypatching, runtime method injection) as load-bearing and document it.** It changes behavior at a distance; the next reader cannot see it without help.
- **Prefer the earliest viable stage.** Earlier = faster and safer. Move later only for information that doesn't exist yet.

---

## Edge Cases & Pitfalls

- **Confusing the annotation with its reader.** `@Cacheable` does nothing unless a proxy/processor reads it. Many "my annotation is ignored" bugs are a missing or misconfigured reader.
- **Wrong retention/stage.** A Java annotation with `SOURCE` retention is invisible to runtime reflection; one with `RUNTIME` is invisible to nothing and bloats class metadata. Choosing the wrong stage silently breaks the feature.
- **Textual macro capture (C).** `#define SQ(x) x*x` then `SQ(a+b)` becomes `a+b*a+b`. Textual macros don't understand expressions. Use parentheses, or better, a real function/inline.
- **Compile-time blowup.** C++ template metaprogramming and heavy const evaluation can explode compile times and error messages. Bound the recursion; prefer `constexpr`/concepts to raw TMP where possible.
- **Reflection breaks under optimization.** Tree-shaking, dead-code elimination, R8/ProGuard, and Go's linker can strip "unused" code that reflection reaches by name at runtime — leading to "works in dev, crashes in prod." Reflection often needs keep-rules.
- **Proxies and `this`/`self` identity.** A dynamic proxy is *not* the original object; identity comparisons, `final` methods, and self-invocation (a method calling another method on the same object) may bypass the proxy. Spring's "self-invocation doesn't trigger the proxy" is a classic.
- **Order of stages matters.** Generated code that another generator depends on must be produced first. Build-time metaprogramming has *dependencies between generators* that, if unordered, produce flaky builds.
- **`eval`/`exec` as a "quick fix."** It's a security hole and a tooling blind spot. Almost any use on dynamic input is a bug.
- **Assuming Python's mutability everywhere.** Not every object allows monkeypatching (C-extension types, `__slots__`, frozen dataclasses). Intercession isn't universal even in flexible languages.

---

## Apply it

1. Find a real component where **What Metaprogramming Is** affects an interface or dependency.
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

- Which boundary is most affected by What Metaprogramming Is?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
