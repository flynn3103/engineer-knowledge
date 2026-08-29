# Macros — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Macros** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Decision: Should This Be a Macro At All?

The professional default is **no**. Macros are justified only when a non-macro mechanism *cannot* do the job. The honest checklist:

- **Can a function do it?** If the thing operates on *values* and does not need to control evaluation, write a function. Functions have signatures, type-check, compose, debug, and produce clean errors.
- **Can a generic + trait do it?** In Rust/C++/Swift, parametric polymorphism handles most "same code, many types" needs without code generation.
- **Can a `const fn` / `constexpr` do it?** Compile-time *computation* over values does not need a macro.
- **Do you need to control evaluation** (short-circuit, wrap a body in setup/teardown, lazy arguments)? Then you need a macro (or a closure-taking function, which is often cleaner).
- **Do you need new *syntax*** the language does not offer (a DSL, an embedded query language)? Macro territory.
- **Do you need *compile-time validation* of literal arguments** (format strings, SQL, regexes, routes)? Macro territory — this is one of the strongest justifications, because it converts run-time failures into build failures.
- **Do you need per-type code generation** the type system cannot infer (`#[derive(Serialize)]`)? Macro territory.

If none of the last four apply, you are about to write a macro to save typing, and that almost always costs more than it saves. The cost is paid by *every future reader*, not by you today.

### 2. Compile Time Is a Production Cost

Macros move work to compile time, and at scale that bill is large. A procedural-macro-heavy Rust crate (`serde`, `diesel`, async frameworks) pulls `syn`/`quote`/`proc-macro2` into the build graph and runs real parsing on *every* annotated item, *every* build. Symptoms: a derive applied to 500 structs adding minutes to a clean build; `cargo build --timings` showing proc-macro crates dominating; CI times creeping up. C++ template metaprogramming has the same pathology — deep instantiation chains and heavy headers blowing up compile time and memory. The professional practices:

- **Measure** (`cargo build --timings`, `-ftime-trace` in Clang) before and after adding a macro-heavy dependency.
- **Prefer `macro_rules!` over proc-macros** when possible — no `syn` parse, much cheaper.
- **Consider `build.rs`/codegen** for *large* or external-data-driven generation, where running a script once and committing/caching the output beats re-parsing on every build.
- **Bound recursion** and avoid quadratic expansion patterns.

The lesson: a macro that makes the *program* faster can make the *team* slower. Both are real costs; weigh them.

### 3. Error Messages Are the Macro's User Interface

The most common professional complaint about macros is not that they are wrong — it is that when *the user* is wrong, the macro's error is incomprehensible. A type error in generated code, reported against a span the user never wrote, sends people on long detours. A macro is a compiler-for-others, and like any compiler its diagnostics are a feature, not an afterthought. Concretely:

- **Forward user spans.** When generated tokens reference the caller's identifiers, attach the caller's span so type errors point at the caller's source.
- **Validate input early and explicitly.** Reject malformed input with `compile_error!`/`syn::Error` carrying a clear message and the offending span, instead of emitting code that fails cryptically three layers down.
- **Never `panic!` in a proc-macro** for user error — it surfaces as "proc macro panicked," the least helpful message possible.
- **Test the failure paths.** Tools like `trybuild` (Rust) snapshot the *exact* compile error for bad input, so you notice when a refactor degrades your diagnostics. The error output is part of your contract.

`println!`/`format!` are the gold standard here: a wrong format string yields a precise, underlined compiler error at the exact byte — that quality is the bar.

### 4. A Public Macro Is Frozen API

The syntax a public macro accepts is part of your semantic-versioning surface, exactly like a function signature. If users write `my_macro!{ name: "x", retries: 3 }`, you cannot quietly rename `retries` or reorder fields without breaking them — and macro inputs are often *harder* to deprecate gracefully than function parameters because there is no overloading and no default-argument story. Implications:

- **Design the accepted syntax as deliberately as a public API.** Once shipped, it is hard to change.
- **Version macro DSLs** and provide migration paths; treat a breaking change to accepted syntax as a major-version bump.
- **Keep the *generated* code's public surface minimal** — every public item a macro emits is also API you must keep stable.

### 5. Debuggability and Tooling Reality

Macros degrade the developer-experience tools your team relies on:

