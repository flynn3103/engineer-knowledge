# Data Marshalling & Memory Layout — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Data Marshalling & Memory Layout** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## String Impedance in Production

Strings are the single most common source of production marshalling bugs, because four runtimes have four incompatible string representations and there is no universal answer.

### The four representations

| Side | In-memory form | Terminator | Encoding |
|------|----------------|-----------|----------|
| **C** | `char*` | NUL (`\0`) marks the end | Convention — UTF-8 on modern Unix, often a legacy code page on old Windows |
| **C (Windows wide)** | `wchar_t*` / `LPWSTR` | NUL (`\0\0`) | UTF-16LE |
| **Rust** | `String`/`&str` = (ptr, len) | **none** | UTF-8 (guaranteed valid) |
| **Go** | `string` = (ptr, len) | **none** | UTF-8 |
| **Java** | `String` (char[] of UTF-16 code units + length) | none | UTF-16 internally; JNI gives "modified UTF-8" |
| **Python 3** | `str` (abstract text) vs `bytes` (raw) | none | `str` is decoded; `bytes` is your raw channel |
| **C#/.NET** | `string` (UTF-16 code units) | none | UTF-16 internally |

Three independent decisions live in every string crossing: **termination** (NUL vs length-counted), **encoding** (UTF-8 vs UTF-16 vs legacy), and **ownership of a returned string** (who frees it, with what). Getting any one wrong is a distinct production bug class — mojibake, truncation, leak, or crash.

### The transcoding obligations

- **Rust/Go → C:** append a NUL (`CString::new`, `C.CString`). Both are already UTF-8, so UTF-8 C APIs are friendly. Reading a C `char*` *back* into Rust requires validating UTF-8 (`CStr::to_str` can fail on invalid bytes) — don't `unwrap()` on untrusted input; use `to_string_lossy` if you must accept anything.
- **Java/.NET → C:** transcode UTF-16 → UTF-8 (Unix) or → UTF-16 wide (Windows). `CharSet.Utf8`/`CharSet.Unicode` in .NET; `GetStringUTFChars` in JNI gives modified UTF-8 (where U+0000 is encoded as two bytes and supplementary characters as surrogate pairs — *not* standard UTF-8, a real interop trap with non-BMP characters).
- **Python → C:** explicitly `.encode("utf-8")` a `str` into `bytes`; `ctypes` `c_char_p` accepts `bytes`, never `str`. Reading back: `c_char_p(...).value` yields `bytes`; you `.decode()` it.

### Windows wide vs narrow

The Win32 API ships every function in two forms: `...A` (ANSI/narrow, code-page-dependent `char*`) and `...W` (wide, UTF-16 `wchar_t*`). The `W` form is the correct one for Unicode; the `A` form mangles anything outside the active code page. `wchar_t` is **2 bytes on Windows** but **4 bytes on Unix** — so `wchar_t`-based marshalling is itself non-portable. Marshal Windows wide strings as explicit UTF-16, not as "the platform `wchar_t`."

### Who frees a returned `char*` — the question that crashes programs

When C returns a `char*`, you must know its ownership before touching it:

- **Library-owned / static (do NOT free).** `strerror`, `getenv`, `inet_ntoa`, and many "return a pointer to internal state" functions hand you a pointer you must **never** free and must copy *before the next call* (some reuse a static buffer). Freeing it crashes; the program may run for hours and then die when the bad free corrupts the freelist.
- **Callee-allocated, caller frees with a paired function.** `sqlite3_mprintf` → `sqlite3_free`, `g_strdup` → `g_free`. The library allocated with *its* allocator; you must free with *its* free, not libc `free`.
- **Callee-allocated with libc `malloc`, caller frees with libc `free`.** Documented as such (e.g. POSIX `strdup`). Only then is plain `free` correct.

> The single most expensive string rule: **the `char*` you must NOT free.** Calling `free` on a static or library-internal buffer is undefined behavior that frequently corrupts the heap silently and crashes elsewhere. When the docs are unclear, the safe default is "do not free, copy it out immediately."

### Freeing a Rust string with C `free` — why it crashes

A `CString::into_raw()` pointer was allocated by **Rust's global allocator**. Passing it to C's `free()` is undefined behavior: the two allocators maintain different metadata (different freelists, arena headers, size classes), and libc's `free` reads metadata that Rust never wrote. The result is usually heap corruption that detonates on a *later, unrelated* allocation. The rule is iron: a `CString::into_raw` pointer must come back to Rust via `CString::from_raw` to be dropped by Rust's allocator. Symmetrically, a C `malloc`'d pointer must go to C's `free`, never be wrapped in a Rust `CString` and dropped. The allocator that created it is the only one that may free it.

---

## The Allocator Boundary: Who Frees What

Underneath every ownership convention is one law: **memory from allocator X is freed by allocator X.** The boundary is invisible to the type system, so you encode it by hand.

### Why crossing the boundary corrupts, not errors

