# Interpreters — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Interpreters** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Compile vs. Interpret — the one-sentence difference

A **compiler** is a translator: source goes in, a different program (usually machine code) comes out, and you run *that* later. An **interpreter** is a performer: source goes in, and the *result of running it* comes out immediately. The compiler does its work once, ahead of time; the interpreter does its work every time the program runs.

You can feel the difference: `gcc hello.c` produces a file you run separately. `python hello.py` reads the file and *does what it says* on the spot. (Python actually compiles to bytecode first, then interprets that — more on this in `middle.md` — but from your seat, it just "runs" the file.)

### 2. The pipeline: text → tokens → tree → evaluation

Every interpreter, no matter how simple, has roughly these stages:

```text
  source text          tokens               AST                  result
  "2 + 3 * 4"   ──►   [2] [+] [3]    ──►    (+ 2 (* 3 4))   ──►    14
                      [*] [4]
   (lexer)            (parser)              (eval / tree-walk)
```

This page assumes the lexer and parser already exist (or that you write them quickly) and focuses on the **last arrow**: turning the tree into a result. That last arrow is the interpreter proper.

### 3. The AST is a tree of "what to do"

An AST node is just a small object/struct that says *what kind* of thing it is and holds its children. For arithmetic you might have:

```text
Number(value)                  e.g. Number(3)
BinaryOp(op, left, right)      e.g. BinaryOp("+", Number(2), BinaryOp("*", Number(3), Number(4)))
```

The expression `2 + 3 * 4` becomes a tree where `+` is the root, its left child is `2`, and its right child is the `*` subtree. Precedence (`*` binds tighter than `+`) is already baked into the *shape* of the tree by the parser — the interpreter does not re-think precedence; it just walks what it is given.

### 4. `eval(node)` — the heart of everything

The interpreter is one recursive function. It looks at the node's type and decides what to do:

```text
eval(node):
    if node is a Number:      return node.value
    if node is a BinaryOp:    left  = eval(node.left)
                              right = eval(node.right)
                              return apply(node.op, left, right)
```

That recursion is the entire idea. To evaluate any node, you **first evaluate its children, then combine them**. This pattern — recurse into children, then act — is called a *post-order traversal*, and it is how arithmetic, function calls, and almost everything else gets evaluated.

### 5. Variables live in an Environment

Programs have variables, so the interpreter needs somewhere to store them. That store is the **environment**: usually just a hash map from name to value.

```text
env = { "x": 10, "y": 25 }

eval(Variable("x"), env)  ->  look up "x" in env  ->  10
eval(Assign("x", expr), env)  ->  env["x"] = eval(expr, env)
```

The environment gets passed *into* `eval` so that every node can read and write variables. When you call a function or enter a block, you often create a *new* environment that can also see the outer one — that is how **scope** works, and we go deeper on it in `middle.md` and `senior.md`.

### 6. Statements vs. expressions

- An **expression** produces a value: `2 + 2` evaluates to `4`.
- A **statement** performs an action and usually produces no useful value: `print(x)`, `x = 5`, `if (c) { ... }`.

Your interpreter typically has `eval` for expressions (returns a value) and `exec` (or the same `eval`) for statements (performs effects). Control flow — `if`, `while` — lives on the statement side: you evaluate the condition expression, then *choose which branch to execute*.

### 7. Control flow is just conditional recursion

Here is the beautiful part: you do not need any special machinery for `if` and `while`. They fall out of ordinary host-language control flow inside `eval`:

```text
eval(If(cond, then_branch, else_branch), env):
    if truthy(eval(cond, env)):
        exec(then_branch, env)
    else:
        exec(else_branch, env)

eval(While(cond, body), env):
    while truthy(eval(cond, env)):
        exec(body, env)
```

The interpreter's `while` loop *implements* the interpreted language's `while` loop. The recursion and looping of the language you write the interpreter *in* (the **host language**) provide the recursion and looping of the language you are interpreting (the **guest language**).

### 8. Why tree-walking is slow (and why you should not care yet)

Each time you evaluate `x`, you walk to a `Variable` node, check its type, do a hash-map lookup by string name, and return. Each `+` re-dispatches on node type and chases pointers to its children, which may be scattered all over memory. For a tight loop running millions of times, all this pointer-chasing and per-node type-checking is *slow* — often 10–100× slower than a bytecode interpreter, and far slower than compiled code.

But for a config file, a template, a query, a build script, or a teaching language, "slow" is still microseconds, and *nobody cares*. Build the tree-walker first. Optimize only when a profiler tells you to. The bytecode approach in `middle.md` is the next step when speed actually matters.

