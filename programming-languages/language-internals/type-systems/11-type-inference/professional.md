# Type Inference — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Type Inference** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Annotation Is Three Things at Once

The professional reframes every annotation as serving three jobs simultaneously, and weighs all three:

1. **Documentation.** A signature is the most-read, least-stale form of docs. `fn parse(s: &str) -> Result<Config, Error>` tells a caller everything without a doc comment.
2. **Error localization.** An annotation is a *firewall*. With a written return type, a mistake inside the function is reported *in* the function; without it, the mistake leaks out as a confusing error at every call site. Annotations cut error blast radius.
3. **Inference anchor.** A written type seeds the solver, preventing widening (TS), resolving ambiguity (Haskell), and stabilizing inference against unrelated edits.

Because one keystroke buys all three, the right annotation is rarely "wasteful." The waste is annotating *non-boundaries* — local temporaries whose type is obvious — where you pay verbosity for no localization or documentation benefit.

### 2. The Boundary Principle Is a Cost Model

"Annotate boundaries, infer bodies" isn't a slogan; it's the optimum of a cost model. Boundaries (exported functions, public fields, module interfaces) are:

- **Read the most** (every caller) → documentation payoff is highest.
- **The error firewall** → localization payoff is highest.
- **The inference seed** → anchoring payoff is highest.
- **The stability surface** → annotating them decouples your module's inferred internals from callers, so internal refactors don't ripple type errors outward.

Bodies are read rarely, change often, and their types are usually obvious from context — so inference's concision wins there. Codify this: *required* annotations on exports, *discouraged* annotations on obvious locals.

### 3. The `auto` / `var` Debate, Resolved

This debate consumes endless code-review threads. The resolution is a single testable rule plus a linter:

- **Allow** inference when the type is *manifest on the line*: `var users = userRepo.findAll();`, `auto it = container.begin();`, `let cfg = Config::default();`. The reader sees the type without leaving the line.
- **Forbid** inference when the type is *not* manifest: `var x = process(input);` — the reader must chase `process`'s signature. Write the type.
- **Always** spell out the type when the *specific* type matters and the default would differ: numeric width, owning vs. borrowed (`auto` copies!), nullable vs. not.

The "almost always auto" camp (Herb Sutter) optimizes for not committing to a concrete type and for correctness (no implicit conversions); the "explicit" camp optimizes for diff-readability without an IDE. Both are right in their context — *server code reviewed in plain diffs* leans explicit; *template-heavy generic C++* leans `auto`. The professional move is to pick per-codebase and **enforce it with a linter**, ending the per-PR argument.

### 4. Engineering Error Quality

Inference's worst tax is bad error messages, and this is an *engineering* problem the language and the codebase both influence:

- **Language side:** Elm and Rust invested heavily in diagnostics — Elm rephrases unification failures in human terms; Rust points at both conflicting spans and suggests annotations. Terse compilers (older GHC, raw OCaml) dump unification internals.
- **Codebase side:** *you* improve error quality by annotating boundaries (localization), enabling stricter flags (`-Wall`, `-Werror`, `strict` in TS, `#![deny(warnings)]`), and adding type signatures as "tripwires" around tricky generic code so a mismatch is caught early and locally.

A team that treats "the error pointed at the wrong line" as inevitable is leaving hours on the table. Treat misleading errors as a signal to add an anchoring annotation upstream.

### 5. Diagnosing "Inference Gave the Wrong Type"

A recurring production-grade incident: the code compiled, but inference produced a type you didn't intend, and the bug surfaced far downstream. The professional diagnostic loop:

1. **Observe the actual inferred type.** Use the IDE (hover, rust-analyzer, TS quick-info) or force a deliberate error to make the compiler print it (`let _: () = the_value;`).
2. **Identify the divergence.** Compare inferred vs. intended. Common gaps: TS widened a literal to `string`; an empty container defaulted; a numeric literal took the wrong width; a `?` collapsed two branches to a least-upper-bound.
3. **Find the anchor point.** Where *should* the type have been pinned? Usually the nearest boundary or the literal that widened.
4. **Annotate there, re-check.** A single seed annotation usually both fixes the type and tightens every downstream error.

### 6. Inference and Codebase Stability / Refactorability

