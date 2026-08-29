# Character & String Internals (Unicode) — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Character & String Internals (Unicode)** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Bytes are not text — an encoding is required

When you save the word `café` to a file, the file contains bytes. *Which* bytes depends on the encoding:

```
"café" in UTF-8:          63 61 66 C3 A9       (5 bytes — é is two bytes)
"café" in Latin-1:        63 61 66 E9          (4 bytes — é is one byte)
"café" in UTF-16LE:       63 00 61 00 66 00 E9 00   (8 bytes — 2 per char)
```

The same word, three different byte sequences. If you write the file as UTF-8 and someone reads it as Latin-1, they see garbage. **There is no such thing as "plain text."** Every text has an encoding, even when nobody told you what it is. The famous rule from Joel Spolsky: *it does not make sense to have a string without knowing what encoding it uses.*

### 2. The four layers

Take the family emoji, 👨‍👩‍👧‍👦. Let us count it at each layer (in UTF-8):

| Layer | What it counts | Count for 👨‍👩‍👧‍👦 |
|-------|----------------|---------------------|
| **Bytes** | Raw 8-bit numbers | 25 |
| **Code units** (UTF-8) | 1-byte chunks (same as bytes here) | 25 |
| **Code points** | Unicode numbers | 7 (four people + three "joiners") |
| **Grapheme clusters** | What a human sees | **1** |

One emoji. Seven code points. Twenty-five bytes. A human sees *one* character. When you ask `length`, the answer depends entirely on which layer your language counts, and most languages count code units — the *least* human-meaningful layer.

### 3. ASCII: the 128-character ancestor

ASCII (1963) used 7 bits, giving 128 codes:
- 0–31: control characters (newline = 10, tab = 9, etc.)
- 32–126: printable (`space` = 32, `A` = 65, `a` = 97, `0` = 48)
- 127: delete

ASCII covers English and nothing else. No `é`, no `ñ`, no `日本語`. A byte has 8 bits, so 128 more values (128–255) sat unused — and *everyone* used them differently. That is where mojibake comes from.

### 4. The mojibake era: legacy encodings

Before Unicode, every region invented its own way to use bytes 128–255:
- **Latin-1 / ISO-8859-1**: Western European (`é`, `ñ`, `ü`).
- **Windows-1252**: Microsoft's near-clone of Latin-1 with curly quotes and the € sign.
- **ISO-8859-5**: Cyrillic. **ISO-8859-7**: Greek.
- **Shift-JIS, EUC-JP**: Japanese (used *two* bytes per character — already breaking the "one byte one char" idea).

The same byte `0xE9` was `é` in Latin-1, `щ` in one Cyrillic encoding, and part of a kanji in Shift-JIS. Email and web pages constantly displayed garbage because the sender's encoding and the reader's encoding disagreed. This chaos is *why* Unicode exists.

### 5. Unicode: one catalogue for everything

Unicode does **one job**: it assigns every character a unique number, the code point. It does not say how to store them in bytes — that is the encoding's job. Unicode has room for `U+0000` to `U+10FFFF` (about 1.1 million slots), organized into **17 planes** of 65,536 each. The first plane, the **Basic Multilingual Plane (BMP)**, holds almost everything you use daily (Latin, Cyrillic, CJK, Greek). Characters above `U+FFFF` — emoji, rare CJK, ancient scripts — live in the **astral planes** (also called supplementary planes), and they are exactly the ones that break naive code.

### 6. UTF-8: why it won

UTF-8 encodes each code point in 1 to 4 bytes:
- 1 byte for ASCII (`U+0000`–`U+007F`) — **identical to ASCII**.
- 2 bytes for Latin accents, Greek, Cyrillic, Hebrew, Arabic.
- 3 bytes for most CJK (Chinese, Japanese, Korean).
- 4 bytes for emoji and astral characters.

UTF-8 won the web (over 98% of pages) because:
- **It is backward-compatible with ASCII** — old English text is already valid UTF-8.
- **It has no byte-order problem** (UTF-16 does; see `middle.md`).
- **It is self-synchronizing** — if you land in the middle of a file you can find the next character boundary easily.
- **It is compact for English/Western text.**

