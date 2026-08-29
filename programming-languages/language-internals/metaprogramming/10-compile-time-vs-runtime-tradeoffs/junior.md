# Compile-Time vs Runtime Trade-offs — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Compile-Time vs Runtime Trade-offs** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Two Moments to Do Work

Every program has (at least) two distinct moments:

```text
   YOU / CI MACHINE                          USER'S MACHINE / SERVER
   ┌──────────────────┐                      ┌──────────────────────┐
   │   COMPILE TIME   │   ── ship artifact ─►│      RUN TIME        │
   │  build the app   │                      │   execute the app    │
   └──────────────────┘                      └──────────────────────┘
   happens once,                              happens every time,
   before anyone runs it                      for every user
```

The central insight: **work done at compile time is paid for *once*; work done at run time is paid for *every single time the program runs* (and sometimes every single operation).** That asymmetry drives almost everything.

### 2. The Same Goal, Two Places to Solve It

Take a concrete goal: *turn a `User` object into JSON.* Two strategies:

**Compile-time strategy:** A build tool reads the `User` type and *writes a function* like:
```text
func userToJSON(u User) string {
    return "{\"name\":\"" + u.Name + "\",\"age\":" + str(u.Age) + "}"
}
```
This function is generated during the build. At run time it's just a normal, fast function — no surprises, no inspection.

**Runtime strategy:** Nothing is generated. At run time the serializer does:
```text
for each field in reflect(u):       // inspect the object live
    read field name
    read field value
    append to JSON string
```
Every call re-discovers the structure of `User` by inspecting it.

Same JSON out. Completely different *when* and *how* the cleverness happens.

### 3. The Core Trade-Off in One Picture

| You care most about... | Lean toward... |
|------------------------|----------------|
| Raw speed, especially in a hot loop | **Compile-time** (the work is pre-baked, no per-call inspection) |
| Fast startup / serverless cold start | **Compile-time** (nothing to scan at boot) |
| Catching mistakes *before* shipping | **Compile-time** (errors are build errors) |
| Adapting to things unknown until run time | **Run time** (plugins, dynamic data, hot reload) |
| Tiny, simple build with no code generators | **Run time** (build stays simple) |
| Shipping a native binary / AOT / native-image | **Compile-time** (reflection breaks or needs config) |

Keep this table in your head. Most of `middle.md` is just expanding each row with detail and numbers.

### 4. Why Compile-Time Is Fast

When the work is done at compile time, the running program has plain code. The CPU and any optimizer can **inline** it, optimize it, and run it with zero "figuring out." There's no inspecting the object, no looking up a field by name, no dictionary of methods — it's as if a human wrote the specialized function by hand. **Zero runtime cost for the meta-level.**

### 5. Why Runtime Is Flexible

When the work is done at run time, the program can handle things it *could not have known at build time*:

- A **plugin** loaded from a folder you didn't compile against.
- A **dynamic schema** — JSON whose shape comes from a config file or a database, decided long after the build.
- **Hot reload** — swapping behavior while the program keeps running.
- A **REPL** — typing new code into a live program.

Compile-time approaches can't do these, because the build already happened and is frozen. Runtime approaches shine exactly where the variation is genuinely *late*.

### 6. Why Compile-Time Catches Errors Early

If a generator or macro produces broken code, or a type doesn't fit, you find out **at build time** — the build fails, red on your screen, before any user is affected. With runtime reflection, a typo like calling a method `"getNmae"` (misspelled) compiles fine and only explodes **in production**, at 3 a.m., as a `MethodNotFound` error. Compile-time = **fail fast**; runtime = **fail late, possibly on a customer**.

### 7. The Modern Twist: Startup and Native Images

Two modern forces have pushed the industry *toward* compile-time:

- **Serverless cold start.** A function that boots in 30ms beats one that boots in 3 seconds, because users wait during the boot. Reflective frameworks scan thousands of classes at startup — slow. Compile-time frameworks wired everything during the build — fast boot.
- **Native images / AOT.** To make a self-contained native binary that starts instantly, the toolchain wants a **closed world** — everything known at build time. Heavy runtime reflection fights this; it needs special configuration or simply breaks. So teams shift the meta-work to compile time.

This is why you'll hear that newer frameworks (Quarkus, Micronaut, Dagger) "moved things to compile time" while older ones (Spring, Guice) "do it at run time."

---

## Code Examples

We'll solve the same problem — **serialize a simple object to a string** — both ways, in approachable form. Don't worry about perfect syntax; focus on *where the work happens*.

### Runtime approach (Python reflection)

```python
def to_dict(obj):
    # At RUN TIME, inspect the object's attributes live.
    result = {}
    for field_name in vars(obj):          # reflection: "what fields exist?"
        result[field_name] = getattr(obj, field_name)
    return result

class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

print(to_dict(User("Ada", 36)))   # {'name': 'Ada', 'age': 36}
```

`to_dict` works for *any* object — `User`, `Product`, anything you invent later. That's the flexibility win. But every call pays for the live inspection (`vars`, `getattr`), and a typo in a field name only fails when that code path runs.

### Runtime approach (Java reflection, sketch)

```java
String toJson(Object obj) throws Exception {
    StringBuilder sb = new StringBuilder("{");
    // RUN TIME: ask the object's class what fields it has.
    for (Field f : obj.getClass().getDeclaredFields()) {
        f.setAccessible(true);
        sb.append('"').append(f.getName()).append("\":")
          .append(f.get(obj)).append(',');
    }
    return sb.append('}').toString();
}
```

