# Build-Time Code Generation — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Build-Time Code Generation** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Spectrum: Three Kinds of Generation

The three kinds are best understood by *what is the input* and *who triggers the generator*.

```text
  KIND                INPUT                         TRIGGER                       EXAMPLES
  ─────────────────   ───────────────────────────   ───────────────────────────   ──────────────────────
  Template-based      a template + a data model     you run the templating tool   Mustache, Jinja, T4,
                                                     (often via a script/Make)     Go text/template
  Schema-driven       a formal schema / IDL         a dedicated generator,        protoc, openapi-gen,
                                                     run from build/Make/CI        sqlc, jOOQ, Thrift
  Annotation-driven   annotations on your source    the compiler itself, via      Lombok, Dagger,
                                                     a processor plugin            MapStruct, KSP/KAPT
```

The deeper you go down this list, the more the generation is *integrated* with the language. Template-based generation is language-agnostic glue. Schema-driven generation is a separate compiler for a separate language (the IDL). Annotation-driven generation runs *inside your language's compiler* and reads your actual source.

### 2. Template-Based Generation

The most general technique: a **template** (a string with `{{placeholders}}`) plus a **data model** (a map/struct of values) produces text. The text can be source code, SQL, config, HTML, anything.

```text
   template ("Hello, {{.Name}}")  +  data ({Name: "Ada"})  ──▶  "Hello, Ada"
```

Strengths: total control, no schema required, works for any output. Weaknesses: *you* are responsible for producing valid code — the template engine does not understand the target language, so a missing brace produces broken output the engine cheerfully emits. This is why template-based generation is best for *small, controlled* outputs (a config file, a registry, a switch table) and why dedicated schema-driven generators exist for the heavy cases.

### 3. Schema-Driven Generation

Here the input is a **formal schema** in an IDL, and a **dedicated generator** that *understands that IDL* produces typed code. The generator knows the target language's idioms, so the output is correct by construction.

- **protobuf / gRPC:** `.proto` → `protoc` → message structs (`.pb.go`, `User.java`) and, with the gRPC plugin, client/server stubs from `service` definitions.
- **OpenAPI / Swagger:** an OpenAPI YAML/JSON spec → `openapi-generator` → typed HTTP clients and server scaffolding in dozens of languages.
- **Thrift:** Apache Thrift IDL → typed structs and RPC, similar to protobuf.
- **GraphQL:** an SDL schema → typed resolvers/clients (e.g. `graphql-codegen`, `gqlgen`).
- **SQL → typed query code:** `sqlc` reads your SQL queries + schema and generates typed Go functions; jOOQ reads your database schema and generates a typed Java query DSL. A column rename becomes a *compile error*, not a runtime surprise.

The shared property: the schema is **language-independent**, so the *same* schema generates a Go server, a Java client, and a Python script — all guaranteed to agree on the wire.

### 4. Annotation-Driven Generation

Here you do not write a separate schema; you annotate your **own source**, and a **processor runs inside the compiler** to emit companion code.

- **Java APT:** annotation processors are registered with `javac`. During compilation the compiler invokes them; they read annotated elements and write new source files (which are then compiled in the same run). **Lombok** generates accessors/equals/toString; **AutoValue** generates immutable value classes; **MapStruct** generates type-safe object mappers; **Dagger** generates a compile-time dependency-injection graph.
- **Kotlin KSP/KAPT:** KAPT runs the Java APT machinery over Kotlin (slow, generates Java stubs); **KSP** is a faster, Kotlin-native API that processes Kotlin symbols directly.

The defining trait: the trigger is **the compiler**, so generation and compilation are one step. There is no separate "run the generator" command — `javac`/`kotlinc` does it. (Lombok is a slight outlier: it *modifies the AST* rather than emitting separate files, but it rides the same APT entry point.)

### 5. Dagger vs Spring — Compile-Time vs Runtime DI

A concrete, interview-worthy contrast. Both wire up dependency injection, but at different times:

| | **Dagger** | **Spring (classic)** |
|------|------|------|
| When the DI graph is built | **Compile time** (annotation processor generates the wiring code) | **Runtime** (reflection scans classes, builds the graph as the app starts) |
| Errors surface | At **compile time** — a missing binding fails the build | At **runtime** — a missing bean fails on startup (or later) |
| Startup cost | Near-zero (wiring is precompiled) | Reflection + classpath scanning at boot |
| Native-image friendliness | High (no reflection needed) | Lower (reflection config required for GraalVM) |

