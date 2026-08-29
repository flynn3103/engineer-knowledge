# Character & String Internals (Unicode) — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Character & String Internals (Unicode)** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. JVM compact strings (JEP 254)

Before Java 9, every `String` held a `char[]` — 2 bytes per character, even for pure-ASCII strings, which are the vast majority in real applications. JEP 254 changed the backing store to a `byte[]` plus a `coder` flag:

- If every character fits in Latin-1 (`U+0000`–`U+00FF`), store **1 byte per character** (`coder = LATIN1`).
- Otherwise, store **2 bytes per character** in UTF-16 (`coder = UTF16`).

For ASCII-heavy heaps this roughly halves `String` storage; Oracle measured ~10% overall heap reduction on typical workloads. The cost is a branch on `coder` in many `String` methods. Note the asymmetry: a single non-Latin-1 character (one emoji, one `日`) flips the *entire* string to 2 bytes/char — there is no per-segment mixing. This is why a log line that is 99% ASCII plus one emoji doubles its storage.

### 2. CPython PEP 393 flexible representation

CPython picks the narrowest fixed-width representation that fits the widest code point in the string:

- All chars ≤ `U+00FF` → **1 byte each** (Latin-1).
- All chars ≤ `U+FFFF` → **2 bytes each** (UCS-2).
- Any char > `U+FFFF` → **4 bytes each** (UCS-4).

`sys.getsizeof("a")` vs `sys.getsizeof("Ā")` vs `sys.getsizeof("\U0001F600")` shows three different per-character costs. Like the JVM, it is "widest character wins": one emoji in a long string promotes *all* of it to 4 bytes/char. This is why `"a" * 1000` and `"a" * 999 + "😀"` differ wildly in memory. CPython also keeps the indexing O(1) (fixed width internally) while presenting code points to the programmer — the best of both worlds at the cost of this promotion rule.

### 3. Small-String Optimization (SSO)

`std::string` in libstdc++/libc++ stores short strings (typically ≤15 or ≤22 bytes) **inline** in the object, with no heap allocation. The object is, say, 32 bytes: for short strings the bytes live in those 32; for long strings the object holds a pointer + size + capacity. This makes short-string construction allocation-free — critical for code that builds millions of small strings. Rust's `String` does *not* do SSO (it is always heap-allocated `Vec<u8>`), which is why crates like `smartstring`, `smol_str`, and `compact_str` exist; Swift's `String` does SSO for strings up to 15 UTF-8 bytes. The trade-off: a fatter string object (worse cache density when strings are long) for zero allocations when they are short.

### 4. Ropes and cords

A **rope** represents text as a balanced tree of substring fragments. Concatenation is O(1) (a new internal node), insertion and deletion in the middle are O(log n), and you never copy a megabyte to insert one character. Text editors (the classic example) and large-document systems use ropes/cords (Abseil's `Cord`, the `xi-editor` rope, JGit's variants) so that editing huge files stays responsive. The cost is that indexing and iteration are O(log n) rather than O(1), and cache locality is worse than a flat array. Contrast: most language `String` types are *immutable flat arrays*, optimized for read and share, terrible for mutate-in-place.

### 5. Immutability and interning

Java, Python, JavaScript, C#, and Go strings are **immutable**: every "modification" allocates a new string. Immutability enables safe sharing across threads, cheap substrings (in some runtimes), and **interning** — keeping one canonical copy of each distinct string so equal strings are also `==`-identical. Java's string pool interns literals (and `String.intern()` on demand); over-interning user-controlled strings is a memory leak / DoS vector because the pool historically did not collect. The trade-off of immutability is allocation churn in string-building loops, which is why every language provides a mutable builder (`StringBuilder`, `bytes.Buffer`, `String::push_str`).

### 6. Unicode as an attack surface

Every semantic subtlety becomes a weapon:

- **Homoglyph / IDN spoofing:** `аррӏе.com` (Cyrillic letters) renders like `apple.com`. Punycode (`xn--80ak6aa92e.com`) is the ASCII form, but browsers may display the Unicode form. Phishing and fake package names exploit this.
- **Trojan Source (CVE-2021-42574):** bidi override characters (`U+202E` etc.) reorder how source code *displays* without changing how it *compiles*. A reviewer sees `if (isAdmin)` but the compiler sees a comment — a hidden backdoor invisible in code review.
- **Overlong UTF-8:** encoding `/` as `0xC0 0xAF` instead of `0x2F` can slip past a path filter that only checks for the byte `0x2F`, enabling directory traversal. (The IIS "Unicode" worm of 2001 used exactly this.)
- **Normalization bypass:** a validator checks the raw string for a forbidden substring, but the downstream consumer normalizes (NFKC) first; an attacker encodes the forbidden text using compatibility characters (`＜script＞` full-width) that pass the filter and become `<script>` after normalization.
- **Case-folding bypass:** filter checks `"admin"` but the system later lowercases with a locale where `İ`→`i`, letting `admİn` through.
- **Decoder DoS / crashes:** maliciously crafted sequences (deeply nested combining marks, specific code-point combinations) have crashed renderers and parsers.

