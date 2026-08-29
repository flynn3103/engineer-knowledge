# DSLs in Practice — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **DSLs in Practice** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The front end / back end split

Draw a hard line through your DSL:

```text
        FRONT END                         BACK END (pick one or more)
text → lex → tokens → parse → AST  ─┬─→ interpret  → run now
                                    ├─→ compile    → bytecode → VM
                                    ├─→ transpile  → SQL / JS / Go source
                                    └─→ analyse    → lints, type-check, docs
```

The AST is the contract between the two halves. This separation is the single most valuable design decision: the same front end can feed an interpreter for development, a transpiler for production, *and* a linter for editor tooling. Mixing parsing with evaluation (a classic beginner shortcut) destroys that reuse.

### 2. The four ways to build the front end

**Recursive descent (hand-written).** One function per rule. Best when: you want full control, the best possible error messages, and no build-time dependency. This is what most production language front ends actually use (Go, Clang, the V8 parser, `rustc`). Downside: operator precedence with many levels gets verbose.

**Pratt parsing (top-down operator precedence).** A refinement of recursive descent specifically for expressions with many operators and precedence levels. Each token gets a *binding power*; the parser loops, consuming operators while their binding power exceeds the current threshold. Best when: your DSL has rich expressions (`a + b * c ^ d == e`). It collapses a tower of `expression`/`term`/`factor` functions into one elegant loop.

