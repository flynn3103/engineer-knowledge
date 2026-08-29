# DSLs via Metaprogramming — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **DSLs via Metaprogramming** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Macros Move the DSL to Compile Time

A runtime DSL builds and interprets data while the program runs. A **macro-based DSL** transforms *syntax into code* before the program runs. Rust's declarative `macro_rules!` is the gentle entry point:

```rust
macro_rules! hashmap {
    ( $( $key:expr => $val:expr ),* $(,)? ) => {{
        let mut m = std::collections::HashMap::new();
        $( m.insert($key, $val); )*
        m
    }};
}

let scores = hashmap! {
    "alice" => 10,
    "bob"   => 20,
};
```

The macro matched the `key => val` pattern and **expanded** it into real Rust (`m.insert(...)` per pair) at compile time. There is no runtime parser, no expression tree to walk — the DSL *became* ordinary code before the program ever ran. `vec![...]` and `json!{...}` (serde_json) work the same way at the declarative or procedural level.

### 2. Procedural Macros: Arbitrary Compile-Time Code Generation

When pattern matching is not enough, **procedural macros** receive a `TokenStream` (the raw tokens of the DSL) and return a `TokenStream` (the generated code). This is a full programmable transformation:

```rust
// usage (Yew):
html! {
    <div class="card">
        <h1>{ title }</h1>
        { for items.iter().map(render_item) }
    </div>
}
```

The `html!` proc-macro parses the JSX-like syntax, type-checks the expressions in `{ ... }`, and emits Rust that constructs a virtual DOM. Because it runs in the compiler, it can produce **compile errors** for malformed markup and can use **spans** to point those errors at the exact offending token in your source.

### 3. Compile-Time Validation: The `sqlx::query!` Superpower

The most striking compile-time DSL is `sqlx::query!`. It connects to a real database **during compilation** and checks the SQL:

```rust
let user = sqlx::query!(
    "SELECT id, name, age FROM users WHERE id = $1",
    user_id
)
.fetch_one(&pool)
.await?;

// user.name is &str, user.age is i32 — types INFERRED from the DB schema.
```

If you misspell `name`, reference a non-existent table, or mismatch a parameter type, the program **does not compile**. The macro also generates a struct whose field types come from the database's own type information. This is the apex of "the DSL catches bugs before runtime" — it pulls a class of errors all the way from production back to your build. The trade-off is explicit: you need DB access (or a cached `.sqlx` schema) at build time, and macro errors can be cryptic.

### 4. Ruby's Runtime Metaprogramming: `method_missing` and `instance_eval`

Ruby builds the most fluent runtime DSLs in mainstream use, and two hooks do most of the work.

**`method_missing`** turns *any* method name into behavior — the engine behind ActiveRecord's `find_by_email_and_status`:

```ruby
class Config
  def initialize; @settings = {}; end
  def method_missing(name, *args)
    if name.to_s.end_with?("=")
      @settings[name.to_s.chomp("=").to_sym] = args.first   # setter
    else
      @settings[name]                                        # getter
    end
  end
  def respond_to_missing?(name, include_private = false)
    true
  end
end

c = Config.new
c.timeout = 30        # method_missing("timeout=", 30)
c.timeout             # => 30
```

**`instance_eval`** runs a block with `self` rebound, which is how `do ... end` config DSLs drop the receiver prefix:

```ruby
def configure(&block)
  config = Config.new
  config.instance_eval(&block)    # block's `self` becomes `config`
  config
end

settings = configure do
  self.timeout = 30
  self.retries = 3
end
```