The unifying rule: **canonicalize once, early, and validate the canonical form** — never validate one representation and consume another.

---

## Code Examples

### Observing representation costs

```python
import sys
print(sys.getsizeof("a" * 100))            # ~149  (Latin-1, ~1 byte/char)
print(sys.getsizeof("Ā" * 100))       # ~274  (UCS-2, ~2 bytes/char)
print(sys.getsizeof("\U0001F600" * 100))   # ~456  (UCS-4, ~4 bytes/char)
# One emoji promotes everything:
print(sys.getsizeof("a" * 999))            # ~1048  (Latin-1)
print(sys.getsizeof("a" * 999 + "😀"))     # ~4096  (whole string now UCS-4!)
```

```java
// JVM compact strings: one non-Latin-1 char flips the backing store to UTF-16.
String ascii = "x".repeat(1000);      // byte[] of 1000 bytes (LATIN1)
String mixed = "x".repeat(999) + "あ"; // byte[] of 2000 bytes (UTF16) — doubled
// Verify via JOL (Java Object Layout) or -XX:+PrintFlagsFinal CompactStrings (default true 9+)
```

### Building strings without allocation churn

```rust
// Rust: avoid reallocations by reserving; or use a SSO crate for many small strings.
let mut s = String::with_capacity(1024);   // one allocation
for i in 0..100 { s.push_str(&i.to_string()); }

// For millions of short strings, a compact/inline type avoids per-string heap allocs:
// use compact_str::CompactString;  // inline up to 24 bytes, heap beyond
```

### Detecting a homoglyph / mixed-script identifier

```python
import unicodedata
def scripts(s):
    return {unicodedata.name(ch, "?").split()[0] for ch in s if ch.isalpha()}

print(scripts("apple"))      # {'LATIN'}
print(scripts("аpple"))      # {'CYRILLIC', 'LATIN'}  ← mixed-script: suspicious!
# Real defense: UTS #39 confusable "skeleton" + single-script restriction.
```

### Catching a Trojan Source bidi attack

```python
BIDI_CONTROLS = {0x202A,0x202B,0x202C,0x202D,0x202E,0x2066,0x2067,0x2068,0x2069}
def has_bidi_override(src: str) -> bool:
    return any(ord(ch) in BIDI_CONTROLS for ch in src)

# Linters/compilers (rustc, gcc, GitHub) now warn on these in source files.
src = "access_level = 'user' ‮ ⁦// Check if admin⁩ ⁦"
print(has_bidi_override(src))   # True — block or warn
```

### Rejecting overlong UTF-8

```go
import "unicode/utf8"
// Go's decoder rejects overlong forms automatically:
fmt.Println(utf8.Valid([]byte{0x2F}))        // true  — '/'
fmt.Println(utf8.Valid([]byte{0xC0, 0xAF}))  // false — overlong '/', correctly rejected
// NEVER hand-roll a decoder that accepts these; use the stdlib.
```

### The normalization-bypass trap

```python
import unicodedata, re
attacker = "＜script＞"        # ＜script＞ using full-width brackets
print(bool(re.search(r"<script>", attacker)))   # False — filter passes it
normalized = unicodedata.normalize("NFKC", attacker)
print(normalized)                                # "<script>"  ← becomes dangerous
# FIX: normalize FIRST, then validate the normalized string.
```

---

## Coding Patterns

**Pattern 1: Canonicalize-then-validate-then-consume, all in one representation.** Eliminate the gap attackers exploit by normalizing at the trust boundary, validating the normalized form, and consuming that same form.

**Pattern 2: Single-script + confusable skeleton for identities.** Restrict identifiers to a single script (or an allowed mixed set), compute the UTS #39 confusable skeleton, and reject collisions with existing identities.

**Pattern 3: Strict decoders at the edge.** Use the standard library's strict UTF-8 validation on all untrusted bytes; map invalid input to `U+FFFD` or reject, never silently drop.

**Pattern 4: Profile-driven representation choice.** Default to the runtime's immutable string; switch to SSO/compact types or ropes only where a profiler shows allocation or copy cost dominating.

**Pattern 5: Block bidi controls in code paths.** Lint source, config, and any field rendered to other humans for bidi override / invisible characters; allow them only where genuine RTL content is expected, using isolates correctly.

---

## Best Practices

