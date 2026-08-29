# Semantic Analysis — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Semantic Analysis** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Resolution as disambiguation, interleaved with inference

The junior/middle picture — "look the name up, get its declaration" — assumes each name has exactly one declaration. Modern languages routinely break that:

- **Overloading.** `print(int)`, `print(String)`, `print(Object)` all exist. The call `print(x)` must select one *based on the argument's type*. The algorithm collects a **candidate set** (all `print`s visible), filters to those *applicable* (each argument assignable to the corresponding parameter), then picks the **most specific** (a partial order: `print(String)` is more specific than `print(Object)` because `String <: Object`). Ambiguity (no unique best) is an error.
- **Traits / typeclasses / interfaces.** `x.area()` where `area` comes from a `Shape` trait: resolution must find the `impl Shape for Circle` (Rust), the `instance Shape Circle` (Haskell), or confirm `Circle` satisfies the `Shape` interface (Go). This is *not* a symbol-table lookup; it's a search over implementations, constrained by **coherence** (at most one impl per type/trait, enforced by orphan rules).

Crucially, resolution and type inference are **mutually dependent and often interleaved**. You can't pick the overload without the argument types; sometimes you can't fully infer an argument type without knowing which overload (and thus which expected parameter type) applies. Real compilers run a constraint-based loop: gather candidates, propagate the constraints each imposes, and converge. The clean phase separation of the senior level bends here — typing and resolution share a fixpoint.

### 2. Generics: check once, instantiate everywhere

A generic `fn max<T: Ord>(a: T, b: T) -> T` is type-checked **once**, against the *bound* `T: Ord` (the body may only use operations the bound guarantees — here, comparison). Then each *use site* `max(3, 4)` or `max("a", "b")` is checked by **instantiation**: substitute the concrete type for `T` and verify it satisfies the bound (`int: Ord`, `String: Ord`). Two semantic obligations:

- **Bound satisfaction at the use site.** `max(Point, Point)` errors if `Point` isn't `Ord`. The error is reported at the *call*, but it references the *declaration's* bound.
- **Variance.** Given `List<T>`, is `List<Cat> <: List<Animal>`? Depends on how `T` is used. If only produced (read), covariant; if only consumed (written), contravariant; if both, invariant. Getting variance wrong is a *soundness* hole (the classic Java array-covariance `ArrayStoreException`).

The *representation* decision — **monomorphization** (Rust, C++ templates: one specialized copy per type, fast but code-bloating) vs. **erasure** (Java: one copy, type arguments forgotten at runtime, small but limited) vs. **dictionary passing** (Haskell, Swift: pass the trait/witness as a hidden argument) — is partly a semantic-analysis decision because it determines what information the typed AST must carry into codegen.

### 3. Borrow checking is semantic analysis

Rust's borrow checker is the clearest demonstration that "semantic analysis" extends well past names and types into proving *safety properties*. After type checking, the borrow checker proves three things, all flow-sensitively over the CFG:

1. **No use-after-move.** Once a value is moved out of a variable, the source is invalid; reading it is an error. This is a *forward* analysis tracking which paths leave a place moved.
2. **Aliasing XOR mutation.** At any point, a place may have *many* shared borrows (`&`) *or* exactly *one* mutable borrow (`&mut`), never both. Overlapping conflicting borrows are an error.
3. **No dangling references.** A reference must not outlive the data it points to. This is the **lifetime/region** constraint: the borrow's region must be contained in the referent's.

Modern Rust uses **Non-Lexical Lifetimes (NLL)**: a borrow lives only over the program region where the reference is *actually used* (a liveness dataflow analysis), not until the end of its lexical scope. This is why code that the old lexical checker rejected now compiles — the borrow "ends" at its last use. Borrow checking is thus a *family of dataflow analyses* layered on the typed AST/MIR, and it's the senior-level CFG/dataflow machinery turned up to a memory-safety proof.

### 4. Access control and visibility

Name resolution across module boundaries must also enforce **visibility**: a name may be *resolvable* (it exists) yet *inaccessible* (private). The check has two parts — does the name exist in the target module, and is the referencing site permitted to see it? Languages encode visibility differently: Rust `pub`/`pub(crate)`, Java `public`/`protected`/`package`/`private`, C++ `public`/`protected`/`private` plus `friend`, Go's capitalization rule (exported iff the identifier starts uppercase). Subtleties: a `protected` member is accessible from subclasses but not arbitrary code; a `pub` field of a `pub(crate)` struct is only as visible as the struct; re-exports (`pub use`) can widen visibility deliberately. Access control runs *after* resolution finds the candidate and *before* (or alongside) type checking uses it.

