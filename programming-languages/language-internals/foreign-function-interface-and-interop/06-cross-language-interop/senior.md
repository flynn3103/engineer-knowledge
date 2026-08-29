# Cross-Language Interop — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Cross-Language Interop** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Shared-Runtime Interop: Solve the ABI by Not Having Two ABIs

The JVM and CLR make interop almost disappear by a simple trick: **don't let the languages have separate ABIs at all.** Kotlin and Scala don't compile to native code with their own calling conventions — they compile to **JVM bytecode**, the same target Java uses. At runtime there is one heap, one object model, one GC, one exception mechanism. A Scala `List` *is* a JVM object a Kotlin or Java method can hold directly. No marshalling, no serialization, no flattening. Calling Java from Kotlin is just a method call.

.NET does the same through the **CLI/CTS**: C#, F#, and VB.NET all compile to CIL (Common Intermediate Language) and obey one Common Type System, so a class defined in F# is a first-class type in C#. The platform *is* the interop layer.

The cost is buy-in: every participating language must target that runtime and accept its object model and GC. You cannot bring an arbitrary native language into the JVM heap. But within the family, interop is the cheapest it ever gets.

### 2. GraalVM/Truffle: Polyglot in One Engine

GraalVM generalizes the shared-runtime idea beyond a single bytecode. With **Truffle**, language interpreters are written so the Graal JIT can optimize them, and a shared **interop protocol** lets a JavaScript object be read by Python, a Java method be called from Ruby, or a value flow between R and LLVM-compiled C. The languages keep their own semantics but exchange objects through a common message protocol (read member, execute, get array element). The result is multiple languages in **one process, one heap**, sharing live objects — without each pair needing a hand-written binding.

The trade-off is that you're committing to the GraalVM engine, and peak performance and language completeness vary by guest language. But conceptually it's the most ambitious "shared types, shared GC" interop available today outside a single bytecode family.

### 3. WebAssembly Core: A Neutral, Sandboxed Compilation Target

Core Wasm is deliberately minimal: a portable stack machine with four numeric types and a **linear memory** (one flat byte array). Dozens of languages — C, C++, Rust, Go, C#, Swift — can compile to it. It is **sandboxed** (a module can only touch its own linear memory and the imports it's explicitly given) and **portable** (the same `.wasm` runs anywhere there's a runtime).

But core Wasm has the *same old interop problem in a new place*: to pass a string between two modules, you must agree on how to lay it out in linear memory (pointer + length? null-terminated? which encoding?). At the core level, that agreement is unspecified — you're back to hand-rolling an ABI, just inside the sandbox. This is exactly what the Component Model fixes.

### 4. The Component Model + WIT: A Shared IDL That Solves the ABI

The **Component Model** layers language-neutral, richly typed interfaces on top of core modules, and **WIT** is its IDL. You write an interface once:

```wit
// calculator.wit
package example:calc;

interface calculator {
    record point { x: f64, y: f64 }
    add: func(a: s64, b: s64) -> s64;
    distance: func(p1: point, p2: point) -> f64;
    parse: func(text: string) -> result<s64, string>;
}
```

Any language with a Component Model toolchain can **implement** this interface (producing a component) or **consume** it. The toolchain knows how to **lower** a guest language's native string/record/list into the **canonical ABI** representation in linear memory and **lift** it back on the other side. Crucially, the canonical ABI is *specified and stable* — it is the standardized solution to the very ABI problem that makes C++ interop miserable. Two components written in Rust and Python compose because both speak WIT through the same canonical ABI, not because they share a heap.

The conceptual leap: **the Component Model is in-process interop where the "lingua franca" is a modern, rich, ABI-stable IDL instead of the lowest-common-denominator C ABI.** It's the C-ABI lingua-franca idea, redesigned with strings, lists, variants, and a proper ownership story (`resource`).

### 5. WASI and Capability-Based Access

A sandboxed component can do nothing by default — it can't open files or sockets. **WASI** provides those capabilities, but in a **capability-based** way: the host explicitly grants a component a preopened directory, a clock, a socket. There is no ambient authority. This makes Wasm components a strong substrate for running untrusted or third-party code in-process: you get near-native speed *and* isolation, the combination that in-process FFI famously cannot offer.

### 6. Object/Component Systems: COM and Its Descendants

