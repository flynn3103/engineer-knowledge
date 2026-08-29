# Parsers — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Parsers** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Two-Stage Pipeline: Lexer then Parser

Source code is just a string of characters. Trying to find structure character-by-character is painful. So compilers split the work:

```text
  "x = 3 + 4 * 2"
        │
        ▼   LEXER (characters → tokens)
  [ IDENT("x"), EQUALS, NUMBER(3), PLUS, NUMBER(4), STAR, NUMBER(2) ]
        │
        ▼   PARSER (tokens → tree)
        =
       / \
      x   +
         / \
        3   *
           / \
          4   2
```

The lexer handles "what are the words?" The parser handles "how do the words fit together?" Keeping them separate makes both simpler. The parser never deals with whitespace, comments, or how many digits a number has — that's all the lexer's job.

### 2. A Grammar Is a Set of Rules

A **grammar** describes the legal shapes of a language. The standard notation is a list of **productions**, each saying "this nonterminal can be replaced by this sequence of symbols." Here is a tiny grammar for arithmetic:

```text
Expression → Expression + Term
Expression → Expression - Term
Expression → Term
Term       → Term * Factor
Term       → Term / Factor
Term       → Factor
Factor     → ( Expression )
Factor     → NUMBER
```

- **Nonterminals** (`Expression`, `Term`, `Factor`) are the named rules — the parts you can expand.
- **Terminals** (`+`, `-`, `*`, `/`, `(`, `)`, `NUMBER`) are the actual tokens — you can't expand them further.
- The **start symbol** is the top rule, here `Expression`. A whole program is one big `Expression`.

This kind of grammar — where each rule's left side is a *single* nonterminal — is called a **context-free grammar (CFG)**. "Context-free" means a rule like `Term → Term * Factor` applies no matter what surrounds it. CFGs are the workhorse of programming-language syntax.

Notice how the grammar *encodes precedence*: `Term` (which handles `*` and `/`) sits *below* `Expression` (which handles `+` and `-`), so multiplication naturally groups tighter. We'll see why this works in the examples.

### 3. Derivations: Growing the Tree

A **derivation** is a sequence of rule applications that turns the start symbol into your actual tokens. To check that `3 + 4 * 2` is valid, you find a derivation:

```text
Expression
→ Expression + Term            (apply Expression → Expression + Term)
→ Term + Term                  (Expression → Term)
→ Factor + Term                (Term → Factor)
→ 3 + Term                     (Factor → NUMBER)
→ 3 + Term * Factor            (Term → Term * Factor)
→ 3 + Factor * Factor          (Term → Factor)
→ 3 + 4 * Factor               (Factor → NUMBER)
→ 3 + 4 * 2                    (Factor → NUMBER)
```

If a derivation exists, the input is valid. If none exists, it's a syntax error. The **parse tree** is just this derivation drawn as a tree.

### 4. Parse Tree vs Abstract Syntax Tree (AST)

A **parse tree** (concrete syntax tree) records *every* rule and *every* token, including parentheses and the chain of single-child rules like `Expression → Term → Factor → NUMBER`. It's faithful but verbose.

An **AST** throws away the noise and keeps only meaning. For `(3 + 4)`:

```text
PARSE TREE (concrete)           AST (abstract)
   Factor                            +
  / |   \                           / \
 (  Expr  )                        3   4
     |
   Expr + Term
    |       |
  Term    Factor
    |       |
  Factor    4
    |
    3
```

The AST has no `(` or `)` node — the parentheses did their job (grouping) during parsing and aren't needed afterward. The AST has no redundant `Expr → Term → Factor` chain either. **Every later stage of the compiler works on the AST, not the parse tree.** As a junior, the practical takeaway: your parser should *produce an AST*, using the grammar only as a guide for the parsing logic.

### 5. Two Families: Top-Down and Bottom-Up

There are two big strategies for parsing.

- **Top-down** starts at the root (the start symbol) and works downward, asking "given the next token, which rule should I expand?" The most popular hand-written form is **recursive descent**: you write one function per nonterminal. This is what we'll do in the code examples. It's intuitive — the call stack *is* the tree.
- **Bottom-up** starts at the tokens (leaves) and combines them into bigger pieces until it reaches the root. The classic form is **shift-reduce / LR parsing**, usually produced by a tool like yacc or bison. It handles a larger class of grammars but is harder to write by hand.

