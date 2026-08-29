# Semantic Analysis — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Semantic Analysis** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Job: From "Spelled Right" to "Makes Sense"

After parsing, you have a tree that is *grammatically* valid. Semantic analysis asks a different question: is this tree *meaningful*? It does this by walking the tree and checking rules. The two biggest rule families:

1. **Name rules.** Every name used must be declared somewhere visible. This is **name resolution**.
2. **Type rules.** The types of operands and assignments must be compatible. This is **type checking**.

There are smaller rule families too — you can't `break` outside a loop, you can't `return` a value from a `void` function, you can't read a variable that was never given a value — but for a junior, name resolution and type checking are the heart of it.

### 2. Declarations vs. Uses

Every name in a program is either a **declaration** (introduces the name) or a **use** (refers to an existing name):

```text
let count = 0;     // declaration of `count`
count = count + 1; // two USES of `count` (read on right, write on left)
print(count);      // a USE of `count`, and a USE of `print`
```

Name resolution's job is to draw an arrow from every *use* back to its *declaration*. If you can't draw the arrow — there's no declaration in scope — that's the **"undefined variable"** error.

### 3. Scope: Where a Name Lives

A **scope** is the region of the program where a declaration is visible. The most familiar example is a function body or a `{ }` block:

```text
let x = 1;          // outer scope
{
    let y = 2;      // inner scope; y is visible only inside these braces
    print(x);       // OK — x is visible here (inner can see outer)
    print(y);       // OK — y is visible here
}
print(x);           // OK — x still visible
print(y);           // ERROR — y is out of scope here
```

The key rule of **lexical scope** (the default everywhere): an inner scope can see names from enclosing scopes, but an outer scope cannot see names declared inside a nested scope. Scopes nest like Russian dolls.

### 4. Shadowing

When an inner scope declares a name that already exists in an outer scope, the inner one **shadows** the outer one — within the inner scope, the name refers to the inner declaration:

```text
let x = 1;
{
    let x = 99;     // shadows the outer x
    print(x);       // prints 99
}
print(x);           // prints 1 — the outer x was never changed
```

Shadowing is legal in most languages (Rust even encourages it). Name resolution handles it naturally: it always picks the *nearest* enclosing declaration.

### 5. The Symbol Table

To resolve names, the compiler keeps a **symbol table**: a map from each name to information about it (where it was declared, its type, its scope). The simplest mental picture is a dictionary:

```text
{ "count" → (variable, type=int, declared at line 1) ,
  "print" → (function, takes any, declared in std) }
```

But one flat dictionary can't handle scopes — `x` might mean different things in different blocks. So real symbol tables are **scoped**: think of a *stack* of dictionaries, one per active scope. To **look up** a name, you search the top dictionary, then the one below, then below, until you find it or run out (which means "undefined"). You build the proper version in `middle.md`; for now, the mental model is "a stack of dictionaries."

### 6. Type Checking

Once names resolve, the compiler knows the *type* of every variable and expression. **Type checking** verifies the type rules. Walk the tree bottom-up: a literal `5` has type `int`, a literal `"hi"` has type `string`, and an expression like `a + b` has a type *derived from its parts*. If `a` is `int` and `b` is `int`, then `a + b` is `int` — fine. If `a` is `int` and `b` is `string`, the language may forbid it — that's a **type error**.

```text
let a: int = 5;
let b: string = "x";
let c = a + b;   // TYPE ERROR: cannot add int and string
```

