# Endianness & Byte Order — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Endianness & Byte Order** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Byte-swapping, concretely

To convert a value between big- and little-endian you **reverse its bytes**. For a 32-bit value `0x12345678`:

```text
before:  12 34 56 78
after:   78 56 34 12
```

By hand, with shifts and masks:

```c
uint32_t bswap32(uint32_t v) {
    return ((v & 0x000000FFu) << 24) |
           ((v & 0x0000FF00u) <<  8) |
           ((v & 0x00FF0000u) >>  8) |
           ((v & 0xFF000000u) >> 24);
}
```

This is portable but verbose. Every CPU since the 1990s has a single instruction for it: x86 `BSWAP`, ARM `REV`. Compilers expose it as `__builtin_bswap32` (GCC/Clang), `_byteswap_ulong` (MSVC), and — finally standardized — `std::byteswap` in C++23. **Use the intrinsic**; the compiler emits the one-instruction version, and your code says what it means.

### 2. The crucial distinction: swap vs. convert

A naked byte swap is **unconditional** — it always reverses bytes. But you usually don't want "always swap"; you want "make this big-endian regardless of my host." Those are different:

```text
host_to_be(x):  if host is big-endian   -> do nothing
                if host is little-endian -> swap
```

`htonl` encodes exactly this conditional. On a big-endian host, `htonl` is the identity function; on little-endian it swaps. **That's why you call `htonl` and not `bswap` directly** — `htonl` does the right thing on *any* host, while a hardcoded swap would be wrong on a big-endian machine. Modern libraries (Go's `binary.BigEndian`, Rust's `to_be_bytes`) bake this conditional in so you never think about your host's endianness at all.

### 3. Trap #1 — Endianness: the pointer cast lies

```c
uint32_t v = *(uint32_t *)buf;   // interprets buf in NATIVE order
```

This reads the four bytes at `buf` using your CPU's native endianness. If `buf` holds big-endian wire data and you're on little-endian x86, `v` is byte-reversed garbage. The cast has *no knowledge* of the data's intended order — it just reinterprets raw memory. **Always convert explicitly after loading**, or better, load with an order-aware idiom.

### 4. Trap #2 — Alignment: the address might be illegal

A `uint32_t` typically must live at an address divisible by 4. But `buf + offset` is an arbitrary byte offset into a packet — `offset` could be 3, 7, 13. Dereferencing a `uint32_t*` at an unaligned address is:

- On x86: **allowed but slower** (the hardware tolerates it).
- On older ARM, SPARC, MIPS: a **bus error / SIGBUS** — your program crashes.
- In the C standard: **undefined behavior**, full stop, even on x86.

This is why `*(uint32_t*)(buf+3)` is a portability time bomb: it works on your dev laptop and crashes on an embedded target. The `memcpy` idiom (below) sidesteps it because `memcpy` handles arbitrary alignment.

### 5. Trap #3 — Strict aliasing: the optimizer may miscompile you

C and C++ assume that pointers of *different* types don't point at the same memory (except `char*`, which may alias anything). This lets the optimizer reorder and cache loads. When you do `*(uint32_t*)buf` where `buf` is a `char*`/`uint8_t*`, you're accessing a region "as a `uint32_t`" that was never created as one. That **violates strict aliasing** and is undefined behavior — the compiler is free to assume the `uint32_t` write and a nearby `char` write don't interact and reorder them, producing wrong results under `-O2`. The bug is invisible at `-O0` and appears only in optimized builds, which is the worst kind.

### 6. The fix for all three: `memcpy`

```c
uint32_t load_be32(const uint8_t *buf) {
    uint32_t v;
    memcpy(&v, buf, sizeof v);     // alias-safe, alignment-safe, no UB
    return be32toh(v);             // then convert to host order
}
```

`memcpy(&v, buf, 4)`:

- is **alias-safe** — copying through `char`-level access is always legal;
- is **alignment-safe** — `memcpy` works at any address;
- **compiles to nothing** under optimization — GCC/Clang recognize the pattern and emit a single (possibly unaligned) load, exactly as fast as the unsafe cast.

So you pay *zero* runtime cost for correctness. This is the idiom to internalize. Then layer the endianness conversion (`be32toh`, `__builtin_bswap32`, etc.) on top.

### 7. Even simpler: shift-and-OR (no host endianness involved at all)

```c
uint32_t read_be32(const uint8_t *b) {
    return ((uint32_t)b[0] << 24) | ((uint32_t)b[1] << 16) |
           ((uint32_t)b[2] <<  8) | ((uint32_t)b[3]);
}
```

