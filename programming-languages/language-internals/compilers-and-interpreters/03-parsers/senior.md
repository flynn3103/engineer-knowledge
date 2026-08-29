# Parsers — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Parsers** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why production compilers hand-write recursive descent

This is the most consequential parsing decision in industry, and the answer is nearly unanimous: **GCC** switched its C++ parser *away* from a bison grammar to a hand-written recursive-descent parser (2004); **Clang**, **rustc**, the **Go** compiler, **V8** (and most JS engines), TypeScript, and the C# (Roslyn) compiler all hand-write. The reasons are not theoretical — they are operational:

- **Error messages.** A hand-written parser knows exactly where it is and what it expected, so it can say "expected `;` after expression on line 42, found `}`" and even suggest a fix. An LALR table, by contrast, fails in an automaton state that does not map cleanly to a human-meaningful "I was parsing a `for`-loop header." Generated error messages are notoriously generic ("syntax error"); making them good is a research problem in its own right. For a compiler whose UX *is* its diagnostics, this alone decides it.
- **Control over recovery.** When the input is wrong (always, during development), a hand-written parser can apply construct-specific recovery: "I'm in an argument list, the user wrote a stray comma, skip it and keep going." Table-driven recovery is coarse.
- **Lexer feedback.** C and C++ require the parser to inform the lexer (the typedef/template problems below). A hand-written parser, sharing a symbol table with the lexer, does this naturally. Wiring it into a generator's rigid token stream is awkward.
- **Context sensitivity.** Real languages have rules a pure CFG can't express (offside-rule indentation in Python, contextual keywords in C# like `async`/`await`/`yield` that are also valid identifiers). Hand-written code just handles these with an `if`. A generator fights them.
- **No build-time dependency, no generated-code debugging.** The parser is just code you step through in a debugger. No `.y` → `.c` generation step, no "where did this state come from" mysteries.
- **Performance and incrementality.** Hand-written parsers are easy to make incremental and to tune; the Go parser, for instance, is famously fast partly because it is plain, predictable code.

The cost is real too: a hand-written parser is *more code* and must be kept consistent with the language spec by hand, with no machine check that it matches a grammar. But for a flagship language, the diagnostics and control win decisively. The standard production shape is **recursive descent for statements + Pratt for expressions**, exactly the hybrid you learned at the middle level — now you know *why every major compiler converged on it*.

### 2. When a generator is still the right call

Hand-writing is not always correct. Reach for a generator when:

- **The grammar is large, formally specified, and stable** — SQL is the canonical example. SQL dialects are huge LALR grammars; PostgreSQL's parser is bison-generated, and that is the right choice for a 500-production grammar that changes slowly and has a standard to match.
- **You want the grammar to be the source of truth**, machine-checked. A `.y` or `.g4` file *is* an executable spec; a conflict report tells you objectively that your grammar is ambiguous, something a hand-written parser will silently paper over.
- **It's a quick internal DSL** where great error messages don't matter and you'd rather write 40 lines of grammar than 400 of parser.
- **You need a parser in many languages** — ANTLR generates Java, C#, Python, Go, JS, C++ from one grammar, valuable for tooling that must run everywhere.

The honest senior framing: *generators optimize for grammar-as-spec and speed-of-authoring; hand-written optimizes for diagnostics, recovery, and control.* Pick by which you're optimizing for. A compiler chooses control; a database engine chooses spec-fidelity.

### 3. Resolving LALR conflicts in practice

When you do use bison-class tools, conflicts are your daily reality. Three levers:

- **Precedence and associativity declarations.** `%left '+' '-'` / `%left '*' '/'` / `%right '^'` tell the generator how to resolve shift-reduce conflicts in the expression grammar without rewriting it. This is how you keep the *natural* ambiguous expression grammar (`E → E '+' E`) and still get a deterministic parser — the declarations encode precedence directly into the shift/reduce table. It is cleaner than the layered grammar and is the standard idiom.
- **The dangling-else default.** bison resolves shift-reduce by shifting, which correctly binds `else` to the nearest `if`. You can rely on it (and comment that you did) or assign precedence to `THEN`/`ELSE` to make the resolution explicit.
- **Grammar restructuring.** A reduce-reduce conflict almost always means a real ambiguity or an over-merged LALR state; the fix is to refactor the grammar (e.g. matched/unmatched statements for the dangling else), not to suppress the warning.