Allocators store bookkeeping (size, freelist links, arena/heap headers) adjacent to or alongside each block, and that metadata layout is allocator-specific. When the wrong allocator frees a block, it interprets foreign metadata as its own — pushing a bogus block onto its freelist, decrementing a count that was never incremented, or writing a coalescing header into live data. The corruption is *silent at the point of the bad free*; it surfaces on the next allocation or free that touches the poisoned structure, which is why these crashes have stack traces that point at innocent code.

### The conventions, restated for production

| Convention | Free with | Common real APIs |
|------------|-----------|------------------|
| You allocated it | Your allocator | A buffer you `malloc`'d and passed in |
| Library allocated, gave a paired free | The paired free | `sqlite3_free`, `g_free`, `CoTaskMemFree`, `curl_free` |
| Library owns it (static/internal) | Nothing — never free | `strerror`, `dlerror`, `gai_strerror` |

The professional habit: **before writing the binding, find the ownership statement in the docs for every returned pointer.** If the docs don't say, treat it as library-owned and copy out — guessing "probably `malloc`" is how heaps get corrupted.

### .NET's `Marshal` allocator pitfalls

When .NET marshals a managed string to native, *it* allocates the native copy. If a native function returns a string the .NET runtime allocated (e.g. via `Marshal.StringToHGlobalAnsi`), you free it with `Marshal.FreeHGlobal`. COM-allocated strings use `Marshal.FreeCoTaskMem`. Mixing these — or calling libc `free` on a `Marshal`-allocated block — is the same allocator-mismatch bug in .NET clothing.

---

## GC Moved the Buffer: Pinning and Keep-Alive Under Load

The most insidious marshalling bug class is the one that *passes every test* and *crashes under load*, because it depends on a garbage collection happening at a specific instant — which tests rarely trigger and production constantly does.

### Forgetting to pin → GC moves the buffer

In a moving collector (HotSpot, .NET, Go), you take the address of a managed array, hand it to C, and during the call the GC runs and *relocates the array to defragment the heap*. C is now writing to (or reading from) the array's *old* location — freed-or-reused memory. The symptom: intermittent corruption or crashes that scale with GC pressure (i.e. with load), are unreproducible locally, and "go away" when you add logging (because the logging changed allocation timing). The fix is to pin for the call's duration:

```csharp
// WRONG: GCHandle not pinned, or no pin at all — GC may move `data` mid-call.
static unsafe void BrokenFill(byte[] data) {
    fixed (byte* _ = data) { }            // pin ends immediately — useless
    NativeFill(GetUnsafePtr(data), data.Length); // C touches a movable array
}

// RIGHT: pin spans the whole native use.
static unsafe void Fill(byte[] data) {
    fixed (byte* p = data) {              // pinned for the block
        NativeFill(p, data.Length);
    }                                      // unpinned after C is done
}
```

In Java the equivalent is doing real work between `GetPrimitiveArrayCritical` and `Release` *correctly*, or — worse — caching the critical pointer past the `Release`, which is a use-after-unpin. In Go it's letting C retain a Go pointer past the call, which the cgo checker may not always catch.

### `GC.KeepAlive` keeping an object alive across a call

Distinct from movement is *collection*. If the only managed reference to an object is one the JIT can prove is dead (its last managed use already happened), the GC may collect it — even while C holds a pointer derived from it. This bites when C retains a buffer or context:

```csharp
var buffer = new byte[1 << 20];
IntPtr ctx = native_register(buffer);   // C stores a pointer into `buffer`
ProcessAsync(ctx);                       // buffer has no further managed use here
GC.KeepAlive(buffer);                    // <-- without this, GC may collect buffer
                                         //     while native code still reads it
```

`GC.KeepAlive` does nothing at runtime except be an unconditional "use" of `buffer` at that point, forcing the JIT to keep it reachable until then. It does *not* pin (the object can still move) — so for a *retained* pointer you typically need a pinned `GCHandle` (stable address) *and* a live reference (no collection), and `KeepAlive` covers the latter for stack-rooted cases. This is a shipped-in-production bug class, especially with `delegate`/callback contexts whose lifetime exceeds the registering method.

### The non-moving exception

CPython's reference-counting collector never moves objects, so there's no pinning concern — only lifetime. Keep a Python reference (refcount > 0) for as long as C holds the pointer. The trap there is subtler: a temporary that the interpreter drops at the end of the statement (`lib.f(make_buffer())`) can free the buffer before C is done if C retains it — bind it to a name that outlives the native use.

---

## Numeric and Boolean Width Traps

### The LP64 / LLP64 `long` trap

The two dominant 64-bit data models disagree on `long`:

| Model | Platforms | `int` | `long` | pointer |
|-------|-----------|-------|--------|---------|
| **LP64** | 64-bit Linux, macOS, BSD | 32 | **64** | 64 |
| **LLP64** | 64-bit Windows | 32 | **32** | 64 |