1. **Normalize before validating untrusted input;** validate and consume the same canonical form.
2. **Decode untrusted UTF-8 strictly** — reject overlong, surrogate, and truncated sequences.
3. **Canonicalize identities with NFKC_Casefold + confusable/single-script checks** to defeat homoglyph spoofing.
4. **Scan source and human-facing text for bidi overrides and invisible characters;** treat findings as suspicious.
5. **Compare/store domains in Punycode/ASCII form;** warn on confusable display.
6. **Do not intern user-controlled strings** without bounds — it is a memory-exhaustion vector.
7. **Profile string memory with the "widest char wins" rule in mind;** keep wide-character fields out of otherwise-ASCII bulk data when footprint matters.
8. **Use ropes/cords only for large mutable text;** flat immutable strings everywhere else.
9. **Pin and track your Unicode/ICU data version;** confusable and normalization tables evolve, and security decisions depend on them.

---

## Edge Cases & Pitfalls

**One emoji quadruples your memory.** A million-row table where each `name` is ASCII except a handful containing an emoji: those rows silently jump from 1 to 4 bytes/char (CPython) or 1 to 2 (JVM) — a real, surprising heap cost discovered only under profiling.

**Interning a DoS.** Calling `String.intern()` on attacker-supplied strings (or relying on a framework that does) can fill an uncollected pool and OOM the process.

**Validator/consumer normalization mismatch.** The WAF checks the raw bytes; the application NFKC-normalizes; the attacker uses compatibility characters to pass the WAF and become a payload. Same bug class as double-decoding.

**Overlong-encoding filter bypass.** Any custom byte-level filter that does not first decode-and-validate UTF-8 can be bypassed with overlong forms. This is the IIS-worm class of bug.

**Bidi in a "harmless" comment.** A pull request whose diff *looks* benign can compile to a backdoor via bidi overrides. Diff viewers that do not reveal these controls hide the attack.

**Lone surrogate serialization.** A JS string holding an unpaired surrogate (from slicing an emoji) cannot be encoded to valid UTF-8; `JSON.stringify` may emit `\uD83D` and a strict consumer rejects it.

**Replacement-character data loss.** A lenient decoder that maps bad bytes to `U+FFFD` *destroys* the original bytes; if those bytes were meaningful (a binary field misrouted through a text path), the data is gone irreversibly.

**Case-folding length change breaking buffers.** `ß`→`SS` during case-insensitive processing changes length; fixed-size buffers or column-aligned formats overflow or misalign.

---

## Real Incidents

**The "effective power" / Unicode-of-death iOS crash (2015).** A specific Arabic/Marathi text string, when received in a notification, crashed `SpringBoard` on iOS, rebooting the phone and making Messages unusable until the message was cleared. The root cause was a text-rendering bug triggered by a particular sequence of code points and combining marks. Lesson: text rendering is a code path that processes adversarial input and must be hardened; a single message can be a remote DoS.

**The Telugu character crash (2018, CVE-2018-4124).** A single Telugu grapheme cluster (a base consonant + sign joined by a virama/ZWNJ) crashed iOS and macOS apps that tried to render it — Messages, Safari, even Springboard — across iPhones and Macs. A character in a notification could brick the Messages app. Again: a grapheme that the renderer's state machine could not handle, weaponized by simply sending it.

**Spotify username canonicalization account takeover (2013).** Spotify's username canonicalization normalized Unicode inconsistently between the point of registration and the point of lookup. An attacker could register a username that canonicalized to a victim's username, then trigger a password reset that resolved to the victim's account — a normalization-mismatch account takeover. The fix was to canonicalize once, consistently, and compare canonical forms everywhere. This is the textbook real-world case for "canonicalize-then-validate, one representation."

**Trojan Source (2021, CVE-2021-42574 / CVE-2021-42694).** Researchers showed that bidi override characters in source code let an attacker make code display one way to reviewers while compiling another way, across nearly every major language and compiler. Homoglyph identifiers compounded it. The response was compiler/linter/host warnings (rustc, gcc, GitHub, and others now flag bidi controls in source). Lesson: the source code itself is untrusted text, and the gap between display and semantics is exploitable.

**IIS Unicode directory-traversal worm (2001).** Microsoft IIS decoded overlong/double-encoded UTF-8 *after* its path-security check, so `%c0%af` (overlong `/`) bypassed the filter and enabled `../` traversal and remote command execution, exploited en masse by the "Code Red"/"Nimda"-era worms. Lesson: decode and canonicalize *before* security checks, never after.

---

## Apply it

1. Define the user or business outcome that **Character & String Internals (Unicode)** should improve.
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

- Which measurable outcome justifies investing in Character & String Internals (Unicode)?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