### 5. Module / import resolution and separate compilation

Resolving names *across files* adds machinery beyond a single scope tree:

- **Import resolution.** `use foo::bar` / `import x.y.Z` / `from m import n` maps an external path to a symbol in another module's table. Glob imports (`use foo::*`) bring in many names and create **ambiguity** rules (a glob-imported name loses to an explicit local one).
- **Cyclic imports.** Module `A` imports `B` and `B` imports `A`. Languages handle this differently: some forbid it (Go errors on import cycles), some allow it with care (Python via deferred binding, Java freely since classes are resolved lazily). The resolver must detect cycles and either break them (two-phase: declare all module interfaces, then resolve bodies — the same collect-then-check pattern, now across modules) or report them.
- **Separate compilation.** Each module is analyzed against the *interfaces* (signatures) of its dependencies, not their bodies. This requires a stable **module interface artifact** (`.hi` files in GHC, `.rlib`/crate metadata in Rust, `.class` signatures in Java). Semantic analysis emits and consumes these interfaces; that's what makes incremental, parallel, and distributed builds possible.

### 6. Query-driven, incremental analysis

A batch front end recomputes the whole pipeline on each invocation — fine for `cc -c`, fatal for an editor that must respond in milliseconds per keystroke. The modern architecture inverts control: instead of *pushing* data through passes, the compiler *pulls* answers via **queries**:

```text
type_of(node) -> asks resolve(node) -> asks parse(file) -> ...
each query result is MEMOIZED ; an edit INVALIDATES only the queries whose
inputs changed, and transitively their dependents.
```

`rustc` is built on a query system (with Salsa-style incrementality in `rust-analyzer`); Roslyn uses **red-green trees** (immutable green nodes shared across edits, red nodes for position); Swift uses a request-evaluator. The semantic facts — `type_of`, `resolve`, `borrowck`, `is_exhaustive` — become memoized queries with tracked dependencies. The win: edit one function body and only that function's (and its dependents') analyses rerun. This is the single biggest architectural difference between a 1990s batch compiler and a 2020s language server, and it reshapes how every check above is structured (each must be expressible as a pure, memoizable function of its inputs).

### 7. The handoff to code generation

This is where the entire topic lands. After all analysis succeeds, semantic analysis produces the artifact codegen consumes — typically a **typed, decorated AST** or a **typed IR** in which:

- Every `Name` node has a **resolved binding** to a concrete declaration (across modules).
- Every expression has a **concrete type** — for generics, the *instantiated* type (post-monomorphization) or enough info to do erasure/dictionary passing.
- Every method/overload call is **resolved to a specific target** (the exact `impl`, the exact overload, the exact vtable slot), so codegen never re-disambiguates.
- Every coercion (widening, boxing, deref) is made **explicit** as an inserted node, so codegen doesn't infer them.
- Verified properties (exhaustiveness, definite assignment, borrow safety) are *assumed*, letting codegen omit runtime checks the front end already proved unnecessary.

The contract is the same one stated since the junior page, now precise: **codegen trusts that the front end proved validity, and the decorated artifact carries every decision codegen needs so the back end can be a mechanical lowering.** The "decorate the AST; codegen consumes the typed AST" promise is fulfilled here.

---

## Code Examples

### Example 1: Overload resolution — candidates, applicable, most specific

```python
def resolve_overload(name, arg_types, scope):
    candidates = scope.lookup_all(name)          # ALL decls with this name
    applicable = [c for c in candidates
                  if len(c.params) == len(arg_types)
                  and all(assignable(a, p) for a, p in zip(arg_types, c.params))]
    if not applicable:
        error(f"no overload of '{name}' matches ({', '.join(arg_types)})")
        return ERROR_CANDIDATE
    # "most specific": c1 beats c2 if every c1 param is assignable to the c2 param
    def more_specific(c1, c2):
        return all(assignable(p1, p2) for p1, p2 in zip(c1.params, c2.params))
    best = [c for c in applicable
            if all(more_specific(c, other) for other in applicable if other is not c)]
    if len(best) != 1:
        error(f"ambiguous call to '{name}'; candidates: {applicable}")
        return ERROR_CANDIDATE
    return best[0]
```

```text
print(String) , print(Object)   and a call print(someString)
  candidates  = both
  applicable  = both (String assignable to String AND to Object)
  most specific = print(String)   (String <: Object, so String beats Object)
```

The "most specific" partial order is where the real subtlety lives: with multiple parameters it can be a tie (one overload better on arg 1, the other on arg 2) → genuine ambiguity → error. C++, Java, and Swift each have pages of rules refining this.

