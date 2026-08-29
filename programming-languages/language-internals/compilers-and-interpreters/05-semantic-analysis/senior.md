# Semantic Analysis — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Semantic Analysis** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Attribute grammars: the formal shape of the whole phase

Semantic analysis is, formally, the evaluation of an **attribute grammar**. Each grammar production has *semantic rules* that compute attributes on the parse/AST nodes. There are two flows:

- **Synthesized attributes** flow *up*. A node computes them from its children. The type of `a + b` from the types of `a` and `b` is synthesized. So is "this block returns on all paths" computed from its statements.
- **Inherited attributes** flow *down*. A node receives them from its parent or context. The *expected type* of an expression (from the variable it's assigned to), the *current function's return type*, "are we inside a loop?", and the symbol table in scope are all inherited.

```text
            assignment  (inherited: nothing; synthesized: void)
           /          \
   target:Name      value:Expr
   syn type=Float    INHERITED expected=Float ──┐
                     syn type=Int               │
                     check: assignable(Int,Float)? yes (widen)
                     └────── synthesized flows up; expected flows down
```

Why this matters: the number of passes you need is determined by how attributes depend on each other. If everything is synthesized (**S-attributed**), one bottom-up pass suffices. If inherited attributes depend only on the parent and left siblings (**L-attributed**), one left-to-right depth-first pass suffices — and most practical checkers are L-attributed by construction (the symbol table and expected type are exactly such inherited attributes). When attributes have cyclic or right-to-left dependencies (a name used before its definition, mutually recursive types), you need *multiple passes* or a fixpoint. The synthesized/inherited vocabulary is how compiler engineers *talk about* and *plan* the number and order of passes.

### 2. Bidirectional type checking: synthesis meets checking

The middle-level checker was pure synthesis: every expression computed its own type upward. Real languages need the other direction too. Consider an empty array literal:

```text
let xs: List<int> = [];
```

`[]` has no inherent element type — synthesis alone yields `List<?>`. But the annotation `List<int>` is an *inherited* expected type pushed down. **Bidirectional type checking** formalizes this: two judgments, *synthesize* (`e ⇒ T`, infer the type up) and *check* (`e ⇐ T`, verify against an expected type down). Lambdas, literals, `null`/`None`, and generic calls are checked against an expected type; variables, applications, and annotated expressions synthesize. This is how TypeScript, Rust, Swift, and Kotlin do local inference without full global unification, and it maps perfectly onto inherited (expected type, down) plus synthesized (actual type, up) attributes.

### 3. Phase ordering: the pipeline of passes

A maintainable front end is a sequence of passes, each with a contract:

```text
Pass 0  Parse                 -> AST with spans
Pass 1  Collect declarations  -> top-level names/types in symbol table (no bodies)
Pass 2  Resolve type refs     -> every type annotation resolved to a real type
Pass 3  Resolve names (bodies) -> every Name node has a binding
Pass 4  Type-check            -> every expression has a type; assignability checked
Pass 5  Control-flow checks   -> definite assignment, reachability, exhaustiveness
Pass 6  Lower / decorate      -> typed AST handed to IR generation
```

The dependencies are real: you cannot type-check a body (4) before type references in signatures are resolved (2); you cannot run definite assignment (5) before names and types are known (3, 4). Collapsing passes for speed is the usual source of "works until the language grows a feature." Separating them makes each pass a small, testable function with a precondition it can assert. Mutually recursive declarations are exactly why passes 1–2 precede 3–4: collect *all* signatures, *then* check bodies.

### 4. Control flow is a graph, and some checks live on it

Scoping answers "is this name visible here?" It cannot answer "is this variable assigned on every path that reaches this read?" or "can this statement ever execute?" Those are **control-flow** questions, and they require a **control-flow graph (CFG)**: basic blocks (straight-line code) connected by edges for branches, loops, returns, and exceptions.

```text
   x = ?            B0: enter
   if c             B0 -> B1 (c true), B0 -> B2 (c false)
   B1: x = 1        B1 -> B3
   B2: (nothing)    B2 -> B3
   B3: use(x)       is x assigned on every path into B3?
                    path through B2 never assigned x -> ERROR
```

You build the CFG from the AST (or from a lowered IR), then run **dataflow analysis**: each program point gets a set of facts, computed by iterating to a fixpoint over the graph.

### 5. Definite assignment as forward dataflow

Definite assignment (Java, C#) is a *forward, must* dataflow problem. The fact at each point is "the set of locals definitely assigned on *every* path reaching here." Transfer functions:

- An assignment `x = e` adds `x` to the out-set.
- A read of `x` requires `x` in the in-set, else it's an error.
- At a merge point (after `if`/loops), the in-set is the **intersection** of predecessors' out-sets — "must" analysis: assigned only if assigned on *all* incoming paths.

For loops you iterate to a fixpoint (the back-edge feeds the loop head's in-set). The middle-level "intersect the branches" trick was this analysis specialized to a single `if`; the senior version handles loops, early returns, `break`/`continue`, and `throw` by giving each its correct CFG edges (e.g., a `return` has no edge to the following statement, which is exactly why code after it is unreachable).

### 6. Reachability and dead-code detection

Reachability is the dual question, computed on the same CFG: a statement is **reachable** if some path from entry reaches its block. After an unconditional `return`, `break`, `continue`, `throw`, or an infinite loop with no `break`, the following statements are **unreachable**. Languages differ on severity: Java makes unreachable statements a *compile error*; Rust and Go warn (Go errors on "missing return" but warns on some dead code via vet); C is silent in the standard but compilers warn. Reachability also feeds the "missing return" check: a value-returning function is valid only if control cannot *fall off the end* — i.e., the exit block is unreachable or every path returns.

### 7. Exhaustiveness checking for pattern matching

`match`/`switch` over a sum type (enum, ADT, sealed class) should cover every case. **Exhaustiveness** is the check that it does; it is computed by a *usefulness* algorithm (Maranget's): for the implicit "wildcard" arm after the user's arms, ask "is there any value the existing arms don't match?" If yes, the match is non-exhaustive and you can even synthesize a *witness* — a concrete uncovered pattern — for the diagnostic.

```rust
enum Shape { Circle, Square, Triangle }
match s {
    Shape::Circle => ...,
    Shape::Square => ...,
    // ERROR: non-exhaustive; `Triangle` not covered
}
```

The same algorithm catches **unreachable arms** (an arm matched entirely by earlier arms is "useless") and **redundant guards**. Rust, OCaml, Haskell, and Swift do this; C-style `switch` historically does not, which is why `default:` and `-Wswitch` exist. Exhaustiveness is a synthesized property of the match node computed from its arms and the scrutinee's type — and it's a major safety feature: adding a variant to the enum makes every non-exhaustive match a compile error, forcing you to handle the new case.

### 8. Error recovery at three granularities

The middle-level `ErrorType` recovers within an *expression*. A senior checker recovers at three levels:

- **Expression level.** Poison the node with `ErrorType`; every rule short-circuits on it. (Already covered.)
- **Statement level.** A statement with an unrecoverable error is *skipped* — analyze the next statement with the scope state unchanged. A malformed `let x =` (no initializer) still inserts `x` with `ErrorType` so later uses resolve.
- **Declaration level.** A function whose signature is malformed still gets inserted with a best-effort signature (parameters typed `ErrorType`), so calls elsewhere don't cascade. A type referencing an undefined type resolves to `ErrorType`, and *fields of that type* still get checked.

The unifying principle is **salvage**: at every failure, substitute the most plausible value (`ErrorType`, a synthetic symbol, a recovered signature) so that *subsequent* analysis proceeds and finds *independent* errors, while the poison sentinel keeps *dependent* errors silent. The metric of a good recovery strategy: error count tracks the number of *independent* mistakes, not the depth of the AST.

### 9. The output contract: a fully decorated, validated AST

After all passes, the AST is decorated: every `Name` has a binding, every expression a type, every `match` a verified-exhaustive flag, every block a "returns-on-all-paths" bit. Equally important is the *contract* the front end gives the back end: **if there were no errors, every invariant codegen relies on holds** — names resolve, types are consistent, control flow is well-formed. Codegen then never needs to handle "what if undefined" — it trusts the front end. (If there *were* errors, the front end typically stops before codegen; the decorated-but-poisoned AST exists only to maximize diagnostics, not to be compiled.)

---

## Code Examples

### Example 1: Inherited "expected type" — bidirectional checking

```python
def check(node, expected):           # `expected` is an INHERITED attribute (down)
    if node.kind == "ArrayLit":
        if expected and expected.is_list():
            elem = expected.elem
            for e in node.elements:
                check(e, elem)        # push element type DOWN
            node.type = expected      # adopt the expected type
            return node.type
        # no expectation: synthesize from elements, or error if empty
        if not node.elements:
            error("cannot infer type of empty array", node.span)
            node.type = ERROR; return ERROR
        t = synth(node.elements[0])
        for e in node.elements[1:]:
            if not assignable(synth(e), t):
                error("array elements have differing types", e.span)
        node.type = List(t); return node.type
    # ... other forms fall back to synth() ...

def synth(node):                      # SYNTHESIZED type (up), no expectation
    return check(node, expected=None)
```

`let xs: List<int> = []` calls `check([], List<int>)`: the inherited `List<int>` supplies the element type that synthesis alone couldn't produce. This is the inherited/synthesized split made concrete.

### Example 2: A pass pipeline with explicit contracts

```python
def analyze(program):
    diags = Diagnostics()
    table = SymbolTable()

    collect_declarations(program, table, diags)   # post: top-level names present
    resolve_type_refs(program, table, diags)      # pre: names present; post: types resolved
    resolve_names(program, table, diags)          # pre: types resolved; post: bindings set
    type_check(program, diags)                     # pre: bindings set; post: every expr typed
    control_flow_checks(program, diags)            # pre: typed; checks DA, reachability, match
    return diags  # if empty, the AST is a valid, decorated input for codegen
```

Each function asserts its precondition (e.g., `type_check` asserts every `Name` has a binding) so a contract violation fails loudly during development instead of producing a mysterious crash three passes later.

### Example 3: Definite assignment as forward dataflow

```python
# Forward MUST analysis: fact = set of locals assigned on EVERY path to a point.

def definite_assignment(cfg, diags):
    IN  = {b: set() for b in cfg.blocks}
    OUT = {b: set() for b in cfg.blocks}
    IN[cfg.entry] = set()

    changed = True
    while changed:                                # iterate to fixpoint (handles loops)
        changed = False
        for b in cfg.blocks_in_rpo():             # reverse postorder converges fast
            preds = cfg.predecessors(b)
            new_in = (set.intersection(*[OUT[p] for p in preds])  # MUST = intersect
                      if preds else set())
            new_out = transfer(b, new_in, diags)  # add assignments; check reads
            if new_in != IN[b] or new_out != OUT[b]:
                IN[b], OUT[b] = new_in, new_out
                changed = True

def transfer(block, assigned_in, diags):
    assigned = set(assigned_in)
    for stmt in block.stmts:
        for use in reads_of(stmt):
            if use.local and use.name not in assigned:
                diags.error(f"variable '{use.name}' may not be assigned", use.span)
        if stmt.kind == "Assign" and stmt.target.is_local:
            assigned.add(stmt.target.name)
    return assigned
```

The intersection at merges is the "must on every path" rule; the fixpoint loop is what lets it handle loops correctly (a `break` out of a loop and a back-edge into it both contribute edges). The middle-level single-`if` version is this with one merge and no iteration.

### Example 4: Reachability and the "missing return" check (Go-flavored)

```go
// A block "completes normally" if control can flow off its end.
// A value-returning function is well-formed iff its body does NOT complete normally.

func completesNormally(s Stmt) bool {
    switch s := s.(type) {
    case *Return, *Break, *Continue, *Throw:
        return false                       // these transfer control away
    case *Block:
        for i, inner := range s.Stmts {
            if !completesNormally(inner) {
                if i < len(s.Stmts)-1 {
                    diag(s.Stmts[i+1].Span(), "warning", "unreachable code")
                }
                return false               // a non-completing stmt ends the block
            }
        }
        return true
    case *If:
        if s.Else == nil {
            return true                    // no else: the false path completes
        }
        return completesNormally(s.Then) || completesNormally(s.Else)
    case *Infinite: // for {}  with no break
        return false
    default:
        return true
    }
}

func checkReturns(fn *Func) {
    if fn.ReturnType != Void && completesNormally(fn.Body) {
        diag(fn.Body.CloseBrace, "error", "missing return")
    }
}
```

`completesNormally` is a synthesized attribute over statements, and "missing return" falls straight out of it: a non-void function whose body *can* complete normally has a path with no `return`.

### Example 5: Exhaustiveness via usefulness, simplified

```python
# Sum type `T` has a known finite set of constructors.
# A match is exhaustive iff a wildcard arm AFTER the user's arms would be USELESS
# (i.e., the user's patterns already cover everything).

def missing_cases(scrutinee_type, arms):
    if scrutinee_type.is_enum():
        all_ctors = set(scrutinee_type.constructors)        # e.g. {Circle,Square,Triangle}
        covered = set()
        for arm in arms:
            if arm.pattern.is_wildcard():
                return set()                                 # wildcard covers the rest
            covered.add(arm.pattern.constructor)
        return all_ctors - covered                           # uncovered = a witness set
    if scrutinee_type.is_bool():
        needed = {True, False}
        return needed - {a.pattern.value for a in arms if a.pattern.is_literal()}
    # for open/infinite types (int, string) a wildcard is REQUIRED
    if not any(a.pattern.is_wildcard() for a in arms):
        return {"_"}    # needs a default
    return set()

def check_match(node):
    missing = missing_cases(node.scrutinee.type, node.arms)
    if missing:
        node.exhaustive = False
        error(f"non-exhaustive match; missing: {sorted(missing)}", node.span)
    else:
        node.exhaustive = True
    # also flag arms that can never match (useless), omitted for brevity
```

The real algorithm (Maranget) handles nested patterns, ranges, and guards via matrix specialization, but the principle is identical: compute what's left uncovered, and if nonempty, that set *is* the diagnostic's witness. The synthesized `node.exhaustive` flag is what later phases (and the safety guarantee "adding a variant breaks the build") rely on.

### Example 6: Statement- and declaration-level recovery

```python
def analyze_decl(decl, table, diags):
    if decl.kind == "Func":
        # Salvage a signature even if a parameter type is undefined,
        # so CALLS to this function elsewhere don't cascade.
        params = []
        for p in decl.params:
            ty = resolve_type(p.type_ann, table, diags)   # may report + return ERROR
            params.append(ty)                              # ERROR is a fine placeholder
        ret = resolve_type(decl.ret_ann, table, diags) if decl.ret_ann else VOID
        table.insert(Symbol(decl.name, "func", FuncType(params, ret), decl.span))
        # Body errors are INDEPENDENT of signature errors; check the body regardless.
        try:
            check_body(decl.body, FuncType(params, ret), table, diags)
        except UnrecoverableStmt:
            pass   # skip the rest of the body; we already inserted the signature

def analyze_block(block, table, diags):
    for stmt in block.stmts:
        try:
            analyze_stmt(stmt, table, diags)
        except UnrecoverableStmt as e:
            diags.error(e.message, e.span)
            # SKIP this statement, keep the scope, continue with the next one
            continue
```

The design rule: a failure in one declaration or statement must not prevent analysis of the *independent* ones. Salvage the broken piece, keep the scope consistent, move on.

---

## Coding Patterns

- **Attribute threading.** Pass inherited attributes (expected type, return type, in-loop, symbol table) *down* as parameters or a context object; return synthesized attributes (type, completes-normally) *up*.
- **Check vs. synthesize split.** Two entry points: `check(node, expected)` and `synth(node)`. Literals, lambdas, and empty collections route to `check`; variables and applications to `synth`.
- **Pass contracts as assertions.** Each pass asserts its precondition at entry. Cheap; catches phase-ordering bugs immediately.
- **CFG once, many analyses.** Build the CFG a single time; run definite assignment, reachability, and any other flow check over the same graph.
- **Fixpoint with reverse postorder.** Iterate dataflow over blocks in RPO for fast convergence; loop until no set changes.
- **Witness-producing checks.** When a check fails, produce a concrete counterexample (an uncovered pattern, an unassigned-on-this-path variable) for the diagnostic, not just a boolean.
- **Salvage at every failure.** On any error, substitute a plausible value (`ErrorType`, recovered signature, synthetic symbol) and continue.

---

## Clean Code

- **One pass, one file/function, one contract.** Resist merging passes "for speed." Each pass should be readable in isolation with its pre/postcondition documented at the top.
- **Make the CFG a first-class structure,** not implicit in the recursion. Flow checks are far clearer as explicit graph algorithms than as ad-hoc flags threaded through a tree walk.
- **Separate "report" from "decide."** A check function decides (returns the missing cases, the unassigned reads); a thin layer turns decisions into diagnostics. This keeps checks unit-testable without a diagnostics sink.
- **Inherited attributes are explicit parameters, not globals.** Threading `expected` and `return_type` as parameters keeps each node's rule self-contained and reentrant.
- **Name the recovery substitutions.** `ErrorType`, `RECOVERED_SIGNATURE`, `SYNTHETIC_SYMBOL` — distinct, greppable sentinels make the recovery strategy auditable.
- **Witnesses in messages.** "non-exhaustive; missing `Triangle`" beats "non-exhaustive match." The witness you already computed *is* the better message.

---

## Best Practices

| Practice | Why |
|---|---|
| Frame the design in synthesized/inherited terms before coding | Tells you how many passes and which direction info flows |
| Use bidirectional checking for local inference | Handles empty literals, lambdas, generics without global unification |
| Order passes by dependency and assert preconditions | Prevents "works until a feature is added" phase-ordering bugs |
| Do flow checks on a CFG, not via tree-walk flags | Correctly handles loops, breaks, early returns, throws |
| Iterate dataflow to a fixpoint in reverse postorder | Correct for loops; converges quickly |
| Compute and report witnesses (uncovered case, unassigned path) | Turns vague errors into actionable ones |
| Recover at expression, statement, AND declaration level | Error count tracks real mistakes, not AST depth |
| Salvage with plausible substitutes; never throw past one error | Maximizes independent diagnostics; never crashes |
| Stop before codegen if any error occurred | The poisoned AST is for diagnostics, not compilation |
| Make exhaustiveness an error, not a warning, for sealed types | Adding a variant should break every unhandled match |

---

## Edge Cases & Pitfalls

- **Mutually recursive declarations.** `A` references `B` and `B` references `A`. A single pass fails on whichever comes first. Collect *all* signatures (pass 1) before checking any body (pass 4).
- **Definite assignment across loops.** A naive single pass mishandles a variable assigned inside a loop body but read after. You need the fixpoint with the back-edge contributing to the loop head's in-set.
- **`break`/`continue`/`throw` edges in the CFG.** Forgetting these makes reachability and definite assignment wrong: code after a `throw` is unreachable; a `break` skips the rest of the loop body.
- **Exhaustiveness with guards.** `Some(x) if x > 0 =>` does *not* cover all `Some`, because the guard can fail. A guarded arm cannot make a match exhaustive on its own.
- **Inherited type from a poisoned context.** If the expected type is `ErrorType`, *checking* against it must succeed silently (don't report a mismatch against a type that's already an error).
- **Reachability vs. "obviously infinite" loops.** `while (true) {}` makes the following code unreachable, but `while (cond) {}` does not — even if `cond` is always true at runtime; the checker reasons syntactically, not about runtime values.
- **Over-recovery.** Salvaging too aggressively (e.g., inventing a type for *every* failure) can suppress *real, independent* errors. Salvage only the broken node; let independent code report its own problems.
- **Pass that mutates state a later pass re-reads.** If pass 3 mutates a symbol's type and pass 4 assumes the original, you get heisenbugs. Keep pass outputs additive (decorate) where possible.

---

## Common Mistakes

1. Doing everything in one pass and then failing the first time a feature needs forward references or mutual recursion.
2. Implementing flow checks (definite assignment, reachability) with ad-hoc boolean flags on a tree walk instead of a CFG, then getting loops and early returns wrong.
3. Forgetting `break`/`continue`/`throw`/`return` edges, so dead code and unassigned-variable checks misfire.
4. Treating type checking as purely synthesized, then being unable to type empty literals, lambdas, or generic calls.
5. Letting an `ErrorType` *expected* type produce a spurious mismatch diagnostic.
6. Bailing out of analysis on the first error (no statement/declaration recovery), so users fix-and-recompile repeatedly.
7. Over-recovering and hiding real, independent errors behind aggressive salvage.
8. Computing exhaustiveness but ignoring guards, wrongly accepting a guarded match as total.
9. Not producing a witness, so "non-exhaustive match" leaves the user guessing which case is missing.
10. Skipping the precondition asserts between passes, so phase-ordering bugs surface as distant, confusing crashes.

---

## Tricky Points

- **L-attributed is the sweet spot.** Most real checkers are L-attributed (inherited attributes depend only on parent and left siblings), which is exactly why a single left-to-right depth-first walk handles both the symbol table (inherited) and types (synthesized) — *except* for forward references, which break left-to-right dependency and force the extra collect pass.
- **"Must" vs. "may" decides the merge operator.** Definite assignment is a *must* analysis (intersect at merges). A *may* analysis (e.g., "this variable might be null") *unions* at merges. Picking the wrong lattice/merge silently inverts the check.
- **A non-void function is valid iff its body cannot complete normally — that's reachability, not a return-count.** "Has at least one return" is neither necessary (an infinite loop needs none) nor sufficient (a return in only one branch isn't enough).
- **Exhaustiveness is what makes sum types safe to extend.** The compile error on `match` after adding a variant is the *entire point* of sealed/enum types for evolution. Demoting it to a warning quietly removes that guarantee.
- **Recovery quality is a UX property, not a correctness one.** A checker that's correct but bails on the first error is *correct and unusable*. In IDEs, recovery quality dominates perceived quality.
- **Bidirectional checking blurs "infer" and "check."** Whether a node infers or is checked depends on context, not on the node kind alone — the same lambda synthesizes in one position and is checked in another.

---

## Apply it

1. State the system invariant that **Semantic Analysis** must protect.
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

- Which invariant must remain true when Semantic Analysis fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
