# Parsers — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Parsers** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Front-end architecture: where the boundaries go

A professional front end is a pipeline of well-chosen boundaries, and *where* you draw them determines what's possible later:

- **Source text → lexer → token stream (with trivia).** The lexer attaches whitespace and comments as **trivia** to adjacent tokens rather than discarding them. This one decision is what later lets a formatter and a refactoring tool reconstruct exact source. Throwing trivia away here is a choice you cannot reverse cheaply.
- **Token stream → parser → CST.** The parser builds a **full-fidelity concrete syntax tree** that contains every token and all trivia. The CST is the durable, sharable artifact.
- **CST → AST.** The semantic tree is *derived* from the CST, dropping trivia and redundant syntax. Crucially, the AST keeps **source spans** pointing back into the CST/text, so every later phase (type errors, warnings) can point at the exact source location.

The professional insight is that **the CST is the platform and the AST is a view of it.** A batch-compiler-only design can collapse these and go straight to an AST. But the moment an IDE, formatter, or codemod tool needs to participate, you need the CST — and bolting it on after the fact is a front-end rewrite. The successful modern languages decided this on day one.

Another boundary decision: **how much semantic work leaks into the parser.** Purists want a context-free parser and all meaning in later phases. Reality (C/C++ typedef, contextual keywords, offside rule) forces *some* context into parsing. The professional stance is to **minimize** parser-resident semantics to exactly what the grammar genuinely needs, keep that coupling explicit (a clearly-named "is this an identifier a type?" query), and resist letting the parser quietly accumulate semantic knowledge.

### 2. Grammar evolution: growing a language without breaking it

A grammar is not finished at 1.0; it grows for the life of the language. The professional skill is adding syntax without invalidating billions of lines of existing code. The central tool is the **contextual (soft) keyword**:

- A **reserved keyword** (`if`, `class`, `return`) can never be an identifier. Adding a new reserved word is a *breaking change* — every program that used that word as a variable name stops compiling. This is why mature languages almost never add reserved words.
- A **contextual keyword** (`async`, `await`, `yield`, `record`, `var`, `await`, `from`/`select` in C# LINQ, Python's `match`/`case`) is a keyword *only in specific grammatical positions* and a perfectly legal identifier everywhere else. `async` is a keyword before a method, an identifier as a variable name; the parser disambiguates by position. This lets the language grow indefinitely without breaking old code — but it pushes complexity into the parser, which must now decide by context whether a word is syntax or a name.

Python's history is the clean case study: `match`/`case` (structural pattern matching, 3.10) are **soft keywords** precisely so existing code with variables named `match` keeps working. The walrus operator `:=` (3.8) added new syntax with a new token, avoiding the keyword issue entirely. The lesson: **every syntactic addition has a compatibility cost, and the parser is where that cost is paid.** A hand-written recursive-descent parser absorbs contextual keywords gracefully (it's an `if` on position); a rigid LALR grammar can find them genuinely hard, because "this token is a keyword here but an identifier there" is exactly the kind of context-sensitivity that fights a CFG. Grammar evolvability is therefore *another* reason flagship languages hand-write.

The complementary discipline is **restraint**. Go is famous for a small, stable grammar — the team treats every syntactic addition as a permanent tax on every reader and every tool. A professional weighs each new piece of syntax against the parser complexity, the compatibility risk, and the cognitive cost it imposes forever. The cheapest syntax is the syntax you don't add.

### 3. The one-tree platform: compiler, IDE, formatter, linter from a single parser

The defining architectural move of the most successful modern language platforms is to build the *entire* toolchain on **one parser and one syntax-tree library**:

- **Roslyn** (.NET) exposes the C#/VB compiler as an API — "compiler as a service." The same parser and the same immutable syntax trees power `csc` (the compiler), the Visual Studio IDE (completion, refactoring, squiggles), the formatter, the analyzers (linters), and codemods. There is exactly one definition of "what a C# program's syntax is," and everyone consumes it.
- **Swift** ships **SwiftSyntax** (libSyntax), a full-fidelity, round-trippable tree library used by the compiler, the formatter (`swift-format`), and migration tools.
- **Rust** has a deliberate split — `rustc`'s internal parser for compilation and `rust-analyzer` (built on the `rowan` red-green CST library, with a separate but spec-compatible parser) for the IDE — and the ecosystem feels the cost of *two* parsers that must agree. It's the instructive counterexample: maintaining two parsers for one language is an ongoing tax, and the Rust project has worked toward sharing more between them precisely because divergence is painful.
- **TypeScript** uses one parser for `tsc` and the language service that powers VS Code.