This is the codegen value proposition in miniature: **move work from runtime to build time**, turning runtime failures into compile errors.

### 6. Build-System Integration

A generator is only useful if the build runs it reliably. Each ecosystem has a hook:

- **Make:** a target with the generated file as output and the schema as prerequisite — `make` reruns the generator only when the schema is newer. This is the original incremental-regeneration mechanism.
- **`go generate`:** a convention, *not* part of `go build`. A `//go:generate <cmd>` comment plus `go generate ./...` runs the commands. Importantly, `go build` does **not** run `go generate` — you (or CI) must. So Go projects typically *commit* generated files.
- **Gradle/Maven:** annotation processors run automatically during compilation (`annotationProcessor` / `<annotationProcessorPaths>`). Schema generators are wired as build tasks (e.g. the protobuf Gradle plugin) into `build/generated/`, and added to the source set so the compiler sees them.
- **Cargo + `build.rs`:** Cargo compiles and runs `build.rs` *before* the crate. It is the idiomatic place to call `prost`/`tonic` (protobuf) or `bindgen` (C headers → Rust FFI), writing into `OUT_DIR` and pulling the result in with `include!(concat!(env!("OUT_DIR"), "/generated.rs"))`. This makes generation part of every build, so Rust projects often *do not* commit generated code.
- **Bazel:** generation is a first-class build rule (`genrule`, `proto_library`, language `*_proto_library`). Bazel tracks the schema as a declared input and the generated code as a declared output, giving **hermetic, incremental** generation — the generator version is part of the build graph.

### 7. The Committed-vs-Gitignored Decision

A real engineering choice with consequences either way:

**Commit generated code when:** the generator is awkward to install (a specific `protoc` + plugins), you want zero-setup clones and fast CI, or your ecosystem does not auto-run generation (Go). Cost: noisy diffs, regenerate-and-commit discipline, version-skew diffs.

**Gitignore + regenerate-on-build when:** the generator runs automatically in your build (Cargo `build.rs`, Gradle annotation processing) so there is no extra setup, or you want a clean repo. Cost: every dev and CI must have the pinned generator; offline/air-gapped builds get harder.

The deciding factors: *does the build run the generator automatically?* and *is the generator easy to pin and install?* (More trade-off depth in `senior.md`.)

### 8. Incremental Regeneration and Drift Checks

**Incremental:** regenerate only what changed. Make and Bazel do this via input/output timestamps and the dependency graph. Naive scripts that "regenerate everything" are slow and a common build-speed complaint.

**Drift check:** the antidote to stale generated code. In CI, run the generator, then `git diff --exit-code`. If the working tree changed, someone forgot to regenerate — fail the build. This single check eliminates an entire class of "works locally, broken in review" bugs and is the most valuable piece of generation plumbing you can add.

---

## Code Examples

### Example 1: Go `go generate` with `mockgen`

```go
//go:generate mockgen -source=store.go -destination=store_mock.go -package=app

type Store interface {
    Get(id string) (User, error)
    Put(u User) error
}
```

`go generate ./...` runs `mockgen`, which produces `store_mock.go` containing a `MockStore` implementing `Store` for tests. Note: `go build` will **not** run this — you run `go generate` and commit `store_mock.go` (or wire it into CI/Make).

### Example 2: A Make rule with incremental regeneration

```makefile
# Regenerate user.pb.go only when user.proto is newer.
user.pb.go: user.proto
	protoc --go_out=paths=source_relative:. user.proto

.PHONY: gen
gen: user.pb.go
```

`make gen` regenerates only if `user.proto` changed since `user.pb.go` was written — the original incremental-regeneration mechanism.

### Example 3: Rust `build.rs` generating protobuf with `prost`

```rust
// build.rs — compiled and run by Cargo before the crate.
fn main() {
    prost_build::compile_protos(&["proto/user.proto"], &["proto/"]).unwrap();
}
```

```rust
// src/lib.rs — pull in the generated module from OUT_DIR.
pub mod user {
    include!(concat!(env!("OUT_DIR"), "/example.rs"));
}
```

