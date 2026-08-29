# Lexers & Tokenizers — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Lexers & Tokenizers** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## The Lexer Is Often the Hot Path

Because the lexer processes every character, it is frequently the single hottest phase
on large inputs, and small constant factors matter:

- **Avoid per-token allocation.** Don't allocate a new string per token; slice into the
  source buffer (store offsets/spans) and **intern** identifiers so each unique name is
  allocated once.
- **Buffer efficiently.** Read the whole file into one contiguous buffer where
  possible; pointer/index advancement beats stream abstractions with per-char overhead.
- **Branch-friendly dispatch.** A `switch` on the first character (or a 256-entry
  classification table) keeps the inner loop predictable; hand-written lexers win here
  over generic regex engines.
- **Minimize backtracking.** Maximal munch with at most a character or two of lookahead
  stays O(n); avoid patterns that force re-scanning.

For multi-megabyte generated files or monorepo-scale builds, these decisions move
total compile time measurably, which is part of why GCC/Clang/rustc/Go hand-write
lexers tuned for exactly this.

---

## Error Recovery in the Lexer

A compiler that stops at the first bad character is hostile. The lexer must **recover**
and continue:

- On an illegal character or malformed token, emit an **error token** (with a span and
  message) and skip forward to a plausible resynchronization point (next whitespace,
  next line, closing quote) so the rest of the file still lexes.
- Report the **opening position** for unterminated strings/comments, not just "EOF
  reached."
- Keep producing tokens so the parser can report *its* errors too — many real
  diagnostics depend on lexing surviving the first mistake.

Good recovery is what lets a compiler report a dozen real errors in one run instead of
one-at-a-time.

---

## Incremental and Editor Lexing

In an IDE the lexer runs on every keystroke, so re-lexing the whole file each time is
wasteful. Production editor tooling lexes **incrementally**: re-tokenize only the
region around an edit, reusing tokens before and after. The challenge is that an edit
can change tokenization arbitrarily far (typing `/*` comments out the rest of the
file), so incremental lexers track how far a change can propagate and re-lex a bounded
window, often integrated with an incremental parser.

- **Tree-sitter** re-lexes and re-parses incrementally for editor highlighting and
  structural selection across many languages.
- **Roslyn** (C#) uses red-green trees with incremental lexing/parsing for responsive
  IDE features.
- Syntax highlighting, semantic highlighting, and "expand selection" all sit on this
  incremental token stream.

---

## Unicode and Security

- **Identifiers in Unicode** must be handled per the language spec (e.g. UAX #31):
  which code points start/continue an identifier, and **normalization** (NFC) so
  visually identical identifiers compare equal.
- **Confusable/homoglyph attacks:** identifiers that look identical but differ in code
  points (Cyrillic `а` vs Latin `a`), and **bidi-override** characters (the *Trojan
  Source* attack) that make source render differently than it tokenizes — a real
  supply-chain risk. Lexers/linters increasingly reject or warn on dangerous code
  points.
- **Overlong/invalid UTF-8** must be rejected, not silently accepted.

---

## Best Practices

- **Slice, don't allocate; intern identifiers.** Keep the inner loop allocation-free.
- **Recover from errors** with error tokens and resynchronization; report opening
  positions.
- **Design for incrementality** if you'll power an editor — bound the re-lex window.
- **Follow the Unicode identifier spec and normalize**; warn/reject confusables and
  bidi controls.
- **Profile the lexer** on your largest real inputs — it's often the hot path.

---

## Edge Cases & Pitfalls

- **Per-token string allocation** quietly dominating compile time on big files.
- **A `/*` edit** invalidating tokenization to EOF, breaking naive incremental lexers.
- **Unterminated string/comment** errors that point at EOF instead of the opening
  delimiter.
- **Trojan Source / homoglyph** identifiers passing review because the editor renders
  them benignly.
- **Tabs/spaces and CRLF/LF** inconsistencies affecting indentation-sensitive lexers.

---

## Apply it

1. Define the user or business outcome that **Lexers & Tokenizers** should improve.
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

- Which measurable outcome justifies investing in Lexers & Tokenizers?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