RSpec's `describe/it`, Rake's task blocks, and Rails routing all combine `instance_eval`/`instance_exec` (run a block in your object's context) with `define_method` (generate methods on the fly). The cost is the dark side of `method_missing`: a typo'd method name does not error — it silently becomes "missing method" behavior, and stack traces point into the metaprogramming machinery, not your DSL.

### 5. The Technique-to-Style Map

A senior carries a mental table of *which metaprogramming tool produces which DSL flavor*:

| Technique | Host examples | DSL style it yields | Validation |
|-----------|---------------|---------------------|------------|
| Method chaining / builder | everywhere | Fluent config/query skeleton | Runtime |
| Operator overloading | SQLAlchemy, pandas | Expression/query/math DSL | Runtime |
| Blocks + `instance_eval` | RSpec, Rake, Rails | Config/testing/build DSL | Runtime (weak) |
| Lambdas-with-receiver | Kotlin HTML, Gradle KTS, Ktor | Typed nested builder | Compile (types) |
| Declarative macros | `vec!`, `hashmap!` | Literal/collection DSL | Compile |
| Procedural macros | `html!`, `json!`, `sqlx::query!` | Markup/serialization/query DSL | Compile (strong) |
| `method_missing`/`define_method` | ActiveRecord | Dynamic, open-ended DSL | None (dynamic) |
| Decorators / reflection | Flask routes, Spring annotations | Declarative config DSL | Runtime/startup |

The right column is the crux: **macros buy you compile-time validation; dynamic Ruby buys you fluency at the cost of all static checking.** Choosing a technique is choosing where on the validation spectrum your DSL sits.

### 6. DSL Design Is Interface Design Under a Cost Model

At this tier the central skill is judgment. A DSL imposes a second language on every reader; it earns that cost only when it (a) is used often, (b) is read more than written, and (c) genuinely clarifies the domain. Three design properties decide whether a DSL is a gift or a liability:

- **Error provenance.** When something goes wrong, does the error name the *domain* mistake (`unknown column "naem"`) or leak the *implementation* (`NoneType has no attribute 'compile'`, or a 40-line macro-expansion trace)? This single property predicts how much a team will love or hate your DSL.
- **Leak resistance.** Under unusual input, does the abstraction hold, or must users suddenly understand the plumbing? Every DSL leaks *somewhere*; good ones leak gracefully (a documented escape hatch) rather than catastrophically (an unreadable stack trace).
- **Tooling.** Autocomplete, go-to-definition, type checking, formatting. A typed Kotlin builder gives all four; a `method_missing` DSL gives almost none. Tooling support is often the deciding factor for adoption.

---

## Code Examples

### Example 1: A declarative macro DSL with trailing-comma support (Rust)

```rust
macro_rules! routes {
    ( $( $method:ident $path:literal => $handler:expr ),* $(,)? ) => {{
        let mut r = Router::new();
        $( r.add(stringify!($method), $path, $handler); )*
        r
    }};
}

let router = routes! {
    GET  "/"        => home,
    GET  "/users"   => list_users,
    POST "/users"   => create_user,
};
```

The DSL reads like a routing table; the macro expands it to `r.add(...)` calls at compile time. `$(,)?` permits a trailing comma — a small courtesy that makes the DSL feel native. No runtime cost, and malformed entries fail to compile.

### Example 2: Compile-time-checked query (sqlx, conceptual)

```rust
// If the column "naem" does not exist, THIS LINE fails to compile.
let row = sqlx::query!(
    "SELECT id, naem FROM users WHERE id = $1",
    id
).fetch_one(&pool).await?;
//   error: no column found for name: naem
//          --> src/main.rs:3:5
```

The payoff: a class of bugs (schema drift, typos, type mismatches) is moved from runtime to build time. The price: the build needs database metadata, and when the macro *does* error, the message — while better than most — still lives partly in macro-expansion terms.

### Example 3: A Ruby DSL combining `instance_eval` + `define_method`

```ruby
class Pipeline
  def self.build(&block)
    p = new
    p.instance_eval(&block)
    p
  end

  def initialize; @steps = []; end

  def step(name, &body)
    @steps << [name, body]
    # generate a query-method per step: pipeline.has_validate?
    self.class.define_method("has_#{name}?") { @steps.any? { |n, _| n == name } }
  end

  def run(input)
    @steps.reduce(input) { |acc, (_, body)| body.call(acc) }
  end
end

pipe = Pipeline.build do
  step(:validate) { |x| raise "bad" unless x.is_a?(Integer); x }
  step(:double)   { |x| x * 2 }
end

pipe.run(21)         # => 42
pipe.has_double?     # => true   (method generated at build time)
```

This shows the Ruby pattern in full: `instance_eval` for the block DSL, `define_method` to generate methods reactively. It is fluent and powerful — and note the failure mode: a typo like `pipe.has_doubel?` raises `NoMethodError` deep in Ruby, not a domain-level "no such step."

### Example 4: Designing the leak — a safe escape hatch

```python
class Query:
    def where(self, expr): ...; return self
    def raw(self, sql_fragment, *params):
        """Documented escape hatch: when the expression DSL can't express
        something (a vendor-specific function), drop to raw SQL — but the
        params are still bound, so this stays injection-safe."""
        self._raw.append((sql_fragment, params))
        return self

q.where(User.age > 21).raw("age <@ int4range(?, ?)", 18, 65)
```

The senior move: the abstraction *will* leak (some SQL is inexpressible), so you design a leak that preserves the DSL's core guarantee (parameter binding) instead of letting users fall back to unsafe string concatenation.

---

## Coding Patterns

**Pattern: expand to plain code, then reason about the plain code.** When writing or reviewing a macro DSL, mentally (or with `cargo expand`) produce the expansion and verify *that* is correct. The macro is just the generator.

**Pattern: attach spans so errors point at the user.** In Rust proc-macros, propagate source spans so a bad token reports *at the user's call site*, not at the macro's internals. This is the difference between a usable and a hated macro.

**Pattern: pair `method_missing` with `respond_to_missing?`.** Always implement both, or reflection, `respond_to?`, and `method()` lie — breaking duck-typing and tooling that depends on them.

**Pattern: define the escape hatch up front.** Assume the DSL cannot express everything; provide a documented, *safe* fallback (`raw(...)` with bound params) so users do not improvise unsafe ones.

**Pattern: generate methods, do not intercept, when you can.** `define_method` (concrete, introspectable, autocompletable) beats `method_missing` (invisible to tooling) whenever the set of methods is knowable up front.

**Pattern: keep the DSL surface small.** A focused DSL (a dozen well-named constructs) is learnable and maintainable; a sprawling one becomes a dialect only its author understands.

---

## Best Practices

- **Design the error path before the happy path.** Decide what each likely mistake reports, in domain terms, before you polish the fluent syntax. Users meet your DSL through its errors.
- **Prefer compile-time validation where the payoff is high.** For queries, schemas, and routes, catching errors at build time (macros, types) is worth real complexity. For one-off config, runtime is fine.
- **Make expansions visible.** Document how the macro expands (and point users to `cargo expand`); make `method_missing` behavior discoverable. A DSL nobody can see through is a DSL nobody can fix.
- **Respect the host's tooling.** Choose techniques that keep autocomplete and go-to-definition working (typed builders, `define_method`) over those that blind the IDE (`method_missing`) unless the fluency gain is decisive.
- **Write the "why not a plain library?" paragraph.** Before building a DSL, articulate what it buys over ordinary functions. If you cannot, build the functions.
- **Budget for the maintenance of a mini-compiler.** A macro crate or metaprogramming layer is long-lived infrastructure. Staff and document it accordingly.

---

## Edge Cases & Pitfalls

- **Macro hygiene leaks.** A macro that introduces an identifier (`let tmp = ...`) can collide with the user's `tmp`. Rust's hygiene mostly prevents this; hand-rolled or `unhygienic` cases can break subtly.
- **`method_missing` swallowing typos.** A misspelled DSL method silently routes to fallback behavior or raises late. Always implement `respond_to_missing?`, and consider whitelisting valid names.
- **`sqlx`/compile-time DB coupling.** CI without DB access fails unless you commit cached schema metadata. Plan the offline-build story before adopting.
- **Expansion-error illegibility.** A small mistake inside `html!`/`json!` can produce a wall of generated-code errors. Provide examples and, where possible, custom error messages with spans.
- **`instance_eval` rebinds `self` surprisingly.** Inside the block, `self` is no longer what the reader expects; references to outer instance variables and constants can resolve unexpectedly. Document the receiver explicitly.
- **Performance of dynamic dispatch.** Heavy `method_missing` use is slower than direct calls and defeats some JIT/inline-cache optimizations; hot paths should use generated concrete methods.
- **Two-implementation drift.** A DSL plus its escape hatch can encode the same operation two ways that disagree. Keep one canonical lowering.
- **Building a DSL for a problem that was a function.** The recurring senior pitfall: a clever macro/metaprogramming layer where three named functions would have been clearer, faster to onboard, and trivially debuggable.

---

## Apply it

1. State the system invariant that **DSLs via Metaprogramming** must protect.
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

- Which invariant must remain true when DSLs via Metaprogramming fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