At the junior level, focus on top-down recursive descent — it's how most real compilers (GCC, Clang, the Go compiler, V8) actually parse, and it's something you can write yourself today. `middle.md` explains the bottom-up family in detail.

### 6. Precedence and Associativity

Two rules govern how operators group:

- **Precedence**: `*` and `/` bind tighter than `+` and `-`. So `2 + 3 * 4` means `2 + (3 * 4) = 14`, not `(2 + 3) * 4 = 20`.
- **Associativity**: when operators have the *same* precedence, which side wins? Subtraction is **left-associative**: `10 - 3 - 2` is `(10 - 3) - 2 = 5`, not `10 - (3 - 2) = 9`. Exponentiation (in many languages) is **right-associative**: `2 ^ 3 ^ 2` is `2 ^ (3 ^ 2)`.

A parser must get these right, or `1 + 2 * 3` computes the wrong answer. The grammar above bakes precedence in by *layering* the rules (`Expression` over `Term` over `Factor`). In recursive descent, this becomes a chain of functions: `parseExpression` calls `parseTerm` calls `parseFactor`.

---

## Code Examples

We'll build a small **recursive-descent calculator**: parse and evaluate arithmetic like `3 + 4 * 2 - (1 + 1)`, respecting precedence and left-associativity. We assume the lexer already gave us a token list. We'll show the same parser in Python, JavaScript, and Go.

### The Grammar We Implement

```text
expression → term (('+' | '-') term)*
term       → factor (('*' | '/') factor)*
factor     → NUMBER | '(' expression ')'
```

This is the same arithmetic grammar, rewritten to avoid **left recursion** (a rule referring to itself as its first symbol, like `Expression → Expression + Term`). Left recursion makes naive recursive descent loop forever, so we replace it with a **loop** — `term (('+' | '-') term)*`. (The deep "why" is in `middle.md`; for now, just know: recursive descent uses loops, not self-first recursion.)

### Python

```python
# Tokens are simple tuples: ("NUMBER", 3), ("PLUS", "+"), ("LPAREN", "("), ...
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ("EOF", None)

    def advance(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def expect(self, kind):
        tok = self.peek()
        if tok[0] != kind:
            raise SyntaxError(f"expected {kind}, got {tok[0]} at position {self.pos}")
        return self.advance()

    # expression → term (('+' | '-') term)*
    def expression(self):
        node = self.term()
        while self.peek()[0] in ("PLUS", "MINUS"):
            op = self.advance()[0]
            right = self.term()
            node = ("binop", op, node, right)   # build an AST node
        return node

    # term → factor (('*' | '/') factor)*
    def term(self):
        node = self.factor()
        while self.peek()[0] in ("STAR", "SLASH"):
            op = self.advance()[0]
            right = self.factor()
            node = ("binop", op, node, right)
        return node

    # factor → NUMBER | '(' expression ')'
    def factor(self):
        tok = self.peek()
        if tok[0] == "NUMBER":
            self.advance()
            return ("num", tok[1])
        if tok[0] == "LPAREN":
            self.advance()
            node = self.expression()
            self.expect("RPAREN")
            return node
        raise SyntaxError(f"unexpected token {tok[0]}")

def evaluate(node):
    if node[0] == "num":
        return node[1]
    _, op, left, right = node
    l, r = evaluate(left), evaluate(right)
    return {"PLUS": l + r, "MINUS": l - r, "STAR": l * r, "SLASH": l / r}[op]

# 3 + 4 * 2 - (1 + 1)  ==  3 + 8 - 2  ==  9
tokens = [("NUMBER", 3), ("PLUS", "+"), ("NUMBER", 4), ("STAR", "*"),
          ("NUMBER", 2), ("MINUS", "-"), ("LPAREN", "("), ("NUMBER", 1),
          ("PLUS", "+"), ("NUMBER", 1), ("RPAREN", ")")]
ast = Parser(tokens).expression()
print(evaluate(ast))   # 9
```

Read the three functions next to the three grammar rules — they match line for line. `expression` handles `+`/`-`, `term` handles `*`/`/`, and because `term` is *called inside* `expression`, multiplication binds tighter automatically. The `while` loop gives **left-associativity**: each new operator wraps the running result on the left.

