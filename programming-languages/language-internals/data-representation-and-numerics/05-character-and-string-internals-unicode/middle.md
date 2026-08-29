# Character & String Internals (Unicode) — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Character & String Internals (Unicode)** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. UTF-8: the bit pattern, derived

UTF-8 distributes a code point's bits across 1 to 4 bytes using a fixed template. The number of leading `1` bits in the first byte tells you the length; continuation bytes always start `10`.

| Code point range | Bytes | Bit template |
|------------------|-------|--------------|
| `U+0000`–`U+007F` | 1 | `0xxxxxxx` |
| `U+0080`–`U+07FF` | 2 | `110xxxxx 10xxxxxx` |
| `U+0800`–`U+FFFF` | 3 | `1110xxxx 10xxxxxx 10xxxxxx` |
| `U+10000`–`U+10FFFF` | 4 | `11110xxx 10xxxxxx 10xxxxxx 10xxxxxx` |

The `x` bits hold the code point, most-significant first. Worked example, `U+1F600` (😀):

```
U+1F600 = 0001 1111 0110 0000 0000  (21 bits)
Needs 4 bytes (template gives 3+6+6+6 = 21 payload bits).
Spread the bits into 11110xxx 10xxxxxx 10xxxxxx 10xxxxxx:

  bits:    000   011111   011000   000000
  byte 0:  11110 000  = 0xF0
  byte 1:  10  011111  = 0x9F
  byte 2:  10  011000  = 0x98
  byte 3:  10  000000  = 0x80

UTF-8 of 😀 = F0 9F 98 80
```

You can decode by hand: see `0xF0` (`11110...`), so it is a 4-byte sequence; collect the 3 + 6 + 6 + 6 payload bits and reassemble. **No lookup table is needed** — the bytes are self-describing.

### 2. Why UTF-8 is self-synchronizing

Because lead bytes never look like continuation bytes (`0xxxxxxx`, `11...` vs `10xxxxxx`), you can drop into the middle of a UTF-8 stream and find the next character: skip backward or forward over `10xxxxxx` bytes until you hit a lead byte. A single corrupted or lost byte costs you *one* character, not the rest of the stream. This is a major reason UTF-8 won: it is robust to truncation, concatenation at arbitrary points, and corruption.

### 3. The 16-bit problem and surrogate pairs

UTF-16 uses 16-bit code units. But Unicode has code points up to `U+10FFFF`, which needs 21 bits — too many for one 16-bit unit. The solution: reserve a block of the BMP — `U+D800`–`U+DFFF`, 2048 code points — declare it **off-limits to real characters forever**, and use it as machinery. Code points above `U+FFFF` are encoded as two of these reserved units:

```
To encode code point C (where C ≥ 0x10000) as a surrogate pair:
  C' = C - 0x10000                  (now 0..0xFFFFF, 20 bits)
  high = 0xD800 + (C' >> 10)        (top 10 bits)  → 0xD800..0xDBFF
  low  = 0xDC00 + (C' & 0x3FF)      (bottom 10 bits) → 0xDC00..0xDFFF

Example, 😀 = U+1F600:
  C' = 0x1F600 - 0x10000 = 0x0F600 = 0000111101 1000000000
  high = 0xD800 + 0b0000111101 = 0xD83D
  low  = 0xDC00 + 0b1000000000 = 0xDE00
  UTF-16 of 😀 = D83D DE00
```

This is exactly why `"😀"` has `.length === 2` in JavaScript and Java: it is *two* 16-bit code units. The reserved range is what makes pairs unambiguous — a `0xD83D` can *only* be a high surrogate, never a standalone character, so a decoder always knows it must be followed by a low surrogate.

### 4. The `D800–DFFF` hole exists in UTF-8 too

Because surrogates are not real characters, **no valid encoding may produce them as code points**. Valid UTF-8 must never encode `U+D800`–`U+DFFF`; a 3-byte sequence that decodes to a surrogate is invalid UTF-8. This is the difference between "code points" and "Unicode scalar values": a scalar value is any code point *except* the surrogate range. Rust's `char` type is precisely a scalar value, which is why Rust strings can never contain unpaired surrogates and why `OsString` on Windows needs the WTF-8 escape hatch.

### 5. UTF-32: simple but wasteful

