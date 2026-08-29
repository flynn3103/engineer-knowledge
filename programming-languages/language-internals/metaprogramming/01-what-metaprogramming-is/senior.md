# What Metaprogramming Is — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **What Metaprogramming Is** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Staging Is the Master Concept

At senior level, stop thinking "compile-time or runtime" as a binary and start thinking of the **full stage chain** and how *a single feature flows across it*. A `#[derive(Serialize)]` is not "compile-time metaprogramming" — it is a value that originates at read-time (the attribute), is consumed at macro-expansion (proc-macro emits an `impl`), is checked at type-check, is specialized at monomorphization, and is finally executed at runtime. Each stage is an opportunity for power *and* a place where errors can surface confusingly.

The senior questions are:

- **At which stage does each piece of meta-work belong?** (The earliest stage that has the necessary information.)
- **How many stages does the value cross, and is the provenance preserved across them?** (Can a runtime error point back to the human source?)
- **What is the cost at each stage?** (Build time, binary size, startup time, per-call time.)

Mastering staging is mastering metaprogramming. Everything else is detail.

### 2. The Power/Comprehensibility Trade Is a Budget, Not a Switch

The field's defining tension: metaprogramming buys **generative power and DRY-ness**; it spends **comprehensibility, debuggability, and tooling**. Crucially, this is not a one-time decision — it's a *budget* that depletes as you add magic:

- The first derive macro is pure win. The fiftieth bespoke proc-macro in a codebase is a maintenance tax.
- One well-known framework's reflection is fine (everyone understands Spring). A homegrown reflective DI container is a liability nobody but its author can debug.

Seniors allocate this budget. A useful framing: **every unit of metaprogramming should buy more than it costs, where "cost" is measured in the comprehension of the *least experienced person who will maintain it*, not the author.** Cleverness that only the author understands is debt, not equity.

### 3. Closed-World vs Open-World Decides the Technique

A deep architectural fork:

- **Closed-world:** the full set of types and usages is known at build time. This *enables* code generation, AOT compilation, monomorphization, and whole-program optimization. Rust, C++, and AOT-compiled Java (GraalVM native-image) live here. Metaprogramming can be pushed early and the runtime pays nothing.
- **Open-world:** new types/plugins/classes appear at runtime. This *forces* reflection and dynamic dispatch, because you cannot generate code for types you haven't seen. JVM with dynamic class loading, Python, and plugin architectures live here.

Many real systems are mostly closed with open edges. The senior move is to *minimize the open-world surface*: do as much as possible at build time (closed), and confine runtime reflection to the genuinely dynamic boundary (plugin loading, deserialization of unknown shapes). This is why "reflection-config" files exist — they re-close a partially-open world for an AOT optimizer.

### 4. How Real Frameworks Compose Techniques

No serious framework uses one technique; they *compose* them across stages. Reading a framework is reading its staging:

- **Spring (Java):** annotations (data) + classpath scanning via reflection (runtime discovery) + dynamic proxies / bytecode generation (runtime intercession for transactions, AOP) + increasingly, annotation processing and AOT for native images (shifting work earlier). The same `@Transactional` is processed differently depending on the deployment target's stage budget.
- **Hibernate (Java):** annotations/XML mapping + runtime reflection to read/write fields + proxies for lazy loading + bytecode enhancement (build- or load-time) to instrument entities.
- **serde (Rust):** `#[derive]` proc-macros generate `Serialize`/`Deserialize` impls at compile time → fully closed-world, zero runtime reflection, monomorphized per type. The *entire* serialization decision is made before the program runs.
- **Django / Rails:** metaclasses and dynamic method generation at class-creation time (runtime) build models, query APIs, and admin interfaces from declarations. Open-world and gloriously dynamic.
- **gRPC / protobuf:** schema → build-time code generation of typed stubs. Closed-world, visible, checked-in (or build-step) artifacts.
- **Mocking libraries:** runtime proxies / bytecode generation to synthesize stand-ins.

