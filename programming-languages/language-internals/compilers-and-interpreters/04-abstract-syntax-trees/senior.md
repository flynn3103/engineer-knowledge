# Abstract Syntax Trees — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Abstract Syntax Trees** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. AST vs CST: what the parser keeps and what it throws away

A **parse tree / CST (Concrete Syntax Tree)** mirrors the grammar one-to-one: every parenthesis, every `;`, every keyword token, every intermediate grammar production (`Term → Factor → Primary`) shows up as a node. An **AST** keeps only what carries meaning. `(1 + 2)` and `1 + 2` produce the *same* AST — the parens were a grouping instruction to the parser, already consumed by the time the tree exists. A chain `Expr → AdditiveExpr → MultiplicativeExpr → PrimaryExpr → 1` collapses to a single literal node.

The distinction is not academic. Most compilers parse straight into an AST (the CST is conceptual, never materialized) because the CST is enormous and full of nodes no later phase cares about. But a crucial class of tools *wants* the CST: formatters, refactoring engines, and IDEs need to reproduce or surgically edit the original text, including comments and whitespace, which a pure AST has discarded. This is exactly why **Roslyn keeps a full-fidelity tree** (you can round-trip the exact source byte-for-byte) and why **libcst** ("Concrete Syntax Tree") exists for Python alongside the lossy `ast`. The rule of thumb: a compiler can throw away syntax; a *source-rewriting tool* usually cannot.

### 2. The AST as a phase interface

The single most useful senior-level reframing: the AST is not a thing the compiler *has*, it is the *contract between phases*. Parsing produces it; name resolution annotates it; type checking annotates it further; lowering transforms it; codegen consumes it. Each phase is a function `Tree → Tree` (or `Tree → AnnotatedTree`), and the tree's shape *is* the API.

This has a sharp design consequence: **you can change a phase without touching its neighbors as long as the tree contract holds.** Swap a recursive-descent parser for a generated one — downstream phases never notice, because they consume the AST, not the parser. Add a new optimization pass — it slots between two existing passes as another `Tree → Tree`. This is why compilers are organized as pipelines of tree transforms and why "the AST" is really "the family of trees that flow between phases."

### 3. Desugaring and the narrow core

The front end's job is to shrink the language. The programmer writes a wide surface language; the back end implements a narrow core; **desugaring is the bridge.** Canonical examples:

- `a += b` → `a = a + b` (and `a[i] += b` carefully, evaluating `a[i]` *once*).
- `for x in iter { body }` → roughly `{ let mut it = iter.into_iter(); while let Some(x) = it.next() { body } }`.
- `x?.y` → `match x { Some(v) => Some(v.y), None => None }` (or equivalent).
- List comprehension `[f(x) for x in xs if g(x)]` → a loop that appends.
- `async fn` → a state machine returning a future.
- Default/keyword arguments → call-site argument reordering and fill-in.

After desugaring, the back end sees a handful of constructs — function, call, conditional, loop, assignment, literal — instead of dozens. Every later pass is simpler because of it. The art is choosing the core: too small and desugaring becomes a contortion (encoding everything as lambdas); too large and you have not actually simplified the back end.

The subtle part is *semantics preservation*. `a[expensive()] += 1` must evaluate `expensive()` exactly once, so the naive desugar `a[expensive()] = a[expensive()] + 1` is **wrong** — you must introduce a temporary: `let i = expensive(); a[i] = a[i] + 1`. Desugaring that changes evaluation count, order, or short-circuiting is a correctness bug, and these bugs are notoriously easy to ship.

### 4. Multiple lowered ASTs: HIR, MIR, and friends

Why not desugar in one pass? Because different analyses want different shapes. Real compilers maintain a *staircase* of trees, each lower than the last:

**rustc** is the textbook example:
- **AST** — exactly what the parser produced; macros not yet expanded fully, sugar intact.
- **HIR (High-level IR)** — after macro expansion and name resolution; `for`/`while let`/`?` desugared; still tree-shaped and close to source. Borrow-check-irrelevant. Carries spans everywhere.
- **THIR (Typed HIR)** — HIR with full type information attached; used for exhaustiveness checking and as the input to MIR building.
- **MIR (Mid-level IR)** — a *control-flow graph* of basic blocks, not a tree. Borrow checking, drop elaboration, and many optimizations happen here. This is where the "tree" finally becomes a graph.

Other languages do the same with different names: **Swift** lowers `AST → SIL` (Swift Intermediate Language, where ARC and ownership are made explicit); **GHC** lowers Haskell's giant surface syntax `HsSyn` into tiny **Core** (System FC, about a dozen constructs) before optimizing; **Kotlin** has a frontend IR (FIR) and a backend IR. The pattern is universal: **lower in stages, each stage narrower and more explicit than the last, each a separate data type so the type system enforces "you cannot accidentally use a surface construct in the back end."**

### 5. The typed / annotated AST

A freshly parsed AST is a *syntactic* artifact: it knows shape, not meaning. `a + b` is a `BinOp(Add, Var("a"), Var("b"))` — but it does not yet know whether `a` is an `int`, a `String`, an overloaded operator, or undeclared. **Semantic analysis annotates the tree**: name resolution attaches each `Var` to the symbol it refers to (which `a`? the local or the field?); type checking attaches a resolved type to every expression node; constant evaluation may attach computed values.

After this, the same tree means much more. `BinOp(Add, ...)` now carries "result type `i32`, this is integer addition, no overload." This annotated tree is what enables everything downstream: codegen needs the type to pick the right instruction; overload resolution needs it to pick the right method; the borrow checker needs resolved bindings. Some compilers store annotations *in* the node (a `ty` field), some in a *side table* keyed by node id (rustc keeps a `TypeckResults` map keyed by `HirId`, which keeps the HIR itself immutable and shareable). The side-table approach is increasingly favored: it keeps the tree clean and lets type information be computed lazily and cached per-function.

The conceptual jump: **a typed AST is the boundary between "what the program says" and "what the program means."** Before it, you have syntax; after it, you have semantics, and every interesting compiler error (type mismatch, unresolved name, non-exhaustive match) is a query against the annotated tree.

### 6. Spans surviving every transform

The thread from middle level becomes a discipline at senior level. As the tree is lowered through HIR, MIR, and beyond, the original source span must survive, because the user wrote *surface* syntax and any diagnostic — even one discovered in MIR borrow checking — must point at the surface text. rustc carries a `Span` on essentially every HIR and MIR node, and crucially tracks **desugaring provenance**: a span can record "this node came from desugaring a `?` operator," so the error message can say "the `?` operator cannot be used here" instead of pointing at synthesized machinery the programmer never wrote.

The failure mode is concrete: desugar `for` into `while` without copying spans, and a type error in the loop variable points at column 0, or at the synthesized `while` that has no textual existence. Worse, a *correct* span pointing at the wrong *conceptual* construct ("error in this `while`" when the user wrote a `for`) confuses more than no span at all. Production compilers therefore track both *where* (byte range) and *why* (desugaring origin), and lowering passes are reviewed specifically for span hygiene.

### 7. Real ASTs you will actually use

Theory meets practice in five widely-used trees:

- **Python `ast`** — a clean sum-of-classes (`Module`, `FunctionDef`, `BinOp`, `Call`, `Constant`...) with `NodeVisitor` (read) and `NodeTransformer` (rewrite). Lossy: it drops comments, parens, and exact formatting. `ast.parse` / `ast.unparse` round-trips *semantics*, not *text*. For text-faithful work, **libcst** keeps a concrete tree.
- **Babel / ESTree** — JavaScript's AST is a JSON object graph following the **ESTree** spec, the shared contract that lets acorn (parser), ESLint (linter), Prettier (formatter), and Babel (transpiler) all operate on the *same* tree shape. This shared format is why the JS tooling ecosystem composes so well: one parse, many consumers.
- **Clang AST** — a C/C++ tree of `Stmt`/`Expr`/`Decl` classes, traversed with `RecursiveASTVisitor`. It is famously *rich and faithful* — it retains enough source detail that clang-tidy, clang-format, and refactoring tools work on real code. Inspect it with `clang -Xclang -ast-dump`.
- **Roslyn (C#/VB)** — uses **red-green trees** (next section / `professional.md`): immutable, full-fidelity (round-trips exact source including trivia/whitespace), and built for incremental IDE editing.
- **rustc HIR** — the desugared, name-resolved tree described above; typed via side tables; spans everywhere.

Each embodies a different priority: Python `ast` favors simplicity, Clang favors fidelity for tooling, Roslyn favors incremental editing, rustc favors a clean lowering staircase. Knowing *which tree you are holding* tells you what it will and will not preserve.

### 8. Uses beyond compilers

The AST escaped the compiler decades ago. The same tree powers an entire class of source-level tools:

- **Linters** (ESLint, clang-tidy, ruff) — visitor-based rules over the AST that *report* style/bug patterns.
- **Formatters** (Prettier, gofmt, clang-format, Black) — parse to a tree, throw away the original layout, re-emit canonical layout. The tree is the proof that formatting is purely a printing decision.
- **Codemods** (jscodeshift, libcst, OpenRewrite) — AST transformers applied at repo scale to perform mechanical migrations ("rename this API across 10,000 files").
- **Transpilers** (Babel, TypeScript, SWC) — parse one language's AST, lower/translate, print another.
- **Static analysis & security tools** (Semgrep, CodeQL) — match patterns against the AST (and beyond) to find vulnerabilities.

What unifies them: they all need *structure*, not text. The moment a tool must understand "is this a function call or a variable named the same thing," it needs an AST. This is why "learn the AST" pays off far beyond writing a compiler.

## Code Examples

### Python — desugaring `+=` correctly (evaluate target once)

```python
import ast

class DesugarAugAssign(ast.NodeTransformer):
    """
    Rewrite `target OP= value` into `target = target OP value`.
    For a simple Name target this is safe. For a subscript/attribute target
    a naive rewrite would evaluate the target expression twice — a bug.
    """
    def visit_AugAssign(self, node):
        self.generic_visit(node)
        if isinstance(node.target, ast.Name):
            # Safe: a plain name has no side effects when evaluated.
            load = ast.Name(id=node.target.id, ctx=ast.Load())
            new = ast.Assign(
                targets=[ast.Name(id=node.target.id, ctx=ast.Store())],
                value=ast.BinOp(left=load, op=node.op, right=node.value),
            )
            return ast.copy_location(new, node)   # <-- span survives
        # Subscript/attribute targets need a temporary to evaluate the
        # base ONCE; left as an exercise (see tasks.md). Don't ship the
        # naive double-eval version.
        return node

src = "x += 1"
tree = DesugarAugAssign().visit(ast.parse(src))
ast.fix_missing_locations(tree)
print(ast.unparse(tree))   # x = x + 1
```

The `copy_location` call is the span discipline in miniature: the synthesized assignment inherits the original `+=`'s position, so a later error still points at the user's line.

### Inspecting a real lowering — Clang AST dump

```bash
# See the tree Clang actually builds. Note how `for` is kept structurally
# but every implicit conversion becomes an explicit ImplicitCastExpr node.
clang -Xclang -ast-dump -fsyntax-only example.c
```

```text
`-FunctionDecl <line:1:1> main 'int ()'
  `-CompoundStmt
    |-DeclStmt
    | `-VarDecl sum 'int' cinit
    |   `-IntegerLiteral 'int' 0
    `-ForStmt
      |-DeclStmt ...
      |-BinaryOperator 'int' '<'
      | |-ImplicitCastExpr 'int' <LValueToRValue>   <-- made explicit
      | | `-DeclRefExpr 'i' 'int'
      | `-IntegerLiteral 'int' 10
      ...
```

The lesson: even a "faithful" AST has *already lowered* things — implicit conversions that were invisible in source are now explicit nodes. The AST is never a pure mirror of source; it is source with some semantics already baked in.

### Rust-style lowering sketch — `for` → `while let` (pseudocode)

```rust
// Surface:
//   for x in iter { body }
//
// HIR lowering (conceptually), preserving the for-loop's span on synthesized nodes:
{
    let mut __iter = IntoIterator::into_iter(iter);   // span = `iter`
    loop {                                             // span = whole `for`
        match __iter.next() {                          // span = whole `for` (desugared)
            Some(x) => { body }                        // x-span = original `x`
            None => break,
        }
    }
}
```

Two things to notice: a fresh `__iter` temporary is introduced (the iterator is evaluated exactly once), and every synthesized node carries a span tagged as *desugared from `for`*, so a borrow error in the loop reports against the user's `for`, not against machinery they never typed.

### A typed AST as a side table (Rust-flavored pseudocode)

```rust
// The HIR stays immutable and span-rich. Types live in a SEPARATE table
// keyed by node id — so the tree itself is never mutated by type checking.
struct Hir { nodes: Arena<HirNode> }          // built once, shared
struct TypeckResults {
    node_types: HashMap<HirId, Ty>,           // expr id -> resolved type
    bindings:   HashMap<HirId, DefId>,        // name use -> definition
}

fn type_of(expr: HirId, results: &TypeckResults) -> Ty {
    results.node_types[&expr]                 // query, don't mutate
}
```

Keeping types out-of-band is what lets rustc share the HIR across queries and recompute typeck per-function without rebuilding the tree.

## Trade-offs

| You gain... | ...at the cost of... |
| --- | --- |
| Multiple lowered ASTs (HIR/MIR) — each pass sees the simplest shape it needs | More data types, more conversions, more code to maintain |
| A small core language after desugaring | Desugaring logic must rigorously preserve semantics (eval count/order) |
| Annotations in a side table (immutable tree) | An extra indirection on every "what's the type of this node" query |
| Annotations stored on the node | Mutable or rebuilt trees; harder to share across phases |
| Full-fidelity CST (Roslyn, libcst) | Much larger trees; more memory; you carry trivia you may not need |
| Lossy AST (Python `ast`) | Cannot round-trip exact source; useless for formatters |
| Shared AST format (ESTree) | Locked into a spec; evolving the language means evolving the spec for everyone |
| Span provenance tracking | Every node grows; every transform must maintain it |

## Coding Patterns

### 1. One AST type per altitude

Give each level of the staircase its own data type (`Ast`, `Hir`, `Mir`). The type system then *forbids* using a surface construct in the back end — a desugared-away `for` simply cannot be constructed at the HIR level.

### 2. Side-table annotations

Keep the syntactic tree immutable; store types/bindings in a map keyed by node id. The tree stays shareable and cheap to clone; semantic facts are computed and cached separately.

### 3. Span-copying constructors

Never call a raw node constructor in a lowering pass. Wrap it: `mk(kind, span_of(original))`. Make it impossible to synthesize a span-less node.

### 4. Desugar with explicit temporaries

When a target appears more than once after lowering (`a[i] += b`), bind it to a fresh temporary first. Make "evaluate once" a structural property of the lowered tree, not a hope.

### 5. Separate "lower" from "optimize"

Lowering changes the *language* (wide → narrow); optimization changes the *program* within a fixed language. Keep them as distinct pass categories so each is independently testable.

## Best Practices

- **Decide CST-or-AST by your output.** If you must reproduce source text (formatter, refactoring tool), keep a concrete/full-fidelity tree. If you only consume meaning (compiler, interpreter), parse straight to an AST.
- **Make each lowering total and semantics-preserving.** Write a property test: lowering then interpreting must give the same result as interpreting the surface form.
- **Propagate spans mechanically, not manually.** A helper that *requires* a source span to build a node beats remembering to set one.
- **Track desugaring provenance** so diagnostics can explain "this came from a `?`/`for`/comprehension."
- **Prefer side tables for type annotations** when the tree must be shared or incrementally recomputed.
- **Reuse the ecosystem's AST format** (ESTree for JS, libcst/ast for Python) rather than inventing your own — interop with linters/formatters is free.
- **Test lowerings with round-trip and differential checks**, not just spot examples; sugar interactions are where bugs hide.

## Edge Cases & Pitfalls

- **Double evaluation in desugaring.** `a[f()] += 1` → `a[f()] = a[f()] + 1` calls `f()` twice. Introduce a temporary.
- **Short-circuit loss.** Desugaring `a && b` or `x?.y` into something that always evaluates both sides changes behavior.
- **Span-less synthesized nodes.** Forgetting `copy_location` / span propagation yields "error at 0:0" or carets under nonexistent text.
- **Wrong-construct spans.** A correct byte range that points at a synthesized `while` confuses the user who wrote a `for`. Track provenance.
- **Lossy AST used for formatting.** Python `ast` drops comments and parens; a formatter built on it silently deletes them. Use libcst.
- **Macro expansion order.** In languages with macros (Rust, Lisp), desugaring must happen *after* expansion, or you desugar code that does not exist yet.
- **Annotations on a mutated tree.** If type info is stored on nodes and a later pass rebuilds nodes, the annotations are lost or stale. Side tables avoid this.
- **Assuming the AST mirrors source.** Even Clang's AST inserts `ImplicitCastExpr`; the tree already encodes semantics that were invisible in text.

## Common Mistakes

1. **Treating "the AST" as singular** in a compiler that actually has three or four trees. Know which altitude you are at.
2. **Desugaring that changes evaluation count or order** — the classic `+=`/comprehension/short-circuit bug.
3. **Losing spans across lowering**, then wondering why error messages degraded.
4. **Storing types by mutating nodes**, then rebuilding nodes in a later pass and silently dropping the types.
5. **Building a formatter on a lossy AST** and deleting the user's comments.
6. **Inventing a bespoke AST format** when ESTree/`ast`/libcst already exist, then losing all linter/formatter interop.
7. **Confusing lowering with optimization** and mixing language-narrowing logic with program-improving logic in one tangled pass.
8. **Desugaring before macro expansion** in a macro language.

## Tricky Points

- **The CST is usually never materialized** — most parsers go grammar → AST directly; the "CST" is a mental model, except in fidelity-preserving tools that deliberately keep it.
- **rustc's MIR is not a tree** — it is a CFG of basic blocks. The "AST staircase" stops being a tree at MIR; the word "AST" stops applying.
- **Type info location is a real architectural choice** — on-node (simple, mutable) vs side-table (shareable, immutable). rustc, Roslyn, and most incremental compilers chose side tables for a reason.
- **`ast.unparse` round-trips semantics, not text** — `unparse(parse(src))` is *equivalent* code, not *identical* source. Comments, parens, and whitespace are gone.
- **ESTree is a community spec, not an official ECMAScript one** — yet it is more load-bearing than many official specs because the whole JS toolchain depends on it.
- **Clang's AST is immutable by design** — clang's RecursiveASTVisitor reads; rewriting C++ is done via a separate `Rewriter` working on source ranges, not by mutating the tree.
- **Spans can carry *why*, not just *where*** — rustc's `SpanData` records an expansion/desugaring context, which is how it produces "in this expansion of macro `foo`" diagnostics.

---

## Apply it

1. State the system invariant that **Abstract Syntax Trees** must protect.
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

- Which invariant must remain true when Abstract Syntax Trees fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
