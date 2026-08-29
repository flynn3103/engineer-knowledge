# DSLs in Practice — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **DSLs in Practice** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A DSL is *text that a program reads*

The single most important idea: when you write `SELECT name FROM users`, those characters are just a **string**. Some program — the database — reads that string, figures out what it means, and acts on it. A DSL implementation is exactly such a program. Our job in this topic is to *be* that program for a language of our own.

So an external DSL always has two sides:

1. The **language** itself: its keywords, syntax, and meaning (the part a *user* sees).
2. The **implementation**: the lexer + parser + evaluator that reads the language (the part a *builder* writes).

A junior usually only ever sees side 1. This topic is about side 2.

### 2. The pipeline: text → tokens → tree → result

Almost every external DSL is processed the same way:

```text
"3 + 4 * 2"
     │
     ▼  LEXER  (split into tokens)
[ NUMBER(3), PLUS, NUMBER(4), STAR, NUMBER(2) ]
     │
     ▼  PARSER  (arrange into a tree by grammar rules)
        ( + )
       /     \
    3       ( * )
            /    \
          4       2
     │
     ▼  INTERPRETER  (walk the tree, compute)
11
```

- The **lexer** does *not* understand `+` versus `*` precedence. It just chops the string into meaningful pieces. It would reject `3 @ 4` only if `@` is not a valid character.
- The **parser** understands structure. It knows `*` binds tighter than `+`, so it builds `3 + (4 * 2)`, not `(3 + 4) * 2`. It rejects nonsense like `3 + + 4`.
- The **interpreter** understands meaning. It walks the tree bottom-up: compute `4 * 2 = 8`, then `3 + 8 = 11`.

This is the whole game. Every DSL — SQL, a config language, a rules engine — is some version of this pipeline.

### 3. Lexing: from characters to tokens

The lexer reads the input one character at a time and groups characters into tokens:

- It skips whitespace (`" "`, tabs, newlines) — those usually do not matter.
- When it sees a digit, it keeps reading digits to form a whole `NUMBER`.
- When it sees a letter, it keeps reading letters to form a `WORD` (which might be a keyword like `SELECT` or a name like `users`).
- Single characters like `+`, `*`, `(`, `)` become their own tokens.

Each token carries a **type** (`NUMBER`, `PLUS`, `NAME`) and sometimes a **value** (the actual number `3`, the actual name `"users"`).

### 4. Parsing: from tokens to a tree

The parser asks: *do these tokens form a valid program, and what is its structure?* The simplest way to write a parser by hand is **recursive descent**: you write one function per "shape" in the language. For a calculator:

- `parseExpression()` handles `+` and `-`.
- `parseTerm()` handles `*` and `/`.
- `parseFactor()` handles a number or a parenthesised sub-expression.

These functions call each other, and the nesting of the calls *is* the tree. We will see the code shortly.

### 5. Interpreting vs compiling

Once you have a tree you can do one of two things:

- **Interpret it** — walk the tree and produce a result *right now*. This is the easiest and what we do at this level. A spreadsheet evaluating `=A1+A2` interprets a tiny formula DSL.
- **Compile / transpile it** — translate the tree into something else: bytecode, machine code, or another language (a DSL that turns into SQL, or into JavaScript). The result runs later. This is more work but can be faster and reusable. Higher levels cover it.

For a junior, "DSL" mostly means "I parse it and interpret it."

### 6. The "little languages" idea

Unix is full of tiny DSLs: `awk` for text processing, `sed` for stream edits, `make` for builds, `dc` for arithmetic, `find`'s expression syntax. The philosophy — credited to Jon Bentley's *Little Languages* essay — is that a small, focused language often beats a pile of command-line flags or a big config file. You are learning to build exactly these.

---

## Code Examples

We will build a **four-function calculator DSL** end to end in Python: it reads strings like `"3 + 4 * (2 - 1)"` and prints the answer. This is the smallest complete external DSL — lexer, parser, interpreter — and the foundation for everything later.