Inference is double-edged for large-scale change. **Pro:** change an implementation's internals and inferred local types follow automatically — no churn. **Con:** change a *boundary's* inferred type (because it wasn't annotated) and the new type silently flows to every caller, possibly compiling with subtly different behavior or erupting in errors across the codebase. The professional mitigation is exactly the boundary principle: **annotated public types are a contract that decouples a module's evolution from its consumers.** This is why large TS/Rust codebases enforce explicit boundary types — not for the compiler, but for *change management*.

### 7. Type-Driven Development: Inference as Assistant, Not Author

At scale, the most reliable workflow inverts the junior intuition. Instead of writing code and letting inference name everything, you **write the annotated type first** (the function signature, the data model) and let inference fill the *body* against that fixed target. The type *drives* the implementation; inference *assists within* it. The benefits compound: the boundary is documented and stable from day one, errors are localized from the start, and the body still enjoys concision. This is standard practice in Haskell, idiomatic in Rust and TS for public surfaces, and the discipline that separates "inference as a convenience" from "inference as part of a design method."

---

## Code Examples

### Policy as code: TypeScript module-boundary types (ESLint)

```jsonc
// .eslintrc — enforce the boundary principle in CI
{
  "rules": {
    // Exported functions MUST have explicit param + return types:
    "@typescript-eslint/explicit-module-boundary-types": "error",
    // No silent any (inference's escape hatch) anywhere:
    "@typescript-eslint/no-explicit-any": "error"
  }
}
```

```typescript
// Fails the lint — inferred boundary:
export function load(id) { return db.get(id); }        // ❌

// Passes — annotated boundary, inferred body:
export function load(id: string): Promise<User> {       // ✅
  const row = db.get(id);   // body inferred — fine
  return row.then(toUser);
}
```

### Forcing the compiler to reveal an inferred type (diagnostic trick)

```rust
// Make the compiler print what it inferred, on purpose:
let v = data.iter().map(|x| x.parse()).collect::<Vec<_>>();
let _: () = v;   // error: expected `()`, found `Vec<Result<i32, ...>>`
                 // — now you SEE the inferred type in the message.
```

```typescript
// TS: hover shows it, or trip an error to surface it:
const config = loadConfig();
const _assert: never = config;   // error reveals config's actual type
```

### The `auto`/`var` rule in practice (C++)

```cpp
// ALLOWED — type is manifest on the line:
auto it   = users.find(id);          // iterator — clear from .find
auto user = std::make_unique<User>();// type is in the expression

// DISCOURAGED — type is NOT manifest:
auto x = compute();                  // x is... ? reader must chase compute()
SomeResult x = compute();            // explicit: self-documenting

// REQUIRED explicit — auto would change meaning:
const std::string& name = obj.name();
auto copy = name;        // ⚠ COPY (auto strips &/const) — usually a bug
const auto& ref = name;  // ✅ bind by reference as intended
```

### Diagnosing a too-wide TypeScript inference in real code

```typescript
// Incident: a feature flag check silently never matches.
const FLAGS = { newCheckout: "on" };      // inferred { newCheckout: string }
function isOn(v: "on" | "off") { return v === "on"; }
// isOn(FLAGS.newCheckout)  // compiles? No — string not assignable.
// Worse variant: comparisons against widened strings that "look" fine.

// Fix: anchor the literal so the type matches intent.
const FLAGS2 = { newCheckout: "on" } as const;  // { readonly newCheckout: "on" }
isOn(FLAGS2.newCheckout);                        // ✅ type is "on"
```

### A misleading HM error whose real bug is elsewhere (Haskell)

```haskell
-- The compiler points HERE:
report xs = putStrLn ("total: " ++ show (total xs))
-- error: No instance for (Show ...) / couldn't match ... in `report`

-- ...but the real bug is in a DIFFERENT function:
total :: [Int] -> String     -- BUG: should return Int, not String
total = foldr (\x acc -> show x ++ acc) ""

-- Fix the upstream signature/impl; the downstream error vanishes.
-- Lesson: annotate `total` correctly and the error moves to its true home.
```

### Type-driven development: signature first, body inferred against it

```rust
// 1. Write the contract first (boundary, annotated):
pub fn dedup_sorted<T: Ord + Clone>(items: &[T]) -> Vec<T> {
    // 2. Body filled in; inference works AGAINST the stated return type.
    let mut out: Vec<T> = Vec::new();   // anchor where collect/new is ambiguous
    for x in items {
        if out.last() != Some(x) { out.push(x.clone()); }
    }
    out
}
```

---

## Coding Patterns

### Pattern 1: Encode the boundary principle in CI

Make "annotate exports" a lint error, not a review comment. The argument disappears once the linter owns it.

```jsonc
"@typescript-eslint/explicit-module-boundary-types": "error"
```

### Pattern 2: Seed one anchor to fix a cascade

```rust
// 20 errors at call sites → add ONE return-type-driven anchor:
let parsed: Vec<i32> = raw.iter().map(|s| s.parse().unwrap()).collect();
```

### Pattern 3: `as const` at every literal-data boundary (TS)

```typescript
export const EVENTS = ["click", "hover", "focus"] as const;
export type EventName = typeof EVENTS[number];
```

### Pattern 4: Tripwire annotations around tricky generics

```haskell
-- Put a signature on the helper so a mismatch is caught HERE, not at callers.
combine :: (Semigroup a) => [a] -> Maybe a
combine = foldr (\x acc -> Just (maybe x (x <>) acc)) Nothing
```

### Pattern 5: Reveal-then-fix for wrong inferred types

```typescript
// Force the compiler to print the inferred type, compare to intent, anchor.
const _reveal: never = suspiciousValue;  // read the error, then annotate source
```

---

## Best Practices

- **Make annotation policy explicit and enforced.** Write it in the style guide; encode it in the linter. "Annotate exports, infer locals" is a good default for nearly every team.
- **Treat a misleading error as a missing anchor, not bad luck.** When the compiler points at the wrong line, add a boundary annotation upstream and watch the error relocate to its real home.
- **Never let `auto`/`var` hide a type the reader needs.** The test is "is the type manifest on this line?" If not, write it.
- **Watch for inference that copies or widens.** C++ `auto` strips `&`/`const`; TS widens literals; Haskell defaults numerics. Annotate where the default differs from intent.
- **Adopt signature-first (type-driven) development for public surfaces.** Write the annotated contract, then fill the body. Documentation, localization, and stability come for free.
- **Use the compiler's strict modes.** `strict` (TS), `-Wall -Werror` (Haskell/GCC/Clang), `#![deny(warnings)]` (Rust). They convert silent inference surprises into actionable diagnostics.
- **Teach the team to *read the inferred type* (IDE hover, reveal trick) before trusting it.** Most "the type was wrong" incidents are caught in seconds this way.
- **Prefer languages/tools with good diagnostics for inference-heavy code,** and lean on their suggestions (Rust's "consider giving this a type annotation," Elm's rephrased errors).

---

## Edge Cases & Pitfalls

- **Inferred boundary types are an invisible API.** If a public function's return type is inferred, you can break consumers by a *change that still compiles locally*. Always annotate the public surface; it's a contract.
- **`auto` accidental copies in hot paths.** `for (auto x : bigThings)` copies each element. `for (const auto& x : bigThings)` doesn't. A performance bug born from convenience inference.
- **TS widening at config/edge boundaries.** Feature flags, action types, route tables inferred as `string`/`string[]` instead of literal unions — silent logic bugs. `as const` or annotate.
- **The error points at the wrong function.** HM/unification surfaces the clash at a *use*, often a different module than the buggy definition. Don't trust the line number; trace types, annotate the suspected boundary to relocate the error.
- **A small change floods the codebase with errors.** Editing an unannotated boundary's inferred type ripples to all callers at once. The flood usually has *one* root cause; annotate the boundary to localize it.
- **Defaulting masks intent in subtle ways.** Haskell numeric defaulting and TS structural widening "help" by guessing — until the guess is wrong and the bug is silent. Annotate when the default isn't what you mean.
- **Over-annotation is also a cost.** Annotating every obvious local buries the *meaningful* annotations (the boundaries) in noise and creates churn on refactors. Spend the annotation budget on boundaries.
- **Inference disagreements across compiler versions.** Widening rules, defaulting, and contextual-typing behavior evolve (TS especially). Code that relied on a particular inferred type can break on upgrade. Annotate the load-bearing types so upgrades don't shift them.

---

## Apply it

1. Define the user or business outcome that **Type Inference** should improve.
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

- Which measurable outcome justifies investing in Type Inference?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