### JavaScript

```javascript
function makeParser(tokens) {
  let pos = 0;
  const peek = () => tokens[pos] ?? { kind: "EOF" };
  const advance = () => tokens[pos++];
  const expect = (kind) => {
    if (peek().kind !== kind) throw new SyntaxError(`expected ${kind}, got ${peek().kind}`);
    return advance();
  };

  function expression() {              // term (('+'|'-') term)*
    let node = term();
    while (peek().kind === "PLUS" || peek().kind === "MINUS") {
      const op = advance().kind;
      node = { type: "binop", op, left: node, right: term() };
    }
    return node;
  }
  function term() {                    // factor (('*'|'/') factor)*
    let node = factor();
    while (peek().kind === "STAR" || peek().kind === "SLASH") {
      const op = advance().kind;
      node = { type: "binop", op, left: node, right: factor() };
    }
    return node;
  }
  function factor() {                  // NUMBER | '(' expression ')'
    const t = peek();
    if (t.kind === "NUMBER") { advance(); return { type: "num", value: t.value }; }
    if (t.kind === "LPAREN") { advance(); const n = expression(); expect("RPAREN"); return n; }
    throw new SyntaxError(`unexpected ${t.kind}`);
  }
  return { parse: expression };
}

function evaluate(node) {
  if (node.type === "num") return node.value;
  const l = evaluate(node.left), r = evaluate(node.right);
  return { PLUS: l + r, MINUS: l - r, STAR: l * r, SLASH: l / r }[node.op];
}
```

Same structure, different syntax. The shape of a recursive-descent parser is the same in every language: peek, decide, advance, recurse, loop, build a node.

### Go

```go
package main

import "fmt"

type Token struct {
	Kind  string
	Value float64
}

type Node struct {
	Kind        string // "num" or "binop"
	Op          string
	Value       float64
	Left, Right *Node
}

type Parser struct {
	tokens []Token
	pos    int
}

func (p *Parser) peek() Token {
	if p.pos < len(p.tokens) {
		return p.tokens[p.pos]
	}
	return Token{Kind: "EOF"}
}
func (p *Parser) advance() Token { t := p.peek(); p.pos++; return t }

func (p *Parser) expression() *Node { // term (('+'|'-') term)*
	node := p.term()
	for p.peek().Kind == "PLUS" || p.peek().Kind == "MINUS" {
		op := p.advance().Kind
		node = &Node{Kind: "binop", Op: op, Left: node, Right: p.term()}
	}
	return node
}
func (p *Parser) term() *Node { // factor (('*'|'/') factor)*
	node := p.factor()
	for p.peek().Kind == "STAR" || p.peek().Kind == "SLASH" {
		op := p.advance().Kind
		node = &Node{Kind: "binop", Op: op, Left: node, Right: p.factor()}
	}
	return node
}
func (p *Parser) factor() *Node { // NUMBER | '(' expression ')'
	t := p.peek()
	if t.Kind == "NUMBER" {
		p.advance()
		return &Node{Kind: "num", Value: t.Value}
	}
	if t.Kind == "LPAREN" {
		p.advance()
		n := p.expression()
		if p.peek().Kind != "RPAREN" {
			panic("expected )")
		}
		p.advance()
		return n
	}
	panic("unexpected token " + t.Kind)
}

func eval(n *Node) float64 {
	if n.Kind == "num" {
		return n.Value
	}
	l, r := eval(n.Left), eval(n.Right)
	switch n.Op {
	case "PLUS":
		return l + r
	case "MINUS":
		return l - r
	case "STAR":
		return l * r
	default:
		return l / r
	}
}

func main() {
	toks := []Token{{"NUMBER", 3}, {"PLUS", 0}, {"NUMBER", 4}, {"STAR", 0},
		{"NUMBER", 2}, {"MINUS", 0}, {"LPAREN", 0}, {"NUMBER", 1},
		{"PLUS", 0}, {"NUMBER", 1}, {"RPAREN", 0}}
	ast := (&Parser{tokens: toks}).expression()
	fmt.Println(eval(ast)) // 9
}
```

Three languages, one idea. This *is* how production compilers parse — they hand-write functions like these (with far more cases). You now know the core technique.

---

## Coding Patterns

### Pattern 1: One Function Per Nonterminal