Flexible (works on any class), but `getDeclaredFields()` and `f.get(obj)` run on *every* call, and this is the kind of code that GraalVM native-image complains about because it can't see, at build time, which fields will be reflected on.

### Compile-time approach (Rust derive)

```rust
use serde::Serialize;          // serde generates the code at COMPILE TIME

#[derive(Serialize)]           // <- this macro writes a custom serializer
struct User {
    name: String,
    age: u32,
}

fn main() {
    let u = User { name: "Ada".into(), age: 36 };
    // No reflection at run time. The serializer for User was generated
    // during the build and is plain, inlinable code.
    println!("{}", serde_json::to_string(&u).unwrap());  // {"name":"Ada","age":36}
}
```

`#[derive(Serialize)]` runs a macro **at compile time** that writes a `User`-specific serializer. At run time there's no inspection — just straight-line code. Fast, AOT-friendly, and if `User` had an unserializable field you'd hear about it *at build time*.

### Compile-time approach (Go code generation, sketch)

```go
//go:generate gen-serializers ./...

// A build step reads this struct and GENERATES a file user_json.go
// containing a hand-written-quality function:
//
//   func (u User) MarshalJSON() ([]byte, error) {
//       return []byte(`{"name":"` + u.Name + `","age":` + strconv.Itoa(u.Age) + `}`), nil
//   }
//
// At run time, MarshalJSON is just normal, fast code — no reflection.

type User struct {
    Name string
    Age  int
}
```

The generator runs during the build (`go generate`). The shipped binary contains plain code. Contrast with Go's standard `encoding/json`, which uses reflection at run time — simpler to use, but slower and reflection-based.

### Seeing the trade-off side by side

```text
SERIALIZE A USER

 Runtime (reflection)            Compile-time (derive / codegen)
 ─────────────────────           ───────────────────────────────
 + Works on any type,            + Zero per-call overhead
   even ones added later         + Errors caught at build
 + No build step / codegen       + Native-image friendly
 - Per-call inspection cost      - Needs a macro/generator
 - Typos fail in production      - Frozen: only the types you
 - Native-image needs config       built for are supported
```

---

## Coding Patterns

### Pattern 1: Prefer compile-time when the answer is known at build time

If you can answer a question during the build, do it then. Don't reflect at run time to discover a field set you already knew when you wrote the type.

### Pattern 2: Reach for runtime only at the genuine "late" boundary

Use reflection/dynamic dispatch exactly where new information arrives late — at the plugin boundary, the config-driven boundary, the user-script boundary — and keep everything inside that boundary compile-time and fast.

### Pattern 3: Generate, then ship plain code

The codegen pattern: a build step writes ordinary source, which compiles normally. You get build-time work and runtime simplicity. The generated file is real code you can read.

### Pattern 4: Cache the result of reflection

If you must use reflection, do the expensive inspection **once** (e.g. at startup) and cache a fast plan, instead of re-inspecting on every operation. This is "runtime, but pay-once-ish" — a common middle ground.

### Pattern 5: Check what your deploy target requires

Before choosing, ask: *are we deploying to native-image / a trimmed bundle / a serverless cold-start-sensitive environment?* If yes, that pressure pushes you toward compile-time before any other consideration.

---

## Best Practices

- **Default to compile-time for fixed, known structure.** It's faster, safer, and AOT-friendly. Use runtime where you actually need late flexibility.
- **Put runtime dynamism behind a clear boundary.** Don't sprinkle reflection everywhere; confine it to the plugin/config edge.
- **Don't reflect on every call.** If you use reflection, build a plan once and reuse it.
- **Let the deploy target drive the choice.** Native-image or serverless cold-start concerns can override "it was easier to use reflection."
- **Read the generated code.** A big advantage of compile-time is that the output is real — open it, step through it, understand it.
- **Pick libraries by *where their meta-level runs*, not by name.** "Fast" and "native-friendly" almost always means compile-time; "flexible" and "dynamic" almost always means runtime.
- **Measure before assuming.** For a cold, low-volume path, runtime reflection's overhead may be irrelevant — don't over-engineer codegen for something called twice a day.

---

## Edge Cases & Pitfalls

- **"It works on my JVM" but breaks in native-image.** Reflection-based code compiles and runs fine in normal mode, then fails after a native-image build because the toolchain didn't know which classes you'd reflect on. A classic surprise.
- **The typo that compiles.** `getMethod("getNmae")` (misspelled) compiles fine and throws only when that line runs — possibly months later, in production.
- **Slow cold starts you didn't expect.** A small reflective framework can add seconds to boot by scanning classes — invisible on a long-running server, painful on serverless.
- **Generated-code bloat.** Codegen and template instantiation can multiply binary size (a serializer per type, a template per type combination). Compile-time isn't "free"; it spends *build time* and *binary size*.
- **Frozen-at-build means no plugins.** A compile-time-only design literally cannot accept a plugin discovered at run time. If your requirement is "load behavior we didn't compile against," compile-time is the wrong tool.
- **Treating the GIL/JIT/optimizer as magic.** Beginners assume "the runtime will optimize my reflection away." It usually can't — reflective calls are opaque to the optimizer.
- **Forgetting builds get slower.** Heavy compile-time metaprogramming (big macros, lots of codegen) can make builds painfully slow. You moved the cost, you didn't delete it.

---

## Apply it

1. Choose one small, known input for **Compile-Time vs Runtime Trade-offs**.
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

- What problem does Compile-Time vs Runtime Trade-offs solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