Long before Wasm, **COM** solved cross-language objects on Windows with a *binary* standard. A COM object exposes one or more **interfaces**, each laid out as a **vtable** (a table of function pointers) with a fixed, agreed binary shape. Every interface derives from **IUnknown**, which provides `QueryInterface` (ask an object "do you support interface X?") and **reference counting** via `AddRef`/`Release`. Because the contract is the *vtable layout plus IUnknown*, any language that can call through a vtable and respect the refcount can use a COM object — C++, C#, VB, Delphi, scripting languages. **WinRT** is the metadata-rich modern evolution. **.NET COM interop** bridges managed code to COM via runtime callable wrappers. On Apple platforms, the dynamic **Objective-C runtime** plays a similar bridging role for Swift↔Objective-C.

The enduring lesson from COM: **a binary-stable interface contract (vtable + identity + lifetime protocol) lets arbitrary languages share objects** — which is exactly what the Component Model's `resource` and canonical ABI re-derive with modern, portable, sandboxed semantics.

### 7. The Decision Framework

Place every approach on one axis from *fastest/most-coupled* to *slowest/most-isolated*:

```text
  In-process C-FFI     Polyglot VM         Wasm component        RPC / IPC
  ───────────────      ───────────────     ───────────────       ───────────────
  fastest call          shared GC & types   sandboxed, portable   isolated, slow
  zero isolation        zero isolation*     strong isolation       strong isolation
  ABI fragility         runtime lock-in     stable canonical ABI   schema + network
  native code           same-runtime langs  many langs → Wasm      any langs, any host
```

(*polyglot VMs isolate languages logically but still share one process/heap, so a VM crash takes everyone down.)

Decision questions, in order:
1. **Do the languages already share a runtime** (all JVM, all .NET)? Use the shared-runtime interop — it's nearly free.
2. **Do you need maximum call throughput with native code and accept fragility/coupling**? Raw FFI (flatten C++ to C).
3. **Do you need many languages, in-process speed, *and* sandboxed isolation/portability**? Wasm components — the emerging answer.
4. **Do you need fault isolation, independent deploy/scale, or a cross-machine boundary**? RPC/IPC, accept the latency.

The senior skill is recognizing which question dominates for *this* system, and not defaulting to whatever the team used last time.

---

## Code Examples

### Shared-runtime interop: Kotlin calling Java, no marshalling

```java
// Greeter.java
public class Greeter {
    public String greet(String name) { return "Hello, " + name; }
}
```

```kotlin
// Main.kt — different language, SAME JVM heap and types
fun main() {
    val g = Greeter()                 // a real Java object on the JVM heap
    println(g.greet("Ada"))           // direct virtual call — no FFI, no copy
}
```

There is no boundary code at all. `Greeter` is a JVM object; Kotlin holds it directly and dispatches a method. The "interop" is invisible because there is only one runtime, one object model, one GC.

### .NET: F# type consumed from C#, sharing the CTS

```fsharp
// Library.fs
namespace Shared
type Point = { X: float; Y: float }
module Geometry =
    let distance (a: Point) (b: Point) =
        sqrt ((a.X - b.X) ** 2.0 + (a.Y - b.Y) ** 2.0)
```

```csharp
// Program.cs — C# uses the F#-defined type as a first-class CTS type
using Shared;
var a = new Point(0.0, 0.0);
var b = new Point(3.0, 4.0);
Console.WriteLine(Geometry.distance(a, b)); // 5 — one type system, no glue
```

### WebAssembly Component Model: one WIT, two languages compose

The shared interface:

```wit
// adder.wit
package demo:adder;
world adder {
    export add: func(a: s32, b: s32) -> s32;
}
```

A Rust component *implements* it (sketch using the standard binding macro):

```rust
wit_bindgen::generate!({ world: "adder" });
struct Component;
impl Guest for Component {
    fn add(a: i32, b: i32) -> i32 { a + b }
}
export!(Component);
```

A different host or component — written in, say, Python or JavaScript — *consumes* the same component through the same WIT, and the toolchain lifts/lowers the values across the canonical ABI. Neither side knows or cares what language the other is; the WIT contract and canonical ABI are the entire agreement. Pass a `string` or a `list<u8>` instead of an `s32` and the toolchain still handles the layout — the thing core Wasm could not do by itself.

### COM in spirit: an interface contract any language can call

```c
// IUnknown-shaped vtable: identity + lifetime + methods, binary-stable layout
struct ICalcVtbl {
    HRESULT (*QueryInterface)(ICalc*, REFIID, void**);
    ULONG   (*AddRef)(ICalc*);
    ULONG   (*Release)(ICalc*);          // refcounting lifetime
    HRESULT (*Add)(ICalc*, int a, int b, int* out);  // the actual method
};
struct ICalc { struct ICalcVtbl* lpVtbl; };
```