The defining pattern of recursive descent. Each grammar rule becomes a function. `parseExpression`, `parseTerm`, `parseFactor`, `parseStatement`, `parseIf`. The function names read like the grammar.

### Pattern 2: peek / advance / expect

Three tiny helpers underpin every hand-written parser:

```python
def peek(self):    return self.tokens[self.pos]          # look, don't consume
def advance(self): self.pos += 1; return self.tokens[self.pos-1]  # consume one
def expect(self, kind):                                  # consume or error
    if self.peek().kind != kind: raise SyntaxError(...)
    return self.advance()
```

`peek` lets you decide what to do; `advance` consumes a token; `expect` consumes a *required* token and errors if it's missing (used for closing `)`, `}`, `;`).

### Pattern 3: Loop for Repetition, Recursion for Nesting

A grammar like `term (('+' | '-') term)*` has a `*` (zero or more). Implement `*` with a **`while` loop**, not recursion. Use **recursion** only for genuine nesting, like a parenthesized `expression` inside a `factor`. This is the trick that avoids left-recursion infinite loops.

### Pattern 4: Build the AST as You Return

Don't build a parse tree and then convert it. Each parse function directly constructs and returns the **AST node** it represents. `factor` returns a `num` node; `expression` returns a `binop` node. The tree assembles itself from the bottom up as functions return.

### Pattern 5: Layer Functions for Precedence

Lowest-precedence operator at the top, highest at the bottom: `expression` (`+ -`) → `term` (`* /`) → `factor` (numbers, parens). Because the lower-precedence function *calls* the higher-precedence one, tighter-binding operators end up deeper in the tree. To add a new precedence level, insert a new function in the chain.

---

## Best Practices

- **Write the grammar first.** Before any code, write the grammar on paper. The parser is a transcription of it. Skipping this step is the #1 cause of tangled parser code.
- **One token of lookahead is usually enough.** Design your grammar so the next single token tells you which rule applies. This keeps the parser simple and fast.
- **Always produce an AST, not a parse tree.** Drop parentheses and redundant nodes immediately. Downstream code wants meaning, not punctuation.
- **Make `expect` produce a good error.** "Expected `)` to close the group opened at line 3, but found `;`" beats "syntax error." Your future self will thank you.
- **Keep the lexer and parser separate.** The parser should never look at raw characters or whitespace. If you find yourself checking `if char == ' '` in the parser, that logic belongs in the lexer.
- **Test with both valid and invalid input.** A parser that accepts valid programs but crashes ugly on bad input is half-done. Feed it garbage on purpose.
- **Rewrite left recursion into loops.** Any rule of the form `A → A op B` must become `A → B (op B)*` (a loop) for recursive descent to work.

---

## Edge Cases & Pitfalls

- **Left recursion = infinite loop.** If `expression()` calls `expression()` as its *very first* action, it recurses forever without consuming a token. Always rewrite `A → A op B` as a loop. This is the single most common beginner crash.
- **Forgetting to consume a token.** If a parse function reaches a token but never calls `advance()`, the parser gets stuck reading the same token forever. Every path must make progress.
- **Wrong precedence from a flat grammar.** If you put `+` and `*` at the *same* level, you get `2 + 3 * 4 = 20`. Layering the functions is what fixes it.
- **Wrong associativity from recursion.** Implementing `term (op term)*` with right-recursion instead of a loop makes `10 - 3 - 2` evaluate as `10 - (3 - 2) = 9` instead of `5`. Use the loop for left-associative operators.
- **Not checking for leftover tokens.** After parsing, if tokens remain (e.g. `3 + 4 )` has a stray `)`), that's an error. A clean parser checks that it consumed everything up to EOF.
- **Off-by-one in `peek`/`advance`.** Calling `advance` when you meant `peek` skips a token; the bug shows up as a confusing later error. Be disciplined about which one you call.
- **The dangling-else ambiguity (preview).** In `if a then if b then x else y`, which `if` does the `else` belong to? Languages resolve this by a rule (the `else` binds to the *nearest* `if`). You'll meet this properly in `middle.md`; just know it exists.
- **Empty input.** A grammar that requires at least one token will crash on `""`. Decide what an empty program means and handle it explicitly.

---

## Apply it

1. Choose one small, known input for **Parsers**.
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

- What problem does Parsers solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