### Step 1 — The lexer (text → tokens)

```python
# tokens are just (type, value) pairs
def lex(src):
    tokens = []
    i = 0
    while i < len(src):
        c = src[i]
        if c.isspace():                 # skip spaces, tabs, newlines
            i += 1
        elif c.isdigit():               # read a whole number
            num = ""
            while i < len(src) and src[i].isdigit():
                num += src[i]
                i += 1
            tokens.append(("NUMBER", int(num)))
        elif c in "+-*/()":             # single-character tokens
            tokens.append((c, c))
            i += 1
        else:
            raise SyntaxError(f"unexpected character: {c!r}")
    tokens.append(("EOF", None))        # marks the end of input
    return tokens

print(lex("3 + 4 * 2"))
# [('NUMBER', 3), ('+', '+'), ('NUMBER', 4), ('*', '*'), ('NUMBER', 2), ('EOF', None)]
```

The lexer never thinks about precedence or validity of *structure*. It only knows characters. Notice the `EOF` token at the end — a tiny trick that makes the parser simpler because it always has "one more token" to look at.

### Step 2 — The parser (tokens → AST)

We use **recursive descent**, with three functions matching three grammar rules. The AST is just nested tuples.

```python
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def eat(self, kind):
        tok = self.tokens[self.pos]
        if tok[0] != kind:
            raise SyntaxError(f"expected {kind}, got {tok[0]}")
        self.pos += 1
        return tok

    # expression := term (('+' | '-') term)*
    def expression(self):
        node = self.term()
        while self.peek()[0] in ("+", "-"):
            op = self.eat(self.peek()[0])[0]
            right = self.term()
            node = ("binop", op, node, right)
        return node

    # term := factor (('*' | '/') factor)*
    def term(self):
        node = self.factor()
        while self.peek()[0] in ("*", "/"):
            op = self.eat(self.peek()[0])[0]
            right = self.factor()
            node = ("binop", op, node, right)
        return node

    # factor := NUMBER | '(' expression ')'
    def factor(self):
        tok = self.peek()
        if tok[0] == "NUMBER":
            self.eat("NUMBER")
            return ("number", tok[1])
        if tok[0] == "(":
            self.eat("(")
            node = self.expression()
            self.eat(")")
            return node
        raise SyntaxError(f"unexpected token {tok[0]}")

def parse(src):
    p = Parser(lex(src))
    tree = p.expression()
    p.eat("EOF")               # nothing should be left over
    return tree

print(parse("3 + 4 * 2"))
# ('binop', '+', ('number', 3), ('binop', '*', ('number', 4), ('number', 2)))
```

The magic of precedence: because `expression` calls `term`, and `term` reads all the `*`/`/` it can before returning, multiplication "sticks together" *below* addition in the tree. We did not write any precedence table — the *shape of the function calls* encodes it.

### Step 3 — The interpreter (AST → value)

```python
def evaluate(node):
    kind = node[0]
    if kind == "number":
        return node[1]
    if kind == "binop":
        _, op, left, right = node
        a = evaluate(left)        # recurse into children first
        b = evaluate(right)
        if op == "+": return a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op == "/": return a / b
    raise ValueError(f"unknown node {node}")

def run(src):
    return evaluate(parse(src))

print(run("3 + 4 * 2"))      # 11
print(run("(3 + 4) * 2"))    # 14
print(run("10 / 4 - 1"))     # 1.5
```

That is a complete external DSL: 60-ish lines, three clearly separated stages, its own syntax. Everything in this topic is an elaboration of these three steps.

### A second tiny DSL: a key=value config reader

Not every DSL is arithmetic. Here is a minimal config language (`port = 8080` style), to show the same pipeline applied to a different domain.

```python
def parse_config(text):
    config = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.split("#", 1)[0].strip()   # strip comments + whitespace
        if not line:
            continue
        if "=" not in line:
            raise SyntaxError(f"line {lineno}: expected key = value")
        key, value = line.split("=", 1)
        config[key.strip()] = value.strip()
    return config

cfg = parse_config("""
    # server settings
    port = 8080
    host = localhost
""")
print(cfg)   # {'port': '8080', 'host': 'localhost'}
```

