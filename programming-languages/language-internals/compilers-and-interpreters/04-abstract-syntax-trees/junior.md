# Abstract Syntax Trees — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Abstract Syntax Trees** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Text Is Not Structure — The Tree Is

The string `if (x > 0) y = 1;` is a line of characters. The compiler cannot ask it "what is the condition?" or "what is the body?" — strings do not have a condition or a body. The AST does:

```text
IfStatement
├── test:  BinaryExpression (>)
│           ├── left:  Identifier  "x"
│           └── right: Literal       0
└── then:  AssignmentStatement (=)
            ├── target: Identifier "y"
            └── value:  Literal      1
```

Now every question has an answer that is just "follow a child pointer": the condition is the `test` child; the body is the `then` child. **This is the entire point of an AST** — it turns *questions about code* into *navigation of a tree*.

### 2. The AST Drops Syntactic Noise

Look again at `1 + 2 * 3`. In the source you might also write `(1 + (2 * 3))` or `1+2*3` with no spaces. All three produce **the exact same AST**, because the parentheses, the spaces, and the precedence rules were only ever there to help work out the structure. Once the structure is captured by the tree's *shape*, that scaffolding is no longer needed.

Things the AST typically throws away:

- **Grouping parentheses** — `(1 + 2)` and `1 + 2` (when already grouped by structure) collapse to the same subtree.
- **Whitespace and indentation** — irrelevant once you have a tree.
- **Comments** — usually dropped (some tools keep them attached; more on that later).
- **Some punctuation** — semicolons, commas separating arguments. The fact that there *are* arguments is captured as a list of children; the commas themselves are gone.

This is the difference between the AST and the **parse tree** (also called the **concrete syntax tree**, or **CST**). The parse tree keeps *all of it* — every parenthesis and comma is a node. That is useful for tools that must reproduce the source *exactly* (a code formatter, a refactoring engine that preserves your comments). But for most jobs — evaluation, type-checking, optimization — the noise is in the way, and we use the simpler AST.

> 💡 **Rule of thumb:** the AST keeps what *matters to the meaning*; the parse tree keeps what *matters to the exact text*.

### 3. Every Node Has a Kind

An AST is not a tree of anonymous boxes. Each node has a **kind** (sometimes called a *type* or *tag*) that says what it is: `BinaryExpression`, `IfStatement`, `FunctionDeclaration`, `Literal`, `Identifier`, and so on. The kind determines what children the node has:

- A `Literal` has a value and no children. It is a leaf.
- A `BinaryExpression` has an operator (`+`, `*`, …), a `left` child, and a `right` child.
- An `IfStatement` has a `test`, a `then` body, and an optional `else` body.
- A `FunctionDeclaration` has a name, a list of parameters, and a body.

When you "do something" with an AST, you almost always **switch on the node's kind**: "if it's a `BinaryExpression`, do X; if it's a `Literal`, do Y."

### 4. Walking the Tree