The pattern: **the framework absorbs the metaprogramming so its users only see a declaration.** Senior framework authors carry the staging complexity so application authors don't have to. Senior application authors, in turn, choose frameworks partly by *which stage* they do their magic at, because that dictates startup time, native-image compatibility, and debuggability.

### 5. Reflection vs AOT: The Modern Battleground

The most consequential current tension in mainstream metaprogramming is **runtime reflection vs ahead-of-time compilation**. Reflection assumes an open world and a JIT; AOT (GraalVM native-image, Go's static binaries, Rust) assumes a closed world and strips everything unreached. They collide:

- Code reached *only by reflection* (by string name) looks "unused" to an AOT optimizer and gets stripped → `ClassNotFoundException`/`NoSuchMethodError` in production, not in dev.
- The industry's response is to *shift metaprogramming earlier*: Spring's AOT engine, Quarkus, and Micronaut do at *build time* (via annotation processing and codegen) what classic Spring did via runtime reflection — precisely to be native-image-friendly and start in milliseconds.

A senior must know: **runtime reflection is in tension with AOT, fast startup, and small binaries, and the modern trend is to move metaprogramming from runtime to build time.** When you choose a reflection-heavy approach, you are implicitly choosing a JIT-and-warm-up runtime model.

### 6. Multi-Stage Programming and Monomorphization as Disciplined Generation

Generics-via-monomorphization (Rust, C++) are metaprogramming whether or not the language calls it that: the compiler *generates a specialized copy of code per concrete type*. This is principled, type-checked, hygienic code generation — the safe end of the generative spectrum. Contrast with `eval` (the unsafe end: arbitrary code from a string at runtime, no checking). Most of the senior's job is to keep generation as far toward the *monomorphization/derive* end and as far from the *eval/monkeypatch* end as the problem allows — i.e., **prefer generation that is staged early, hygienic, and type-checked over generation that is late, unhygienic, and unchecked.**

### 7. Provenance: The Debuggability Dimension

The single biggest practical cost of metaprogramming is *lost provenance*: when generated/expanded/proxied code fails, can you trace it back to the human source? Mature systems invest heavily here:

- Rust proc-macros can attach spans so errors point at your code, not the expansion.
- Source maps map transpiled JS back to TypeScript.
- Checked-in generated code gives real file/line numbers in stack traces.
- Java's bytecode enhancement preserves line tables.

When provenance is preserved, metaprogramming's debuggability cost is bounded. When it isn't — a stack trace into anonymous proxy `$Proxy17.run()` with no source — the cost is unbounded. **A senior evaluates a metaprogramming technique partly by how well it preserves provenance**, and refuses techniques that don't where the team can't absorb the debugging cost.

---

## Code Examples

These illustrate *senior-level decisions*: choosing the stage, preserving provenance, minimizing the open-world surface.

### Rust — Staging Made Explicit: `derive` (compile) vs runtime `Any` (open-world escape hatch)

```rust
use std::any::Any;

// CLOSED-WORLD, compile-time generation: serde-style derive (sketch).
// All serialization code exists before runtime; zero reflection.
#[derive(Debug, Clone)]
struct Config { retries: u32 }

// OPEN-WORLD escape hatch: runtime type inspection via `Any`.
// Use ONLY at the dynamic boundary (plugin registry), never in hot paths.
fn handle(obj: &dyn Any) {
    if let Some(c) = obj.downcast_ref::<Config>() {
        println!("got Config with retries={}", c.retries);
    } else {
        println!("unknown type at the dynamic boundary");
    }
}

fn main() {
    let c = Config { retries: 3 };
    println!("{:?}", c.clone());   // generated Debug + Clone, compile-time
    handle(&c);                    // runtime inspection, confined to the boundary
}
```

The senior point: Rust offers both ends of the spectrum. `#[derive]` is closed-world, compile-time, zero-cost. `dyn Any` is the open-world escape hatch — reserved for the genuinely dynamic edge. Confining `Any` to the boundary keeps the world *mostly closed*.

### Java — The AOT/Reflection Collision (and the keep-rule that fixes it)

```java
// This works under a JIT but BREAKS under native-image / aggressive R8:
// the class is reached only by NAME, so the optimizer thinks it's dead.
Class<?> handler = Class.forName(configValue);     // "com.acme.PaymentHandler"
Object instance = handler.getDeclaredConstructor().newInstance();
```

```json
// reflect-config.json — re-closes the world for the AOT compiler:
[
  {
    "name": "com.acme.PaymentHandler",
    "allDeclaredConstructors": true,
    "allDeclaredMethods": true
  }
]
```

The senior lesson made concrete: **reflection by string name is invisible to closed-world optimizers.** Either supply reflection-config (re-close the world) or — better — replace the reflective lookup with build-time code generation so no keep-rule is needed at all. The modern Spring/Quarkus/Micronaut answer is the latter.

### Python — Intercession with a Capability Boundary

```python
# Monkeypatching is maximal capability (action at a distance).
# A senior confines it: scoped, documented, reversible.
import contextlib

@contextlib.contextmanager
def patched(obj, name, replacement):
    original = getattr(obj, name)
    setattr(obj, name, replacement)
    try:
        yield
    finally:
        setattr(obj, name, original)   # provenance + reversibility

class Clock:
    def now(self): return "real-time"

c = Clock()
with patched(Clock, "now", lambda self: "frozen-time"):
    print(c.now())   # frozen-time  -- only inside this scope
print(c.now())       # real-time    -- restored
```

Python *permits* unrestricted intercession; a senior *constrains* it — scoped, reversible, and explicit — so the action-at-a-distance is bounded and auditable. The contrast with an unscoped, permanent monkeypatch (which silently changes behavior program-wide forever) is the whole point.

### Go — Codegen Over Reflection in the Hot Path

```go
// reflect-based generic encoder: flexible, OPEN-WORLD, but SLOW per call.
func encodeReflect(v any) []byte { /* walks reflect.Value every call */ ; return nil }

//go:generate encoder-gen -type=Order
// generated Order_encode.go: a specialized, allocation-free encoder.
// Same input, work moved from RUNTIME (reflect) to BUILD (codegen).
func (o Order) Encode() []byte { /* generated, no reflection */ ; return nil }
```

Go's idiom encodes the senior trade-off into the language's tooling: reflection for flexibility at the boundary, `go generate` to *shift* the hot-path cost to build time and recover speed with code you can read and step through.

### Java — Proxy Self-Invocation Trap (a staging/semantics edge)

```java
@Service
class Billing {
    @Transactional
    public void charge() { doWork(); }     // proxy wraps charge() — OK

    @Transactional
    public void doWork() { /* ... */ }     // self-call below BYPASSES the proxy
}
// Calling billing.charge() runs doWork() via `this`, NOT through the proxy,
// so doWork()'s @Transactional is silently ignored.
```

A senior must know *why*: the proxy intercepts external calls, but `this.doWork()` is an internal call on the real object, not the proxy. This is a direct consequence of intercession-via-proxy being a runtime wrapper rather than a true language construct — a structural limitation, not a bug, and one you only avoid by understanding the mechanism.

---

## Coding Patterns

### Pattern 1: Stage-first design

Before choosing reflection vs codegen vs macro, decide the *stage*: what's the earliest point that has the information? Then pick the technique that fits that stage. Reversing this (picking a technique, then living with its stage) is how teams end up with runtime reflection where build-time codegen belonged.

### Pattern 2: Minimize the open-world surface

Architect so the world is closed by default and open only at explicit, small boundaries (plugin loader, deserializer of unknown shapes). Everything inside the boundary can be generated/monomorphized/AOT-compiled. This pattern is what makes a codebase native-image-ready and fast-starting.

### Pattern 3: Engineer provenance deliberately

For any generation/expansion, ensure errors point back to human source: proper macro spans, source maps, checked-in generated files with real line tables. Treat provenance as a feature, not an afterthought — it caps your debugging cost.

### Pattern 4: Grant minimum capability

Pick the *least powerful* mechanism that works: introspection over intercession, derive over `eval`, scoped patch over global monkeypatch. Smallest blast radius wins on both security and maintainability.

### Pattern 5: Make the magic legible

Where metaprogramming changes behavior, leave a trail: a documented annotation reader, a comment naming the metaclass/proxy, a `// generated by X — do not edit` header. The reader cannot see the mechanism; tell them.

### Pattern 6: Budget the cleverness against the maintainer

Calibrate every metaprogramming decision to the comprehension of the *least experienced maintainer*, not the author. If only you can debug it, it's debt.

---

## Best Practices

- **Decide stage and capability before technique.** These two choices drive performance, safety, AOT-compatibility, and blast radius; the technique is downstream.
- **Push work upstream.** Run metaprogramming at the earliest stage with sufficient information. Move downstream only for genuinely runtime-only data.
- **Keep the world closed; open it only at named boundaries.** This preserves AOT, monomorphization, and fast startup, and confines reflection to where it's unavoidable.
- **Treat runtime reflection as in tension with AOT.** If you depend on it, own the keep-rules/reflection-config and the warm-up cost — or migrate it to build time.
- **Preserve provenance.** No metaprogramming technique earns its place if its failures can't be traced to source the maintainer can read.
- **Prefer hygienic, type-checked generation** (derive, monomorphization, syntactic macros) over unhygienic/unchecked generation (textual macros, `eval`).
- **Constrain intercession.** Scope it, make it reversible, document it. Unbounded action-at-a-distance is a team-scale hazard.
- **Spend the comprehensibility budget consciously.** Each construct must buy more than it costs *for the maintainer*. When it doesn't, write the boring code.
- **Read frameworks by their staging.** Choose dependencies partly on *where* they do their magic, because that dictates startup, native-image fit, and debuggability.

---

## Edge Cases & Pitfalls

- **Reflection stripped by AOT/tree-shaking.** Code reached only by name is "dead" to closed-world optimizers. Symptom: works in dev (JIT), `NoSuchMethod`/`ClassNotFound` in native/optimized prod. Fix: keep-rules or, better, build-time codegen.
- **Proxy self-invocation.** Internal `this.method()` calls bypass the proxy, silently disabling `@Transactional`/advice on the inner call. A structural property of proxy-based intercession.
- **Compile-time blowup and inscrutable errors.** Heavy TMP / const-eval / generic monomorphization can explode build time, binary size, and error message length. Bound recursion; prefer concepts/`constexpr` to raw TMP.
- **Lost provenance.** A stack trace into `$Proxy17` or an anonymous generated unit with no source mapping makes debugging open-ended. Refuse techniques that can't preserve it where you can't afford the cost.
- **Generator ordering / build-graph hazards.** When one generator's output feeds another, unordered builds are flaky. Make inter-generator dependencies explicit in the build graph.
- **Open-world creep.** A codebase that's "mostly closed" but reflects "just here and there" can't be AOT-compiled and starts slowly. The open surface must be a *deliberate, small boundary*, not scattered.
- **Capability inflation.** Reaching for `eval`/monkeypatching where introspection/derive suffices grants far more capability than the problem needs — a security and maintainability liability.
- **Versioned generated code drift.** Generated artifacts checked in but not regenerated diverge from their source schema/macro; CI must verify regeneration matches.
- **Metaprogramming-induced coupling.** A central macro/metaclass that every type depends on becomes a chokepoint: one change reverberates everywhere, and it's a single point of failure for both builds and understanding.

---

## Apply it

1. State the system invariant that **What Metaprogramming Is** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when What Metaprogramming Is fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