The practical advice for a junior: **use UTF-8 everywhere** — files, APIs, databases, source code — unless something forces you otherwise.

---

## Code Examples

### The "length is a lie" demo across five languages

Take the string `"a😀b"`: one ASCII letter, one astral emoji, one ASCII letter. It is **3 code points** and a human sees **3 characters**.

**JavaScript** (UTF-16 internally — counts code units):

```javascript
const s = "a😀b";
console.log(s.length);              // 4  ← WRONG for humans (😀 = 2 UTF-16 units)
console.log([...s].length);         // 3  ← spread iterates code points
console.log(s[1]);                  // "\uD83D"  ← half an emoji! a lone surrogate
console.log([...s][1]);             // "😀"       ← correct
console.log(s.codePointAt(1).toString(16)); // 1f600
```

**Java** (UTF-16 internally — `char` is a 16-bit code unit):

```java
String s = "a😀b";
System.out.println(s.length());                  // 4  ← counts UTF-16 code units
System.out.println(s.codePointCount(0, s.length())); // 3  ← counts code points
System.out.println((int) s.charAt(1));           // 55357 ← a surrogate, NOT 😀
s.chars().forEach(c -> System.out.print(c + " ")); // wrong: 97 55357 56832 98
s.codePoints().forEach(c -> System.out.print(c + " ")); // right: 97 128512 98
```

**Go** (bytes internally, but `range` decodes UTF-8 into runes):

```go
s := "a😀b"
fmt.Println(len(s))                 // 7  ← BYTES (😀 = 4 bytes in UTF-8)
fmt.Println(utf8.RuneCountInString(s)) // 3  ← code points
fmt.Println(s[1])                   // 240 ← a raw byte, not a character
for i, r := range s {               // range gives (byteIndex, rune)
    fmt.Printf("%d:%c ", i, r)      // 0:a 1:😀 5:b  ← note indices skip
}
```

**Python 3** (`str` is a sequence of code points — the friendliest model):

```python
s = "a😀b"
print(len(s))           # 3  ← code points. Python str hides bytes from you.
print(s[1])             # 😀  ← one full code point
print(ord(s[1]))        # 128512 = 0x1F600
print(len(s.encode("utf-8")))  # 6  ← bytes, only when you ask
```

**Rust** (`String` is UTF-8 bytes; `.chars()` gives code points):

```rust
let s = "a😀b";
println!("{}", s.len());                  // 6  ← BYTES (len is byte length)
println!("{}", s.chars().count());        // 3  ← code points (char = code point)
// println!("{}", &s[1..2]);              // PANIC: byte 1 is mid-emoji, not a char boundary
println!("{}", s.chars().nth(1).unwrap()); // 😀
```

**The lesson:** five languages, five different default answers (`4`, `4`, `7`, `3`, `6`) for the *same three-character string*. None of them is "the length" — each measures a different layer. Know which one your language gives you for free.

### Seeing the bytes

```python
# Python: prove that an encoding is a choice
text = "café"
print(text.encode("utf-8"))    # b'caf\xc3\xa9'   (é = 2 bytes: c3 a9)
print(text.encode("latin-1"))  # b'caf\xe9'       (é = 1 byte: e9)
print(text.encode("utf-16le")) # b'c\x00a\x00f\x00\xe9\x00'

# Decode the UTF-8 bytes as Latin-1 to manufacture mojibake:
b = text.encode("utf-8")
print(b.decode("latin-1"))     # 'cafÃ©'  ← the classic garble
```

### Safely truncating to N characters (not N bytes)

A database column is `VARCHAR(20)` and you naively cut the string to 20 *bytes*. If byte 20 lands in the middle of a multi-byte character, you write half a character.

```python
# Python: truncate by code points (safe), not bytes
def truncate_chars(s, n):
    return s[:n]            # str indexing is by code point — safe here

# But if you must fit BYTES (e.g. a fixed buffer), cut on a boundary:
def truncate_bytes(s, max_bytes):
    b = s.encode("utf-8")[:max_bytes]
    return b.decode("utf-8", errors="ignore")  # drop the broken tail
```