This is a *line-oriented* DSL — no recursion needed because the structure is flat. Recognising when your DSL is flat (config) versus nested (expressions) tells you how much parsing machinery you actually need.

---

## Coding Patterns

### Pattern: keep the three stages separate

```text
lex(text)        -> [tokens]
parse([tokens])  -> AST
evaluate(AST)    -> result
```

Never mix them. If lexing happens inside parsing, a bug in one hides the other. Three functions, three responsibilities.

### Pattern: one parse function per grammar rule

In recursive descent, the cleanest design maps each rule to a method (`expression`, `term`, `factor`). If you can write the rule in English, you can write the method.

### Pattern: a `peek`/`eat` pair for the parser

`peek()` looks at the current token without consuming it; `eat(kind)` consumes it and errors if it is the wrong kind. Almost every hand-written parser has this pair. It keeps position-tracking in one place.

### Pattern: represent the AST as simple data

At this level, use tuples or small dicts (`("binop", "+", left, right)`). You do not need classes yet. The interpreter just matches on the first element.

### Pattern: an `EOF` sentinel token

Always append an end-of-input token in the lexer so the parser never indexes past the end of the list. It also gives you a clean "expected end of input but found extra tokens" error.

---

## Best Practices

- **Build the smallest thing that works first.** Get `1 + 1` returning `2` before adding parentheses or variables. A DSL grows feature by feature.
- **Test the lexer alone.** Print the token list for a few inputs and eyeball it before touching the parser. Most "parser bugs" are actually lexer bugs.
- **Give errors a position.** Even just "syntax error at character 7" is hugely kinder to users than "syntax error."
- **Reject leftover input.** After parsing, assert you reached `EOF`. Otherwise `3 + 4 garbage` silently returns `7` and ignores the garbage.
- **Write down your grammar in comments.** The three-line grammar above is documentation *and* the structure of your code.
- **Don't add features you don't need.** A calculator does not need variables until something actually needs variables. (Higher levels discuss the "config language that grew into a programming language" trap — the seed of it is added "just one more feature.")
- **Prefer interpreting first.** Compiling/transpiling is an optimisation. Make it correct by interpreting, then make it fast if you must.

---

## Edge Cases & Pitfalls

- **Empty input.** What does your DSL do with `""`? Decide: error, or "no result." Handle it explicitly so it does not crash mysteriously.
- **Numbers that touch operators.** `3+4` (no spaces) must work just as well as `3 + 4`. Because the lexer skips whitespace and reads digits greedily, ours already handles both — verify it does.
- **Unbalanced parentheses.** `(3 + 4` should produce a clear error ("expected `)`"), not an index crash. Our `eat(")")` does this, but check it.
- **Division by zero.** `4 / 0` will throw a Python error. Decide whether the DSL should report a friendly "division by zero" instead.
- **Leftover tokens.** `1 2 3` lexes fine but is not a valid expression. The `EOF` check catches it; without that check you would silently return `1`.
- **Multi-character operators.** If you ever add `==` or `<=`, the lexer's "one character at a time" loop must look ahead. A single-char lexer cannot see `==` — a common first stumbling block.
- **Confusing the two acronyms.** "GPL" in this topic means general-purpose language, *not* the software license. Context makes it clear, but it trips people up.
- **Treating a config file's grammar as "not a real DSL."** It is. A `.env` parser is a DSL implementation, just a flat one. Respecting that helps you write better parsers for them.

Master the calculator until you can write it from memory. Every larger DSL — config languages, rule engines, query languages — is the same three stages with a bigger grammar. The `middle.md` level adds variables, functions, better error messages, and the idea of *transpiling* a DSL into another language.

---

## Apply it

1. Choose one small, known input for **DSLs in Practice**.
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

- What problem does DSLs in Practice solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