**Parser combinators.** A parser is "a function from input to (result, rest-of-input)." Tiny parsers (`number`, `keyword("SELECT")`) combine with operators: `seq(a, b)`, `a.or(b)`, `many(a)`. Libraries: **parsec** (Haskell), **nom** (Rust), **FParsec** (F#), and ports in many languages. Best when: you want a parser that reads almost like the grammar, in code, with no separate build step. They shine for medium DSLs and config formats. Downside: error messages and left-recursion need care; performance can lag a tuned hand-written parser.

**Parser generators (ANTLR, Lex/Yacc).** You write a grammar file; the tool generates lexer + parser source. **ANTLR** is the modern go-to for external DSLs: write `Expr.g4`, run ANTLR, get a lexer, parser, and a **visitor** skeleton in Java/Python/Go/C#/JS. **Lex/Yacc** (and GNU **Flex/Bison**) are the classic C toolchain: Lex generates the lexer from regex rules, Yacc generates an **LR** parser from a grammar. Best when: the grammar is large and stable, you want the grammar itself to be the source of truth, and you can accept generated code plus a build step. Downside: less control over errors, a learning curve, and a build dependency.

A practical rule: **small/medium DSL → recursive descent or combinators; expression-heavy → add Pratt; large formal grammar → ANTLR.**

### 3. Variables and environments

The moment your DSL has names (`let x = 5`, then `x + 1`), the interpreter needs an **environment**: a map from name to value, threaded through evaluation. Nested scopes (a function body, a block) become *chained* environments — look up a name in the current scope, fall back to the parent. This is the seed of how every real language handles scope.

### 4. Interpret vs compile/transpile — the back-end choice

- **Interpret (tree-walk).** Walk the AST each time you run. Simplest, easiest to debug, fast to *build*. Slowest to *run*. Right for config evaluation, one-shot rule checks, REPLs.
- **Compile to bytecode.** Turn the AST into a flat instruction list a small VM executes. More work; much faster for repeated execution (a rules engine evaluating millions of events).
- **Transpile to another language.** Emit source in a target the host already runs well. The biggest real-world category:
  - A query DSL → **SQL** (you generate `SELECT ... WHERE ...`).
  - A template language → **HTML**/text.
  - A reactive-UI DSL → **JavaScript**.
  - A schema DSL (Protobuf `.proto`) → generated structs in many languages.
  Transpiling lets you reuse a mature engine (the SQL database, the JS runtime) instead of writing your own.

### 5. Error messages are a feature

A DSL's error messages are part of its UX. Minimum bar: report **line and column**, the **token that was unexpected**, and **what was expected**. Better: show the offending source line with a caret. Hand-written parsers (recursive descent / Pratt) give you the most control here, which is a major reason production languages avoid generators. For multi-error reporting you add **error recovery**: on a parse error, skip tokens until a *synchronisation point* (a `;`, a newline, a closing brace), then keep parsing so the user sees *all* their mistakes, not just the first.

### 6. Where the internal/external line really bites

An **internal** DSL (method chains in the host language) gives you the host's parser and error messages for free — but every expression must be valid host syntax, so you cannot have your own keywords or operators, and a typo produces a *host*-language error, not a domain error. An **external** DSL gives you any syntax and domain-specific errors, at the cost of building (and maintaining) everything on this page. Choosing external means signing up for a lexer, a parser, an evaluator/transpiler, *and* eventually tooling — forever.

---

## Code Examples

### A Pratt parser for expressions

This replaces the junior tower (`expression`/`term`/`factor`) with one loop driven by binding powers. Adding a new operator is a one-line table change.

```python
# binding power (precedence). higher = binds tighter.
BP = {"+": 10, "-": 10, "*": 20, "/": 20, "^": 30}
RIGHT_ASSOC = {"^"}            # exponent groups right: 2^3^2 = 2^(3^2)

class Pratt:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def peek(self): return self.toks[self.i]
    def next(self):
        t = self.toks[self.i]; self.i += 1; return t

    # parse an expression whose operators must bind tighter than `min_bp`
    def expr(self, min_bp=0):
        tok = self.next()
        if tok[0] == "NUMBER":
            left = ("number", tok[1])
        elif tok[0] == "(":
            left = self.expr(0)
            assert self.next()[0] == ")", "expected )"
        elif tok[0] == "-":                      # unary minus (prefix)
            left = ("neg", self.expr(100))
        else:
            raise SyntaxError(f"unexpected {tok}")

        while True:
            op = self.peek()[0]
            if op not in BP or BP[op] < min_bp:
                break
            self.next()
            # for right-assoc, recurse with the SAME bp; else bp+1
            next_min = BP[op] if op in RIGHT_ASSOC else BP[op] + 1
            right = self.expr(next_min)
            left = ("binop", op, left, right)
        return left
```

The whole precedence table lives in `BP`. Compare with three near-identical functions in recursive descent — Pratt is why interpreter authors love it for expression languages.

### Transpiling a filter DSL to SQL

A common real task: a safe little filter language that users type, which you turn into a parameterised SQL `WHERE` clause. Input like `age > 18 and country = "US"` becomes SQL plus bound parameters (never string-concatenated — that would be SQL injection).

```python
# AST shape from a small parser (omitted):
#   ("and", left, right) | ("cmp", op, field, value)
def to_sql(node, params):
    kind = node[0]
    if kind == "and":
        l = to_sql(node[1], params)
        r = to_sql(node[2], params)
        return f"({l} AND {r})"
    if kind == "or":
        l = to_sql(node[1], params)
        r = to_sql(node[2], params)
        return f"({l} OR {r})"
    if kind == "cmp":
        _, op, field, value = node
        if field not in ALLOWED_FIELDS:           # allow-list, not raw input
            raise ValueError(f"unknown field {field}")
        params.append(value)                       # parameterised!
        return f"{field} {op} ?"
    raise ValueError(node)

ALLOWED_FIELDS = {"age", "country", "status"}

params = []
where = to_sql(("and",
                ("cmp", ">", "age", 18),
                ("cmp", "=", "country", "US")), params)
print(where)    # (age > ? AND country = ?)
print(params)   # [18, 'US']
# final query:  SELECT * FROM users WHERE (age > ? AND country = ?)
```

Two things make this safe and maintainable: an **allow-list of fields** (the DSL cannot reference arbitrary columns) and **parameter binding** (values never enter the SQL string). This is the heart of "transpile a DSL to SQL," and the security points return at the senior level.

### A parser combinator sketch (in code)

Combinators in miniature, to show the style. Each parser is a function `input -> (value, rest) | None`.

```python
def lit(s):                                  # match a literal string
    def p(inp):
        if inp.startswith(s):
            return (s, inp[len(s):])
        return None
    return p

def seq(*parsers):                           # all in order
    def p(inp):
        out = []
        for parser in parsers:
            r = parser(inp)
            if r is None: return None
            val, inp = r
            out.append(val)
        return (out, inp)
    return p

def alt(*parsers):                           # first that matches
    def p(inp):
        for parser in parsers:
            r = parser(inp)
            if r is not None: return r
        return None
    return p

# grammar in code: greeting := ("hello" | "hi") " world"
greeting = seq(alt(lit("hello"), lit("hi")), lit(" world"))
print(greeting("hi world"))     # (['hi', ' world'], '')
print(greeting("bye"))          # None
```

Real libraries (parsec, nom, FParsec) add whitespace handling, error positions, `many`, `sep_by`, and backtracking control — but this is the whole idea: build big parsers from small ones.

### Interpreter with variables (an environment)

```python
def evaluate(node, env):
    kind = node[0]
    if kind == "number":  return node[1]
    if kind == "var":     return env[node[1]]
    if kind == "let":                       # ("let", name, value_expr, body)
        _, name, value_expr, body = node
        new_env = dict(env)
        new_env[name] = evaluate(value_expr, env)
        return evaluate(body, new_env)
    if kind == "binop":
        _, op, a, b = node
        x, y = evaluate(a, env), evaluate(b, env)
        return {"+": x+y, "-": x-y, "*": x*y, "/": x/y}[op]
    raise ValueError(node)

# let x = 10 in x * 2   →  20
tree = ("let", "x", ("number", 10), ("binop", "*", ("var", "x"), ("number", 2)))
print(evaluate(tree, {}))   # 20
```

A fresh `dict(env)` per scope gives correct lexical scoping cheaply. Real interpreters chain environments instead of copying, but the model is the same.

---

## Coding Patterns

### Pattern: separate `Lexer`, `Parser`, and `Evaluator`/`Emitter` classes

Three files, three responsibilities. The `Emitter` (for transpilers) or `Evaluator` (for interpreters) shares the same `Parser`.

### Pattern: the Visitor for AST traversal

For anything beyond a toy, give each node type a class and write a visitor with one method per type (`visit_binop`, `visit_let`). ANTLR generates exactly this. It keeps the interpreter, the transpiler, and the linter as *separate visitors* over one AST.

### Pattern: Pratt binding-power table

Keep precedence as data (`{"+": 10, "*": 20}`) so adding operators never touches control flow. Encode associativity by whether you recurse with `bp` (right) or `bp + 1` (left).

### Pattern: parameterised emission for transpilers

When transpiling to SQL or any host language, *never* inline user values into the output string. Emit placeholders and collect values separately. This is both a correctness and a security pattern.

### Pattern: error recovery via synchronisation tokens

After a parse error, skip tokens until a known boundary (`;`, newline, `}`), then resume. Collect errors in a list; report them all at the end.

---

## Best Practices

- **Pick the parser style deliberately.** Map it to the grammar's shape (see the rule in Core Concepts), not to whatever you used last.
- **Keep an explicit grammar.** Even hand-written parsers benefit from a written EBNF in comments or docs — it is the spec the code must match.
- **Make the AST back-end-agnostic.** No SQL strings or evaluation logic inside parse functions. The AST should not know whether it will be interpreted or transpiled.
- **Report line and column on every error.** Carry positions on tokens from the lexer onward; you cannot reconstruct them later.
- **Prefer transpiling onto a mature engine when semantics fit.** A DSL that compiles to SQL inherits the planner, indexes, and optimiser. Do not reinvent a query engine.
- **Version your grammar from day one.** Even a `# dsl-version: 1` header lets you evolve syntax without breaking old files. (Versioning gets serious at senior level.)
- **Test at the boundaries between stages.** Snapshot the token list and the AST, not just final outputs. A wrong AST that happens to evaluate right will bite you when you add a back end.
- **Resist feature creep.** Each new keyword is permanent grammar, parser code, docs, and tooling. "Just add loops to the config language" is how a config format becomes an accidental programming language.

---

## Edge Cases & Pitfalls

- **Left recursion in combinators and naive recursive descent.** A rule like `expr := expr '+' term` calls itself with no progress and loops forever. Rewrite to iteration (`term ('+' term)*`) or use Pratt.
- **Operator associativity bugs.** `8 - 3 - 2` must be `3`, not `7`. Right-associate by accident and your arithmetic is silently wrong. Pratt's `bp` vs `bp+1` choice is exactly this.
- **Greedy vs longest-match lexing.** Adding `==` while the lexer reads one char at a time makes it see two `=` tokens. The lexer must look ahead for multi-character operators (`==`, `<=`, `->`).
- **String concatenation into SQL/HTML when transpiling.** The injection trap. Always parameterise (SQL) or escape (HTML). A transpiler that builds output by `+`-ing user text is a vulnerability factory.
- **One-error-then-die parsing.** Users hate fixing errors one run at a time. Add synchronisation-based recovery so you can report several.
- **Environment mutation across scopes.** Sharing one mutable `env` dict between scopes leaks variables out of blocks. Copy or chain environments.
- **Forgetting to consume EOF.** `1 + 2 garbage` parses the `1 + 2` and silently ignores the rest unless you assert end-of-input.
- **Choosing ANTLR for a five-rule grammar.** The build step, generated code, and tool dependency are overkill for something a 100-line recursive-descent parser handles with better errors.
- **Choosing hand-written for a 300-rule grammar.** Conversely, hand-maintaining a huge grammar is error-prone; that is exactly where a generator earns its keep.

You now have the tools to build a *usable* external DSL: a parser chosen for the grammar, variables and scope, real error messages, and a back end that either interprets or transpiles. The `senior.md` level goes deeper on compiling DSLs (bytecode, LLVM, transpiling at scale), **sandboxing untrusted DSLs** (resource limits, no arbitrary code execution), grammar **versioning and evolution**, and building **tooling** (LSP, formatter, highlighting) for your language.

---

## Apply it

1. Find a real component where **DSLs in Practice** affects an interface or dependency.
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

- Which boundary is most affected by DSLs in Practice?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