---

## Coding Patterns

**Pattern 1: Decode at the boundary, work in code points, encode at the boundary.** Your program's *inside* should hold decoded text (Python `str`, Go `[]rune` when needed, Java `String`). Bytes appear only at the edges: reading files, network, databases. Decode immediately on the way in, encode at the last moment on the way out. Never let raw bytes leak into business logic.

```python
raw = sock.recv(1024)              # bytes at the boundary
text = raw.decode("utf-8")         # decode immediately
result = process(text)             # work in text
sock.send(result.encode("utf-8"))  # encode at the boundary
```

**Pattern 2: Iterate by the right unit.** When you need "each character," use the code-point iterator your language provides (`for r := range s` in Go, `[...s]` in JS, `s.chars()` in Rust, plain iteration in Python). Never iterate by raw index when the string might be non-ASCII.

**Pattern 3: Specify the encoding, always.** Every `open`, every `decode`, every HTTP header, every DB connection string should name the encoding explicitly. "It defaulted to the right thing on my laptop" is how production breaks.

**Pattern 4: Use a grapheme library for user-facing length.** When you truly need "what a human counts," reach for a grapheme-aware library (`Intl.Segmenter` in JS, `unicode-segmentation` in Rust, ICU in Java) rather than rolling your own.

---

## Best Practices

1. **UTF-8 everywhere by default.** Source files, configs, APIs, storage. Make it boring and consistent.
2. **Never use `string[i]` for non-ASCII iteration.** Indexing addresses code units or bytes, not characters. Use the proper iterator.
3. **Always declare the encoding.** No `open(path)` without `encoding="utf-8"`. No HTTP response without a charset.
4. **Pick your "length" on purpose.** Bytes for storage limits, code points for algorithms, graphemes for UI counts. Comment which one and why.
5. **Use `utf8mb4`, not `utf8`, in MySQL.** The 3-byte `utf8` silently rejects emoji and 4-byte CJK.
6. **Test with non-ASCII fixtures.** Put `Müller`, `日本語`, `😀`, and `👨‍👩‍👧‍👦` in your test data from day one.
7. **Never hand-roll UTF-8/UTF-16 parsing.** The standard library is correct; your loop will have an off-by-one on the surrogate boundary.

---

## Edge Cases & Pitfalls

**The emoji that doubled.** `"😀".length` is `2` in JS and Java because 😀 is one astral code point stored as two UTF-16 code units (a surrogate pair). A character counter that uses `.length` tells the user a single emoji is two characters. Use a code-point or grapheme count.

**Reversing a string corrupts emoji.** The classic "reverse a string" interview answer (`s.split('').reverse().join('')` in JS) splits *between* the two surrogate code units of 😀, swaps them, and produces an invalid lone surrogate — a broken character. Reverse by code point (`[...s].reverse()`) at minimum; by grapheme to also keep family emoji intact.

**Mojibake from a wrong default encoding.** Reading a UTF-8 file as Latin-1 (or the OS default) turns `é` into `Ã©`. The bytes were fine; the *interpretation* was wrong. Always decode with the encoding the data was written in.

**Truncating in the middle of a character.** Cutting a UTF-8 string to N *bytes* can slice a multi-byte character in half, producing an invalid byte sequence that crashes downstream parsers. Cut on a character boundary.

**Indexing a Go or Rust string by byte.** `s[1]` in Go gives a `byte`, not a character. In Rust, slicing `&s[0..2]` *panics* if byte 2 is not a character boundary. These languages expose the byte layer directly — respect it.

**The "café" that won't match "café".** Two strings can look identical but differ in bytes because `é` was written as one code point in one and as `e` + combining accent in the other. String equality fails. This is a normalization problem — see `senior.md`.

**MySQL `utf8` is a lie.** MySQL's `utf8` is actually a maximum-3-byte encoding that cannot store emoji or some CJK. Inserting `😀` silently truncates or errors. The real UTF-8 in MySQL is named `utf8mb4`.

---

## Apply it

1. Choose one small, known input for **Character & String Internals (Unicode)**.
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

- What problem does Character & String Internals (Unicode) solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
