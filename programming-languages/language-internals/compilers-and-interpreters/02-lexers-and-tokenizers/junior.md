# Lexers & Tokenizers — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Lexers & Tokenizers** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A Token Is Three Things

When the lexer recognizes `42`, it doesn't just remember "there was a number." It produces a small record with (at least) three parts:

```text
Token {
    type:   NUMBER          // what kind of thing
    lexeme: "42"            // the exact text it matched
    span:   line 3, col 9   // where it came from
}
```

- The **type** tells the parser what grammatical role this token can play.
- The **lexeme** is the raw text — useful for identifiers (`x` vs `total`) and for reconstructing the source.
- The **span** (position) is what lets a compiler say *"error on line 3, column 9"* instead of a useless *"syntax error somewhere."*

A common mistake juniors make is to throw away the lexeme or the position because "the parser only needs the type." You almost always need all three. Error messages, IDE tooltips, and refactoring tools all depend on positions.

### 2. The Lexer's Loop

Every hand-written lexer has the same shape:

```text
loop:
    skip whitespace and comments
    if at end of input: emit EOF and stop
    look at the current character:
        a letter?           -> read an identifier or keyword
        a digit?            -> read a number
        a quote?            -> read a string
        an operator char?   -> read an operator (maybe multi-char)
        punctuation?        -> emit that single token
        anything else?      -> error: unexpected character
    emit the token, advance the cursor past it
```

That's it. A lexer is fundamentally a `while` loop with a `switch` on the first character of each token. The cleverness is all in "read an identifier" and "read a number" — small helper functions that keep consuming characters as long as they fit the pattern.

### 3. Skipping Whitespace and Comments

Most languages treat whitespace as a *separator* — it tells the lexer where one token ends and the next begins, but it isn't itself a token. So the lexer eats it silently:

```text
while current char is space, tab, newline, or carriage return:
    advance
```

Comments are skipped the same way, but they're trickier because you have to recognize where they start and end. A `// line comment` runs to the end of the line; a `/* block comment */` runs until the closing `*/`. The lexer consumes all of it and emits nothing.

### 4. Recognizing Identifiers and Keywords

An identifier matches a simple rule: it starts with a letter (or `_`), then continues with letters, digits, or underscores. So the lexer reads:

```text
read one letter/underscore
while next char is letter, digit, or underscore:
    advance
the lexeme is everything you just read
```

Now the crucial trick: **keywords look exactly like identifiers.** `if` matches the identifier pattern perfectly. So how does the lexer know `if` is a keyword but `iffy` is a name? The standard answer: **lex it as an identifier first, then look the lexeme up in a keyword table.** If `"if"` is in the table, emit a `KEYWORD_IF` token; otherwise emit an `IDENTIFIER` token. This "lex-then-look-up" pattern is used by virtually every real compiler — it's simpler and faster than trying to special-case every keyword in the scanning logic.

### 5. Recognizing Numbers

For a junior calculator, a number is *one or more digits, optionally with a decimal point and more digits*:

```text
read one digit
while next char is a digit:
    advance
if next char is '.' and the one after is a digit:
    advance past the '.'
    while next char is a digit:
        advance
```

The lexeme might be `"42"` or `"3.14"`. The lexer usually also computes the numeric *value* (the actual `42` or `3.14`) and stores it in the token. Real languages have far more numeric forms (hex `0xFF`, binary `0b101`, underscores `1_000`, exponents `1e10`) — those are covered at higher levels — but the digit-loop idea is the same.

### 6. Maximal Munch — Always Take the Longest Token

Here is the single most important *rule* in lexing. When the lexer is looking at `<=`, it has a choice: it could emit a `<` token and leave `=` for next time, or it could emit a single `<=` token. The rule, called **maximal munch** or **longest match**, says: **always grab the longest valid token.** So `<=` is one token.

Why does this matter? Because operators overlap. `<`, `<=`, `<<`, `<<=` all start with `<`. The lexer can't decide which one it's seeing until it looks ahead. Maximal munch makes the rule unambiguous: keep extending the token as long as the result is still a valid token. This is why you peek at the next character before committing.