### Example 2: Trait resolution with a coherence (orphan) check

```python
# A trait impl registry, keyed by (trait, type). Coherence = at most one entry.
class ImplRegistry:
    def __init__(self): self.impls = {}            # (trait, type) -> impl

    def register(self, trait, ty, impl, local_crate):
        # Orphan rule: you may only impl a trait for a type if YOU define
        # the trait OR the type. Prevents two crates adding conflicting impls.
        if not (trait.crate == local_crate or ty.crate == local_crate):
            error(f"orphan impl: neither {trait} nor {ty} is local")
            return
        key = (trait, ty)
        if key in self.impls:
            error(f"conflicting impls of {trait} for {ty}")   # coherence violation
            return
        self.impls[key] = impl

    def resolve_method(self, ty, method):
        for (trait, t), impl in self.impls.items():
            if t == ty and method in impl.methods:
                return impl.methods[method]      # the unique target for codegen
        error(f"no method '{method}' for type {ty}")
        return ERROR
```

Coherence (one impl per `(trait, type)`) is what lets `x.area()` resolve to a *single* concrete function — without it, two libraries could each define `Shape for Circle` and the call would be ambiguous *globally*. The orphan rule is the mechanism that guarantees coherence under separate compilation.

### Example 3: Generic instantiation with bound checking

```python
def check_generic_call(decl, type_args, arg_types):
    # decl: fn max<T: Ord>(a: T, b: T) -> T
    subst = dict(zip(decl.type_params, type_args))     # T -> concrete

    # 1) every type argument must satisfy its bound
    for tp, ty in subst.items():
        for bound in tp.bounds:                         # e.g. Ord
            if not satisfies(ty, bound):
                error(f"`{ty}` does not satisfy bound `{bound}` "
                      f"required by `{decl.name}`")
    # 2) the (substituted) parameter types must accept the arguments
    for at, pt in zip(arg_types, decl.params):
        expected = substitute(pt, subst)                # T -> ty
        if not assignable(at, expected):
            error(f"argument `{at}` not assignable to `{expected}`")
    # 3) the call's result type is the substituted return type
    return substitute(decl.ret, subst)
```

```text
max(3, 4)        T=int   ; int: Ord ? yes  ; result int
max(p1, p2)      T=Point ; Point: Ord ? NO  -> error AT THE CALL,
                                              citing max's `T: Ord` bound
```

The error is reported at the use site but references the declaration's contract — the hallmark of generics: the body was checked once against the bound; each instantiation re-checks the bound.

### Example 4: Borrow checking — aliasing XOR mutation (sketch)

```python
# Flow-sensitive: at each program point, track live borrows of each place.
# Rule: a place may have many SHARED borrows OR one MUT borrow, never both.

def check_borrows(cfg):
    for point in cfg.points():
        live = live_borrows_at(point)        # NLL: borrows whose last use is >= here
        for place in places_touched_at(point):
            muts    = [b for b in live if b.place == place and b.kind == "mut"]
            shareds = [b for b in live if b.place == place and b.kind == "shared"]
            if muts and (shareds or len(muts) > 1):
                error(f"cannot borrow `{place}` mutably while it is also borrowed",
                      point.span)
            if accesses_moved(place, point):
                error(f"use of moved value `{place}`", point.span)
```

```rust
let mut v = vec![1, 2, 3];
let r = &v[0];        // shared borrow of v, lives until r's last use
v.push(4);            // ERROR: needs &mut v, but a shared borrow (r) is still live
println!("{}", r);    // r's last use -> under NLL the shared borrow ends HERE
```

Move `println!` *above* `v.push(4)` and it compiles: NLL ends the shared borrow at `r`'s last use, so the mutable borrow no longer overlaps. Borrow checking is precisely this overlap analysis over the CFG with liveness.

### Example 5: Cross-module resolution with visibility

```python
def resolve_path(path, current_module, modules):
    # path like  foo::bar::Baz
    mod = modules[path.head]                        # resolve the module
    for segment in path.middle:
        mod = mod.submodule(segment) or error_undef(segment)
    sym = mod.lookup(path.last)
    if sym is None:
        error(f"no `{path.last}` in module `{mod.name}`")
        return ERROR
    if not visible_from(sym, current_module):       # resolvable != accessible
        error(f"`{path.last}` is private to `{mod.name}`")
        return ERROR
    return sym

def visible_from(sym, site):
    if sym.visibility == "public":   return True
    if sym.visibility == "crate":    return site.crate == sym.crate
    if sym.visibility == "private":  return site.module == sym.module
```