- **Debuggers** step through *generated* code; breakpoints and line numbers can be confusing or wrong.
- **IDEs** may not see through a macro for autocomplete, go-to-definition, or inline type hints — a heavily macro-driven DSL can leave engineers without the tooling they expect for ordinary code.
- **Code review** is harder: a reviewer must mentally expand the macro to judge correctness, and `git blame` points at the macro, not the logic.
- **Mitigation:** `cargo expand` / `gcc -E` / `macroexpand` in the dev loop; keep macros thin (a macro that just calls a normal, well-tested function is far easier to reason about than one with logic inline); and document the expansion so readers do not have to reverse-engineer it.

### 6. Security and Determinism

Procedural macros run **arbitrary code at compile time on the developer's and CI's machines**. That is a supply-chain consideration: a malicious or compromised proc-macro dependency can read files, exfiltrate secrets, or alter generated code during your build. And every macro must be **deterministic** — the same input must produce the same output on every machine and every build. A macro that reads the system clock, the network, an environment variable, or an unsorted directory listing breaks reproducible builds and caching, and produces "works on my machine" failures.

- **Vet proc-macro dependencies** as you would any code that runs in CI with your credentials.
- **Keep macros pure** — input tokens in, tokens out; no I/O that changes the result. (`sqlx`'s compile-time DB check is a deliberate, documented exception that requires explicit configuration precisely because it *does* touch external state.)

### 7. Greenspun in Practice: Designing the Metaprogramming Layer

Large systems accrete a metaprogramming layer. The professional move is to make it intentional: a small, documented, tested set of macros with clear ownership, rather than a sprawl of one-off clever macros. Decide as a team: which DSLs are sanctioned, who owns them, where the expansion contracts are documented, and what the bar is for adding a new macro (usually: "a senior reviewer agrees no non-macro mechanism suffices"). The goal is to capture the *leverage* of macros — eliminating real boilerplate, enabling compile-time checks — while containing their *entropy*.

---

## Code Examples

### A thin macro over a tested function (the maintainable shape)

```rust
// The macro does ONLY syntax/ergonomics; all logic is in a normal function.
macro_rules! retry {
    ($attempts:expr, $body:expr) => {
        $crate::retry_impl($attempts, || $body)   // wrap body in a closure → control evaluation
    };
}

// Real, unit-testable, debuggable, clean errors:
pub fn retry_impl<T, E>(attempts: u32, mut f: impl FnMut() -> Result<T, E>) -> Result<T, E> {
    let mut last = None;
    for _ in 0..attempts {
        match f() {
            Ok(v) => return Ok(v),
            Err(e) => last = Some(e),
        }
    }
    Err(last.expect("attempts must be > 0"))
}
```

The macro exists only to let callers write `retry!(3, do_thing())` and have `do_thing()` evaluated lazily on each attempt — the one thing a function cannot do. Everything else is a normal function you can test and debug. This pattern (thin macro, thick function) is the single most important professional habit.

### Validating input and producing a real error (proc-macro)

```rust
// Inside a proc-macro: reject bad input with a spanned, readable error.
let field = match parse_field(&input) {
    Ok(f) => f,
    Err(span) => {
        return syn::Error::new(span, "expected `name = \"...\"`; got something else")
            .to_compile_error()
            .into();   // user sees a clear message at THEIR span, not a panic
    }
};
```

### The C X-macro: one source of truth, many expansions

```c
// Define the list ONCE...
#define COLORS                \
    X(RED,   "red")           \
    X(GREEN, "green")         \
    X(BLUE,  "blue")

// ...expand it as an enum:
typedef enum {
#define X(sym, str) sym,
    COLORS
#undef X
} Color;

// ...and as a name table, from the SAME list:
static const char *color_name[] = {
#define X(sym, str) str,
    COLORS
#undef X
};
```

Add a color in exactly one place and both the enum and the table update — the X-macro's whole point is a single source of truth. It is one of the few C macro idioms that genuinely earns its keep, because no C language feature otherwise keeps an enum and a parallel table in sync.

### Measuring the compile-time cost

```bash
# Rust: which (often proc-macro) crates dominate the build?
$ cargo build --timings        # writes an HTML report of per-crate build time