The senior discipline: **treat the conflict report as a test result.** Zero unexplained conflicts. Every remaining conflict is either resolved by an intentional precedence declaration or documented with the exact input that triggers it and why the default is correct.

### 4. PEG and packrat parsing

A **Parsing Expression Grammar** looks like a CFG but is a *recognition* formalism with one pivotal difference: **ordered choice**. Where a CFG's `A | B` is symmetric (both alternatives are "in the language"), a PEG's `A / B` means "try `A`; if and only if `A` fails, try `B`." The first alternative that succeeds wins, and the parser commits — no backtracking out of a successful choice.

This single rule has large consequences:

- **PEGs are unambiguous by construction.** There is exactly one parse, because choice is ordered. The dangling-else "ambiguity" simply disappears: whichever alternative you list first wins. You never get a shift-reduce conflict because there is no nondeterminism to conflict.
- **PEGs handle some non-CFG languages** (like `aⁿbⁿcⁿ`) via syntactic predicates (`&` and-predicate, `!` not-predicate) that peek without consuming.
- **Packrat parsing** memoizes the result of every rule at every input position, so each (rule, position) pair is computed once. This guarantees **linear time** despite the unlimited lookahead PEGs allow — trading memory (a table proportional to input length × rules) for that guarantee.

The **prefix-capture gotcha** that catches everyone: ordered choice with a shared prefix silently shadows the longer alternative.

```text
keyword <- "if" / "ifx"          # WRONG: "ifx" is unreachable
```

Parsing the input `ifx`, the PEG tries `"if"`, matches the first two characters, *succeeds*, and commits — leaving `x` unconsumed and never trying `"ifx"`. Because ordered choice never reconsiders a success, the second alternative is dead code. The fix is to order longest-first (`"ifx" / "if"`) or anchor with a not-predicate (`"if" !idchar`). CFG alternation does not have this trap (it would consider both); PEG's commit-on-success does. Internalize it: **in a PEG, always list the longer/more-specific alternative first.**

PEGs are excellent for configuration formats, protocol grammars, and DSLs where you want clean composition and no ambiguity to reason about. They are less ideal where you want error messages (a PEG failure is "no alternative matched here," which is hard to make specific) and where the grammar's ordered-choice semantics surprise contributors who think in CFGs.

### 5. GLR and GLL: parsing genuinely ambiguous grammars

Sometimes the grammar is *inherently* ambiguous and you must keep all parses. Natural-language grammars are the obvious case; **C++** is the practical one — its grammar is so context-dependent that some constructs cannot be disambiguated until semantic analysis (is `T * x;` a multiplication or a pointer declaration? It depends on whether `T` is a type). For these, generalized parsers exist:

- **GLR (Generalized LR, Tomita 1985).** A normal LR parser stuck at a conflict picks one action. GLR instead *forks*: it pursues **both** the shift and the reduce using a **Graph-Structured Stack (GSS)**, which shares common stack prefixes so the fork doesn't explode. Parses that turn out invalid die off; survivors are merged. The result is stored as a **Shared Packed Parse Forest (SPPF)** — a DAG that represents exponentially many trees in polynomial space. GLR runs in near-linear time on grammars that are *almost* deterministic (the common case) and degrades gracefully to cubic on highly ambiguous ones. It is what tools like Bison's `%glr-parser`, Elkhound (used by the Oink/C++ frontend), and Tree-sitter's conflict handling build on.
- **GLL (Generalized LL, Scott & Johnstone 2010).** The top-down analogue: it generalizes recursive descent to handle *any* CFG, including left-recursive and ambiguous ones, again producing an SPPF. It appeals to people who like recursive descent's structure but need it to handle arbitrary grammars; it underlies tools like the Iguana parser and some language workbenches (Rascal).

