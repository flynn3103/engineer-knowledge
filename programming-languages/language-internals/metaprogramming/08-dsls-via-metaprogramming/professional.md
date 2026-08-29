# DSLs via Metaprogramming — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **DSLs via Metaprogramming** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## The Production DSL Families

| Family | Examples | Technique |
|---|---|---|
| **Configuration** | Gradle, Rails routes, Ktor | blocks / lambdas-with-receiver, `instance_eval` |
| **Querying** | LINQ, SQLAlchemy, jOOQ, Ecto | operator overloading → expression trees, builders |
| **Testing** | RSpec, Spock, Jest `describe/it` | blocks, method chaining |
| **Markup / UI** | Jetpack Compose, kotlinx.html, JSX | type-safe builders, macros/transpilation |
| **Build / tasks** | Rake, Gradle tasks | blocks, dynamic method definition |
| **Validation / schema** | pydantic, Zod, ActiveRecord validations | decorators/operator overloading, DSL methods |

Each maps to a metaprogramming tool: Ruby DSLs lean on `instance_eval`/`method_missing`/
`define_method`; Kotlin DSLs on **lambdas with receiver** and `@DslMarker`; Rust DSLs on
**macros** (`vec!`, `json!`, yew's `html!`, `sqlx::query!`); query DSLs on **operator
overloading** building expression trees that compile to SQL.

---

## Compile-Checked vs Runtime DSLs

The most consequential axis (and the link to the section's central theme):

- **Compile-checked DSLs** (Rust macros, Kotlin type-safe builders, jOOQ, F# computation
  expressions) catch malformed DSL usage at build time and give IDE autocomplete on the
  DSL's vocabulary. `sqlx::query!` even checks your SQL against the database schema at
  compile time. The cost: harder to author (macro/type machinery), and macro errors can
  be cryptic.
- **Runtime DSLs** (Ruby `instance_eval` DSLs, most Python fluent builders) are trivial to
  author and endlessly flexible, but a typo'd DSL keyword fails at runtime, autocomplete
  is weak, and "go to definition" lands in framework internals.

The professional default for a DSL that real teams depend on leans toward
compile-checked where the host language supports it well — the up-front authoring cost
buys back tooling and fail-fast errors that pay off across every consumer.

---

## The Things That Decide Whether a DSL Survives

1. **Error messages in domain terms.** When a user misuses the DSL, do they see "expected
   a `where` clause" or a 40-line macro-expansion / `method_missing` stack trace? Good
   DSLs invest heavily here; it's the difference between adoption and revolt.
2. **IDE support.** Autocomplete on the DSL vocabulary, type-checked builders, jump-to-def.
   Kotlin's `@DslMarker` (preventing the wrong receiver's methods from leaking into an
   inner block) exists precisely to keep large DSLs navigable.
3. **Debuggability.** Can you breakpoint inside the DSL? Runtime block-based DSLs often
   can; macro-expanded ones need `cargo expand`-style tooling.
4. **Discoverability / "now you have two languages."** Every DSL is a second language the
   team must learn and maintain. The bar for introducing one is high.
5. **Leak resistance.** When the host syntax fights the domain, the abstraction leaks and
   users must understand the implementation. A DSL that frequently leaks is worse than a
   plain API.

---

## Code Examples

A Kotlin type-safe builder (compile-checked, IDE-assisted, `@DslMarker`-scoped):

```kotlin
@DslMarker annotation class HtmlDsl

@HtmlDsl class BODY { fun p(block: P.() -> Unit) { /* ... */ } }
@HtmlDsl class P   { operator fun String.unaryPlus() { /* append text */ } }

fun html(block: HTML.() -> Unit): HTML = HTML().apply(block)

// Usage reads like the domain, and the IDE autocompletes p/+ inside body:
html { body { p { +"Hello" } } }
```

The same shape in Ruby is runtime and `instance_eval`-based — terser to build, weaker
to tool:

```ruby
def html(&blk) = HtmlBuilder.new.tap { |b| b.instance_eval(&blk) }
html { body { p { text "Hello" } } }   # `p`, `text` resolved dynamically at runtime
```

---

## Best Practices

- **Make errors speak the domain.** Validate DSL usage and raise messages in the user's
  vocabulary; for macro DSLs, spend effort on diagnostic spans.
- **Prefer compile-checked builders/macros** where the host supports them well — you gain
  autocomplete and fail-fast.
- **Use scope markers** (`@DslMarker`) so nested blocks don't leak outer methods.
- **Keep an escape hatch to a plain API** — power users should be able to drop below the
  DSL.
- **Justify the second language.** Introduce a DSL only when the domain is used widely
  enough that fluency pays back the learning/maintenance cost; otherwise ship a plain
  fluent API.
- **Version the DSL like an API** — its surface is a contract.

---

## Edge Cases & Pitfalls

- **Cryptic errors:** macro/operator-overload DSLs can surface errors in implementation
  terms; unguarded `method_missing` DSLs swallow typos.
- **Receiver leakage:** without `@DslMarker`/scoping, an inner block can accidentally call
  an outer builder's method.
- **Operator-overload surprises:** overloading `>`/`==` to build expression trees means
  those operators no longer mean comparison — confusing if it leaks (e.g. using a query
  column in a boolean context).
- **Debugging through `instance_eval`:** `self` is rebound, stack traces are opaque.
- **Two-languages tax:** onboarding, tooling, and maintenance costs of a bespoke DSL.
- **Over-DSLing:** a DSL where a config file (YAML/JSON) or a plain builder API would do.

---

## Apply it

1. Define the user or business outcome that **DSLs via Metaprogramming** should improve.
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

- Which measurable outcome justifies investing in DSLs via Metaprogramming?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