### 7. Why Skip to a Token Stream at All?

Why not just let the parser read characters directly? Two reasons:

1. **Separation of concerns.** The parser works with grammar rules like *"an expression is a term plus a term."* It's far cleaner if "term" means a single `NUMBER` token than if it means "read a digit, then maybe more digits, then maybe a dot…". Lexing hides all that character-level detail.
2. **It's faster.** The lexer does one cheap left-to-right pass and hands the parser a compact stream. The parser never has to re-examine whitespace or comments again.

The token stream is the clean interface between the messy world of characters and the structured world of grammar.

---

## Code Examples

We'll build the same thing in every language: **a lexer for a tiny calculator language** that handles numbers, identifiers, the keywords `let` and `print`, the operators `+ - * /`, parentheses, and the assignment `=`. It skips whitespace and `#` line comments. Input like `let x = 3 + 4 * (2 - 1)` becomes a token stream.

### Python — A Complete Hand-Written Lexer

```python
from dataclasses import dataclass

@dataclass
class Token:
    type: str       # "NUMBER", "IDENT", "PLUS", "EOF", ...
    lexeme: str     # the exact characters
    line: int       # 1-based line number
    col: int        # 1-based column number

KEYWORDS = {"let", "print"}

class Lexer:
    def __init__(self, src: str):
        self.src = src
        self.pos = 0          # index of next char to read
        self.line = 1
        self.col = 1

    def _peek(self) -> str:
        return self.src[self.pos] if self.pos < len(self.src) else "\0"

    def _advance(self) -> str:
        c = self.src[self.pos]
        self.pos += 1
        if c == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return c

    def tokens(self) -> list[Token]:
        out = []
        while True:
            self._skip_trivia()
            start_line, start_col = self.line, self.col
            c = self._peek()
            if c == "\0":
                out.append(Token("EOF", "", start_line, start_col))
                return out
            if c.isalpha() or c == "_":
                out.append(self._read_ident(start_line, start_col))
            elif c.isdigit():
                out.append(self._read_number(start_line, start_col))
            elif c in "+-*/()=":
                self._advance()
                kind = {"+": "PLUS", "-": "MINUS", "*": "STAR",
                        "/": "SLASH", "(": "LPAREN", ")": "RPAREN",
                        "=": "ASSIGN"}[c]
                out.append(Token(kind, c, start_line, start_col))
            else:
                raise SyntaxError(f"unexpected char {c!r} at line {self.line} col {self.col}")

    def _skip_trivia(self):
        while True:
            c = self._peek()
            if c in " \t\r\n":
                self._advance()
            elif c == "#":                      # line comment
                while self._peek() not in ("\n", "\0"):
                    self._advance()
            else:
                return

    def _read_ident(self, line, col) -> Token:
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        lexeme = self.src[start:self.pos]
        kind = "KEYWORD" if lexeme in KEYWORDS else "IDENT"
        return Token(kind, lexeme, line, col)

    def _read_number(self, line, col) -> Token:
        start = self.pos
        while self._peek().isdigit():
            self._advance()
        if self._peek() == "." and self.pos + 1 < len(self.src) and self.src[self.pos + 1].isdigit():
            self._advance()                     # consume '.'
            while self._peek().isdigit():
                self._advance()
        return Token("NUMBER", self.src[start:self.pos], line, col)

if __name__ == "__main__":
    src = "let x = 3 + 4 * (2 - 1)  # a comment\nprint x"
    for t in Lexer(src).tokens():
        print(t)
```

Run it and you get a token per line, ending with `Token(type='EOF', ...)`. Notice the structure: a main loop, a "skip trivia" helper, and one helper per multi-character token kind. This is the shape of essentially every hand-written lexer.

### Go — The Same Lexer

