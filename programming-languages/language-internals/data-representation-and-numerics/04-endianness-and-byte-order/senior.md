# Endianness & Byte Order — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Endianness & Byte Order** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. How a byte swap compiles

Write the portable shift-and-mask `bswap32`, the `__builtin_bswap32` intrinsic, or `std::byteswap` — at `-O2` they **all compile to the same single instruction**:

```text
x86-64:   bswap eax           ; 32-bit reverse
ARM64:    rev   w0, w0        ; 32-bit reverse
```

The compiler pattern-matches the idiomatic shift/mask sequence and emits the hardware op. So you never need inline assembly for a swap — write the intrinsic (or even the portable C) and trust the optimizer. The portable C version exists precisely so the *one* compiler that lacks the intrinsic still gets a correct (if slightly slower) swap.

### 2. `MOVBE`: the free swap

On Intel Atom/Haswell+ there's `MOVBE` — "move big-endian" — which **loads or stores a value while reversing its bytes**, fused into the memory operation. When you do `be32toh(load)` on such a chip, the compiler can emit a single `movbe` instead of `mov` + `bswap`. The byte swap costs *nothing extra* — it rides on the load you were doing anyway. This is why "convert at the boundary" has essentially zero performance cost on modern hardware: the swap is amortized into the memory access.

### 3. Bulk swapping with SIMD

When you must byte-swap a *large array* (e.g. converting a megabyte of big-endian samples to host order), per-element `bswap` is slow. SIMD shuffles fix this. `PSHUFB` (SSSE3) reorders 16 bytes per instruction according to an index vector; AV2/AVX-512 do 32/64 bytes:

```text
shuffle mask for 4x uint32 swap (per 16-byte lane):
  3 2 1 0  7 6 5 4  11 10 9 8  15 14 13 12
```

One `vpshufb` swaps four 32-bit ints at once. With AVX2 you swap eight per instruction. This is how high-performance codecs (image decoders, columnar databases, network capture tools) convert bulk data — often 8–16× faster than scalar swaps. The compiler auto-vectorizes simple swap loops at `-O3`, but for guaranteed throughput you write the intrinsics.

### 4. Compile-time endianness detection

You want conversion code that is **a no-op on the native-order host and a single swap on the other**, decided at compile time so there's no runtime branch:

```c
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
  #define HOST_IS_LE 1
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
  #define HOST_IS_LE 0
#else
  #error "unknown byte order"
#endif
```

In C++20, prefer the standard, type-safe query:

```cpp
#include <bit>
constexpr bool host_is_le = std::endian::native == std::endian::little;
```

Because it's `constexpr`, the compiler eliminates the dead branch entirely: on a little-endian host, `host_to_be` becomes a swap with no branch; on big-endian it becomes the identity, also branchless. This is strictly better than runtime detection — same correctness, zero runtime cost, and it composes into `constexpr` serialization.

> **Why not runtime detection?** The classic `union {uint32_t i; char c[4];}` or `*(char*)&x` runtime check works but adds a branch and defeats constant folding. Use it only when you genuinely don't know the order until runtime (essentially never for a fixed target). Compile-time is the senior default.

### 5. Bi-endian architectures: what actually switches

ARM, PowerPC, MIPS, and SPARC v9 are **bi-endian**: a mode bit selects the byte order for data accesses. Critical nuances:

- The switch affects **how multi-byte loads/stores interpret memory**, not the bytes themselves. Memory is just bytes; the mode decides assembly.
- **Instructions are usually fixed-endian** regardless of the data mode (ARM instruction fetch has its own rule). So "switch to big-endian" means *data*, not *code*.
- ARM offers `SETEND BE`/`SETEND LE` (AArch32) to flip data endianness for a region — historically used to consume big-endian network data on a little-endian-configured core. AArch64 dropped `SETEND`; you use `REV` instead.
- **Almost everyone runs ARM and PowerPC little-endian today** (Linux on ARM64 is LE; even POWER moved to LE for ppc64le). Big-endian ARM/PPC exist mainly in legacy networking gear and some embedded.

The practical upshot: *don't* rely on a runtime endianness mode to do your conversions. Pin byte order in the format and convert explicitly; that works on any mode of any chip.

### 6. The historical big-endian machines (and why network order is BE)

Network byte order is big-endian because the dominant machines of the 1970s–80s — IBM mainframes, the Motorola 68000 (early Macs, Amiga, Sun), PDP-10, and later SPARC and PowerPC — were big-endian. When TCP/IP was specified, BE was the natural "neutral" choice. Then x86 (little-endian) took over the world, leaving us with the permanent friction: **hosts are LE, the wire is BE.** That mismatch is the entire reason `htonl` exists and the entire reason endianness bugs are a perennial.

