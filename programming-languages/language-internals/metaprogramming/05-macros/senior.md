# Macros — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Macros** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Token Trees: Rust's Macro Substrate

Rust macros do not see characters (like C) or fully-parsed ASTs (like Lisp). They see **token trees**: a stream of tokens in which every `()`, `[]`, `{}` pair groups everything between it into a nested unit. So `f(a + b)` is the identifier `f` followed by a parenthesized group containing `a`, `+`, `b`. This representation is deliberately chosen: it is structured enough that brackets always balance and a macro can recurse into groups, but loose enough that a macro can accept syntax that is *not yet valid Rust* (a `sql!("SELECT …")` macro can accept tokens that mean nothing to Rust's grammar). The macro's job is to turn token trees into *valid* Rust.

### 2. `macro_rules!`: Declarative, Fragment-Typed, Hygienic

A `macro_rules!` macro is a list of `(matcher => transcriber)` rules. The matcher is a token-tree pattern with **metavariables** like `$x`, each tagged with a **fragment specifier** that says what category of syntax it must be:

```rust
macro_rules! square {
    ($x:expr) => { ($x) * ($x) };   // $x must be an expression
}

let b = square!(2 + 3);   // expands to ((2 + 3)) * ((2 + 3)) → 25
```

Crucially, `$x:expr` does **not** paste tokens. It captures `2 + 3` as a *parsed expression*, an opaque unit. When it is substituted into `($x) * ($x)`, Rust treats it as one expression — so the C precedence bug **cannot happen**: there is no way for `2 + 3` to "bleed" into the surrounding `*`. The fragment specifier turns the macro from a text-splicer into a syntax-splicer.

Fragment specifiers you will use constantly: `expr` (expression), `ty` (type), `ident` (identifier), `pat` (pattern), `block`, `stmt`, `path`, `literal`, and `tt` (a single token tree — the escape hatch for "anything"). Choosing the right specifier is a real design decision: `expr` lets the matcher accept rich syntax but *restricts* where the result can be used afterward (Rust will not let you re-inspect an `expr` fragment's internals), while `tt` is maximally flexible but unstructured.

**Repetition** handles variable arity:

```rust
macro_rules! my_vec {
    ( $( $x:expr ),* $(,)? ) => {        // zero or more exprs, comma-separated
        {
            let mut v = Vec::new();
            $( v.push($x); )*            // emit one push per captured $x
            v
        }
    };
}

let xs = my_vec![1, 2, 3];   // builds a Vec with 1, 2, 3
```

`$( ... ),*` means "match this group zero or more times, separated by commas." In the transcriber, `$( v.push($x); )*` *replays* the group once per match. The `$(,)?` allows an optional trailing comma. This is the same idea as Scheme's `...` ellipsis.

**Hygiene:** the `v` introduced inside `my_vec!` is automatically distinct from any `v` in the caller's scope. You can call `my_vec!` inside a function that already has a `v` and nothing breaks — Rust's macro expander attaches hygiene context (via spans) so the macro's `v` and the caller's `v` are different identifiers even though they are spelled the same. This is `syntax-rules` hygiene, carried into a statically typed language.

### 3. Procedural Macros: Parse with `syn`, Generate with `quote`

`macro_rules!` is declarative and limited — it matches shapes and replays templates, but it cannot run arbitrary logic, read a struct's fields by name, or talk to the type system. **Procedural macros** can: they are ordinary Rust functions, compiled into a compiler plugin, that receive a `TokenStream` and return a `TokenStream`. In practice you never manipulate raw tokens — you use two crates:

- **`syn`** parses the input `TokenStream` into a typed AST (`syn::DeriveInput`, `syn::ItemFn`, `syn::Expr`, …).
- **`quote!`** builds the output `TokenStream` from a quasiquote template, where `#var` interpolates a value and `#(...)* ` repeats — the direct analog of Lisp's `` ` ``/`,`/`,@`.

There are **three kinds**:

**(a) Derive macros** — `#[derive(MyTrait)]` on a type, generating an `impl`. This is what powers `#[derive(Debug, Clone, Serialize)]`. The macro receives the type's definition and emits an implementation:

```rust
use proc_macro::TokenStream;
use quote::quote;
use syn::{parse_macro_input, DeriveInput};

#[proc_macro_derive(HelloName)]
pub fn derive_hello(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);
    let name = &ast.ident;                       // the struct's name
    let expanded = quote! {                       // a quasiquote template
        impl HelloName for #name {
            fn hello() -> &'static str {
                stringify!(#name)
            }
        }
    };
    expanded.into()
}
```

Now `#[derive(HelloName)] struct Widget;` automatically gains a `HelloName` impl. The macro reads the type's name via `syn` and writes the `impl` via `quote!`. This is how `serde` generates serialization code, how `clap` generates argument parsers — enormous boilerplate, written once, generated per type.

**(b) Attribute macros** — `#[name(args)]` that *transform the item they annotate*. Web frameworks use these: `#[get("/users/{id}")]` on a function rewrites it into a registered route handler. The macro receives both the attribute's arguments and the annotated item, and returns replacement tokens.

**(c) Function-like procedural macros** — `name!(...)` that look like `macro_rules!` calls but run procedural code. Example: `sqlx::query!("SELECT * FROM users")` parses the SQL *at compile time*, checks it against your database schema, and generates strongly-typed result code — a compile-time check no function or declarative macro could do.

### 4. Hygiene, Formally

Hygiene is the property that **the meaning of an identifier is determined by where it was *written*, not where it ends up after expansion.** Two failure modes it prevents:

- **Capture of caller by macro:** a macro introduces `let tmp = ...;`. Hygiene guarantees this `tmp` is invisible to the caller's code and does not shadow the caller's `tmp`.
- **Capture of macro by caller:** a macro expands to `result + 1` referring to a function `result` from the macro's own crate. Hygiene guarantees the caller cannot accidentally redirect that `result` to a local of their own.

Implementation-wise, hygiene is carried by **spans**: every token gets a hygiene context, and name resolution treats two same-spelled identifiers from different hygiene contexts as *different names*. This is the modern, span-based reformulation of Scheme's renaming algorithm. (Common Lisp's `gensym` is a *manual* approximation: by minting an un-typeable name, you simulate a distinct hygiene context for that one binding.)

Two important nuances a senior should know:
- **`macro_rules!` is mostly hygienic, but not for everything.** Identifiers passed *in by the caller* (`$x:ident`) are intentionally not renamed — they refer to the caller's scope, which is what you want. Hygiene applies to identifiers the macro *writes literally*.
- **Procedural macros have *opt-in* hygiene.** `quote!` by default produces tokens with call-site spans, which means an identifier you generate can be visible to the caller (sometimes desired, sometimes a bug). You control this explicitly via `Span::call_site()` vs `Span::mixed_site()`/`def_site`. Senior engineers writing proc-macros must reason about spans deliberately; hygiene is not fully automatic the way `macro_rules!` is.

### 5. Expansion Ordering and Recursion

Macros expand outside-in in Rust, and a macro may expand to code containing further macro calls, which are then expanded in turn. `macro_rules!` macros can be **recursive** (a rule that calls the same macro on the "rest" of its input), which is how they implement variadic and structural transformations:

```rust
macro_rules! count {
    () => { 0 };
    ($head:tt $($tail:tt)*) => { 1 + count!($($tail)*) };
}
```

Rust caps recursion depth (`#![recursion_limit]`) to bound compile time. C++ template instantiation recurses similarly (and historically had the same depth-limit dance). The senior insight: **macro recursion runs at compile time, so deep recursion costs *compile* time, not run time** — a real budget you spend.

### 6. The Same Design Space: C++ Templates and Elixir

**C++ templates** are, in effect, a separate (Turing-complete, accidentally so) compile-time language. Template metaprogramming generates code by *instantiation*, and modern `constexpr`/`consteval` functions let ordinary-looking code run at compile time:

```cpp
template <typename T> T max_t(T a, T b) { return a > b ? a : b; }  // no double-eval, type-checked

constexpr int factorial(int n) {        // may run at compile time
    return n <= 1 ? 1 : n * factorial(n - 1);
}
consteval int must_be_compile_time(int n) { return n * n; }  // MUST run at compile time
```

`max_t` solves the C `MAX` macro's double-evaluation and type-safety problems entirely — it is a real (instantiated) function, so each argument is evaluated once and type-checked. This is why modern C++ guidance is *"replace function-like macros with templates and `constexpr`."* Templates do not, however, give you arbitrary syntax transformation or new control flow the way Rust proc-macros or Lisp macros do — they generate code by substituting *types and values*, not by rewriting *syntax*.

**Elixir** brings Lisp-style macros to the BEAM: `quote` turns code into its AST representation, `unquote` splices values in, and `defmacro` defines a transformer. Elixir's entire `if`/`unless`/`with` surface, and much of Phoenix and Ecto's DSL, is built from macros over a quoted AST — the same homoiconic-style model as Lisp, with Elixir-specific hygiene rules (variables are hygienic by default; you opt out with `var!` when you deliberately want to inject into the caller's scope).

---

## Code Examples

### `macro_rules!` with multiple fragment specifiers and repetition

```rust
macro_rules! hash_map {
    ( $( $key:expr => $val:expr ),* $(,)? ) => {{
        let mut m = ::std::collections::HashMap::new();
        $( m.insert($key, $val); )*
        m
    }};
}

let m = hash_map!{ "a" => 1, "b" => 2 };   // hygienic 'm', one insert per pair
```

### A derive macro skeleton (`syn` + `quote`)

```rust
#[proc_macro_derive(Builder)]
pub fn derive_builder(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);
    let name = &ast.ident;
    let builder = quote::format_ident!("{}Builder", name);

    // (real code would iterate ast.data's fields here)
    let expanded = quote! {
        pub struct #builder { /* per-field Option<...> */ }
        impl #name {
            pub fn builder() -> #builder { #builder { } }
        }
    };
    expanded.into()
}
```

This is the shape of `serde`, `clap`, `thiserror`: parse the type, iterate fields, emit an `impl`. The `#name` / `#builder` interpolations are `quote!`'s unquote.

### Seeing the truth: `cargo expand`

```bash
$ cargo install cargo-expand
$ cargo expand            # prints the whole crate with all macros expanded
$ cargo expand my_module::my_fn
```

`cargo expand` is non-negotiable when debugging a macro — it shows the actual generated code, with hygiene-mangled identifiers rendered, so you can see exactly what the compiler compiled. It is the Rust analog of `gcc -E` and `macroexpand`.

### Elixir `quote`/`unquote`

```elixir
defmacro unless(condition, do: block) do
  quote do
    if !unquote(condition), do: unquote(block)
  end
end

# unless x > 0, do: IO.puts("non-positive")
# expands to:  if !(x > 0), do: IO.puts("non-positive")
```

`quote do ... end` builds the AST; `unquote(...)` splices the caller's expressions in — homoiconic macros on the BEAM, hygienic by default.

---

## Trade-offs

- **`macro_rules!` vs procedural macros.** Declarative macros are simpler, hygienic by default, and need no separate crate — prefer them for token-shape transformations and variadic helpers. Procedural macros are required when you must read a type's structure, run logic, or accept foreign syntax (SQL, GraphQL), but they live in a separate `proc-macro` crate, slow compiles, and demand careful span/hygiene reasoning.
- **Compile time vs run time.** Macros move work to compile time — great for run-time performance and compile-time checks (`println!` validates its format string; `sqlx::query!` validates SQL against the schema), but heavy macro use (and `syn`/`quote` in dependency trees) is a leading cause of slow Rust builds.
- **Power vs error quality.** The more a macro transforms, the worse its errors can become — generated code that fails to type-check points at *generated* spans the user never wrote. Good macros invest heavily in span management so errors point back at the user's source.
- **Macros vs templates (C++).** Templates are type-checked and integrate with overload resolution, but their error messages are notoriously verbose; macros transform syntax but lack type awareness. Modern C++ prefers templates/`constexpr` over function-like macros for exactly the safety reasons in `junior.md`.
- **Macros vs plain functions/traits.** A macro that could be a generic function + trait usually *should* be — functions have signatures, are debuggable, compose, and produce clean errors. Reserve macros for what functions provably cannot do.

---

## Coding Patterns

**Pattern: prefer `macro_rules!` first.** Reach for a proc-macro only when you need to inspect type structure or run logic.

**Pattern: `syn` to parse, `quote!` to generate.** Never hand-build `TokenStream`s; the `syn`/`quote` pair is the standard, and `quote!`'s `#var`/`#(...)* ` is your quasiquotation.

**Pattern: forward spans for good errors.** When generating tokens that reference the user's identifiers, carry the user's spans so type errors point at *their* code, not the macro body. Use `syn::Error::to_compile_error()` to emit precise diagnostics instead of `panic!`.

**Pattern: a `macro_rules!` "internal" recursion accumulator.** Use a private `(@internal ...)` rule to thread state through recursive expansion.

**Pattern: `compile_error!` for invalid input.** Emit a clear message at compile time rather than producing code that fails cryptically downstream.

---

## Best Practices

- **Use the weakest macro mechanism that works:** function/trait < `macro_rules!` < proc-macro. Escalate only when forced.
- **`cargo expand` every non-trivial macro** during development and read the output, exactly as you would `gcc -E`.
- **Engineer error messages deliberately** — preserve user spans, prefer `compile_error!`/`syn::Error` over `panic!`, and test the *failure* paths (use a tool like `trybuild` to assert error output).
- **Bind potentially side-effecting fragments once** in `macro_rules!` (`let x = $e;`) before reusing them, just as you `gensym` in Lisp — `:expr` does not protect against repeated evaluation if your template uses it twice.
- **Reason about hygiene in proc-macros explicitly** — know whether a generated identifier should be `call_site` (visible to caller) or `def_site`/`mixed_site` (private to the macro), and choose deliberately.
- **Watch the compile-time budget** — `syn`/`quote` and deep recursion cost build time; profile with `cargo build --timings`.
- **Document the macro's expansion contract and the syntax it accepts** — callers cannot read it from a signature.

---

## Edge Cases & Pitfalls

- **Repeated `:expr` still double-evaluates.** `macro_rules! square { ($x:expr) => { $x * $x } }` evaluates `$x` *twice* — same double-eval hazard as C, despite the fragment typing. Bind once: `{ let v = $x; v * v }`.
- **Fragment specifier "follow-set" restrictions.** After an `:expr` fragment, `macro_rules!` only permits certain following tokens (`=>`, `,`, `;`). The parser must stay unambiguous; you will hit cryptic "no rules expected this token" errors when you violate this.
- **`:expr` opacity.** Once a fragment is captured as `:expr`, you cannot re-match its internals in a later rule — it is a sealed unit. Use `:tt` when you need to keep inspecting structure.
- **Proc-macro hygiene leaks.** A generated identifier with a `call_site` span can collide with — or be shadowed by — the caller's names. Subtle, and the opposite of the safety `macro_rules!` gives you by default.
- **Order/recursion-limit hits.** Deeply recursive `macro_rules!` or template instantiation blows `recursion_limit`/instantiation depth and fails to compile.
- **Errors pointing at generated code.** Without span care, a type error in generated code shows the user a span inside `quote!` they never wrote — the single most common complaint about macro-heavy crates.
- **C++ template double-error-storm and SFINAE noise** — the template equivalent of "bad macro error messages."

---

## Common Mistakes

1. **Reaching for a proc-macro when `macro_rules!`, a generic, or a trait would do.**
2. **Assuming `:expr` prevents double evaluation** — it prevents *precedence* bugs, not *duplication* bugs.
3. **`panic!`-ing in a proc-macro** instead of emitting a spanned `compile_error!`, giving users an unhelpful "proc macro panicked."
4. **Ignoring spans**, so every error from generated code is unreadable.
5. **Not reasoning about proc-macro hygiene** (`call_site` vs `def_site`) and leaking or capturing identifiers.
6. **Treating C++ templates as text macros** — they substitute *types/values* and are type-checked, a different model.

---

## Apply it

1. State the system invariant that **Macros** must protect.
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

- Which invariant must remain true when Macros fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
