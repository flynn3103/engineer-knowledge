# Build-Time Code Generation — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Build-Time Code Generation** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Triangle: Codegen vs Macros vs Reflection

Three routes to "describe once, derive the boilerplate." They sit at different points in the compile/run timeline:

```text
   describe once
        │
        ├── REFLECTION ───── work happens at RUNTIME
        │      • inspects types by name as the program runs
        │      • no separate artifact; nothing to commit
        │      • NOT statically checked; errors at runtime
        │      • breaks AOT/native-image (closed-world)
        │      • cost: per-call runtime introspection
        │
        ├── MACROS ───────── work happens INSIDE THE COMPILER
        │      • transforms AST/tokens during compilation
        │      • no separate files (output is ephemeral)
        │      • statically checked; errors at compile time
        │      • AOT-friendly (output is real code)
        │      • cost: compile time; output hard to inspect
        │
        └── CODE GENERATION ─ work happens at BUILD TIME (before compile)
               • emits real source files on disk
               • files are inspectable, debuggable, autocompletable
               • statically checked; errors at compile time
               • AOT-friendly (it is ordinary code)
               • cost: build plumbing, diff noise, regeneration discipline
```

**Decision criteria:**

| Criterion | Prefer codegen | Prefer macro | Prefer reflection |
|------|------|------|------|
| Must the generated code be *inspectable/debuggable*? | ✔ (real files) | ✘ (ephemeral) | ✘ |
| AOT / native image target? | ✔ | ✔ | ✘ (needs config) |
| Cross-language artifact from one source? | ✔ (IDL) | ✘ (language-bound) | ✘ |
| Zero build plumbing, fully dynamic, plugin-discovery? | ✘ | ✘ | ✔ |
| Tightest integration with the language's syntax? | ✘ | ✔ | – |
| Runtime cost must be zero? | ✔ | ✔ | ✘ |

The senior summary: **reflection is the most flexible and the most expensive and the least safe; macros are the most language-integrated but the least inspectable; codegen is the most operationally visible (real files, real diffs) at the cost of build plumbing.** Most cross-language, AOT-targeted systems land on codegen.

### 2. Rust `derive` — the Boundary Case

`#[derive(Serialize, Deserialize)]` (serde) is *macros that do codegen*. A procedural macro is a compiled program that reads your struct's token stream and emits trait `impl` blocks at compile time. It has the macro's tight syntactic integration and AOT-friendliness, but the *output is ephemeral* — you cannot open a file to read it (you need `cargo expand` to see it). Compare to `build.rs` + `prost`, which writes a real `.rs` file to `OUT_DIR` you *can* open. Same goal (serialization without hand-writing), different point on the macro↔codegen continuum: derive favors integration, `build.rs` favors inspectability and cross-language schemas. Knowing *why* serde uses derive (it is language-internal, no external schema) but gRPC uses `build.rs` codegen (the `.proto` is the cross-language source of truth) is the senior distinction.

### 3. Why Codegen Beats Reflection for AOT / Native Image