UTF-32 stores each code point in a fixed 32 bits. Indexing is O(1) and there are no surrogates or variable widths. But it wastes 4 bytes for an ASCII `A` and 4 bytes for everything, making it 4× larger than UTF-8 for English text. It is used internally (Python's PEP 393 may pick a 4-byte representation; some C `wchar_t` platforms) but almost never on the wire or on disk. Its one virtue — constant-time indexing — is rarely worth the memory.

### 6. The BOM (Byte Order Mark)

`U+FEFF` (zero-width no-break space) can be placed at the start of a file as a Byte Order Mark:

| Encoding | BOM bytes |
|----------|-----------|
| UTF-8 | `EF BB BF` |
| UTF-16 BE | `FE FF` |
| UTF-16 LE | `FF FE` |
| UTF-32 BE | `00 00 FE FF` |
| UTF-32 LE | `FF FE 00 00` |

For UTF-16/32, the BOM solves a real problem: a 16-bit unit can be stored big-endian or little-endian, and `FE FF` vs `FF FE` tells the reader which. For **UTF-8 the BOM is pointless** — UTF-8 has no byte-order ambiguity (its units are single bytes) — yet Windows tools love to prepend `EF BB BF`. That phantom 3-byte prefix is a frequent bug: it makes a JSON file start with invisible bytes, breaks shell scripts whose first line must be `#!/bin/sh`, and shows up as a stray `﻿` character in the parsed string.

---

## Code Examples

### Decode UTF-8 by hand, in code

```python
def decode_utf8_first_char(b: bytes):
    """Return (code_point, num_bytes) for the first character in b."""
    b0 = b[0]
    if b0 < 0x80:                       # 0xxxxxxx
        return b0, 1
    elif b0 >> 5 == 0b110:              # 110xxxxx
        cp = (b0 & 0x1F) << 6 | (b[1] & 0x3F)
        return cp, 2
    elif b0 >> 4 == 0b1110:             # 1110xxxx
        cp = (b0 & 0x0F) << 12 | (b[1] & 0x3F) << 6 | (b[2] & 0x3F)
        return cp, 3
    elif b0 >> 3 == 0b11110:            # 11110xxx
        cp = (b0 & 0x07) << 18 | (b[1] & 0x3F) << 12 | (b[2] & 0x3F) << 6 | (b[3] & 0x3F)
        return cp, 4
    raise ValueError("invalid lead byte")

print(decode_utf8_first_char(b"\xf0\x9f\x98\x80"))  # (128512, 4)  → U+1F600 😀
print(hex(128512))                                   # 0x1f600
```

### Surrogate-pair conversion (UTF-16)

```javascript
// Encode a code point to a surrogate pair, then read it back.
function toSurrogatePair(cp) {
  if (cp <= 0xFFFF) return [cp];          // BMP: single unit
  cp -= 0x10000;
  const high = 0xD800 + (cp >> 10);
  const low  = 0xDC00 + (cp & 0x3FF);
  return [high, low];
}
console.log(toSurrogatePair(0x1F600).map(x => x.toString(16))); // ["d83d", "de00"]

// The correct, surrogate-aware way to get characters in JS:
const s = "a😀b";
console.log(s.length);                 // 4   ← code units
console.log([...s].length);            // 3   ← code points (iterator is surrogate-aware)
console.log(s.codePointAt(1).toString(16)); // "1f600"  ← reads the WHOLE pair at index 1
console.log(s.charCodeAt(1).toString(16));  // "d83d"   ← reads only the high surrogate
```

### Detecting and stripping a BOM

```python
data = open("maybe_bom.txt", "rb").read()
if data.startswith(b"\xef\xbb\xbf"):
    print("UTF-8 BOM present")
    data = data[3:]                    # strip it before parsing

# Or decode with a codec that eats the BOM if present:
text = data.decode("utf-8-sig")        # 'utf-8-sig' transparently removes a UTF-8 BOM
```

### Walking a UTF-8 string by character boundary (Rust)

```rust
let s = "a😀b";
// Byte indices of character starts:
for (i, c) in s.char_indices() {
    println!("byte {} -> {:?}", i, c);  // 0->'a'  1->'😀'  5->'b'
}
// Slicing must land on a boundary or it PANICS:
// let _ = &s[2..3];                    // panic: byte index 2 is not a char boundary
let head = &s[..1];                     // OK: "a"
let tail = &s[5..];                     // OK: "b"
```

### Validating that bytes are well-formed UTF-8

```go
import "unicode/utf8"

raw := []byte{0xF0, 0x9F, 0x98, 0x80}   // 😀
fmt.Println(utf8.Valid(raw))            // true
bad := []byte{0xC0, 0x80}               // overlong encoding of U+0000 — illegal
fmt.Println(utf8.Valid(bad))            // false
// utf8.DecodeRune returns RuneError (U+FFFD) and width 1 on invalid input:
r, size := utf8.DecodeRune(bad)
fmt.Printf("%U size=%d\n", r, size)     // U+FFFD size=1
```

---

## Coding Patterns

**Pattern 1: Length is a header, not a guess.** When parsing UTF-8 manually, read the lead byte, derive the length, then read exactly that many continuation bytes and validate each is `10xxxxxx`. Reject anything that breaks the pattern as invalid input — do not "best effort" guess.

**Pattern 2: Convert at the API boundary, not in a loop.** If you must move between UTF-8 and UTF-16 (e.g. calling a Windows API), convert the whole string once at the boundary with the platform function, not character-by-character.

**Pattern 3: Treat the BOM as a transport detail.** Strip it on read (`utf-8-sig`, or check the first 3 bytes), and do not emit it for UTF-8 unless a consumer specifically requires it.

**Pattern 4: Use `U+FFFD` for invalid input, deliberately.** The standard "replacement character" `�` (`U+FFFD`) is the conventional way to represent undecodable bytes. Decide whether your context wants to *replace* (lenient) or *reject* (strict) invalid sequences — and never silently drop bytes, which hides corruption.

---

## Best Practices

1. **Default to UTF-8 for storage and transport.** Reserve UTF-16/32 for in-memory interop where an API forces it.
2. **Never emit a UTF-8 BOM** unless a downstream consumer explicitly requires one; strip incoming BOMs.
3. **Validate untrusted UTF-8 strictly** — reject overlong encodings, surrogate-range encodings, and truncated sequences. Lenient decoders are a security surface (see `professional.md`).
4. **Use `codePointAt` / iterators, not `charCodeAt` / raw indexing**, when you need actual characters in UTF-16 languages.
5. **Remember surrogate pairs exist** in every Java/JS/.NET string operation involving emoji or astral characters.
6. **Document whether your "length" is bytes, code units, or code points** at every API boundary.
7. **Trust the standard library** for encoding/decoding; hand-rolled UTF-8 loops are a classic source of off-by-one and overlong bugs.

---

## Edge Cases & Pitfalls

**Overlong encodings.** UTF-8 requires the *shortest* encoding of a code point. `0xC0 0x80` could naively decode to `U+0000` but uses 2 bytes for something that needs 1 — it is illegal. Lenient decoders that accept it open security holes (a NUL byte smuggled past a filter that only checked for raw `0x00`). Always reject overlong forms.

**Encoding a surrogate.** A 3-byte UTF-8 sequence decoding to `U+D83D` is invalid — surrogates are not scalar values. Some sloppy serializers emit these ("CESU-8" or careless UTF-8); strict decoders must reject them.

**Lone surrogates in UTF-16.** Slicing a JS/Java string between the two units of a pair yields a string containing one unpaired surrogate. It is technically not valid Unicode text and may serialize to `U+FFFD` or throw when you try to write it as UTF-8.

**`charCodeAt` vs `codePointAt`.** `charCodeAt(i)` returns a single UTF-16 unit (a surrogate, for astral chars); `codePointAt(i)` returns the full code point if `i` is at the start of a pair. Mixing them up reads half a character.

**The phantom BOM character.** `"﻿".length === 1` and it is *invisible*. A UTF-8 file with a BOM, decoded normally, yields a string starting with `﻿`. `JSON.parse` chokes; string `==` comparisons fail; a CSV header `Name` becomes `﻿Name`. Strip it.

**Assuming UTF-16 is fixed-width.** A persistent myth: "Java/JS strings are 2 bytes per char." False since Unicode 2.0 (1996). Any code that does `for (i = 0; i < s.length(); i++) process(s.charAt(i))` and treats each `char` as a complete character is broken for emoji and astral text.

**Byte length ≠ code unit length ≠ code point count.** For `"😀"`: 4 bytes (UTF-8), 2 code units (UTF-16), 1 code point. A length check that uses one number where another is meant rejects valid input or accepts oversized input.

---

## Apply it

1. Find a real component where **Character & String Internals (Unicode)** affects an interface or dependency.
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

- Which boundary is most affected by Character & String Internals (Unicode)?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