This reads bytes **one at a time** (single-byte access is always aligned and always alias-legal) and assembles the value by **place value**. It is *independent of host endianness* — it produces the same big-endian interpretation on any machine, with no swap, no `htonl`, no UB. It's the most robust idiom and what most hardened parsers use. The compiler still optimizes it to a load+bswap.

### 8. Floats have endianness too

A `float` is 4 bytes, a `double` is 8 — and their bytes are ordered by the *same* endianness as integers on virtually all platforms (IEEE-754 layout, host byte order). So to serialize a float portably you **reinterpret it as an integer of the same size, then byte-swap the integer**:

```c
uint32_t bits;
memcpy(&bits, &my_float, 4);     // grab the float's bit pattern (alias-safe)
bits = htonl(bits);              // put it in big-endian
// write bits...
```

Do **not** byte-swap a `float` "as a float" — there's no such operation. Always go through its integer bit pattern. (A rare historical caveat: a few oddball architectures stored float and integer bytes in different orders, but you'll almost never meet one.)

### 9. UTF-16/32 and the BOM

Text in UTF-16 or UTF-32 is a sequence of 2- or 4-byte code units, so it has endianness. A file may start with a **BOM** (`U+FEFF`):

```text
FE FF        -> UTF-16 big-endian
FF FE        -> UTF-16 little-endian
00 00 FE FF  -> UTF-32 big-endian
FF FE 00 00  -> UTF-32 little-endian
```

If the BOM is absent, you must guess (often defaulting to big-endian per the Unicode standard, or detecting via heuristics). **UTF-8 has no endianness** and needs no BOM (though Windows tools sometimes prepend `EF BB BF` as a signature — which is *not* a byte-order mark, just an annoyance).

### 10. Bitfield order is a *separate*, also-implementation-defined problem

A C struct bitfield like `struct { unsigned a:4; unsigned b:4; };` packs sub-byte fields, and **the order in which fields fill a byte (and how they straddle byte boundaries) is implementation-defined** — *independent* of byte endianness. Two compilers, or the same compiler on BE vs LE, can lay out bitfields differently. **Never use bitfields to parse a wire protocol.** Read the byte, then extract bits with explicit shifts and masks (`(byte >> 4) & 0xF`). This gives you a layout you actually control.

---

## Code Examples

### The full, correct big-endian reader/writer (C)

```c
#include <stdint.h>
#include <string.h>

// Read a 32-bit big-endian value from any offset, no UB:
static uint32_t get_be32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] <<  8) | ((uint32_t)p[3]);
}

// Write a 32-bit big-endian value to any offset:
static void put_be32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >>  8);
    p[3] = (uint8_t)(v);
}
```

No casts, no alignment requirement, no aliasing issue, correct on every machine. This is the gold standard for hand-written parsers.

### Using the platform conversion + memcpy (C, Linux/BSD)

```c
#include <endian.h>   // be32toh, htobe32 (glibc)
#include <string.h>
#include <stdint.h>

uint32_t load_be32(const void *buf) {
    uint32_t raw;
    memcpy(&raw, buf, sizeof raw);  // safe load in host order
    return be32toh(raw);            // convert big-endian -> host
}
```

`be32toh` is `htonl`'s clearer cousin: "big-endian 32 to host." On a big-endian host it's a no-op; on little-endian it swaps.

### `htonl`/`ntohl` for sockets (POSIX)

```c
#include <arpa/inet.h>  // htonl, ntohl, htons, ntohs

uint32_t addr_host = 0x0A000001;          // 10.0.0.1 in host order
uint32_t addr_net  = htonl(addr_host);    // big-endian for the wire
// ... send addr_net ...
uint32_t back = ntohl(addr_net);          // back to host order
```

### Go — explicit, no host-order footgun

```go
import "encoding/binary"

func loadBE32(buf []byte) uint32 { return binary.BigEndian.Uint32(buf) }
func storeBE32(v uint32) []byte {
    b := make([]byte, 4)
    binary.BigEndian.PutUint32(b, v)
    return b
}
```

Go's `binary.BigEndian.Uint32` already handles unaligned slices and never assumes host order. There is no unsafe cast to misuse.

### Rust — order in the method name

```rust
fn load_be32(buf: &[u8; 4]) -> u32 { u32::from_be_bytes(*buf) }
fn store_be32(v: u32) -> [u8; 4]    { v.to_be_bytes() }

// From a &[u8] slice of unknown length, with a length check:
fn read_be32(s: &[u8]) -> Option<u32> {
    let arr: [u8; 4] = s.get(..4)?.try_into().ok()?;
    Some(u32::from_be_bytes(arr))
}
```