```go
package main

import (
	"fmt"
	"unicode"
)

type Token struct {
	Type   string
	Lexeme string
	Line   int
	Col    int
}

var keywords = map[string]bool{"let": true, "print": true}

type Lexer struct {
	src  []rune
	pos  int
	line int
	col  int
}

func NewLexer(s string) *Lexer { return &Lexer{src: []rune(s), line: 1, col: 1} }

func (l *Lexer) peek() rune {
	if l.pos < len(l.src) {
		return l.src[l.pos]
	}
	return 0
}

func (l *Lexer) advance() rune {
	c := l.src[l.pos]
	l.pos++
	if c == '\n' {
		l.line++
		l.col = 1
	} else {
		l.col++
	}
	return c
}

func (l *Lexer) skipTrivia() {
	for {
		c := l.peek()
		switch {
		case c == ' ' || c == '\t' || c == '\r' || c == '\n':
			l.advance()
		case c == '#':
			for l.peek() != '\n' && l.peek() != 0 {
				l.advance()
			}
		default:
			return
		}
	}
}

func (l *Lexer) Tokens() []Token {
	var out []Token
	for {
		l.skipTrivia()
		line, col := l.line, l.col
		c := l.peek()
		switch {
		case c == 0:
			out = append(out, Token{"EOF", "", line, col})
			return out
		case unicode.IsLetter(c) || c == '_':
			out = append(out, l.readIdent(line, col))
		case unicode.IsDigit(c):
			out = append(out, l.readNumber(line, col))
		default:
			kinds := map[rune]string{'+': "PLUS", '-': "MINUS", '*': "STAR",
				'/': "SLASH", '(': "LPAREN", ')': "RPAREN", '=': "ASSIGN"}
			if k, ok := kinds[c]; ok {
				l.advance()
				out = append(out, Token{k, string(c), line, col})
			} else {
				panic(fmt.Sprintf("unexpected char %q at line %d col %d", c, l.line, l.col))
			}
		}
	}
}

func (l *Lexer) readIdent(line, col int) Token {
	start := l.pos
	for unicode.IsLetter(l.peek()) || unicode.IsDigit(l.peek()) || l.peek() == '_' {
		l.advance()
	}
	lexeme := string(l.src[start:l.pos])
	kind := "IDENT"
	if keywords[lexeme] {
		kind = "KEYWORD"
	}
	return Token{kind, lexeme, line, col}
}

func (l *Lexer) readNumber(line, col int) Token {
	start := l.pos
	for unicode.IsDigit(l.peek()) {
		l.advance()
	}
	if l.peek() == '.' && l.pos+1 < len(l.src) && unicode.IsDigit(l.src[l.pos+1]) {
		l.advance()
		for unicode.IsDigit(l.peek()) {
			l.advance()
		}
	}
	return Token{"NUMBER", string(l.src[start:l.pos]), line, col}
}

func main() {
	l := NewLexer("let x = 3 + 4 * (2 - 1)\nprint x")
	for _, t := range l.Tokens() {
		fmt.Printf("%-8s %q (%d:%d)\n", t.Type, t.Lexeme, t.Line, t.Col)
	}
}
```

Same structure as Python, just with Go's `[]rune` so multi-byte characters count as one. Notice both versions follow the identical loop-and-helpers pattern.

### Maximal Munch in Action

To handle two-character operators like `==`, `<=`, `!=`, the operator branch needs one character of lookahead. Here's the idea (Python):

```python
def _read_operator(self, line, col):
    c = self._advance()
    if c == "=" and self._peek() == "=":     # "==" beats "="
        self._advance()
        return Token("EQ", "==", line, col)
    if c == "<" and self._peek() == "=":     # "<=" beats "<"
        self._advance()
        return Token("LE", "<=", line, col)
    single = {"=": "ASSIGN", "<": "LT", ">": "GT", "+": "PLUS"}[c]
    return Token(single, c, line, col)
```

The rule: **check for the longer operator first.** If `=` is followed by `=`, take the two-character `==`. Otherwise fall back to the single-character `=`. That "try long, fall back to short" pattern *is* maximal munch implemented by hand.

### JavaScript — A Minimal Tokenizer (regex flavor)