# C++: where does the compiler spend its time (templates/instantiation)?
$ clang++ -ftime-trace foo.cpp # emits a Chrome-tracing JSON of compile phases
```

---

## Trade-offs

- **Boilerplate saved vs. tooling lost.** A derive that erases 2,000 lines of hand-written impls is a clear win — *unless* it also blinds the IDE and confuses the debugger for the team. Weigh both.
- **Run-time speed vs. compile-time cost.** Compile-time checks and zero-cost expansions buy run-time performance and safety at the price of build time. At small scale, free; at large scale, a CI-budget line item.
- **Expressiveness vs. accessibility.** A powerful DSL is a productivity multiplier for those fluent in it and a wall for everyone else. The more "magic," the higher the onboarding cost and the bus-factor risk.
- **`macro_rules!` vs proc-macro vs `build.rs`.** Declarative macros: cheap, hygienic, limited. Proc-macros: powerful, costly, must engineer hygiene/errors. Build-scripts: best for large external-data-driven generation, but opaque and outside the type system. Match the tool to the scale and source of the generation.
- **Centralized macro DSL vs. plain code everywhere.** A sanctioned DSL standardizes patterns but concentrates risk and ownership; plain code is verbose but universally readable. Most healthy codebases keep the macro layer small and the plain-code layer large.

---

## Coding Patterns

**Pattern: thin macro, thick function.** The macro handles only syntax/laziness/codegen; all logic lives in an ordinary, tested function the expansion calls.

**Pattern: fail fast with great errors.** Validate input at the top of the macro; emit `compile_error!`/`syn::Error` with the user's span and a sentence explaining the fix.

**Pattern: snapshot the failure path.** Keep `trybuild`-style tests asserting the exact diagnostic for malformed input, so error quality is regression-tested.

**Pattern: document the expansion contract.** A doc comment stating accepted syntax and (a sketch of) generated output, so callers and reviewers need not run `cargo expand` to understand it.

**Pattern: single source of truth (X-macro / one declaration → many outputs).** When several artifacts must stay in sync, generate them all from one list.

**Pattern: prefer `build.rs`/committed codegen for big or data-driven generation**, keeping per-build macro cost low.

---

## Best Practices

- **Make "is a macro justified?" an explicit review question.** Require sign-off that no function/generic/trait/`const fn` suffices before a new macro lands.
- **Budget compile time.** Measure with `cargo build --timings` / `-ftime-trace`; prefer `macro_rules!` to proc-macros; consider build-scripts for heavy generation.
- **Engineer diagnostics deliberately** — forward spans, `compile_error!` over `panic!`, test failure paths. Treat the error message as the macro's primary UI.
- **Keep public macro syntax stable** — it is semver surface; version DSLs and provide migrations.
- **Keep macros thin and pure** — logic in functions, no nondeterministic I/O, deterministic output for reproducible builds.
- **Vet proc-macro dependencies** as code that runs in CI with your secrets.
- **Document the expansion contract** and keep `cargo expand` in the team's dev loop.
- **Bound the metaprogramming layer** — a small, owned, documented set of macros, not an emergent sprawl.

---

## Edge Cases & Pitfalls

- **The derive that doubled the build.** A heavyweight proc-macro applied across hundreds of types silently inflating CI time. Catch it with timing reports, not surprise.
- **The error that pointed at generated code.** A missing span turning every user mistake into a confusing diagnostic against tokens they never wrote.
- **The macro that read the environment.** Non-deterministic output breaking reproducible builds and caching ("works on my machine").
- **The frozen DSL.** A widely-adopted macro syntax you now cannot change without a major version bump and a fleet of broken downstreams.
- **The untestable business logic** baked into a macro body, defeating unit testing and debugging.
- **IDE/debugger blindness** leaving a team without tooling around a macro-heavy module.
- **Supply-chain exposure** from an unvetted proc-macro running arbitrary code in CI.
- **C-specific:** unbounded `#define` clobbering names project-wide (the `<windows.h>` `min`/`max` saga), and conditional-compilation thickets where `#ifdef` combinations are never all tested.

---

## Common Mistakes

1. **Writing a macro that should have been a function/generic** — paying all the macro costs for none of the unique benefits.
2. **Neglecting error-message engineering** — shipping a macro whose failures are unreadable.
3. **Ignoring compile-time cost** until CI is slow, then struggling to attribute it.
4. **Treating public macro syntax as changeable** — breaking downstream users on a "minor" change.
5. **Putting logic in the macro instead of a function** — making it untestable and undebuggable.
6. **Trusting proc-macro dependencies** without considering they run arbitrary code in your build.
7. **Letting the metaprogramming layer grow unowned and undocumented** — the Greenspun trap.

---

## Apply it

1. Define the user or business outcome that **Macros** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Macros?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