| Architecture | Endianness |
|--------------|-----------|
| x86 / x86-64 | Little |
| ARM (modern Linux/macOS) | Little (bi-endian capable) |
| RISC-V | Little |
| PowerPC (classic), ppc64 | Big (ppc64le is Little) |
| SPARC | Big (v9 bi-endian) |
| Motorola 68000 | Big |
| IBM z/Architecture (mainframe) | Big |
| MIPS | Bi-endian (both deployed) |
| PDP-11 | Middle-endian (historical curiosity) |

### 7. Designing an endianness-robust format

A format is robust when an engineer *cannot* serialize it wrong:

1. **Pin one byte order in the spec, in writing.** Big-endian is conventional ("network order"); little-endian matches common hardware. Either is fine — *commit*.
2. **Provide the only sanctioned accessors.** Ship `read_be32`/`write_be32` (or a typed reader/writer class) and make the raw buffer private. No one should hand-roll a swap.
3. **Use fixed-width, fixed-order types in the schema.** Avoid native `int`/`long` whose width and order vary. Protobuf, FlatBuffers, Cap'n Proto, and CBOR all pin this.
4. **Add a magic number / version at offset 0.** A magic like `0x89504E47` (PNG's) lets you detect a wrong-endian or wrong-format read immediately — if the magic reads byte-reversed, you know.
5. **Round-trip and golden-bytes tests** in CI, ideally on both an LE and a BE target (or a simulated BE path).

### 8. Float and SIMD-vector byte order

A `float`/`double` follows host integer endianness via its IEEE-754 bit pattern — serialize through the integer (middle tier). For **SIMD vectors** and **struct-of-arrays** data, byte order applies per element; a bulk `PSHUFB` swap handles whole vectors. Beware: some file formats store a vector's *elements* in one order and the *lanes* in another — read the spec, don't assume.

### 9. Why text is the easy case (and the trap that remains)

UTF-8 is byte-order-free — its great virtue. But two traps persist at the senior level:

- **UTF-16 surrogate pairs** are each a 16-bit code unit, so each unit is endian-sensitive; a wrong byte order corrupts the whole stream, not just one character.
- **A "UTF-8 BOM" (`EF BB BF`) is not a byte-order mark** — UTF-8 has no order — it's just a signature some tools emit. It can break parsers (shebangs, JSON) that don't expect leading bytes. Strip it deliberately.

---

## Code Examples

### Branchless, compile-time host↔BE conversion (C++20)

```cpp
#include <bit>
#include <cstdint>
#include <concepts>

template <std::unsigned_integral T>
constexpr T byteswap(T v) noexcept {            // (std::byteswap in C++23)
    auto bytes = std::bit_cast<std::array<std::byte, sizeof(T)>>(v);
    std::ranges::reverse(bytes);
    return std::bit_cast<T>(bytes);
}

template <std::unsigned_integral T>
constexpr T host_to_be(T v) noexcept {
    if constexpr (std::endian::native == std::endian::big) return v;
    else return byteswap(v);                    // single REV/BSWAP, no branch
}
```

`if constexpr` removes the dead branch at compile time. On a big-endian host this is the identity; on little-endian it's one `bswap`. No runtime test, no portability `#ifdef` soup.

### Intrinsic + MOVBE-friendly load (C, GCC/Clang)

```c
#include <stdint.h>
#include <string.h>

static inline uint32_t load_be32(const void *p) {
    uint32_t v;
    memcpy(&v, p, sizeof v);          // alias/alignment safe
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    v = __builtin_bswap32(v);         // compiler may fuse into MOVBE
#endif
    return v;
}
```

On a Haswell-class CPU, `gcc -O2 -mmovbe` can compile the whole function to a single `movbe` instruction — load and swap fused.

### SIMD bulk swap of uint32 array (x86 SSSE3)

```c
#include <tmmintrin.h>   // SSSE3
#include <stddef.h>
#include <stdint.h>

// Byte-swap N uint32 values in place (N multiple of 4 for the fast path).
void bswap32_array(uint32_t *a, size_t n) {
    const __m128i mask = _mm_set_epi8(
        12,13,14,15,  8,9,10,11,  4,5,6,7,  0,1,2,3);  // reverse each 4 bytes
    size_t i = 0;
    for (; i + 4 <= n; i += 4) {
        __m128i v = _mm_loadu_si128((__m128i const*)(a + i));
        v = _mm_shuffle_epi8(v, mask);                 // PSHUFB: 4 swaps at once
        _mm_storeu_si128((__m128i*)(a + i), v);
    }
    for (; i < n; ++i) a[i] = __builtin_bswap32(a[i]); // scalar tail
}
```

One `pshufb` swaps four 32-bit ints; AVX2's `_mm256_shuffle_epi8` does eight. This is the pattern image and database codecs use for bulk byte-order conversion.

### Constexpr serialization (compile-time bytes, Rust)

```rust
// Rust's to_be_bytes is const-evaluable; the bytes can be baked at compile time.
const MAGIC: u32 = 0x8950_4E47;             // "\x89PNG"-ish
const MAGIC_BE: [u8; 4] = MAGIC.to_be_bytes(); // [0x89,0x50,0x4E,0x47] at compile time

fn check(buf: &[u8]) -> bool {
    buf.get(..4) == Some(&MAGIC_BE)
}
```

### Go — order-pinned codec boundary

```go
type Header struct {
	Magic   uint32
	Version uint16
	Length  uint32
}

func (h *Header) MarshalBE() []byte {
	b := make([]byte, 10)
	binary.BigEndian.PutUint32(b[0:], h.Magic)
	binary.BigEndian.PutUint16(b[4:], h.Version)
	binary.BigEndian.PutUint32(b[6:], h.Length)
	return b
}
func UnmarshalBE(b []byte) (Header, error) {
	if len(b) < 10 { return Header{}, io.ErrUnexpectedEOF }
	return Header{
		Magic:   binary.BigEndian.Uint32(b[0:]),
		Version: binary.BigEndian.Uint16(b[4:]),
		Length:  binary.BigEndian.Uint32(b[6:]),
	}, nil
}
```

The byte order lives *only* in the marshal/unmarshal pair; the struct fields are plain native ints everywhere else.

---

## Coding Patterns

### Pattern 1: One codec layer, native everywhere else

Confine all byte-order logic to serialize/deserialize functions. Application and domain code use plain native integers. This is the single most important structural rule.

### Pattern 2: Compile-time order selection, branchless

Use `if constexpr (std::endian::native == ...)` (C++) or `__BYTE_ORDER__` `#if` (C) so conversion folds to identity-or-single-swap with no runtime branch.

### Pattern 3: SIMD with a scalar tail

Vectorize the bulk of an array swap; always include a scalar loop for the remainder and for sizes below the vector width. Never assume the array length is a multiple of the lane count.

### Pattern 4: Magic-number sentinel

Put a known magic at offset 0 of every format. A wrong-endian or wrong-format read trips it immediately, turning a silent corruption into a loud, early failure.

---

## Best Practices

1. **Confine byte order to the serialization layer.** Native everywhere else.
2. **Detect endianness at compile time** (`std::endian::native`, `__BYTE_ORDER__`); avoid runtime branches.
3. **Write intrinsics/portable shift-and-OR, not inline asm** — the compiler emits `BSWAP`/`REV`/`MOVBE`.
4. **Use SIMD only for bulk array conversion**, always with a scalar fallback.
5. **Pin one byte order in the format spec and enforce it with private buffers + sanctioned accessors.**
6. **Add a magic number** so wrong-endian reads fail loudly and early.
7. **Use fixed-width schema types** (`uint32` not `int`), never native `int`/`long` whose size/order vary by platform.
8. **Test serialization against golden bytes in CI**, and exercise the big-endian path (a forced-swap build or a BE emulator) at least in unit tests.
9. **Treat any reliance on a runtime endianness mode (`SETEND`) as legacy** — convert explicitly instead.

---

## Edge Cases & Pitfalls

- **Assuming the swap costs measurable time.** On `MOVBE`/`REV` hardware it's effectively free; "I skipped conversion for speed" is almost always a false economy that buys only bugs.
- **Forgetting the SIMD scalar tail.** A swap loop that handles only full vectors silently skips the last 1–3 elements.
- **Relying on auto-vectorization.** `-O3` *may* vectorize a swap loop, but compiler/version differences mean you can't count on it for guaranteed throughput — write intrinsics when it matters.
- **Confusing instruction vs data endianness on bi-endian chips.** Switching data mode does not byte-swap the instruction stream; reasoning about "switch to BE" without that distinction leads to wrong mental models.
- **`ppc64` vs `ppc64le` mismatch.** Building for the wrong PowerPC ABI flips byte order silently. Match the toolchain triple.
- **The "UTF-8 BOM" breaking parsers.** `EF BB BF` is not a byte-order mark; it can corrupt shebang lines, JSON, and CSV headers. Strip it explicitly on ingest.
- **`std::bit_cast`/`memcpy` for float reinterpret, not a cast.** Type-punning a float through a `uint32_t*` is still strict-aliasing UB at this tier too; use `bit_cast`/`memcpy`.
- **Zero-copy mmap formats are endianness-locked.** If you mmap a file and read native ints directly for speed, the file is only readable on hosts of that endianness. That's a legitimate trade-off — but document it loudly; it's a portability landmine otherwise.

---

## Apply it

1. State the system invariant that **Endianness & Byte Order** must protect.
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

- Which invariant must remain true when Endianness & Byte Order fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
