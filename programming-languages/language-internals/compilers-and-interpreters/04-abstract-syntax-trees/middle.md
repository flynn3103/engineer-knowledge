# Abstract Syntax Trees — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Abstract Syntax Trees** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Two Representations: Sum Type vs Class Hierarchy

There are two dominant ways to model an AST, and which one a language pushes you toward shapes how the rest of your compiler feels.

**Sum type (Rust, OCaml, Haskell, Swift, F#).** The entire AST is one type with many variants:

```rust
enum Expr {
    Lit(i64),
    Var(String),
    BinOp { op: Op, lhs: Box<Expr>, rhs: Box<Expr> },
    Call { callee: Box<Expr>, args: Vec<Expr> },
    If   { cond: Box<Expr>, then: Box<Expr>, els: Box<Expr> },
}
```

An operation is one function that `match`es on the variant:

```rust
fn eval(e: &Expr, env: &Env) -> i64 {
    match e {
        Expr::Lit(n)              => *n,
        Expr::Var(name)           => env.get(name),
        Expr::BinOp { op, lhs, rhs } => apply(*op, eval(lhs, env), eval(rhs, env)),
        Expr::Call { callee, args } => call(eval(callee, env), eval_all(args, env)),
        Expr::If { cond, then, els } =>
            if eval(cond, env) != 0 { eval(then, env) } else { eval(els, env) },
    }
}
```

The compiler checks the `match` is **exhaustive**: add a new variant `Lambda` and every `match` in the codebase that does not handle it becomes a compile error. This is wonderful when your set of *operations* is large and growing (eval, type-check, optimize, pretty-print) but your set of *node kinds* is relatively stable.

**Class hierarchy (Java, C#, traditional C++, TypeScript classes).** Each node kind is a subclass:

```java
abstract class Expr { }
class Lit   extends Expr { final long value; }
class Var   extends Expr { final String name; }
class BinOp extends Expr { final Op op; final Expr lhs, rhs; }
class Call  extends Expr { final Expr callee; final List<Expr> args; }
class If    extends Expr { final Expr cond, then, els; }
```

Where does an operation live? You could put an abstract `eval()` method on `Expr` and override it in each subclass. That works — but it means *every* operation (eval, typecheck, print, optimize) becomes another method bolted onto every node class, and the logic for one pass is smeared across dozens of files. The standard escape hatch is the **visitor pattern** (next section), which collects one operation into one class.

### 2. The Expression Problem

These two designs are not arbitrary taste — they sit at opposite ends of a genuine, named trade-off, the **expression problem** (Philip Wadler's framing). You have a 2-D grid: *node kinds* (rows) × *operations* (columns).

- **Sum types make adding an OPERATION cheap, adding a KIND expensive.** A new operation is one new function with a `match` — touch nothing else. A new *kind* means editing every existing `match` (the compiler at least points you at all of them).
- **Class hierarchies make adding a KIND cheap, adding an OPERATION expensive (without visitors).** A new kind is one new subclass. A new *operation* means adding a method to every subclass — or, with the visitor pattern, adding one visitor *but editing the visitor interface and every node's `accept`*.

```text
              add a new NODE KIND        add a new OPERATION
sum type      edit every match  (hard)   one new function  (easy)
class+visitor one new subclass  (easy)   one new visitor   (easy-ish)
              + edit visitor iface             but visitor iface grows
```

The practical reading: **compilers add operations far more often than node kinds** (you write pass after pass over a roughly fixed grammar), which is one reason rustc, OCaml compilers, and most functional-language compilers use sum types. Conversely, **language frameworks and tooling ecosystems** that expect third parties to add node kinds (plugins, new syntax) lean on class hierarchies and visitors. Neither is "right"; the choice follows which axis you expect to grow.

### 3. The Visitor Pattern, In Depth

The visitor pattern exists to answer one question: *in a class-based AST, how do I add a new operation without editing every node class?* The answer is **double dispatch**.

The mechanism is two methods:

- Every node has an `accept(Visitor v)` that calls the *right* method on the visitor for its own type.
- The visitor interface has one `visit` method per node type.

```java
interface Visitor<R> {
    R visitLit(Lit n);
    R visitVar(Var n);
    R visitBinOp(BinOp n);
    R visitCall(Call n);
    R visitIf(If n);
}

abstract class Expr { abstract <R> R accept(Visitor<R> v); }

class BinOp extends Expr {
    Op op; Expr lhs, rhs;
    <R> R accept(Visitor<R> v) { return v.visitBinOp(this); }  // dispatch #2
}
```

Now an operation is one class:

```java
class Evaluator implements Visitor<Long> {
    public Long visitLit(Lit n)   { return n.value; }
    public Long visitBinOp(BinOp n) {
        long l = n.lhs.accept(this);   // recurse via accept
        long r = n.rhs.accept(this);
        return apply(n.op, l, r);
    }
    // ... visitVar, visitCall, visitIf
}
```

**Why "double dispatch"?** You want behavior that depends on *two* types at runtime: which node (`BinOp` vs `Lit`) and which operation (`Evaluator` vs `Printer`). A single virtual call dispatches on one type. The visitor does it in two hops: `node.accept(visitor)` dispatches on the **node** type (picks `visitBinOp`), and inside, `v.visitBinOp(this)` dispatches on the **visitor** type (picks `Evaluator`'s implementation). Two dispatches → the right (node, operation) cell of the grid.

**Why bother instead of an abstract method per node?** Because the visitor *collects one operation into one place*. All of evaluation lives in `Evaluator`; all of pretty-printing in `Printer`. To add type-checking you write one `TypeChecker implements Visitor` and touch zero node classes. That is the payoff. The cost: adding a new node kind forces a new `visit` method on the interface, which breaks every existing visitor (the expression problem, again).

> 💡 In languages with sum types you do **not** need the visitor pattern — a `match` *is* the dispatch, in one hop, checked for exhaustiveness. The visitor pattern is largely an OOP workaround for the lack of pattern matching. Modern Java (sealed classes + switch patterns), C# (pattern matching), and TypeScript (discriminated unions) are closing this gap.

### 4. Traversal Orders

Walking a tree is not one thing — *when* you do work relative to the children matters:

- **Pre-order** (node, then children): good for things that flow *down* — printing with indentation, building a scope, collecting declarations before bodies.
- **Post-order** (children, then node): good for things computed *up* from leaves — evaluation, type inference, constant folding (you need the children's results first).
- **In-order** (left, node, right): meaningful only for binary-shaped nodes; rarely used for whole ASTs but natural for printing a binary expression as infix text.

Most real walkers do both: some work on the way *in* (pre) and some on the way *out* (post), which is exactly why visitor frameworks often expose `enter(node)` and `exit(node)` hooks (Babel does precisely this).

### 5. Transform In Place vs Build a New Tree

Compilers rewrite trees constantly. Two strategies:

- **In-place mutation:** walk the tree and edit node fields directly. Fast, low allocation. But it is fragile — if any other part of the system holds a reference to the old subtree, you have just changed it under their feet; and you cannot easily compare "before" and "after."
- **Transformer / rewriter (immutable AST):** the walk *returns a new node*. Unchanged subtrees are shared (reused by reference); only the path from the root to a changed node is rebuilt. This is how Python's `ast.NodeTransformer`, Babel's transforms (conceptually), and rustc's lowering work. Immutability makes transforms composable and debuggable: the old tree is still intact, so you can diff, cache, or roll back.

```python
import ast

class PlusOne(ast.NodeTransformer):
    """Rewrite every integer literal n into n + 1."""
    def visit_Constant(self, node):
        if isinstance(node.value, int):
            return ast.BinOp(left=node, op=ast.Add(), right=ast.Constant(value=1))
        return node

tree = ast.parse("x = 5")
new_tree = PlusOne().visit(tree)
ast.fix_missing_locations(new_tree)     # repair source positions on new nodes
print(ast.unparse(new_tree))            # x = 5 + 1
```

Notice `fix_missing_locations` — the freshly created nodes have *no source position*, which leads us to the last core concept.

### 6. Source Positions / Spans

Every node should carry where it came from in the source: a **span**, usually a start and end byte offset (cheap, exact) from which line/column can be derived on demand. Spans are the backbone of diagnostics: when the type-checker finds `"a" + 1`, it reports the error *at the span of that expression*, with a caret under the exact text.

The hard part is **spans surviving transformation**. When you desugar `a += b` into `a = a + b`, the new `+` node did not exist in the source. Good compilers attach the *original* span to the synthesized node (so the error still points at the `+=`), and many track a *desugaring trail* so a message can say "this came from a `+=`." When you create nodes by hand (the `PlusOne` example above), you must copy spans over, or your diagnostics point at line 0. This is why `ast.NodeTransformer` users call `fix_missing_locations`, and why rustc carries a `Span` on essentially every HIR node.

---

## Code Examples

### Example 1 — Adding an operation: sum type vs visitor

**Sum type (Rust): a pretty-printer is just another function.**

```rust
fn print(e: &Expr) -> String {
    match e {
        Expr::Lit(n)               => n.to_string(),
        Expr::Var(s)               => s.clone(),
        Expr::BinOp { op, lhs, rhs } =>
            format!("({} {} {})", print(lhs), op, print(rhs)),
        _ => unimplemented!(),
    }
}
```

No node type changed. The whole operation is one self-contained function.

**Class hierarchy (Java): a pretty-printer is one visitor.**

```java
class Printer implements Visitor<String> {
    public String visitLit(Lit n)   { return Long.toString(n.value); }
    public String visitVar(Var n)   { return n.name; }
    public String visitBinOp(BinOp n) {
        return "(" + n.lhs.accept(this) + " " + n.op + " " + n.rhs.accept(this) + ")";
    }
    // ...
}
```

No node class changed. The whole operation is one `Printer` class. Same payoff, achieved through the visitor instead of `match`.

### Example 2 — A Babel-style enter/exit visitor (JavaScript)

Babel's visitors expose `enter` (pre-order) and `exit` (post-order). Here is the *shape* of a plugin that renames every identifier `foo` to `bar`:

```js
// A Babel plugin is an object returning a `visitor` with per-type handlers.
module.exports = function () {
  return {
    visitor: {
      Identifier(path) {                 // path wraps the node + its context
        if (path.node.name === "foo") {
          path.node.name = "bar";        // in-place mutation of the node
        }
      },
    },
  };
};
```

`path` is more than the node — it knows the node's parent, scope, and how to replace it (`path.replaceWith(...)`), which is how real codemods rewrite safely.

### Example 3 — A transformer that builds a new tree (Python)

```python
import ast

class StripDocstrings(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        self.generic_visit(node)                 # transform children first
        body = node.body
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()] # drop the docstring statement
        return node

src = '''
def f():
    """remove me"""
    return 1
'''
new = StripDocstrings().visit(ast.parse(src))
ast.fix_missing_locations(new)
print(ast.unparse(new))
```

This returns a modified tree; `return node` is what hands the (possibly new) subtree back to the walker. Returning `None` from a `NodeTransformer` visit *deletes* the node — a sharp edge worth remembering.

### Example 4 — Carrying a span through a hand-written desugaring

```rust
struct Span { start: u32, end: u32 }

enum Stmt {
    AddAssign { target: Box<Expr>, value: Box<Expr>, span: Span }, // a += b
    Assign    { target: Box<Expr>, value: Box<Expr>, span: Span }, // a = ...
}

// Desugar `a += b`  →  `a = a + b`, preserving the ORIGINAL span.
fn desugar(s: Stmt) -> Stmt {
    match s {
        Stmt::AddAssign { target, value, span } => {
            let sum = Expr::BinOp {
                op: Op::Add,
                lhs: target.clone(),
                rhs: value,
                span,                 // synthesized node inherits the += span
            };
            Stmt::Assign { target, value: Box::new(sum), span }
        }
        other => other,
    }
}
```

The synthesized `+` node carries the span of the original `+=`, so any later error on it still points at the right text.

---

## Coding Patterns

**Pattern 1 — One visitor (or one function) per operation.** Keep eval, typecheck, print, and optimize as separate visitors/functions; do not interleave concerns.

**Pattern 2 — `enter`/`exit` hooks.** Expose both pre- and post-order callbacks so a single walk can do top-down work (scoping) and bottom-up work (folding) together.

**Pattern 3 — Return-a-node transform.** Make transform visitors return the (possibly new) node so unchanged subtrees are shared and the old tree stays intact.

**Pattern 4 — Span propagation helper.** Provide a `with_span_of(original)` helper used whenever you synthesize a node, so no created node is ever location-less.

**Pattern 5 — `generic_visit` / `super.visit` for the default.** Default behavior should be "recurse into all children"; override only the kinds you care about.

---

## Best Practices

- **Make the default traversal recurse.** A visitor that forgets to descend into children silently misses nested code. Provide and call a generic recurse.
- **Prefer immutable transforms for anything multi-pass.** They compose and debug far better than in-place edits; reach for mutation only in a tight, well-understood hot path.
- **Never synthesize a node without a span.** Copy the source position from whatever the node was derived from; otherwise diagnostics rot.
- **Use exhaustive matching where the language offers it.** Let the compiler enumerate the places a new node kind must be handled.
- **Keep node types data-only.** Behavior belongs in visitors/passes, not bolted onto nodes — this is what keeps the expression problem manageable.
- **Wrap nodes in a `path`/cursor when you need context.** Knowing a node's parent and scope (as Babel's `path` does) is essential for safe replacement and renaming.

---

## Edge Cases & Pitfalls

- **Returning `None` from a transformer deletes the node.** In Python's `NodeTransformer`, forgetting to `return node` silently removes it from the tree.
- **Mutating a shared subtree.** If two parts of the tree reference the same node and you mutate it in place, you changed both. Immutable transforms avoid this.
- **The visitor interface as a breaking change.** Adding a node kind means every third-party visitor must implement a new `visit` method — an API break in published tools.
- **Lost spans on synthesized nodes.** Desugaring without span propagation produces "error at 0:0" or carets under the wrong text.
- **Pre- vs post-order mismatch.** Doing folding work in pre-order (before children are computed) yields wrong results; doing scope setup in post-order (after the body) is too late.
- **Stack overflow on deep trees.** Long chains (`a + a + a + ...`) make recursive walks blow the stack; production compilers sometimes use an explicit work-stack.

---

## Common Mistakes

| Mistake | Why it's wrong | Fix |
|---------|----------------|-----|
| Putting `eval()` etc. as methods on every node class | Smears each operation across all node files; expression problem bites | Use a visitor (or sum type) to collect one operation in one place |
| Forgetting `return node` in a transformer | Node gets deleted | Always return the (possibly new) node |
| Synthesizing nodes with no span | Diagnostics point nowhere | Propagate the original span |
| Mutating in place when others alias the tree | Corrupts unrelated parts | Use immutable transforms with structural sharing |
| Adding a node kind and only fixing the parser | Every visitor/match silently or loudly breaks | Update all operations; let exhaustiveness checks help |
| Doing all work in pre-order | Bottom-up passes need children first | Use post-order (or exit hooks) for upward-flowing computations |

---

## Apply it

1. Find a real component where **Abstract Syntax Trees** affects an interface or dependency.
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

- Which boundary is most affected by Abstract Syntax Trees?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