`from_be_bytes` takes a fixed-size array, so the length and alignment concerns are handled by the type system. There's no aliasing UB possible.

### Float serialization (correct, via integer bits)

```c
#include <string.h>
#include <stdint.h>
#include <arpa/inet.h>

void put_be_float(uint8_t *out, float f) {
    uint32_t bits;
    memcpy(&bits, &f, sizeof bits);  // reinterpret bits, alias-safe
    bits = htonl(bits);              // big-endian
    memcpy(out, &bits, sizeof bits);
}
```

```rust
// Rust makes float byte order explicit too:
let f: f32 = 3.14;
let be: [u8; 4] = f.to_be_bytes();         // big-endian bytes
let back = f32::from_be_bytes(be);
```

### The bug to recognize in review (C)

```c
// THREE bugs in one line — flag this in any code review:
struct hdr { uint32_t len; uint16_t typ; };
struct hdr *h = (struct hdr *)buf;   // cast over a wire buffer
uint32_t n = h->len;                 // native order + alignment + aliasing UB
```

The fix: read each field with `get_be32`/`get_be16` at explicit offsets. Never overlay a struct on a wire buffer.

---

## Coding Patterns

### Pattern 1: Tiny accessor functions per width/order

Define `get_be16`, `get_be32`, `get_be64` (and `le` variants) once, in one header, and call them everywhere. Centralizing the idiom means the tricky code exists in exactly one reviewed place.

### Pattern 2: Bounds-check before every read

```c
if (offset + 4 > len) return PARSE_ERR;   // never read past the buffer
uint32_t v = get_be32(buf + offset);
offset += 4;
```

Endianness bugs and buffer-overrun bugs cluster in the same parsing code. Check length *before* every multi-byte read.

### Pattern 3: Extract bitfields with shifts, never C bitfields

```c
uint8_t flags = buf[12];
uint8_t version = (flags >> 4) & 0x0F;   // explicit, portable
uint8_t mode    =  flags       & 0x0F;
```

You control the layout; the compiler's bitfield order can't surprise you.

---

## Best Practices

1. **Never cast a struct pointer over a wire/file buffer.** Read fields individually with order-explicit accessors.
2. **Use `memcpy` (or shift-and-OR), never `*(T*)`,** to load scalars from byte buffers — kills alignment and aliasing UB at no runtime cost.
3. **Convert with order-aware functions** (`htonl`/`be32toh`/`binary.BigEndian`/`to_be_bytes`), not bare `bswap`, so the code is correct on any host.
4. **Serialize floats via their integer bit pattern**, then byte-swap the integer.
5. **Never parse protocol fields with C bitfields** — extract bits manually.
6. **Bounds-check before every multi-byte read.**
7. **Round-trip test against golden bytes** — assert the exact hex output of your serializer, not just write-then-read equality.
8. **Compile with `-Wall -Wcast-align`** and consider `-fno-strict-aliasing` only as a crutch, not a cure — fix the idiom instead.

---

## Edge Cases & Pitfalls

- **The cast works on your laptop, crashes on the target.** Unaligned `*(uint32_t*)` is fine on x86 and SIGBUS on ARMv5/SPARC. "Works on my machine" is not portability.
- **The `-O2`-only bug.** Strict-aliasing violations are invisible at `-O0` and miscompile at `-O2`. If a parser works in debug and breaks in release, suspect aliasing.
- **Forgetting that `htonl` is conditional.** Replacing `htonl(x)` with a hardcoded `bswap32(x)` is correct on little-endian and *wrong* on big-endian hosts. Don't.
- **Swapping a float "as a float."** There's no such thing; you must go through the integer bit pattern. Treating the float's bytes directly often invokes signaling-NaN traps or just confuses readers.
- **Mixing up 16/32/64 widths.** Calling `ntohl` (32-bit) on a 16-bit field reads two extra bytes. Match the width.
- **PDP-11 / middle-endian.** Historically, the PDP-11 stored a 32-bit value as two 16-bit words in *big-endian word order* but *little-endian byte order within each word* — `0x12345678` became `34 12 78 56`. You won't meet a PDP-11, but the term "middle-endian" survives, and *some* protocols/formats still order multi-word fields surprisingly. Read the spec.
- **BOM in the middle of a stream.** A `U+FEFF` is only a BOM at the *start*; elsewhere it's a zero-width no-break space. Strip it only at position 0.
- **Single bytes have no order.** `uint8_t`, ASCII chars, and `bool` need no conversion. Don't `htons` a byte.

---

## Apply it

1. Find a real component where **Endianness & Byte Order** affects an interface or dependency.
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

- Which boundary is most affected by Endianness & Byte Order?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