The two-step — find it, *then* check you're allowed to see it — is universal. A common bug is conflating the two: reporting "no such name" for a name that exists but is private produces a misleading diagnostic; "exists but is private" is the right message.

### Example 6: A query-driven type_of with memoization

```python
class QueryEngine:
    def __init__(self):
        self.cache = {}              # query -> result
        self.deps  = {}              # query -> set of queries it read

    def type_of(self, node):
        if node in self.cache:
            return self.cache[node]
        deps = set()
        ty = self._compute_type(node, deps)   # records sub-queries into `deps`
        self.cache[node] = ty
        self.deps[node]  = deps
        return ty

    def invalidate(self, changed_node):
        # invalidate the node and everything transitively depending on it
        dirty = {changed_node}
        for q, ds in self.deps.items():
            if ds & dirty:
                dirty.add(q)
                self.cache.pop(q, None)
```

Real systems (Salsa, rustc's query engine) track a revision counter and verify dependencies by re-running cheap "is this still valid?" checks rather than naive transitive invalidation, but the shape is this: *compute on demand, memoize, invalidate by dependency*. Every check in this topic — resolution, typing, borrow check, exhaustiveness — becomes such a query.

### Example 7: The handoff — a typed, fully-resolved IR node

```text
Before analysis (parser AST):
    Call { callee: Name("max"), args: [Int(3), Int(4)] }

After semantic analysis (typed, resolved artifact for codegen):
    Call {
        target:    max$int            # monomorphized instance, ONE concrete fn
        callee_ty: fn(int, int) -> int
        args:      [ Int(3): int, Int(4): int ]
        result_ty: int
        coercions: []                 # none needed; explicit if there were
    }
```

Everything codegen could possibly need to decide has been decided: the *exact* function (`max$int`, the `int` monomorphization), the concrete types on every node, no remaining overload/trait ambiguity, coercions made explicit. Codegen lowers this mechanically to machine code or bytecode — it never re-runs resolution or typing. That is the contract semantic analysis exists to deliver.

---

## Coding Patterns

- **Candidate-filter-rank.** Resolution = gather candidates, filter to applicable, rank by specificity, demand a unique best. Every overload/trait resolver has this shape.
- **Constraint loop for resolution+inference.** When picking an overload needs argument types and inferring an argument needs the overload, gather constraints and iterate to a fixpoint rather than forcing an order.
- **Substitution for generics.** Represent instantiation as a substitution map `type_param -> concrete`; apply it to parameter and return types; check bounds before applying.
- **Dataflow for safety.** Reuse the CFG/dataflow engine for borrow checking (liveness of borrows, moved-out places) exactly as for definite assignment.
- **Two-step resolution then access.** Resolve the name; *then* check visibility. Keep them separate for accurate diagnostics.
- **Two-phase module resolution.** Declare all module interfaces, then resolve bodies — collect-then-check raised to the module level, which also breaks import cycles.
- **Query + memoize + invalidate.** Express each check as a pure function of memoized inputs with tracked dependencies for incrementality.
- **Lower ambiguity away before codegen.** Resolve every call to a concrete target and insert explicit coercions so the back end has no choices left.

---

## Clean Code

- **One registry per resolution concern.** A trait/impl registry, an overload set per name — explicit structures, not logic smeared through the type checker.
- **Diagnostics that explain the ranking.** "ambiguous: candidates `print(int)` and `print(long)` both apply" beats "ambiguous call." Show the candidates and why none won.
- **Separate "resolvable" from "accessible" in messages.** Privacy errors and undefined-name errors are different user problems; never collapse them.
- **Make instantiation explicit in the IR.** A monomorphized call should name its instance (`max$int`), not leave codegen to recompute it. The artifact should be self-describing.
- **Keep queries pure.** No hidden global mutation inside a query; its result must be a function of its declared inputs, or incremental invalidation silently goes wrong.
- **Insert coercions as real nodes.** A widening or auto-deref should appear as an explicit `Coerce` node, not an implicit assumption codegen must rediscover.

---

## Best Practices

| Practice | Why |
|---|---|
| Model resolution as candidate→applicable→most-specific | The only robust way to handle overloading/traits |
| Enforce coherence via orphan rules | Guarantees a single global impl under separate compilation |
| Check generic bounds at the use site, citing the declaration | Errors land where the user can fix them, with the right reason |
| Get variance right; it is a soundness property | Wrong variance is an unsoundness, not a cosmetic bug |
| Implement borrow/ownership checks as CFG dataflow with NLL | Precise, accepts more safe programs than lexical scoping |
| Resolve names, then enforce visibility, as distinct steps | Accurate "undefined" vs. "private" diagnostics |
| Use two-phase (interface-first) module resolution | Handles cycles and enables separate compilation |
| Structure the front end as memoized queries | Keystroke-latency incremental analysis for tooling |
| Emit module interface artifacts | Enables incremental, parallel, distributed builds |
| Make the codegen handoff fully resolved and explicit | A dumb, fast, trustworthy back end |

---

## Edge Cases & Pitfalls

- **Overload ambiguity from numeric/implicit conversions.** `f(int)` and `f(long)` called with a literal that converts to both — ambiguous unless the language's conversion ranking breaks the tie. These rules are language-specific and a frequent source of surprising errors.
- **Trait method vs. inherent method shadowing.** A type's own method can shadow a trait method of the same name; resolution must prefer the inherent one (Rust) or follow defined precedence — easy to get backwards.
- **Variance unsoundness.** Treating `List<T>` as covariant when it has a mutating method opens `ArrayStoreException`-style holes. Mutable containers must be invariant in their element type.
- **Borrow checker rejecting safe code.** Some provably-safe programs don't fit the analysis (especially before NLL, and around self-referential structures). The fix is sometimes `unsafe` or a redesign — the checker is *conservative*, not omniscient.
- **Self-referential / cyclic data and lifetimes.** A struct holding a reference into itself defeats simple region inference; needs `Pin`, arenas, or indices instead of references.
- **Glob-import collisions.** Two `use a::*; use b::*;` both bringing `Foo` — only an *error if `Foo` is actually used*; mere ambiguity in scope is tolerated until referenced. Resolving this lazily vs. eagerly changes the diagnostics.
- **Cyclic module imports.** Eager resolution deadlocks/loops; you need the two-phase interface-first approach or explicit cycle detection.
- **Incremental invalidation that's too coarse or too fine.** Too coarse → no speedup; too fine but unsound (missing a dependency) → stale, wrong results. Dependency tracking must be exact.

---

## Common Mistakes

1. Treating method/operator resolution as a plain symbol-table lookup when overloading or traits are involved.
2. Sequencing resolution strictly after inference when the two are mutually dependent, then failing on cases that need the loop.
3. Checking generic bounds only at the declaration, not at each instantiation — accepting `max(Point, Point)` for a non-`Ord` `Point`.
4. Getting variance wrong on mutable containers, introducing a soundness hole.
5. Implementing borrow/ownership checks with lexical scopes instead of NLL, rejecting far more safe code than necessary.
6. Conflating "name doesn't exist" with "name is private," producing misleading diagnostics.
7. Resolving imports eagerly and looping on cyclic modules instead of two-phasing.
8. Building a batch-only front end, then being unable to deliver IDE-grade incrementality.
9. Leaving overload/trait/generic decisions unresolved in the AST handed to codegen, forcing the back end to re-disambiguate.
10. Implicit coercions assumed rather than inserted as explicit nodes, so codegen and the type checker can disagree.
11. Impure queries (hidden global mutation) that break incremental invalidation invisibly.

---

## Tricky Points

- **Resolution and inference are a fixpoint, not a sequence.** The textbook "resolve then type" order is a simplification; real languages with overloading + inference interleave them, which is why their specifications are so intricate.
- **The orphan rule exists for coherence, not bureaucracy.** It's what makes "there is exactly one `impl Shape for Circle` in the whole program" *provable* without whole-program analysis — essential for separate compilation.
- **Monomorphization vs. erasure is a semantic decision with runtime consequences.** It dictates whether type arguments survive to runtime (reflection, specialization) and whether the typed IR must carry concrete instances. It's chosen during analysis, not codegen.
- **Borrow checking moved from lexical to non-lexical because lexical was needlessly conservative.** NLL reframes lifetimes as a *liveness dataflow* result — the same machinery as senior-level analyses — which is why it accepts strictly more programs while staying sound.
- **Visibility is checked late and is path-sensitive.** A `pub` item inside a private module is effectively private from outside; effective visibility is the *minimum* along the access path, not the item's own modifier.
- **Incrementality reshapes everything.** Designing checks as pure, memoizable queries is not an optimization bolted on at the end; it changes how you structure resolution, typing, and even diagnostics from the start.
- **The handoff is the whole point.** Every clever check exists so codegen can be trivial. If the back end still has to make semantic decisions, the front end didn't finish its job.

---

## Apply it

1. Define the user or business outcome that **Semantic Analysis** should improve.
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

- Which measurable outcome justifies investing in Semantic Analysis?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