Why this matters at the professional level: **a parser that only the compiler uses is a different, easier artifact than a parser an entire ecosystem builds on.** The one-tree design demands an error-tolerant, incremental, full-fidelity, immutable tree (so it's sharable across threads and tools) with a stable public API (because external analyzers and codemods depend on it). Choosing the one-tree platform up front is more work initially and far less work over a decade — it's why the question "compiler-only or platform?" should be answered *before* the first parser line is written. The cost of discovering you need it at version 4.0 is a front-end rewrite that breaks every tool downstream.

### 4. The red-green tree: how immutable + incremental coexist

The one-tree platform needs a syntax tree that is simultaneously **immutable** (sharable, thread-safe, cheap to snapshot), **incremental** (a small edit re-uses most of the old tree), and able to give every node a **parent pointer and absolute position** (tools need "what's the node at offset 4012?" and "what's this node's parent?"). These requirements conflict — absolute positions and parent links seem to demand mutability — and Roslyn's **red-green tree** resolves the conflict:

- **Green nodes** are immutable, position-independent (they store *widths*, not absolute offsets), parent-less, and **structurally shared**. Two identical subtrees can be the same green node. An edit re-builds only the green nodes on the path from the change to the root; everything else is reused.
- **Red nodes** are lazily created wrappers around green nodes that *do* carry a parent pointer and an absolute position, computed on demand as you walk down from the root. They're transient and recomputed per traversal, so they never compromise the green tree's sharability.

This is the persistent-data-structure trick (the same one that makes functional data structures cheap to "modify") applied to syntax trees. It's why an editor can hold the tree immutably, share it across threads, and still re-parse a keystroke's worth of change in O(edit) time. You don't have to use red-green specifically, but you *do* have to solve the same three-way tension, and understanding the canonical solution is part of being able to architect a real platform parser.

### 5. Parser performance at scale

The professional reality check: **the parser is almost never the compiler's bottleneck.** Type checking, optimization, and code generation dominate; parsing is typically a small single-digit percentage of compile time. So the first performance rule is *don't optimize the parser until you've measured that it matters* — which is rare in a batch compiler.

It *does* matter in two regimes:

- **The IDE / language-server loop**, where the parser runs on every keystroke. Here incrementality (re-parse only the edit) is the whole game; raw throughput is secondary to "don't re-parse the 50k-line file." This is why editor parsers are incremental even when batch parsers don't bother.
- **Huge inputs / huge fan-out** — a build system parsing millions of files, a code-search index over a monorepo, a CI step parsing every PR. At that scale the constant factors add up and a fast parser (Tree-sitter's design goal, the Go parser's plainness) pays off across the fleet.

When you *do* tune a parser: avoid per-token allocations (intern identifiers, reuse buffers), keep the lexer tight (lexing is often a larger share than parsing), prefer arena/bump allocation for tree nodes, and make the common path branch-predictable. But the headline stays: **measure first; the parser is usually not where your compile time goes.** The senior-to-professional shift is knowing *when* parser performance is real (the IDE loop, fleet-scale tooling) versus a premature-optimization trap (a batch compiler's parse phase).

### 6. Parsers as an attack surface: security

The parser is, by definition, **the first piece of code to touch fully untrusted input** — a downloaded file, a network message, a user-submitted document, a dependency's source. That makes it a security boundary, and parsers have real, exploited failure modes:

- **Stack-overflow DoS via deep nesting.** A hand-written recursive-descent parser uses the native call stack; input like `((((((((((... ` or `[[[[[[[[[[...` thousands deep recurses until the stack overflows and the process crashes. This is a genuine denial-of-service vector for any parser exposed to untrusted input (JSON parsers, config loaders, query parsers have all shipped this bug). The defenses: a **recursion-depth limit** (count nesting and reject past a sane bound with a clean error), or converting the recursive descent to an explicit heap-allocated stack so "overflow" becomes a catchable allocation failure instead of a crash.
- **Catastrophic backtracking.** Backtracking parsers (and regexes used in lexers) can hit exponential time on crafted input — the classic "ReDoS." A packrat parser's linear-time guarantee is partly a *security* property, not just a performance one. Audit any unbounded backtracking and any regex in the lexer for super-linear behavior on adversarial strings.
- **Resource exhaustion in general.** Memory blowup from packrat memoization on huge inputs, pathological error-recovery loops, or grammar rules that allow unbounded expansion all become DoS vectors when the input is hostile.
- **Parser differentials.** When two parsers for the "same" format disagree (a validating parser vs an enforcing one, or two implementations of a protocol), an attacker can craft input that one accepts and another rejects — the root of many smuggling and bypass attacks. Keeping a *single* authoritative parser (the one-tree platform again) is also a security posture.

The professional rule: **treat the parser as security-critical untrusted-input handling.** Bound recursion, bound memory, bound time, fuzz it continuously, and prefer one authoritative implementation over many subtly-divergent ones.

### 7. Fuzzing and differential testing the grammar

Because the parser handles untrusted input and must never crash, **continuous fuzzing is non-negotiable** at this level. The practices:

- **Coverage-guided fuzzing** (libFuzzer, AFL++) on the parser entry point, run continuously in CI/OSS-Fuzz, catches the crashes (stack overflow, OOM, hangs) that hand-written tests miss. Every flagship language front end is fuzzed this way.
- **Grammar-aware / structured fuzzing** generates *mostly-valid* programs to exercise deep parser paths that random bytes never reach.
- **Differential testing** runs two implementations (e.g. the compiler parser and the IDE parser, or your parser and a reference) on the same input and flags any disagreement — catching both bugs and the parser-differential security issues from §6.
- **Round-trip property testing**: for a full-fidelity parser, assert `print(parse(src)) == src` over a corpus and over generated inputs. A round-trip failure means lost trivia or a tree that can't faithfully reproduce source — fatal for a formatter or codemod platform.

These aren't QE nice-to-haves bolted on; for a parser that's a security boundary and a toolchain foundation, they're core engineering.

### 8. Owning a grammar: the organizational dimension

At the professional level the parser has *stakeholders*. The grammar is depended on by: the compiler team, the IDE team, every analyzer/linter author, every codemod, external tooling, and ultimately every user's source code. That changes how you make changes:

- **A grammar change is an API change.** Adding syntax can break tools that pattern-match the tree; renaming a node type breaks every analyzer. The syntax-tree shape is a public contract, versioned and deprecated with care, exactly like any other API.
- **Backward compatibility is sacred.** New syntax must (almost always) be purely additive — old programs keep parsing. This is why contextual keywords exist and why reserved-word additions are nearly forbidden.
- **One source of truth.** Whether it's a hand-written parser or a grammar file, there must be a single authoritative definition of the language's syntax that everyone derives from — otherwise the compiler, the IDE, and the spec drift, and users hit "compiles but the IDE shows an error" bugs.
- **Documentation and a formal grammar** (even if the real parser is hand-written) let external tool authors build against a stable reference. Many languages publish a grammar in the spec that the hand-written parser is kept consistent with by review and testing.

The professional doesn't just write a parser; they **steward a syntax** that an ecosystem and a user base depend on, with the change-management discipline that responsibility demands.

---

## Code Examples

### Bounding recursion depth to defeat the stack-overflow DoS (Python)

The single most important hardening for a recursive-descent parser exposed to untrusted input.

```python
class Parser:
    MAX_DEPTH = 200          # well below the native stack limit; tune per platform

    def __init__(self, tokens):
        self.toks, self.pos, self.depth = tokens, 0, 0
        self.errors = []

    def _enter(self):
        self.depth += 1
        if self.depth > self.MAX_DEPTH:
            # Clean, reported failure instead of a process-killing stack overflow.
            raise RecursionError(f"nesting too deep (>{self.MAX_DEPTH}) — refusing to parse")

    def _leave(self):
        self.depth -= 1

    def parse_primary(self):
        self._enter()
        try:
            if self.at("LPAREN"):
                self.advance()
                inner = self.parse_expr()      # recursion guarded by depth counter
                self.expect("RPAREN")
                return ("group", inner)
            return ("num", self.advance()[1])
        finally:
            self._leave()
```

Without `MAX_DEPTH`, input like `"(" * 100_000 + "1" + ")" * 100_000` recurses until the native stack overflows and crashes the whole process — a trivial denial-of-service. With it, the parser returns a clean, catchable error and the service stays up. Every parser that touches untrusted input needs this guard (JSON, config, and query parsers have all shipped the bug for lacking it).

### A full-fidelity token with attached trivia (Python sketch)

The data-structure decision that makes a formatter/codemod platform possible.

```python
class Trivia:
    # whitespace and comments — kept, never discarded
    def __init__(self, text, kind):  # kind in {"whitespace", "comment", "newline"}
        self.text, self.kind = text, kind

class Token:
    def __init__(self, kind, text, leading, trailing):
        self.kind = kind
        self.text = text
        self.leading = leading      # Trivia before the token (e.g. indentation, comments)
        self.trailing = trailing    # Trivia after it on the same line

    def to_source(self):
        lead = "".join(t.text for t in self.leading)
        trail = "".join(t.text for t in self.trailing)
        return f"{lead}{self.text}{trail}"

def round_trip(tokens):
    # The defining property of a full-fidelity tree:
    return "".join(t.to_source() for t in tokens)

# print(round_trip(parse(src))) == src   must hold EXACTLY, comments and all.
```

The discipline is that **trivia is attached, never thrown away**, so the original source — every comment, every blank line, every odd indentation — can be reconstructed exactly. A compiler-only parser can skip all of this; a parser that wants to be a *platform* (formatter, refactoring, codemod) cannot, and retrofitting trivia after the fact is a front-end rewrite.

### A contextual-keyword decision in hand-written recursive descent (Python)

How a soft keyword like `async` or `match` is handled — by position, not by reservation.

```python
def parse_statement(self):
    tok = self.peek()
    # "match" is a SOFT keyword: a keyword here only if it's followed by a
    # subject expression and a ':' — otherwise it's an ordinary identifier.
    if tok.text == "match" and self._looks_like_match_statement():
        return self.parse_match_statement()
    # Falls through: "match" used as a plain variable name still parses fine.
    return self.parse_expression_statement()

def _looks_like_match_statement(self):
    # Bounded lookahead: peek past the subject to see a ':' + NEWLINE + INDENT 'case'.
    save = self.pos
    try:
        self.advance()                     # consume 'match'
        if self.at("NEWLINE") or self.at("ASSIGN"):
            return False                   # 'match = ...' or 'match\n' → identifier
        self._skip_expression()            # the subject
        return self.at("COLON")
    finally:
        self.pos = save                    # pure lookahead, no consumption
```

This is exactly the context-sensitivity a hand-written parser absorbs with a single guarded lookahead, and exactly what lets a language add `match` without breaking every program that already uses `match` as a variable. A rigid generated grammar finds this genuinely awkward — which is why grammar *evolvability* is one more reason flagship languages hand-write their parsers.

---

## Trade-offs

| You gain... | ...at the cost of... |
|-------------|----------------------|
| Full-fidelity CST + trivia | Powers formatter, IDE, codemods; exact round-trip | More memory per parse, more parser complexity |
| One-tree platform | Single source of truth, no tool divergence | Big up-front investment; the tree shape becomes a public API |
| Contextual keywords | Grammar grows without breaking old code | Parser context-sensitivity; harder for generated parsers |
| Red-green tree | Immutable + incremental + positions, all at once | Two-layer tree implementation complexity |
| Recursion-depth limits | Stops stack-overflow DoS | Rejects (extremely rare) legitimately-deep input; a tunable bound |
| Packrat linear-time guarantee | Security property (no catastrophic backtracking) | High memoization memory on large inputs |
| Two parsers (compiler + IDE) | Each tuned to its job | Permanent tax to keep them agreeing; divergence = user-visible bugs |
| Grammar restraint (small grammar) | Cheaper tools, easier readers, fewer bugs | Less syntactic sugar; users may want more |

---

## Coding Patterns

### Pattern 1: CST-first, AST-as-projection

Parse to a full-fidelity CST and derive the AST as a lightweight projection that keeps source spans. This single architecture serves both batch compilation and the entire tooling ecosystem; the reverse (AST-first, CST bolted on) does not.

### Pattern 2: Depth-bounded recursion on all nesting constructs

Every recursive entry point (parentheses, brackets, blocks, nested types) increments a depth counter and rejects past a bound. Make it a base-class mechanism so no construct can forget it. This is parser security 101.

### Pattern 3: Soft keywords via guarded bounded lookahead

Implement contextual keywords as a position check: a word is a keyword only when followed by the disambiguating context, otherwise it's an identifier. Use pure (save/restore) lookahead so the probe consumes nothing.

### Pattern 4: Trivia attached to tokens, never discarded

The lexer binds leading/trailing trivia to each token. Round-trip (`print(parse(src)) == src`) is a property test in CI. This is the price of being a formatting/refactoring platform.

### Pattern 5: One authoritative parser, many consumers

Resist the temptation to fork a "lighter" parser for a second tool. Maintain one parser and one tree; if you must split (rustc vs rust-analyzer), invest continuously in keeping them in agreement and treat any divergence as a bug, not a quirk.

### Pattern 6: Fuzz + differential + round-trip in CI

Wire coverage-guided fuzzing, differential testing against any second implementation, and round-trip property tests into continuous integration. For a security-boundary, foundation-level parser these are core, not optional.

---

## Best Practices

- **Decide compiler-only vs platform before the first line.** If any IDE, formatter, or codemod will ever consume the tree, commit to error-tolerant, incremental, full-fidelity, immutable from the start — retrofitting it is a front-end rewrite.
- **Keep trivia from the first commit.** Attach whitespace and comments to tokens even if today's consumer doesn't need them; the formatter you'll want in two years does, and you can't recover discarded trivia.
- **Make the parser a security boundary.** Bound recursion depth, bound memory and time, audit all backtracking/regex for super-linear behavior, and fuzz continuously. The parser is the only code that sees raw untrusted input.
- **Grow the grammar with contextual keywords, not reserved words.** Keep additions backward-compatible; treat every new piece of syntax as a permanent cost to readers, tools, and compatibility.
- **Maintain one source of truth for syntax.** One authoritative parser/grammar that compiler, IDE, and spec all derive from; divergence produces "compiles but IDE disagrees" bugs and security differentials.
- **Treat the syntax-tree shape as a versioned public API.** External analyzers and codemods pattern-match the tree; changing node types is a breaking change to be managed, deprecated, and documented.
- **Measure before optimizing the parser.** It's rarely the batch compiler's bottleneck; spend tuning effort on the IDE incremental loop and fleet-scale throughput, where it actually matters.
- **Verify the round-trip property** (`print(parse(src)) == src`) over a real corpus if the parser feeds a formatter or codemod — a silent trivia loss is a platform bug.

---

## Edge Cases & Pitfalls

- **AST-first regret.** A team builds an AST-only parser for the compiler, then the IDE/formatter need a CST with trivia — and there's no cheap path; it's a rewrite. The most common, most expensive architectural mistake here.
- **The two-parser drift tax.** Maintaining a separate IDE parser (or a separate reference grammar) means they slowly disagree, and users hit cases where the compiler and editor differ. Budget continuous effort to keep them aligned or pay it in bug reports forever.
- **Unbounded recursion shipped to production.** A recursive-descent parser without a depth limit is a stack-overflow DoS waiting for the first nested input. Security teams find these by fuzzing; ship the bound first.
- **Catastrophic backtracking in the lexer's regexes.** A super-linear regex on an untrusted input is a ReDoS even if the parser proper is fine. Audit lexer regexes, not just the grammar.
- **Reserved-word addition as a "small" change.** Adding a reserved keyword breaks every program using that word as an identifier — a massive, often underestimated compatibility break. Use a contextual keyword instead.
- **Trivia silently dropped at the lexer.** If whitespace/comments are discarded during lexing, no later phase can recover them; a formatter built on that tree mangles the user's source. The loss is invisible until the round-trip test (which you should have) fails.
- **Treating parser performance as the compile-time problem.** Optimizing the parser while type checking and codegen dominate is misdirected effort. Profile the whole pipeline first.
- **Grammar churn against a brittle architecture.** A parser that's painful to extend turns every language proposal into a slog and tempts teams to bolt syntax on inconsistently. If the language will evolve, the front end's *evolvability* is a primary design goal, not an afterthought.
- **Parser differentials as a security hole.** Two parsers (a validator and an enforcer, or two protocol implementations) that disagree on edge cases let attackers smuggle input past one through the other. One authoritative parser is also a security posture.

---

## Apply it

1. Define the user or business outcome that **Parsers** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Parsers?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