Because `build.rs` runs on every build, the generated code is typically **not committed** — Cargo regenerates it.

### Example 4: A CI drift check (GitHub Actions)

```yaml
- name: Regenerate
  run: make gen
- name: Fail on drift
  run: |
    if ! git diff --exit-code; then
      echo "Generated code is stale. Run 'make gen' and commit."
      exit 1
    fi
```

This is the single most valuable piece of generation plumbing: it makes "forgot to regenerate" impossible to merge.

### Example 5: Java annotation-driven mapper (MapStruct)

```java
@Mapper
public interface UserMapper {
    UserDto toDto(User user);
}
```

At compile time, MapStruct's annotation processor generates `UserMapperImpl` with field-by-field copying code — no reflection at runtime, and a *compile error* if a field cannot be mapped.

### Example 6: sqlc — SQL to typed Go

```sql
-- name: GetUser :one
SELECT id, name, email FROM users WHERE id = $1;
```

`sqlc generate` produces a typed `GetUser(ctx, id) (User, error)` function. Rename the `email` column in the schema and regenerate: the *generated code changes and your callers fail to compile* — the database schema and the code are kept in lockstep at build time.

---

## Coding Patterns

**Pattern: One canonical generate command, wired into the build.** A `make gen` (or `go generate ./...`, or a Gradle task) that regenerates everything. Document it; CI runs it for the drift check.

**Pattern: Pin the generator version in-repo.** Go's `tools.go` + module versions; a lockfile; or a container image with the exact `protoc` + plugins. Eliminates version skew.

**Pattern: Schema as a library.** Put `.proto`/IDL files in a shared repo/module that all services depend on, so the contract has a single home.

**Pattern: Drift check in CI.** Regenerate, then `git diff --exit-code`. Non-negotiable for committed-generated-code projects.

**Pattern: Keep generated output in a clearly separated location.** `build/generated/`, `OUT_DIR`, or a `*_gen.go` suffix — so humans and tools can tell it apart.

---

## Best Practices

1. **Pick the right *kind* for the job.** Schema-driven for cross-language contracts; annotation-driven for in-language boilerplate; template-based only for small, controlled outputs.
2. **Make the generator a pinned, reproducible build dependency.** Treat it like the compiler.
3. **Decide committed-vs-gitignored from the build's behavior:** if the build auto-runs the generator (Cargo, Gradle APT), gitignore is natural; if not (Go), commit.
4. **Add a CI drift check** wherever generated code is committed.
5. **Lean on the build system's incrementality** (Make prerequisites, Bazel inputs) instead of "regenerate everything" scripts.
6. **Review the schema, not the generated diff.** The schema is the human-meaningful change.
7. **Keep hand-written extensions in separate files** from generated output.

---

## Edge Cases & Pitfalls

**`go build` doesn't run `go generate`.** The classic Go trap. Generation is a manual/CI step; forgetting it yields stale output silently. Mitigate with a Make target and a drift check.

**Annotation-processor ordering and rounds.** APT runs in *rounds*: processors can generate code that triggers further processing. Two processors that each consume the other's output can fail to converge or behave order-dependently. Keep processors independent where possible.

**KAPT is slow; reflection-config differs.** KAPT generates Java stubs for every Kotlin file, inflating build time. Migrating to KSP often halves annotation-processing time. Know which one your build uses.

**`build.rs` runs on *every* build and can wreck incrementality.** A `build.rs` that does heavy work or always re-emits files makes Cargo rebuild downstream every time. Use `cargo:rerun-if-changed=` directives to scope when it reruns.

**Version skew shows up as phantom diffs.** Two developers with different `protoc-gen-go` versions produce slightly different `.pb.go`; the diff churns on every commit. Pin the plugin version repo-wide.

**Template generators emit invalid code happily.** A Go `text/template` with a typo produces a file that fails to compile — but the *generator* succeeds, so the error surfaces later, confusingly. Compile the generated output as part of generation when possible.

**Committed generated code drifts during merges.** Two branches both regenerate; merging produces conflicts in generated files. Resolve by regenerating after the merge, not by hand-merging generated lines.

---

## Apply it

1. Find a real component where **Build-Time Code Generation** affects an interface or dependency.
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

- Which boundary is most affected by Build-Time Code Generation?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