The senior takeaway: **GLR/GLL trade determinism for generality.** You reach for them only when the grammar is truly ambiguous and you genuinely need every parse (or need to defer disambiguation to a later phase). For a normal programming language you do *not* want a forest of trees — you want one — so you stay with deterministic parsing and resolve ambiguity in the grammar. GLR's real industrial niche is exactly the C++-style "can't disambiguate syntactically" problem and language-workbench/IDE tooling that must parse messy, ambiguous, or multi-language input.

### 6. Error recovery and diagnostics quality

A parser that stops at the first error is useless for development. Real parsers recover and keep going so they can report *many* errors per compile and so an IDE can build a tree from broken code. The standard techniques:

- **Panic-mode recovery.** On error, discard input tokens until a **synchronizing token** appears — typically a statement/declaration boundary like `;`, `}`, or a leading keyword (`def`, `class`, `fn`). Then resume parsing at that point. Simple, robust, and the workhorse of hand-written parsers. The art is choosing good sync sets per construct: inside a function body, sync to `;` or `}`; inside an argument list, sync to `,` or `)`.
- **Error productions.** Add grammar rules that match *common mistakes* explicitly, so the parser can give a precise, specific diagnostic and continue cleanly. Example: a rule that matches `=` where `==` was expected in a condition, emitting "did you mean `==`?" Clang's famous diagnostics are built on a large catalogue of these. They're expensive to write but turn cryptic failures into actionable advice.
- **Phrase-level / local recovery.** Insert or delete a single token to repair the parse (the classic "inserted missing `;`"). Risky — a bad guess cascades — but powerful when scoped tightly.

Diagnostics quality is a *first-class feature*, not a side effect. The difference between "syntax error near line 42" and rustc's "expected `;`, found `}` — `help: add `;` here" with a caret under the exact column is the difference between a beloved compiler and a hated one. This is, again, a major reason production compilers hand-write: recovery and diagnostics are where you spend enormous effort, and you want full control of it.

### 7. The lexer feedback / lexer-hack problems

Pure compilation pretends the lexer and parser are cleanly separated phases. Real C and C++ shatter that:

- **The C typedef problem.** In `T * x;`, whether this is a declaration of `x` as pointer-to-`T` or a multiplication expression `T * x` depends on whether `T` was declared as a typedef. The lexer can't know — it has no symbol table. The **lexer hack** has the parser maintain the symbol table and feed type-name information back to the lexer, so an identifier is lexed as `TYPE_NAME` or `IDENTIFIER` depending on context. This breaks the clean phase separation and is one of the strongest arguments for an integrated hand-written front end.
- **The C++ template `>>` problem.** In `vector<vector<int>>`, the `>>` lexes as a right-shift operator, not two closing angle brackets, so older compilers required `vector<vector<int> >` with a space. C++11 fixed this with a special parser rule that re-interprets `>>` as two `>` in template-argument context — again, parser context overriding the naive lexer.
- **The most vexing parse (C++).** `Widget w(Thing());` *looks* like constructing a `Widget` from a `Thing`, but the standard's "if it can be a declaration, it is" rule makes it a declaration of a *function* `w` returning `Widget` taking a function-pointer parameter. The ambiguity is real and lives in the grammar; the compiler must apply the disambiguation rule, and the programmer must use `{}` (`Widget w{Thing{}};`) to mean what they intended. It's the textbook case of a grammar whose surface ambiguity forces a language-level disambiguation rule.

These context-sensitivities are exactly what a CFG cannot express and what a hand-written, symbol-table-aware parser handles with a few `if`s. They are the reason "just write a clean grammar and generate the parser" fails for C-family languages.

### 8. Incremental and error-tolerant parsing for IDEs

An editor re-parses on *every keystroke*, and the file is **syntactically invalid almost the entire time you're typing**. A batch compiler's "parse, fail, exit" is wrong here on two axes: it's too slow (re-parsing a 10k-line file per keystroke) and too brittle (no tree for broken input). Two techniques solve this:

- **Error-tolerant parsing.** The parser *never* fails. When it can't match, it inserts an **error node** (or a "missing" node) into the tree and keeps going, so you always get a complete tree spanning the whole file — broken regions are just marked, not fatal. This is what powers red squiggles, code folding, and even completion *while* your code is incomplete.
- **Incremental parsing.** When the user edits a small range, re-parse only the affected subtree and **splice** the new subtree into the old one, reusing all the untouched nodes. This is O(edit size), not O(file size). **Tree-sitter** (used by GitHub, Neovim, and many editors) is the canonical incremental, error-tolerant GLR-based parser: it keeps a persistent CST, re-parses just the edited span, and produces a usable tree even mid-typo. **Roslyn** (the C#/.NET compiler platform) does the same with a hand-written incremental parser whose syntax trees are immutable and *full-fidelity* (every token, every space, every comment is preserved — round-tripping the exact source), which is what lets it power both the compiler and the IDE from one tree.

Two design implications fall out of this:

1. **You parse to a CST, not just an AST.** IDE tooling needs every token and all trivia (whitespace, comments) to format, refactor, and round-trip source. A batch compiler can throw trivia away; a language server cannot. Modern compilers increasingly keep a full-fidelity CST and derive the AST from it.
2. **Immutability + structural sharing.** Roslyn's trees are immutable so they can be shared across threads and across edits, with each edit producing a new tree that reuses most of the old one — the same persistent-data-structure trick that makes incremental re-parse cheap.

This is the frontier of practical parsing: the parser is no longer a one-shot phase but a *living service* that maintains a tree against a constantly-changing, frequently-broken document. It's why "which parsing technology" for new languages now weighs incrementality and error-tolerance as heavily as raw grammar power.

---

## Code Examples

### A hand-written recursive-descent statement parser with panic-mode recovery (Python)

This shows the production shape: recursive descent for statements, error nodes instead of aborting, and synchronization to a boundary token.

```python
class ParseError:
    def __init__(self, msg, tok): self.msg, self.tok = msg, tok

class Parser:
    def __init__(self, tokens):
        self.toks, self.pos = tokens, 0
        self.errors = []

    def peek(self):  return self.toks[self.pos]
    def at(self, k): return self.peek()[0] == k
    def advance(self): t = self.toks[self.pos]; self.pos += 1; return t

    def expect(self, kind, ctx):
        if self.at(kind):
            return self.advance()
        # Record the error but DO NOT abort — insert a "missing" marker.
        self.errors.append(ParseError(f"expected {kind} {ctx}, found {self.peek()[0]}", self.peek()))
        return ("MISSING", kind)            # error node, parse continues

    def synchronize(self):
        # Panic-mode: skip until a statement boundary so we can report more errors.
        SYNC = {"SEMI", "RBRACE", "DEF", "IF", "WHILE", "EOF"}
        while self.peek()[0] not in SYNC:
            self.advance()
        if self.at("SEMI"):
            self.advance()                  # consume the boundary

    def parse_block(self):
        self.expect("LBRACE", "to start block")
        stmts = []
        while not self.at("RBRACE") and not self.at("EOF"):
            mark = self.pos
            try:
                stmts.append(self.parse_stmt())
            except RuntimeError:            # unrecoverable local failure
                self.synchronize()
            if self.pos == mark:            # made no progress → force advance
                self.advance()
        self.expect("RBRACE", "to close block")
        return ("block", stmts)

    def parse_stmt(self):
        if self.at("IF"):    return self.parse_if()
        if self.at("WHILE"): return self.parse_while()
        expr = self.parse_expr()            # Pratt parser lives here
        self.expect("SEMI", "after expression statement")
        return ("exprstmt", expr)
    # parse_if / parse_while / parse_expr omitted for brevity
```

The two senior moves: `expect` returns a `MISSING` *node* and records an error rather than throwing, so the tree stays complete; and `synchronize` skips to a boundary so one typo doesn't suppress every later error. The `if self.pos == mark: self.advance()` guard is the unglamorous bug-preventer — without a forced-progress check, recovery loops can spin forever on a token they can neither parse nor skip.

### PEG ordered choice and the prefix-capture trap (parser-combinator style, Python)

```python
# Minimal PEG combinators to make ordered-choice semantics concrete.
def lit(s):
    def p(text, i):
        return (i + len(s)) if text.startswith(s, i) else None
    return p

def seq(*ps):
    def p(text, i):
        for sub in ps:
            i = sub(text, i)
            if i is None: return None
        return i
    return p

def choice(*ps):                # ORDERED choice: first success wins, commits.
    def p(text, i):
        for sub in ps:
            r = sub(text, i)
            if r is not None: return r   # commit — never tries later alternatives
        return None
    return p

# WRONG: "if" is a prefix of "ifx", and ordered choice commits on first success.
kw_bad  = choice(lit("if"), lit("ifx"))
# RIGHT: longest / most-specific alternative first.
kw_good = choice(lit("ifx"), lit("if"))

print(kw_bad("ifx", 0))   # -> 2   (matched "if", left "x" dangling, "ifx" never tried!)
print(kw_good("ifx", 0))  # -> 3   (matched the whole "ifx")
```

The output `2` vs `3` *is* the prefix-capture gotcha in one line: `kw_bad` returns after matching the `if` prefix and never reaches `"ifx"`. A CFG's alternation would consider both; PEG's commit-on-success will not. The rule to memorize: **order PEG alternatives longest-first.**

### A bison fragment using precedence to keep the natural expression grammar

```text
%left  '+' '-'        /* lower precedence, left-associative  */
%left  '*' '/'        /* higher precedence                   */
%right '^'            /* highest, right-associative          */
%%
expr : expr '+' expr        { $$ = mkbin('+', $1, $3); }
     | expr '-' expr        { $$ = mkbin('-', $1, $3); }
     | expr '*' expr        { $$ = mkbin('*', $1, $3); }
     | expr '/' expr        { $$ = mkbin('/', $1, $3); }
     | expr '^' expr        { $$ = mkbin('^', $1, $3); }
     | '(' expr ')'         { $$ = $2; }
     | NUMBER               { $$ = mknum($1); }
     ;
%%
```

This grammar is *ambiguous* on its own (`expr '+' expr` doesn't say how to group `a + b + c`), which would normally be a forest of shift-reduce conflicts. The `%left`/`%right` declarations resolve every one of them deterministically by encoding precedence and associativity directly into the parse table — no left-factoring, no precedence-layered grammar. This is the idiomatic way to handle expressions in a generator, and it's the generator-side equivalent of Pratt binding powers.

---

## Trade-offs

| You gain... | ...at the cost of... |
|-------------|----------------------|
| Hand-written recursive descent | Best diagnostics, full recovery/lexer-feedback control | More code, no machine check that it matches a grammar |
| Parser generator (LALR) | Grammar-as-spec, conflict reports, compact fast tables | Generic errors, awkward recovery, fighting context-sensitivity |
| PEG / packrat | No ambiguity by construction, clean composition, linear time | Memory for memoization, prefix-capture surprises, poor error messages |
| GLR / GLL | Parses *any* CFG, keeps all parses of ambiguous input | A parse forest you must disambiguate; worse worst-case complexity |
| Panic-mode recovery | Simple, robust, reports many errors per run | Can skip too much; loses fine-grained structure |
| Error productions | Precise, actionable diagnostics for known mistakes | Expensive to author; must anticipate each mistake |
| Incremental / error-tolerant | Instant editor feedback on broken, evolving files | A persistent CST, trivia handling, more complex parser machinery |

---

## Coding Patterns

### Pattern 1: Recursive descent + Pratt + panic-mode (the production triad)

Statements via recursive descent, expressions via Pratt, recovery via synchronize-to-boundary. This trio is the de-facto standard for a maintainable hand-written front end. Internalize the shape; it's what you'll actually build.

### Pattern 2: `expect` returns a node, never throws

In an error-tolerant parser, a failed `expect` records a diagnostic and returns a `MISSING`/error node so the tree stays complete. Throwing-and-aborting belongs only to batch tools that don't need recovery.

### Pattern 3: Per-construct synchronization sets

Don't use one global sync set. Inside an argument list, sync to `,`/`)`; inside a block, sync to `;`/`}`; at top level, sync to a leading keyword. Tailoring the sync set to the construct is what keeps recovery from skipping half the file.

### Pattern 4: Precedence declarations over grammar layering (in generators)

When using bison-class tools, encode operator precedence with `%left`/`%right` rather than rewriting into a layered grammar. It's the generator analogue of Pratt binding powers and keeps the grammar readable.

### Pattern 5: Longest-alternative-first (in PEGs)

Always order PEG ordered-choice alternatives most-specific/longest first to avoid prefix capture, or guard with a not-predicate (`"if" !idchar`). Make it a reflex.

### Pattern 6: Parse to a full-fidelity CST when tooling needs it

If the parser will feed an IDE/formatter, keep every token and all trivia and derive the AST from the CST. Immutable trees with structural sharing make incremental re-parse cheap.

---

## Best Practices

- **Choose your parsing technology by what artifact should be authoritative** — grammar (generator/PEG) or parser (hand-written) — not by "which is more powerful." State the choice and its reason in a design note.
- **Default to hand-written recursive descent + Pratt for a real language**, and budget real engineering time for recovery and diagnostics. That budget is most of what separates a good compiler from a tolerated one.
- **Never let an error abort the parse in tooling.** Always produce a tree with error nodes; reserve abort-on-error for batch use where recovery has no value.
- **Treat every generator conflict as a test failure.** Resolve it with an intentional precedence declaration or a grammar fix, and document any reliance on a default (dangling-else shift).
- **Order PEG alternatives longest-first** and reach for predicates to express context — but know that PEG error messages will be weak, so weigh that against your UX needs.
- **Keep the lexer and parser able to talk** for C-family languages. If you generate the parser, plan the lexer-feedback channel up front; it's painful to retrofit.
- **Decide CST vs AST by your consumers.** Compiler-only? AST is fine. IDE/formatter/refactoring tool? Keep a full-fidelity CST with trivia.
- **Invest in incrementality only when you need it** — a batch compiler doesn't, a language server absolutely does. Don't pay for a persistent CST you'll never re-splice.

---

## Edge Cases & Pitfalls

- **Recovery that makes no progress.** A synchronize routine that can neither parse nor skip the current token spins forever. Always include a forced-advance guard (`if pos == mark: advance()`).
- **Cascading errors after a bad recovery guess.** Inserting or deleting the wrong token can turn one real error into ten phantom ones. Prefer conservative panic-mode sync over aggressive single-token repair unless you've tested the repair heuristics.
- **PEG prefix capture in keyword/operator tables.** `"<" / "<="` or `"if" / "ifx"` listed shortest-first silently make the longer token unreachable. Longest-first, always.
- **Packrat memory blowup.** Memoizing every (rule, position) on a multi-megabyte input can use enormous memory; pure packrat isn't free. Many "PEG" parsers selectively memoize to control it.
- **Assuming clean lexer/parser separation in C/C++.** The typedef and template-`>>` problems mean the lexer needs parser context. Designing them as fully independent phases for a C-family language is a dead end.
- **The most vexing parse.** `Widget w(Thing());` being a function declaration, not an object construction, surprises everyone; it's a grammar ambiguity resolved by a language rule, not a bug you can parse your way out of.
- **GLR producing a forest you forgot to disambiguate.** If you use a generalized parser for a language that's supposed to have one meaning, you must add a disambiguation pass — otherwise you've parsed the input into several conflicting trees and picked one arbitrarily.
- **Throwing away trivia, then needing it.** A parser that discards whitespace and comments can't power a formatter or faithful refactoring. Retrofitting trivia into an AST-only design is a rewrite.
- **Treating incrementality as "just cache the tree."** True incremental parsing requires splicing a re-parsed subtree into an immutable old tree with correct span adjustment; a naive "re-parse the whole file but debounce it" is not incremental and will lag on large files.

---

## Apply it

1. State the system invariant that **Parsers** must protect.
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

- Which invariant must remain true when Parsers fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