Any language that can call through this vtable and honor `AddRef`/`Release` can use the object — that's how a VB script and a C++ app used the same COM component for decades. The refcount is the cross-language lifetime contract; forgetting a `Release` (or one too many) is the canonical COM leak/crash.

---

## Coding Patterns

### Pattern 1: Prefer shared-runtime when the family already fits

If every language involved already targets the JVM or CLR, the correct "interop strategy" is *no interop layer at all* — just call methods. Don't add FFI or RPC where shared types already exist.

### Pattern 2: WIT-first design for Wasm composition

Write the WIT interface before the implementation, exactly as you'd write a `.proto` before a gRPC service. The interface — records, variants, `result<T,E>`, `resource` handles — is the durable contract; implementations in any language follow.

### Pattern 3: Model owned objects as WIT `resource`s, not raw pointers

The Component Model's `resource` is the principled successor to the opaque `void*` handle: it carries ownership and lifetime semantics across the boundary, so the toolchain — not hand-written discipline — enforces "freed exactly once."

### Pattern 4: Grant capabilities explicitly (WASI)

Never assume ambient authority for a component. Pass exactly the directory, socket, or clock it needs. This turns "run third-party code" from a risk into a bounded, auditable grant.

### Pattern 5: Treat the spectrum as a dial you set per boundary

Different boundaries in one system can sit at different points: a hot inner loop in-process via FFI, a plugin surface via Wasm, a cross-team edge via RPC. Don't force one mechanism on every boundary.

---

## Best Practices

- **Match the mechanism to the dominant constraint** (speed, isolation, portability, team boundaries) — not to habit.
- **Use shared-runtime interop wherever the languages already share a runtime.** It is strictly the cheapest correct option there.
- **Design Wasm interfaces in WIT first** and let the canonical ABI carry rich types; don't hand-roll layouts in linear memory.
- **Lean on capability-based isolation** for untrusted code: Wasm + WASI gives you in-process speed with a sandbox.
- **Respect lifetime contracts** whatever the model — COM refcounts, WIT resources, FFI handles. Lifetime is where cross-language object interop breaks.
- **Keep boundaries narrow and rich-typed where the model allows it.** WIT and the Component Model let you pass real strings/lists/records — use that instead of flattening everything to bytes by hand.
- **Document the crash domain.** Be explicit that polyglot-VM and FFI boundaries share a process (one crash kills all), while RPC and sandboxed components do not.
- **Plan for the maturity gap.** The Component Model is powerful but young; verify your target languages' toolchains support the WIT features you need before committing.

---

## Edge Cases & Pitfalls

- **Assuming polyglot VMs give isolation.** They share types and a GC — and a *process*. A native crash or `OutOfMemoryError` takes down every language at once. Logical interop ≠ fault isolation.
- **GC cycles across runtime boundaries.** When two GCs (or a GC and a refcount) reference each other's objects, neither can prove the cycle is dead; you get leaks. Polyglot and FFI boundaries both hit this.
- **Treating core Wasm as if it solved interop.** Core Wasm only standardizes the *numeric* boundary; passing a string between two core modules still requires an agreed linear-memory layout. The Component Model is what actually solves it.
- **WIT/canonical-ABI version skew.** A component built against one version of the interface or ABI may not compose with another; the ecosystem is still stabilizing. Pin versions.
- **COM refcount leaks and over-releases.** One missing `Release` leaks the object forever; one extra `Release` frees it early and crashes other holders. The classic, still-common COM bug class.
- **`QueryInterface` returning an interface you forgot to `Release`.** Every interface pointer obtained is a new reference you own and must release.
- **Objective-C/Swift bridging surprises.** Bridged types (e.g., `NSString` ↔ `String`) may copy or share depending on context; assuming one or the other causes subtle bugs.
- **Lift/lower cost ignored.** The Component Model isn't free — large records and lists are copied across the canonical ABI. For ultra-hot paths, even this can matter; measure.
- **Capability over-granting in WASI.** Handing a component a whole filesystem root "to be safe" defeats the sandbox. Grant the minimum.
- **Choosing a polyglot VM for languages that don't really fit it.** Forcing a native-heavy or systems language into a managed polyglot engine can cost more than a clean RPC or FFI boundary. The shared-runtime advantage only applies to languages that genuinely target the runtime.

---

## Apply it

1. State the system invariant that **Cross-Language Interop** must protect.
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

- Which invariant must remain true when Cross-Language Interop fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