So a C `long` is 64 bits on Linux and 32 bits on Windows. A struct with a `long` field, or a function taking a `long`, marshals a *different size* per platform. A binding that uses your runtime's `long`-equivalent for C `long` works on Linux, then silently truncates or misaligns on Windows — corrupting the field and every field after it in a struct. The cure: **map to fixed-width types** (`int32_t`/`int64_t` ↔ `i32`/`i64` ↔ `Int32`/`Int64`), and reach for a runtime's `long` *only* when you genuinely mean "the platform's `long`, whatever that is" (rare). `size_t`/`intptr_t`/`ptrdiff_t` are pointer-width: map to `usize`/`isize`, `nuint`/`nint`, `C.size_t`, `ctypes.c_size_t` — these are consistent because they track pointer width, which is 64 in both models.

### `bool` size is not guaranteed

C `_Bool` is *usually* 1 byte, but its size was historically compiler-dependent, and runtimes disagree on how to marshal `bool`:

- **.NET** marshals `bool` as a **4-byte `BOOL`** by default (Win32 legacy). A 1-byte C `_Bool` read as a 4-byte BOOL pulls in 3 adjacent garbage bytes — the field is `true` when it should be `false`, intermittently. Force `[MarshalAs(UnmanagedType.I1)]` for a 1-byte bool.
- **Other runtimes** vary; always pin the width down against the C side's actual `sizeof(_Bool)` or the explicit `int`/`char` the API uses.

C `enum` underlying width can also vary (often `int`, but compilers may shrink to the smallest type that fits); match the C side's actual size, don't assume `int`.

---

## Out-Parameters and Error-Code Conventions

C returns extra values through **out-parameters**: you pass `&result`, the callee writes into it, you read it after. Marshalling one means allocating the destination on your side (or pinning it) and passing its address (`byref`/`ref`/`out`/`&mut`/`POINTER`).

Out-parameters almost always ride alongside an **error-code convention**: the function returns an `int`/`enum` status and writes the real result through the out-parameter. The professional rule is strict: **check the status before reading the out-parameter.** On failure, the out-parameter is frequently *left uninitialized* — reading it after a nonzero status is itself a bug (you read stack garbage or a stale value). The marshalling layer should make this unrepresentable: convert the status to an exception/`Result`/error and only then expose the out-value.

```rust
let mut out: i64 = 0;
let rc = unsafe { c_parse(input.as_ptr(), &mut out) };
if rc != 0 { return Err(Error::from_code(rc)); } // out is meaningless on failure
Ok(out)                                           // trusted only after rc == 0
```

The **two-call size protocol** is the out-parameter idiom for unknown-size results (Win32, POSIX `getXXX_r`): call once with a null/zero buffer to learn the required length (the function returns the size, or a "buffer too small" code), allocate, call again to fill. The marshalling layer must treat the first call's "too small" as a normal control-flow signal, not an error.

---

## Designing a Safe Marshalling Layer

The goal: make the dangerous operations *unrepresentable* in calling code. The boundary is unsafe; everything above it should be safe by construction.

1. **One conversion site per direction.** A single `to_native_string` / `from_native_string` (and one per struct, per buffer). Scattered `encode`/`decode`/`free` calls are where ownership and encoding bugs hide. Centralizing means one place to audit and one place to fix.
2. **Encode ownership in the type.** `OwnedCStr` (frees on drop) vs `BorrowedCStr` (frees nothing). A returned pointer's type should *say* whether you free it. In .NET, return a `SafeHandle` subclass, never a raw `IntPtr`. In Rust, a newtype with a `Drop` that calls the paired free.
3. **Allocators never cross.** Every allocation is paired with its matching free in the same module, ideally the same type's constructor/destructor. The wrong `free` should be impossible to call because the raw pointer is never exposed.
4. **Keep `unsafe`/`DllImport`/`extern` blocks tiny and audited.** The raw declarations live in one private module; nothing outside it sees a raw pointer. Reviewers audit a small, stable surface.
5. **Centralize the C type declarations** so widths (`int32_t`, `size_t`, the LP64/LLP64-safe choices) are stated once. A single header-mapping module is reviewed once and reused.
6. **Pin at the narrowest scope; keep-alive explicitly.** Scoped pins (`fixed`, critical-array) for calls; explicit `GCHandle`+keep-alive only where C retains. Document the retention window.
7. **Add a layout/ABI self-test.** Export `sizeof`/`offsetof` from C; assert against the binding's view at startup. Packing and `long`-width drift then fail loudly at init, not silently in production.
8. **Make status-checking mandatory.** Wrap every error-code call so the out-parameter is unreachable until the status is verified — convert to exception/`Result` at the boundary.

A marshalling layer built this way turns "the team must remember the rules" into "the rules are enforced by the API." That is the difference between a binding that crashes once a week and one that doesn't.

---

## Apply it

1. Define the user or business outcome that **Data Marshalling & Memory Layout** should improve.
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

- Which measurable outcome justifies investing in Data Marshalling & Memory Layout?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