To use an AST you *walk* it: visit the root, then visit its children, then their children, recursively, until you have touched every node. A walk that processes a node *before* its children is **pre-order**; *after* is **post-order**. For an evaluator you usually want post-order (compute the children's values first, then combine them), which is exactly how `1 + 2 * 3` evaluates: figure out `2 * 3 = 6` first, then `1 + 6 = 7`.

The walk is naturally recursive:

```text
walk(node):
    do something with node           # pre-order work
    for each child of node:
        walk(child)                  # recurse
    do something with node           # post-order work
```

That recursion is the heart of every compiler pass, every linter, every formatter you will ever read.

---

## Code Examples

We will look at the *same idea* — building or inspecting an AST — across three ecosystems. The point is not to memorize APIs but to see that the tree-of-nodes concept is universal.

### Example 1 — JavaScript: see a real AST

Modern JS tooling uses a standard AST shape called **ESTree**. You can produce one in your browser's console or with a small script using a parser like Acorn or Babel. For `1 + 2 * 3`, the AST (ESTree shape) is roughly:

```json
{
  "type": "BinaryExpression",
  "operator": "+",
  "left":  { "type": "Literal", "value": 1 },
  "right": {
    "type": "BinaryExpression",
    "operator": "*",
    "left":  { "type": "Literal", "value": 2 },
    "right": { "type": "Literal", "value": 3 }
  }
}
```

Notice: the outer node is the `+` (because `+` happens *last*), and the `*` is nested inside its right child (because `*` happens *first*). The tree's shape encodes precedence. No parentheses anywhere.

### Example 2 — Python: the built-in `ast` module

Python ships an AST library in the standard library. You can parse code and print the tree:

```python
import ast

source = "x = 1 + 2 * 3"
tree = ast.parse(source)

print(ast.dump(tree, indent=2))
```

Output (trimmed):

```text
Module(
  body=[
    Assign(
      targets=[Name(id='x', ctx=Store())],
      value=BinOp(
        left=Constant(value=1),
        op=Add(),
        right=BinOp(
          left=Constant(value=2),
          op=Mult(),
          right=Constant(value=3))))])
```

Same story: `Add` on the outside, `Mult` nested inside as the right operand. The variable name is an `ast.Name` node; the numbers are `ast.Constant` nodes.

### Example 3 — Python: walk the tree with `NodeVisitor`

Python gives you a ready-made walker, `ast.NodeVisitor`. You subclass it and define a method per node kind you care about. Here we print every function name in a file:

```python
import ast

class FunctionFinder(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        print("found function:", node.name)
        self.generic_visit(node)   # keep walking into the body

source = """
def greet(name):
    def helper():
        return 42
    return helper()
"""

FunctionFinder().visit(ast.parse(source))
# found function: greet
# found function: helper
```

The `visit_FunctionDef` method runs once for each `FunctionDef` node. `generic_visit(node)` tells the walker to keep descending into the children — without it, you would never see `helper` (it is nested inside `greet`). This *visitor* pattern is exactly how ESLint, Babel, and most tools walk their trees too.

### Example 4 — Build your own tiny AST (Rust enum)

In languages with **sum types** (Rust, OCaml, Haskell, Swift), an AST is naturally one `enum` whose variants are the node kinds:

```rust
enum Expr {
    Num(f64),                          // a literal: 42
    Add(Box<Expr>, Box<Expr>),         // left + right
    Mul(Box<Expr>, Box<Expr>),         // left * right
}

// The tree for 1 + 2 * 3, built by hand:
fn example() -> Expr {
    Expr::Add(
        Box::new(Expr::Num(1.0)),
        Box::new(Expr::Mul(
            Box::new(Expr::Num(2.0)),
            Box::new(Expr::Num(3.0)),
        )),
    )
}

// Evaluate the tree with a recursive walk (post-order):
fn eval(e: &Expr) -> f64 {
    match e {
        Expr::Num(n)    => *n,
        Expr::Add(a, b) => eval(a) + eval(b),   // children first
        Expr::Mul(a, b) => eval(a) * eval(b),
    }
}
// eval(&example()) == 7.0
```

The `Box<...>` is just "a pointer to another node on the heap," which is how the tree gets its children. The `match` is the switch-on-kind we keep mentioning, and the compiler *forces* you to handle every variant — forget one and it will not compile. (Why `enum` here but a *class hierarchy* in Java? That trade-off is the big idea in `middle.md` and `senior.md`.)

### Example 5 — Build your own tiny AST (JavaScript object)

In JavaScript you do not have sum types, so a node is just an object with a `type` field:

```js
// The tree for 1 + 2 * 3:
const tree = {
  type: "Add",
  left:  { type: "Num", value: 1 },
  right: {
    type: "Mul",
    left:  { type: "Num", value: 2 },
    right: { type: "Num", value: 3 },
  },
};

function evaluate(node) {
  switch (node.type) {
    case "Num": return node.value;
    case "Add": return evaluate(node.left) + evaluate(node.right);
    case "Mul": return evaluate(node.left) * evaluate(node.right);
    default: throw new Error("unknown node type: " + node.type);
  }
}

console.log(evaluate(tree)); // 7
```

Same tree, same recursive walk, different language. The shape of the idea never changes.

---

## Coding Patterns

**Pattern 1 — Switch on node kind.** The fundamental move. Whatever you are doing — evaluating, printing, counting — you branch on the node's `type`/variant and handle each kind.

```js
function describe(node) {
  switch (node.type) {
    case "Num":        return String(node.value);
    case "Add":        return `(${describe(node.left)} + ${describe(node.right)})`;
    case "Mul":        return `(${describe(node.left)} * ${describe(node.right)})`;
    default:           throw new Error("unhandled: " + node.type);
  }
}
```

**Pattern 2 — Recursive walk.** To process a whole tree, process the node, then recurse into its children. The recursion mirrors the tree's nesting.

**Pattern 3 — The visitor.** Instead of one giant switch, register a small handler per node kind and let a generic walker dispatch to the right one. Python's `NodeVisitor` and ESLint rules both work this way. It keeps each concern (one handler) small and separate.

```python
class CallCounter(ast.NodeVisitor):
    def __init__(self): self.count = 0
    def visit_Call(self, node):
        self.count += 1
        self.generic_visit(node)

counter = CallCounter()
counter.visit(ast.parse("print(f(g(x)))"))
print(counter.count)   # 3 calls: print, f, g
```

**Pattern 4 — Accumulate while you walk.** Carry a counter, a list, or a set through the walk to collect facts about the program (all function names, all string literals, the maximum nesting depth).

---

## Best Practices

- **Always handle the `default`/unknown case.** A `switch` on node kind should error loudly on a kind you forgot, not silently do nothing. (In Rust, `match` enforces this for you.)
- **Don't parse code with regexes.** Regular expressions cannot handle nesting (matching parentheses, nested comments). If you find yourself regexing source code to extract structure, you want an AST.
- **Recurse into children.** A common beginner bug is visiting only the top level and missing nested nodes. In Python remember `generic_visit`; in a hand-written walker remember to recurse on every child.
- **Keep node kinds small and meaningful.** Each kind should represent one concept (`IfStatement`, `BinaryExpression`), not a grab-bag.
- **Use the standard tree when one exists.** For JavaScript, target **ESTree** (the de-facto standard) so your tool composes with the rest of the ecosystem. For Python, use the built-in `ast`. Don't reinvent the shape.
- **Read a real AST early.** Paste code into AST Explorer (astexplorer.net) and click around. Seeing the live tree for code you wrote is the fastest way to build intuition.

---

## Edge Cases & Pitfalls

- **Forgetting to recurse.** You write `visit_Call` and it only fires for top-level calls. You forgot `generic_visit` / forgot to descend. Nested calls are invisible.
- **Confusing the AST with the text.** The AST does not remember whether you wrote `1+2` or `1 + 2`. If your tool needs that, a plain AST is the wrong tool.
- **Assuming the parser kept your comments.** Most ASTs drop comments by default. If you need them (for a doc tool), you must ask the parser to attach them.
- **Off-by-one in source positions.** Editors are 1-based for lines but often 0-based for columns; AST libraries vary. Mixing them gives error messages that point one character off.
- **Empty bodies and optional children.** An `if` with no `else`, a function with no parameters, an empty block — the corresponding child is often `null` or an empty list. Walks must not crash on the missing piece.
- **Very deep trees.** Code like `1 + 1 + 1 + ... + 1` a thousand times produces a deeply nested tree; a naive recursive walk can blow the call stack. Rare for juniors, but real.

---

## Common Mistakes

| Mistake | Why it's wrong | Fix |
|---------|----------------|-----|
| Parsing code with `String.replace`/regex | Can't handle nesting, strings, comments | Build/use an AST |
| Visiting only the root's direct children | Misses everything nested | Recurse / call `generic_visit` |
| Expecting the AST to keep formatting | The AST drops whitespace and parens | Use a CST or a position-preserving tree |
| No `default` in the kind switch | Silently ignores unhandled nodes | Throw on unknown kinds |
| Treating a list child like a single child | Function args / block statements are *lists* | Iterate the list |
| Inventing your own JS AST shape | Won't interoperate with the ecosystem | Use ESTree |

---

## Apply it

1. Choose one small, known input for **Abstract Syntax Trees**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Abstract Syntax Trees solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
