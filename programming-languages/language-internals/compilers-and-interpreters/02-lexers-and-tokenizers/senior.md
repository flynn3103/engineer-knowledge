# Lexers & Tokenizers — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Lexers & Tokenizers** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Significant Whitespace: INDENT/DEDENT

In Python, Haskell, and others, indentation is syntactically meaningful — it
delimits blocks. A pure character DFA can't express "this line is indented more than
the last," so the lexer carries **state**: a stack of indentation levels. The off-side
rule is implemented by emitting **synthetic tokens**:

- At the start of a logical line, compare its indentation to the top of the stack.
- More indented → push and emit an `INDENT` token.
- Less indented → pop and emit one `DEDENT` per level popped (and error on a
  mismatch).
- Equal → emit nothing.

The parser then sees a clean stream with explicit `INDENT`/`DEDENT` tokens, as if the
language used braces. The lexer also has to handle line continuations, blank lines,
comments, and brackets (inside `()`/`[]`/`{}`, newlines and indentation are ignored).
This is a stateful lexer — a DFA augmented with a stack — and it's the first sign that
lexing isn't purely regular in practice.

---

## String Interpolation: Lexer/Parser Entanglement

`"hello ${user.name}!"` cannot be a single regular token: the `${ ... }` contains an
arbitrary *expression* that must itself be lexed and parsed. So the lexer must, on
hitting `${`, **re-enter expression mode**, emit normal tokens for the embedded
expression, then return to string mode at the matching `}`. This couples the lexer to
the parser's nesting (the lexer needs a mode stack, and balanced-brace tracking that's
really a context-free concern). Languages implement it with lexer modes (a stack of
states: STRING ↔ EXPR), and it's a common source of subtle bugs (nested
interpolation, braces inside the embedded expression, escapes).

---

## The Lexer Hack and Other Context-Sensitivity

The most famous breach: in C, `A * B;` is a multiplication-expression statement if `A`
is a variable, but a pointer *declaration* if `A` is a `typedef` name. The parser's
grammar is ambiguous without knowing whether `A` names a type — but that's
*semantic* information in the symbol table. The classic fix is the **lexer hack**: the
lexer consults the symbol table (populated as declarations are parsed) and emits
`TYPE_NAME` vs `IDENTIFIER` accordingly. This means the lexer depends on semantic
analysis — a circular dependency that shatters the clean phase ordering, and a
perennial example of why C is hard to parse.

Other context-sensitive tokenization:

- **JavaScript `/`:** is it division or the start of a regex literal? `a / b` vs
  `/regex/`. The lexer can't decide locally; it needs the parser's grammatical context
  (was the previous token a value or an operator?). Engines use heuristics or
  parser-driven lexing.
- **C++ `>>`:** in `vector<vector<int>>`, pre-C++11 the `>>` lexed as the shift
  operator, forcing `> >` with a space; C++11 changed parsing to treat it as two
  closing angle brackets in template context — parser feedback to tokenization.
- **Contextual keywords:** `async`, `await`, `yield`, `record` are keywords only in
  some positions; the lexer emits identifiers and the parser decides.

---

## Code Examples

INDENT/DEDENT with an indentation stack (sketch):

```python
indents = [0]
def handle_line_start(col, emit):
    if col > indents[-1]:
        indents.append(col); emit('INDENT')
    while col < indents[-1]:
        indents.pop(); emit('DEDENT')
    if col != indents[-1]:
        raise LexError("inconsistent dedent")
```

String-interpolation mode stack (sketch):

```text
state STRING:  on '${'  -> push EXPR, emit STRING_PART
state EXPR:    lex normal tokens; on matching '}' -> pop back to STRING
state STRING:  on '"'   -> emit STRING_END
```

---

## Best Practices

- **Model statefulness explicitly** — an indentation stack and a lexer-mode stack,
  not ad-hoc flags.
- **Keep semantic feedback minimal and documented** — the lexer hack works but is a
  known wart; some languages redesign syntax to avoid it.
- **Track precise spans through synthetic tokens** so errors point at real source.
- **Test the seams hard** — nested interpolation, mixed tabs/spaces, dedent mismatches,
  `/`-ambiguity — these are where lexers break.

---

## Edge Cases & Pitfalls

- **Tabs vs spaces** in indentation (Python 3 forbids mixing for this reason).
- **Nested interpolation** (`"${ "${x}" }"`) and braces/strings inside the embedded
  expression.
- **The lexer hack's ordering dependency:** a `typedef` used before its declaration is
  parsed tokenizes wrong.
- **JS regex/division** misclassification breaking the whole parse downstream.
- **Dedent to a non-matching column** must be a clear error, not a silent
  mis-structuring.

---

## Apply it

1. State the system invariant that **Lexers & Tokenizers** must protect.
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

- Which invariant must remain true when Lexers & Tokenizers fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