---

## Code Examples

We will build a tiny but real tree-walking interpreter for a calculator-with-variables language. To keep the focus on **evaluation**, we hand-build the AST instead of parsing text. (Adding a parser is a great exercise — see `tasks.md`.)

The guest language supports: number literals, `+ - * /`, variables, assignment, and printing.

### Python — a complete tree-walking interpreter

```python
# --- AST node types (normally produced by a parser) ---
class Num:    # literal number
    def __init__(self, value): self.value = value

class Var:    # variable reference, e.g. x
    def __init__(self, name): self.name = name

class BinOp:  # e.g. left + right
    def __init__(self, op, left, right):
        self.op, self.left, self.right = op, left, right

class Assign: # x = expr
    def __init__(self, name, expr):
        self.name, self.expr = name, expr

class Print:  # print(expr)
    def __init__(self, expr): self.expr = expr

# --- The interpreter: one recursive eval over the tree ---
def eval_node(node, env):
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Var):
        if node.name not in env:
            raise NameError(f"undefined variable '{node.name}'")
        return env[node.name]
    if isinstance(node, BinOp):
        left  = eval_node(node.left, env)   # recurse into children first
        right = eval_node(node.right, env)
        if node.op == '+': return left + right
        if node.op == '-': return left - right
        if node.op == '*': return left * right
        if node.op == '/':
            if right == 0:
                raise ZeroDivisionError("division by zero")
            return left / right
        raise ValueError(f"unknown operator '{node.op}'")
    if isinstance(node, Assign):
        value = eval_node(node.expr, env)
        env[node.name] = value          # store into the environment
        return value
    if isinstance(node, Print):
        value = eval_node(node.expr, env)
        print(value)
        return value
    raise TypeError(f"cannot evaluate node: {node}")

# --- Run a small program: x = 2 + 3 * 4; print(x) ---
program = [
    Assign("x", BinOp('+', Num(2), BinOp('*', Num(3), Num(4)))),
    Print(Var("x")),
]

env = {}
for statement in program:
    eval_node(statement, env)
# prints: 14
```

That is a real interpreter. Note: `2 + 3 * 4` produced `14`, not `20`, because the *parser* would build the `*` deeper in the tree — the evaluator just respects the shape it is given.

### JavaScript — the same idea

```javascript
function evalNode(node, env) {
  switch (node.type) {
    case "Num":
      return node.value;
    case "Var":
      if (!(node.name in env)) throw new Error(`undefined variable '${node.name}'`);
      return env[node.name];
    case "BinOp": {
      const l = evalNode(node.left, env);
      const r = evalNode(node.right, env);
      switch (node.op) {
        case "+": return l + r;
        case "-": return l - r;
        case "*": return l * r;
        case "/":
          if (r === 0) throw new Error("division by zero");
          return l / r;
      }
      throw new Error(`unknown operator '${node.op}'`);
    }
    case "Assign": {
      const v = evalNode(node.expr, env);
      env[node.name] = v;
      return v;
    }
    case "Print": {
      const v = evalNode(node.expr, env);
      console.log(v);
      return v;
    }
  }
  throw new Error(`cannot evaluate node of type ${node.type}`);
}

// x = 2 + 3 * 4; print(x)
const program = [
  { type: "Assign", name: "x",
    expr: { type: "BinOp", op: "+",
            left: { type: "Num", value: 2 },
            right: { type: "BinOp", op: "*",
                     left: { type: "Num", value: 3 },
                     right: { type: "Num", value: 4 } } } },
  { type: "Print", expr: { type: "Var", name: "x" } },
];

const env = {};
for (const stmt of program) evalNode(stmt, env);
// logs: 14
```

### Adding control flow — `if` and `while`

Once the structure is in place, control flow is tiny. Here is the extra Python you would add:

```python
class If:
    def __init__(self, cond, then_branch, else_branch=None):
        self.cond, self.then_branch, self.else_branch = cond, then_branch, else_branch

class While:
    def __init__(self, cond, body):
        self.cond, self.body = cond, body

def truthy(v):
    return v != 0 and v is not None and v is not False

# inside eval_node, add:
#   if isinstance(node, If):
#       if truthy(eval_node(node.cond, env)):
#           for s in node.then_branch: eval_node(s, env)
#       elif node.else_branch:
#           for s in node.else_branch: eval_node(s, env)
#       return None
#   if isinstance(node, While):
#       while truthy(eval_node(node.cond, env)):
#           for s in node.body: eval_node(s, env)
#       return None
```