```javascript
function tokenize(src) {
  const spec = [
    ["WS",      /^[ \t\r\n]+/],
    ["COMMENT", /^#[^\n]*/],
    ["NUMBER",  /^\d+(\.\d+)?/],
    ["IDENT",   /^[A-Za-z_]\w*/],
    ["OP",      /^[+\-*/()=]/],
  ];
  const keywords = new Set(["let", "print"]);
  const tokens = [];
  let i = 0;
  while (i < src.length) {
    let matched = false;
    for (const [type, re] of spec) {
      const m = re.exec(src.slice(i));
      if (m) {
        const text = m[0];
        i += text.length;
        matched = true;
        if (type === "WS" || type === "COMMENT") break;   // skip trivia
        let kind = type;
        if (type === "IDENT" && keywords.has(text)) kind = "KEYWORD";
        tokens.push({ type: kind, lexeme: text });
        break;
      }
    }
    if (!matched) throw new Error(`unexpected char ${src[i]!} at index ${i}`);
  }
  tokens.push({ type: "EOF", lexeme: "" });
  return tokens;
}

console.log(tokenize("let x = 3 + 4 # hi"));
```

This is the "list of regular expressions, try each in order" approach. It's quick to write, but notice the subtle requirement: the rules are tried *in order*, and ordering matters — if you put `IDENT` before `KEYWORD` handling you'd never see keywords, and a regex engine evaluating each at every position can be slower than a hand-written character switch on big files. Higher levels explain why production compilers rarely lex with regexes at runtime.

---

## Coding Patterns

### Pattern 1: The peek/advance pair

Every lexer has two primitives: `peek()` returns the current character *without* consuming it, and `advance()` returns it *and* moves the cursor forward. Lookahead is just `peek`. All token-reading logic is built from these two.

```python
def peek(self):    return self.src[self.pos] if self.pos < len(self.src) else "\0"
def advance(self): c = self.src[self.pos]; self.pos += 1; return c
```

### Pattern 2: "Consume while" helpers

To read a run of characters that all match a rule, loop on `peek`:

```python
def consume_while(self, predicate):
    start = self.pos
    while predicate(self.peek()):
        self.advance()
    return self.src[start:self.pos]
```

Then `read_number` is `consume_while(str.isdigit)` and `read_ident` is `consume_while(is_ident_char)`. This collapses repetitive loops into one reusable helper.

### Pattern 3: Lex-then-look-up for keywords

Don't try to detect keywords while scanning. Read the whole identifier, then check a set:

```python
lexeme = self.read_ident()
kind = "KEYWORD" if lexeme in KEYWORDS else "IDENT"
```

### Pattern 4: A sentinel EOF token

Append a single `EOF` token at the end instead of returning a flag or `None`. The parser can then treat "end of input" like any other token (`if token.type == "EOF"`), which removes special-case branching everywhere.

### Pattern 5: Capture the start position before reading

Record `(line, col)` *before* you start consuming a token, so the position points at the token's first character, not its last:

```python
start_line, start_col = self.line, self.col
tok = self.read_number()      # reads several chars
# attach (start_line, start_col) to tok
```

---

## Clean Code

- **One helper per token kind.** `read_ident`, `read_number`, `read_string`. Each does one thing and is easy to test.
- **Never index `src[pos]` directly in the main loop.** Go through `peek`/`advance` so bounds-checking and position-tracking live in one place.
- **Keep the token type names as constants or an enum**, not raw strings scattered around. A typo in `"NUMBR"` is a silent bug.
- **Attach positions at creation, not later.** A token born without a position rarely gets one retrofitted correctly.
- **Make the lexer produce a clear error, not a crash,** on an unexpected character: include the character and its position.
- **Don't interpret values you don't have to yet.** Storing the lexeme `"42"` is fine; converting to the integer `42` can happen here or later, but be consistent.

---

## Best Practices