This is the strongest modern argument for codegen. AOT compilers (GraalVM native image, Go's compiler, Dart AOT) assume a **closed world**: every reachable type and method must be statically known. Reflection violates this — "look up the field named `email` at runtime" cannot be resolved at build time, so you must hand-write `reflect-config.json` enumerating every reflectively-accessed member, and miss one and you get a `ClassNotFoundException` in production. Generated code has *no reflection*: the access is compiled into ordinary field reads the AOT compiler sees and includes. This is precisely why Dagger (generated DI) is native-image-friendly while classic Spring (reflective DI) needs extensive configuration, and why protobuf's generated codecs work in native images where a reflective serializer would need per-type config.

### 4. Schema Evolution — The Decade-Long Problem

A schema is the source of truth *over time*, with old and new code coexisting on the wire. Protobuf's design encodes the rules:

- **Field numbers are the contract, not names.** The wire encodes field *numbers*. Renaming `email` → `email_address` is wire-compatible (cosmetic); changing its number from `3` to `4` is a *break* — old readers look for `3` and find nothing, new data under `4` is ignored as unknown.
- **Adding a field is safe** if it gets a *new* number. Old readers ignore unknown fields (preserving them on re-serialize, in proto3); new readers see a default for absent fields.
- **Deleting a field requires `reserved`.** Mark the number (and name) `reserved` so it is never reused. Reuse a deleted number for a different type and you get silent data corruption when old messages arrive.
- **Type changes are mostly breaks.** `int32`↔`int64` is sometimes wire-compatible; `string`↔`bytes` is; most others are not. The generator will happily produce code for an incompatible change — the *wire* breaks, not the build.

The senior lesson: **the generator enforces nothing about wire compatibility.** A schema change can compile cleanly and break every deployed client. Compatibility is a discipline (and a linter — `buf breaking`) on top of generation, not a property of it.

### 5. Committed-vs-Gitignored as Architecture

Reframed from `middle.md` as a senior decision with system-wide consequences:

**Commit generated code →** the repo is **self-contained and reproducible without the generator**. CI builds with no toolchain bootstrap; an auditor can read exactly what ships; a five-year-old commit still builds even if the generator is long gone. Cost: every schema change is a two-step (edit + regenerate + commit), reviews carry mechanical diffs, and you need a drift check to enforce freshness. This favors *long-lived, audited, supply-chain-sensitive* codebases.

**Gitignore + regenerate →** the repo is **clean and DRY**, but builds now *depend on the generator being present and pinned*. This is fine when the build already runs the generator hermetically (Bazel, Cargo `build.rs`, Gradle APT). Cost: reproducing an old build requires reproducing the old generator; offline/air-gapped builds get harder; a broken generator release blocks everyone.

The deciding axes are **reproducibility/audit** (favors commit) versus **DRY/clean-repo + hermetic build tooling** (favors gitignore). Note the meta-point: *the more hermetic and reproducible your build system (Bazel), the safer gitignore becomes,* because the build graph itself guarantees the generator version.

### 6. Generator Version Skew Is an Outage Class

When `protoc-gen-go`, the OpenAPI generator, or a Lombok version differs across developers/CI, you get: (a) churning diffs (committed code), (b) divergent runtime behavior (gitignored code), or (c) a build that passes locally and fails in CI. Treat the generator as a **pinned dependency** with the same rigor as the compiler: pin it in a lockfile/`tools.go`/container image, and have CI assert the pinned version. Skew is the single most common operational pain in generated codebases.

### 7. Debugging Through Generated Layers

A stack trace landing in `user.pb.go:1487` or a serde-expanded impl is disorienting. Techniques: keep generated code committed and source-mapped so debuggers can step into it; use `cargo expand`/`-Xprint` to see macro output; keep your logic *out* of generated files so a frame in generated code points at the *generator/schema*, not your bug. The principle: a frame in generated code should redirect you *upstream* to the schema, not invite you to patch downstream.

---

## Code Examples

### Example 1: Protobuf schema evolution done right

```proto
message User {
  uint64 id = 1;
  string name = 2;
  // string email = 3;   <-- removed
  reserved 3;            // never reuse number 3
  reserved "email";      // never reuse the name
  string email_address = 4;  // new field, NEW number
  bool active = 5;           // additive, safe
}
```

Old clients still read `id`/`name` by number; they ignore `4`/`5`; number `3` can never collide. The build would happily compile a *bad* version that reuses `3` — only a breaking-change linter or review catches it.

### Example 2: serde derive (macro-codegen) vs prost (file codegen)

```rust
// Macro-codegen: ephemeral, language-internal, no external schema.
#[derive(serde::Serialize, serde::Deserialize)]
struct User { id: u64, name: String, email: String }
// `cargo expand` to *see* the generated impls — there is no file on disk.
```

```rust
// File-codegen: real .rs in OUT_DIR, from a cross-language .proto.
// build.rs: prost_build::compile_protos(&["user.proto"], &["."]).unwrap();
include!(concat!(env!("OUT_DIR"), "/example.rs")); // you can open this file
```

Same goal; serde favors integration (no schema, no files), prost favors a cross-language schema and inspectable output.

### Example 3: Dagger (codegen DI) vs reflective DI under native image

```java
@Component(modules = AppModule.class)
interface AppComponent { UserService userService(); }
// Dagger's annotation processor generates DaggerAppComponent with explicit
// `new`-call wiring — no reflection — so GraalVM native image needs no DI config.
```

The reflective equivalent (scan classpath, resolve beans by type at startup) requires `reflect-config.json` listing every injected type, and fails at *runtime* if one is missed.

### Example 4: Pinning the generator to kill version skew

```go
//go:build tools
package tools

import (
    _ "google.golang.org/protobuf/cmd/protoc-gen-go"      // version pinned by go.mod
    _ "google.golang.org/grpc/cmd/protoc-gen-go-grpc"
)
```

Now the plugin versions are part of `go.mod`; everyone generates identical output, and CI can assert it.

### Example 5: A breaking-change gate in CI

```yaml
- name: protobuf breaking-change check
  run: buf breaking --against '.git#branch=main'
```

This catches the wire-compatibility violations the *generator never will* — reused field numbers, type changes, field-number changes.

---

## Coding Patterns

**Pattern: Choose the route by constraints, not habit.** AOT target + cross-language → codegen. Language-internal + no schema → macro. Runtime-dynamic + flexibility-over-cost → reflection.

**Pattern: Layer a compatibility linter over schema-driven codegen.** `buf breaking`, OpenAPI diff tools — because the generator cannot enforce wire/API compatibility.

**Pattern: Treat the generator as a first-class, pinned dependency.** Lockfile/`tools.go`/container; CI asserts the version.

**Pattern: Keep logic out of generated files** so a generated-frame in a trace always redirects upstream.

**Pattern: Let build hermeticity drive the commit policy.** Hermetic build (Bazel) → gitignore is safe; non-hermetic → commit for reproducibility.

---

## Best Practices

1. **Decide codegen/macro/reflection by AOT-fitness, cross-language need, and inspectability — explicitly, and write it down.**
2. **Add a wire/API breaking-change gate** on every schema-driven generator.
3. **Pin generator and plugin versions repo-wide; assert them in CI.**
4. **Match commit policy to build hermeticity and audit needs.**
5. **Never reuse protobuf field numbers; `reserved` on every delete.**
6. **Keep generated code free of hand-written logic** for clean debugging.
7. **Prefer KSP over KAPT, derive over reflection, generated DI over reflective DI** when the target is AOT or startup-sensitive.

---

## Edge Cases & Pitfalls

**Reusing a deleted protobuf field number.** Silent, catastrophic: old messages decode garbage into the new field. Always `reserved`. The build will *not* warn you.

**Macro output you cannot see.** A serde/derive bug or a surprising trait impl is invisible until you `cargo expand`. Teams forget the tool exists and burn hours.

**Native-image failure from one missing reflection entry.** A reflective path that "worked in tests" (JIT mode) fails only in the native image. Generated code sidesteps the entire problem.

**Version skew that only manifests in CI.** Local `protoc` is newer; CI's is pinned; the committed code differs; the drift check fails on an "unrelated" PR. Pin everything.

**Gitignored generated code + a yanked generator release.** A bad upstream generator version can block all builds with no committed fallback. Vendoring/committing mitigates.

**Type change that compiles but breaks the wire.** `int32`→`string` regenerates cleanly and shatters every client. Only a compatibility linter catches it.

**Debugging into a 600-line generated frame.** Without source-mapped, committed generated code, the debugger has nothing to step into. Commit + map, or expand.

---

## Apply it

1. State the system invariant that **Build-Time Code Generation** must protect.
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

- Which invariant must remain true when Build-Time Code Generation fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