The guest's `while` is literally the host's `while`. That is the "host lends its powers" model in action.

### A two-line REPL

A Read-Eval-Print Loop is just `eval` in a loop, keeping the environment alive between lines:

```python
def repl():
    env = {}
    while True:
        line = input(">>> ")
        if line.strip() in ("exit", "quit"):
            break
        ast = parse(line)        # assume a parser exists
        result = eval_node(ast, env)
        if result is not None:
            print(result)
```

Because `env` persists across iterations, `x = 5` on one line is visible to `print(x)` on the next. That persistence *is* what makes a REPL feel like a session rather than a series of unrelated runs.

---

## Coding Patterns

### Pattern 1: One `eval` function, dispatch on node type

The backbone is a single function that switches on the node's kind. Keep each case small and obvious. This is the Visitor pattern's simplest form.

```python
def eval_node(node, env):
    if isinstance(node, Num):   return node.value
    if isinstance(node, BinOp): return eval_binop(node, env)
    if isinstance(node, Var):   return env_lookup(env, node.name)
    # ...one branch per node type...
```

### Pattern 2: Evaluate children first, then combine

For any non-leaf node, recurse into the operands *before* doing the operation. This post-order discipline is correct for arithmetic, comparisons, and function arguments.

```python
left  = eval_node(node.left, env)
right = eval_node(node.right, env)
return combine(node.op, left, right)
```

### Pattern 3: Thread the environment through every call

`env` is a parameter to `eval`, not a global. Passing it explicitly makes scope and function calls (which create new environments) clean to implement later.

### Pattern 4: Separate "evaluate value" from "execute effect"

Use `eval` for expressions (returns a value) and a parallel notion for statements (performs an action). Even if they share one function, keep the mental distinction — it prevents confusion when a statement accidentally needs to return something.

### Pattern 5: Keep node definitions dumb, logic in the interpreter

AST nodes should be plain data (fields only). Put all behavior in `eval`. This keeps the tree serializable, testable, and easy to print — and means there is *one place* to look for "what does this construct do."

---

## Best Practices

- **Write the tree-walker first, always.** Even if you know you will need bytecode later, the tree-walker is your reference implementation and your test oracle.
- **Carry source positions on every node.** Line and column on each node turn "error" into "error at line 7, column 3." Do this from day one; retrofitting is painful.
- **Make `eval` total over node types.** Have an explicit final `else` that raises "unhandled node type" — so a forgotten case fails loudly instead of returning `None` silently.
- **Test each node type in isolation.** A small unit test per construct (`2+2`, variable lookup, `if`, `while`) localizes bugs instantly.
- **Keep the environment explicit.** Pass it in; do not reach for a global. Globals make nested scopes and function calls a nightmare.
- **Define truthiness once.** Decide what counts as true/false in your guest language and put it in a single `truthy()` helper used everywhere.
- **Print your AST.** A `repr`/`toString` that shows the tree is the cheapest, most valuable debugging tool you can write.

---

## Edge Cases & Pitfalls

- **Operator precedence is the parser's job, not the evaluator's.** If `2 + 3 * 4` gives `20`, your *parser* built the wrong tree; the evaluator is faithfully walking it. Do not "fix" precedence in `eval`.
- **Undefined variable lookups.** Reading a name that was never assigned must raise a clear error, not return `None`/`undefined` and silently corrupt later math.
- **Division by zero and type errors.** Decide what your language does (error? infinity? `null`?) and handle it explicitly, with a good message.
- **Forgetting to return a value.** In some host languages, a missing `return` in an `eval` branch silently yields `None`/`undefined`, producing baffling downstream bugs. Make every branch return.
- **Mutating the wrong environment.** When you add functions and blocks, assigning to a variable should hit the right scope. Getting this wrong gives "my variable changed unexpectedly" bugs (covered in `middle.md`).
- **Deep recursion blows the host stack.** A tree-walker recurses as deep as the program nests; deeply nested expressions or deep guest recursion can overflow the *host's* call stack. Real interpreters manage their own stack to avoid this (see `senior.md`).
- **Evaluating both branches of an `if`.** Only execute the taken branch. Accidentally evaluating both (e.g. computing both then choosing) breaks side effects and short-circuiting.
- **Re-evaluating a subexpression by mistake.** If you call `eval(node.left)` twice, side effects (like assignments or prints) happen twice. Evaluate each child exactly once and store the result.

---

## Apply it

1. Choose one small, known input for **Interpreters**.
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

- What problem does Interpreters solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