- **Always emit an EOF token.** It simplifies the parser and prevents "ran off the end of the array" bugs.
- **Track line and column from the start.** Retrofitting positions into a lexer that ignored them is painful. Bump the line counter on every `\n`.
- **Decide your whitespace policy explicitly.** Most languages skip it; a few (Python, YAML, Haskell) make it significant. Know which you are before you write code.
- **Implement maximal munch by checking longer operators first.** `==` before `=`, `<=` before `<`. It's a tiny bit of lookahead that prevents real bugs.
- **Keep comments and whitespace as "trivia" if you're building a formatter or IDE tool**, even though a compiler throws them away. You can't pretty-print code whose comments you deleted.
- **Test the lexer in isolation** before wiring it to a parser. Feed it tricky inputs and assert on the exact token list. Lexer bugs are much easier to find here than after the parser mangles them.
- **Reject, don't guess, on bad input.** If you see a character you don't recognize, produce a precise error. Silent skipping hides typos.

---

## Edge Cases & Pitfalls

- **Numbers ending in a dot.** Is `1.` a float, or the integer `1` followed by a `.`? Is `.5` a float? Languages differ. Your digit-loop needs an explicit rule. (The calculator above requires a digit after the dot, so `1.` lexes as `1` then `.`.)
- **Forgetting maximal munch.** If you emit `<` and `=` as two tokens, `<=` breaks. Always try the longer operator first.
- **Off-by-one in positions.** Recording the position *after* consuming a token points at the wrong spot. Capture it before.
- **Comments that contain token-like text.** `# let x = 5` must be skipped entirely; the lexer must not lex `let` inside a comment. This is why comment-skipping happens *before* the token switch.
- **Unterminated strings/comments.** `/* never closed` should be a clear error, not an infinite loop or an off-the-end crash. Always check for EOF inside your "read until closer" loops.
- **Identifiers that start with a digit.** `3x` is not a valid identifier; the lexer should read `3` as a number and then hit `x`. Make sure your "start of identifier" check excludes digits.
- **The empty input.** A lexer on `""` should produce exactly one token: `EOF`. Test this.
- **Whitespace inside what you thought was one token.** `3 . 14` is *not* the number `3.14` — the spaces separate it into three tokens. The lexer only joins adjacent characters.

---

## Common Mistakes

1. **Lexing directly off `src[i]` everywhere** instead of through `peek`/`advance`, leading to scattered bounds bugs and broken position tracking.
2. **Detecting keywords during scanning** with a tangle of special cases, instead of lex-as-identifier-then-look-up.
3. **Throwing away source positions** because "the parser doesn't need them" — then being unable to produce a decent error message.
4. **Not handling EOF inside loops.** A `while peek() != '"'` loop with no EOF check spins forever on an unterminated string.
5. **Emitting single-character operators only,** so `==`, `<=`, `!=` get split into two tokens and the parser chokes.
6. **Forgetting to skip whitespace before *every* token,** so leading spaces produce a spurious "unexpected character" error.
7. **Mixing the lexeme and the value.** Storing only the parsed integer loses the original text you might need for errors; storing only the text means re-parsing later. Decide and document.
8. **Treating bytes as characters in a Unicode source.** A multi-byte character read one byte at a time corrupts identifiers and positions. Use the language's character/rune type.

---

## Tricky Points

- **Whitespace is usually a separator, not a token — but not always.** In Python, indentation is meaningful, and the lexer has to emit synthetic INDENT/DEDENT tokens. That's a `senior.md` topic, but it's why "lexers always skip whitespace" is an oversimplification.
- **Keywords aren't a separate character pattern.** They share the identifier pattern exactly; the *only* difference is a table lookup after scanning. This surprises people who expect the lexer to "know" `if` is special from its shape.
- **Maximal munch can produce a "wrong" but correct split.** In C, `a+++b` lexes as `a ++ + b` (not `a + ++ b`) because the lexer greedily grabs `++` first. The result compiles strangely but the lexer is behaving exactly as specified.
- **The lexer doesn't understand grammar.** It happily tokenizes `) ) ) + + +` — nonsense to a parser, but each token is individually valid. Catching that nonsense is the *parser's* job, not the lexer's. Keep the responsibilities separate.
- **A number's lexeme and value can disagree on edge cases.** `0xFF` has lexeme `"0xFF"` and value `255`. Don't assume the lexeme *is* the value.

---

## Apply it

1. Choose one small, known input for **Lexers & Tokenizers**.
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

- What problem does Lexers & Tokenizers solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