Type checking also covers function calls (right number of arguments? right types?), assignments (is the value's type assignable to the variable?), and more. The output is an AST where every expression node knows its type — sometimes called the **typed AST** or **decorated AST**.

### 7. The Output: A Decorated AST

Semantic analysis doesn't usually *transform* the tree into something new; it **decorates** it. Each name-use node gets a pointer to its declaration; each expression node gets its computed type. The next phase (IR generation / code generation) consumes this decorated tree — it relies on semantic analysis having already proven everything is valid, so it can generate code without worrying about errors.

---

## Code Examples

These examples are written in pseudo-Python so you can see the *logic* of semantic analysis without language ceremony. They are deliberately tiny.

### Example 1: A flat symbol table (no scopes yet)

```python
# The simplest possible symbol table: one global dictionary.
symbols = {}

def declare(name, type_):
    if name in symbols:
        raise SemanticError(f"'{name}' already declared")
    symbols[name] = type_

def lookup(name):
    if name not in symbols:
        raise SemanticError(f"undefined variable '{name}'")
    return symbols[name]

# Walking these statements:
#   let x: int = 5
#   print(x)
#   print(y)        <-- y was never declared
declare("x", "int")     # symbols = { x: int }
lookup("x")             # OK, returns "int"
lookup("y")             # raises: undefined variable 'y'
```

This works for a program with no blocks. The moment you add `{ }` scopes, a flat dictionary breaks — because `x` inside a block can be a different `x`. That's why we need a *scoped* table.

### Example 2: A scoped symbol table (a stack of dictionaries)

```python
class ScopeStack:
    def __init__(self):
        self.scopes = [{}]          # start with one global scope

    def enter_scope(self):
        self.scopes.append({})      # push a fresh dictionary

    def exit_scope(self):
        self.scopes.pop()           # discard the innermost scope

    def declare(self, name, type_):
        top = self.scopes[-1]
        if name in top:             # redeclaration in the SAME scope is usually an error
            raise SemanticError(f"'{name}' already declared in this scope")
        top[name] = type_

    def lookup(self, name):
        # Search from innermost to outermost — this gives us shadowing for free.
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise SemanticError(f"undefined variable '{name}'")
```

Notice that `lookup` searches **innermost first**. That single line is what makes *shadowing* work: the nearest declaration always wins.

### Example 3: Resolving names while walking the tree

```python
# Pretend the parser gave us this tree for:
#   let x = 1
#   { let y = 2; use(x); use(y) }
#   use(y)         <-- ERROR
#
# Each node is a dict with a "kind".

def analyze(node, scopes):
    kind = node["kind"]

    if kind == "Block":
        scopes.enter_scope()
        for stmt in node["body"]:
            analyze(stmt, scopes)
        scopes.exit_scope()         # y disappears here

    elif kind == "Let":
        analyze(node["value"], scopes)          # check the right-hand side first
        scopes.declare(node["name"], "int")     # then declare the name

    elif kind == "Use":
        scopes.lookup(node["name"])             # raises if undefined
```

Walk through it: `let x` declares `x` in the global scope. The `Block` pushes a new scope; `let y` declares `y` there; `use(x)` finds `x` two scopes down (fine); `use(y)` finds `y` in the top scope (fine). Then the block exits and pops the scope — `y` is gone. The final `use(y)` searches and finds nothing → **"undefined variable 'y'"**. The scope mechanics produce exactly the error a real compiler gives.

### Example 4: A tiny type checker

```python
def type_of(node, scopes):
    kind = node["kind"]

    if kind == "IntLiteral":
        return "int"
    if kind == "StringLiteral":
        return "string"

    if kind == "Name":
        return scopes.lookup(node["name"])     # type comes from the symbol table

    if kind == "Add":
        left  = type_of(node["left"], scopes)
        right = type_of(node["right"], scopes)
        if left == "int" and right == "int":
            return "int"
        if left == "string" and right == "string":
            return "string"                    # allow string concatenation
        raise SemanticError(
            f"cannot add {left} and {right}")  # the classic type error
```

This is type checking in miniature: compute the type of each subexpression *bottom-up*, then apply the rule for the operator. `5 + 3` → both `int` → `int`. `5 + "x"` → `int` and `string` → **type error**. The leaves know their types directly; everything above derives its type from its children.

### Example 5: What a real type error looks like

```text
$ compile demo.lang

demo.lang:3:9: error: cannot add `int` and `string`
    let c = a + b;
            ^ ~~~
note: `a` has type `int`   (declared at demo.lang:1)
note: `b` has type `string` (declared at demo.lang:2)
```

That diagnostic — the line, the caret pointing at the offending expression, the explanation of each operand's type — is the *output* of semantic analysis. The whole point of the phase is to produce messages like this so the programmer can fix the meaning, not just the spelling.

### Example 6: Forward references need two passes

```python
# Consider:
#   foo()                 <-- used here, BEFORE it's declared
#   func foo() { ... }    <-- declared here

# A SINGLE top-to-bottom pass would fail: at foo()'s use, foo isn't in
# the table yet. The fix is TWO passes:

def pass1_collect(program, scopes):
    # First, declare all top-level functions, ignoring their bodies.
    for item in program:
        if item["kind"] == "Func":
            scopes.declare(item["name"], "function")

def pass2_check(program, scopes):
    # Now every function name is already known, so calls resolve
    # regardless of order.
    for item in program:
        analyze(item, scopes)

# This is why you can call a function defined later in the file in
# Go, Java, C# and many others: the compiler collects declarations
# first, then checks bodies.
```

This is a junior's first taste of why semantic analysis needs **multiple passes**: forward references are impossible to resolve in one downward pass.

---

## Coding Patterns

- **The visitor pattern.** Semantic analysis walks the AST. The cleanest way to do that is a *visitor* — one method per node kind (`visit_Let`, `visit_Add`, `visit_Name`). Each method does its check and recurses into children.

- **Enter/exit scope around blocks.** Whenever you walk into a construct that introduces a scope (block, function body, loop), `enter_scope()` on the way in and `exit_scope()` on the way out. Pair them religiously — a missing `exit_scope` corrupts every lookup after it.

- **Declare-then-check the body.** For functions, *declare the name first* (so recursion and forward references work), then walk the body. Doing it in the wrong order breaks recursive functions.

- **Bottom-up typing.** Compute a node's type from its children's types. Leaves (literals, names) return their type directly; internal nodes combine them. This recursion is the spine of every type checker.

- **Collect-then-resolve for the top level.** Two passes: pass one declares all top-level names; pass two checks bodies. This is the standard fix for forward references at file scope.

---

## Clean Code

- **One responsibility per pass.** Don't try to resolve names, check types, and emit warnings all in one tangled walk. Even a junior project benefits from separating "build symbol table" from "check types."

- **Make the symbol table a real object.** Don't sprinkle raw dictionaries through your walker. A `ScopeStack` with `declare`/`lookup`/`enter`/`exit` methods keeps the scope logic in one place.

- **Always carry source locations.** Every AST node should know its line and column. Without it, your errors say "type error" with no location — useless. With it, you can point a caret at the exact spot.

- **Name your errors precisely.** "undefined variable 'foo'" is helpful; "semantic error" is not. The clarity of your diagnostics *is* the quality of your compiler from a user's perspective.

- **Don't mutate the tree destructively.** Decorate it — add a `.resolved_type` or `.binding` field — rather than replacing nodes. Later phases and error messages may still need the original shape.

---

## Best Practices

- **Resolve right-hand sides before declaring the left-hand side.** In `let x = x + 1`, the `x` on the right should refer to the *outer* `x` (or be an error), and only *after* checking the value do you declare the new `x`. Order matters.

- **Report multiple errors, not just the first.** Don't stop at the first undefined variable. Recover and keep walking so the programmer sees all their errors in one compile.

- **Use a sentinel "error type."** When an expression has a type error, give it a special `ErrorType` instead of crashing. Then `ErrorType + anything = ErrorType` with *no new error* — this stops one mistake from producing ten cascading messages.

- **Keep scopes lexical.** Match the language's `{ }` (or indentation) structure exactly. Enter a scope where the source enters one; exit where it exits.

- **Separate "declared here" from "used here" in messages.** The best diagnostics show both the use that failed *and* where the conflicting declaration lives. Carry that information in your symbol table.

---

## Edge Cases & Pitfalls

- **Use-before-declaration in the same scope.** `print(x); let x = 1;` — should this resolve `x`? In most languages, no (the variable isn't in scope yet on that line). Your walker must declare names at the right *point*, not for the whole block at once. (Note: function declarations at file scope are the exception — see two-pass.)

- **Forgetting to pop a scope.** If you `enter_scope()` but a code path skips `exit_scope()` (e.g., an early `return` in your walker), every subsequent lookup is polluted with stale names. Use try/finally or a context manager.

- **Redeclaration in the same scope.** `let x = 1; let x = 2;` in the same block is an error in many languages. But the *same name in a nested block* is legal shadowing. Your `declare` must check only the *current* (top) scope for conflicts, not the whole stack.

- **The right type but wrong direction.** Assigning `int` to a `float` variable is usually fine (widening); assigning `float` to `int` is often an error (narrowing). Type checking is not symmetric — "assignable to" has a direction.

- **Self-referential declarations.** `let x = x;` where the right `x` doesn't exist yet is an error; but `func f() { f(); }` (recursion) must work. The difference is *when* the name becomes visible — and it's why functions are declared before their bodies are checked.

---

## Common Mistakes

- **Treating syntax and semantics as the same phase.** They're separate. The parser does *not* know what `x` means; it only knows it's an identifier. Don't put type checks in the parser.

- **Using one flat symbol table for the whole program.** It works for a calculator and breaks the instant you have blocks or functions. Use a scoped table from the start.

- **Looking up names in the wrong direction.** If you search outermost-to-innermost, shadowing breaks (you'd find the outer `x` instead of the inner one). Always search innermost-first.

- **Crashing on the first error.** A compiler that dies on the first undefined variable is infuriating to use. Recover and continue.

- **Forgetting that types come from the symbol table.** A `Name` node's type isn't stored on the node — it's looked up from where the name was declared. Beginners often try to read it off the use site.

---

## Tricky Points

- **"Lexical" means "where it's written," not "when it runs."** Static/lexical scope is decided by the source layout, fully at compile time. (A few old languages used *dynamic* scope — meaning depended on the call stack at runtime — but that's rare and confusing, which is why lexical scope won.)

- **Declaration order inside a block matters; at file scope it often doesn't.** Inside a function, you usually must declare before use. At the top level of a file, the compiler collects declarations first, so you can call a function defined later. Same language, two different rules — because of two-pass analysis.

- **A type error doesn't mean the program is "wrong" in every language.** A dynamically typed language (Python, JavaScript) does *no* static type checking — `5 + "x"` is found only at runtime. Static type checking is a *choice* a language makes.

- **Shadowing is not reassignment.** `let x = 99` inside a block creates a *new* variable that hides the old one. The outer `x` is untouched. Beginners often think shadowing changes the original.

---

## Apply it

1. Choose one small, known input for **Semantic Analysis**.
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

- What problem does Semantic Analysis solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
