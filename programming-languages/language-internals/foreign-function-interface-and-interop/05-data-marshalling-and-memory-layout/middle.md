# Data Marshalling & Memory Layout — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Data Marshalling & Memory Layout** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Strings: Encoding, Termination, and Who Allocates

A string crossing the boundary involves **three** independent questions, and you must answer all three:

1. **Termination/length:** Is the C side NUL-terminated (`char*`) or length-counted (pointer + `size_t`)? Your side may be the opposite.
2. **Encoding:** UTF-8? UTF-16 (Windows wide / Java)? Something legacy (Latin-1)? Bytes don't carry their encoding; it's a convention you must know.
3. **Ownership of a *returned* string:** If C returns a `char*`, who frees it — and with which function?

Per language, the in-memory string is:

| Language | Representation | NUL-terminated? | Encoding |
|----------|----------------|-----------------|----------|
| C | `char*` | Yes (the NUL is the end) | By convention (usually UTF-8 on Unix) |
| Go | `string` = (ptr, len) | **No** | UTF-8 |
| Rust | `String` = (ptr, len, cap); `&str` = (ptr, len) | **No** | UTF-8 (guaranteed) |
| Java | `String` (UTF-16 code units + length) | No | UTF-16 internally |
| Python 3 | `str` (decoded text) vs `bytes` (raw) | No | `str` is abstract; `bytes` is your raw channel |
| C# | `string` (UTF-16) | No | UTF-16 internally |

So Go and Rust must *append a NUL* to hand a string to C (`C.CString`, `CString::new`). Java and C# must *transcode* UTF-16 → UTF-8 (or → wide on Windows). Python must explicitly `.encode()` a `str` into `bytes`. Rust's UTF-8 guarantee makes it the friendliest to UTF-8 C APIs — but reading an arbitrary C `char*` back into Rust requires checking it's valid UTF-8 (`CStr::to_str` can fail).

**Reading a C string back:** Rust borrows it as `CStr` (no copy, no free) and converts with `to_str()`; Go copies with `C.GoString`; Python reads `.value` from a `c_char_p`; C# uses `Marshal.PtrToStringAnsi/UTF8`. Whether you must free the original `char*` afterward depends on convention #3 above.

### 2. Struct Layout: Alignment and Padding

A C struct is laid out by placing each field at the next offset that satisfies its **alignment**, inserting **padding** as needed, and rounding the whole struct's size up to its largest member's alignment. Consider:

```c
struct S {
    char  a;   // offset 0, size 1
    // 3 bytes padding so the int is 4-aligned
    int   b;   // offset 4, size 4
    char  c;   // offset 8, size 1
    // 7 bytes padding so the double is 8-aligned
    double d;  // offset 16, size 8
};               // total size 24, not 14
```

If your language lays the same fields out without that padding — or reorders them to save space — every read after the first divergence is garbage. That's why you must force C layout:

- **Rust:** `#[repr(C)]`. The default `repr(Rust)` is *unspecified* and the compiler **may reorder fields** to minimize padding. Never rely on it for FFI.
- **C#:** `[StructLayout(LayoutKind.Sequential)]` (and `Pack` if the C side uses a non-default `#pragma pack`).
- **Python ctypes:** subclass `Structure`, declare `_fields_` in order; ctypes computes the same padding (set `_pack_` to mirror packed structs).
- **Go (cgo):** use the cgo-generated `C.struct_X` type, which carries C's layout; if you hand-roll a Go struct, match field order *and* you may need explicit padding fields.
- **Java:** the JVM exposes no raw struct layout. You either marshal field-by-field or use the newer Foreign Function & Memory API with explicit `MemoryLayout`/`VarHandle`.

A subtlety: a field's *type size* must also match. A C `int` is 32 bits; a C `long` is 64-bit on Unix (LP64) but 32-bit on 64-bit Windows (LLP64). Map to fixed-width types (`int32_t`/`int64_t` ↔ `i32`/`i64`, `c_long` only when you truly mean the platform `long`).

### 3. Arrays and Buffers: Pointer + Length, Copy vs Zero-Copy

C has no concept of "an array that knows its length." You pass **two** things: a pointer to the first element and a count (or byte length). The contract is entirely by convention — get the length wrong and C reads out of bounds.

Two strategies:

- **Copy:** marshal a fresh C buffer, pass it, copy the result back. Simple and safe; costs time and memory for large data.
- **Zero-copy:** hand C a pointer *directly into your language's memory*. Fast, but the bytes must stay **valid** and **unmoved** for the whole call. In GC languages this means **pinning**.

Python exposes raw buffers via the **buffer protocol** (`memoryview`, `bytearray`) and scientific arrays via NumPy's `__array_interface__` / `ctypes.data`, enabling zero-copy into C. NumPy arrays are not moved by CPython's (non-compacting) GC, which makes zero-copy there comparatively safe — but you must still keep the array alive.

### 4. Pinning: Keeping GC Memory Still

In compacting/moving collectors (HotSpot's, Go's, .NET's), a live object can be **relocated** to defragment the heap. A raw pointer you gave C becomes stale the instant that happens. Pinning suppresses the move for a window:

- **.NET:** `fixed (byte* p = arr) { native(p, arr.Length); }` pins for the block; or `GCHandle.Alloc(obj, GCHandleType.Pinned)` for a longer-lived pin (must `Free()` it). Pinning fragments the heap, so pin briefly.
- **Java (JNI):** `GetPrimitiveArrayCritical` returns a (usually) direct pointer and effectively pauses GC; you must do *minimal* work and call `ReleasePrimitiveArrayCritical` quickly. The looser `GetByteArrayElements` may copy instead.
- **Go:** you don't pin in the .NET sense. The rule is structural: **C must not retain Go pointers past the call.** You may pass a pointer to Go memory *into* a C call, but C must not store it for later, and Go memory can contain no Go pointers it passes to C. Long-lived buffers shared with C should be C-allocated (or use `runtime.Pinner` in recent Go for bounded cases).
- **Python:** CPython's main GC is reference-counting and **non-moving**, so objects don't relocate — but you must keep a *reference* alive (don't let the refcount hit zero) for as long as C holds the pointer.

### 5. Ownership and Lifetime: The Three Conventions, Precisely

Every pointer crossing the boundary has an owner. The three conventions, with their failure modes:

| Convention | Who frees | Failure if you get it wrong |
|------------|-----------|-----------------------------|
| **Caller allocates, callee fills** | Caller | Buffer too small → overflow; otherwise safe |
| **Callee allocates, caller frees (paired fn)** | Caller, via the library's `free_x()` | Using plain `free` instead → allocator mismatch crash; not freeing → leak |
| **Callee allocates, callee owns** | Callee (you must NOT free) | Freeing it → double-free / freeing static memory → crash |

The **allocator-matching rule** is the law underneath all three: memory from allocator X is freed by allocator X. A Rust `String` freed by C's `free`, a C `malloc` buffer freed by Go's runtime, a .NET array freed by C — all corrupt the heap. When a library *allocates* memory for you, it almost always ships a paired free function precisely so the same allocator reclaims it.

**Keeping objects alive:** the GC frees what it can't see references to. If the only reference to a managed object lives in a native variable (or got optimized away after its last managed use), the GC may collect it *while C is using it*. `GC.KeepAlive(obj)` (.NET) and equivalent "keep a reference until here" patterns extend the object's visible lifetime to cover the native call. This is a real, shipped-in-production bug class, not a theoretical one.

### 6. Numeric Type Mapping and Booleans

The "obvious" numeric types hide traps:

- **`long`:** 64-bit on LP64 (Linux/macOS 64-bit), 32-bit on LLP64 (Windows 64-bit). Don't use a language's `long` to mean C `long` unless you've checked; prefer fixed-width types.
- **`size_t` / `intptr_t`:** pointer-width. Map to `usize`/`isize` (Rust), `nuint`/`nint` (C#), `C.size_t`/`C.intptr_t` (Go cgo), `ctypes.c_size_t` (Python).
- **`bool`:** C `_Bool` is usually 1 byte, but historically and across compilers its size varied. .NET marshals `bool` as a 4-byte BOOL by default unless you say `[MarshalAs(UnmanagedType.I1)]`. Always pin down the bool width.
- **Enums:** a C enum's underlying integer type can vary; match it explicitly.

### 7. Opaque Handles and Out-Parameters

When C exposes a complex object (a database connection, a file handle, a parser), the clean design is an **opaque handle**: C returns a `void*` (or a typed-but-incomplete pointer), and you pass it back to every function that operates on it. You **never** dereference it. This decouples your binding from C's internal layout — the struct can change size and you don't care. Treat the handle as a token.

**Out-parameters** are how C returns multiple values: you pass `&result`, the function writes into it, and you read it after. Marshalling an out-parameter means allocating the destination on your side (or pinning it) and passing its address (`byref`/`ref`/`&mut`/`POINTER`). Error-code conventions ride along: many C functions return an `int` status and write the real result through an out-parameter — your binding must check the status before trusting the out value.

---

## Code Examples

### Python (ctypes): out-parameter, struct, zero-copy buffer

```python
import ctypes

lib = ctypes.CDLL("./libdemo.so")

# --- struct with explicit C layout (matches padding automatically) ---
class Rect(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int32), ("h", ctypes.c_int32)]

# --- out-parameter: int status + result via pointer ---
# int demo_parse(const char *s, int *out);   returns 0 on success
lib.demo_parse.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
lib.demo_parse.restype  = ctypes.c_int

out = ctypes.c_int()
status = lib.demo_parse(b"42", ctypes.byref(out))   # bytes, not str
if status == 0:
    print(out.value)   # 42 — only trust out AFTER checking status

# --- zero-copy: hand C a pointer into a bytearray (non-moving GC) ---
buf = bytearray(1024)
cbuf = (ctypes.c_char * len(buf)).from_buffer(buf)   # no copy
# void demo_fill(char *p, size_t n);
lib.demo_fill.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.c_size_t]
lib.demo_fill(cbuf, len(buf))
# keep `buf` alive as long as C might touch it
```

### Go (cgo): string round-trip, ownership, the "no Go pointers" rule

```go
/*
#include <stdlib.h>
#include <string.h>
char *demo_dup(const char *s);   // mallocs a copy — caller must free
*/
import "C"
import (
	"fmt"
	"unsafe"
)

func dupViaC(s string) string {
	cs := C.CString(s)                 // Go -> C buffer (C allocator)
	defer C.free(unsafe.Pointer(cs))   // free with C's allocator: match!

	out := C.demo_dup(cs)              // C mallocs the result
	defer C.free(unsafe.Pointer(out))  // we own it; free with C free

	return C.GoString(out)             // copy C string back into a Go string
}

func main() { fmt.Println(dupViaC("café")) }
// Rule: do NOT pass a Go pointer that itself points to Go memory containing
// Go pointers; and C must not retain `cs`/`out` past these calls.
```

### Rust: CString out, CStr in, and never free the borrowed one

```rust
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

extern "C" {
    fn demo_dup(s: *const c_char) -> *mut c_char; // C mallocs
    fn demo_free(p: *mut c_char);                 // paired free
    fn demo_version() -> *const c_char;           // static, do NOT free
}

fn dup_via_c(s: &str) -> String {
    let input = CString::new(s).expect("no interior NUL"); // Rust owns/frees
    unsafe {
        let out = demo_dup(input.as_ptr());          // C owns `out`
        let owned = CStr::from_ptr(out).to_string_lossy().into_owned(); // copy
        demo_free(out);                              // use the PAIRED free
        owned
    }
}

fn version() -> &'static str {
    // borrowed, library-owned: read but NEVER free
    unsafe { CStr::from_ptr(demo_version()).to_str().unwrap() }
}
```

`input` is freed by Rust when it drops; `out` is freed by the C-paired `demo_free` (allocator match); `demo_version`'s pointer is never freed because the library owns it.

### C# (P/Invoke): marshalling attributes, pinning, KeepAlive

```csharp
using System;
using System.Runtime.InteropServices;

class Demo {
    [StructLayout(LayoutKind.Sequential)]   // match C field order/padding
    struct Rect { public int w; public int h; }

    // CharSet selects the string encoding; bool needs an explicit width.
    [DllImport("demo", CharSet = CharSet.Utf8)]
    static extern int demo_parse(string s, out int result);

    [DllImport("demo")]
    static extern void demo_fill(byte[] buf, nuint n);   // nuint = size_t

    static unsafe void FillZeroCopy(byte[] data) {
        fixed (byte* p = data) {           // pin for the duration of the block
            demo_fill_ptr(p, (nuint)data.Length);
        }                                   // unpinned here
    }

    [DllImport("demo")] static extern void demo_fill_ptr(byte* p, nuint n);

    static void UseHandle() {
        var obj = new byte[64];
        IntPtr h = SomeNativeRegister(obj);  // C now holds a pointer into obj
        // ... obj has no other managed use; without KeepAlive the GC could
        //     collect/move it here while C still references it:
        GC.KeepAlive(obj);                   // extend lifetime to cover the call
    }
    static IntPtr SomeNativeRegister(byte[] b) => IntPtr.Zero; // stub
}
```

### Java (JNI): UTF-8 transcoding and critical arrays

```c
JNIEXPORT jlong JNICALL Java_Demo_process(JNIEnv *env, jclass c,
                                          jstring s, jbyteArray data) {
    // String: JVM gives modified-UTF-8; pair Get with Release.
    const char *cs = (*env)->GetStringUTFChars(env, s, NULL);

    // Array: critical pointer pins (suspends GC). Do minimal work, release fast.
    jsize n = (*env)->GetArrayLength(env, data);
    void *p = (*env)->GetPrimitiveArrayCritical(env, data, NULL);
    jlong result = demo_process(cs, p, (size_t)n);
    (*env)->ReleasePrimitiveArrayCritical(env, data, p, 0);

    (*env)->ReleaseStringUTFChars(env, s, cs);
    return result;
}
```

`GetPrimitiveArrayCritical` effectively pins by suspending GC — so the window between Get and Release must be short and must not call back into the JVM, allocate, or block.

---

## Coding Patterns

### Pattern: Status code + out-parameter, checked

```rust
let mut out: i32 = 0;
let rc = unsafe { demo_parse(input.as_ptr(), &mut out) };
if rc != 0 { return Err(rc); }
Ok(out) // only trust `out` after rc == 0
```

### Pattern: Paired allocate/free, scoped

```go
out := C.demo_dup(cs)
defer C.demo_free(out) // the library's free, not C.free, if docs say so
```

### Pattern: Pin only as long as needed

```csharp
fixed (byte* p = buffer) {
    native_call(p, buffer.Length); // tightest possible pin scope
}
```

### Pattern: Keep-alive across a stored pointer

```csharp
native_register(obj);
// ... work that might let the GC see obj as dead ...
GC.KeepAlive(obj); // ensures obj lives until at least here
```

### Pattern: Borrow vs own on returned strings

```rust
// borrowed (library-owned): read, never free
let v = unsafe { CStr::from_ptr(lib_version()).to_str()? };
// owned (callee-allocated): copy out, then free with paired fn
let s = unsafe { let p = make_string(); let r = CStr::from_ptr(p).to_str()?.to_owned(); free_string(p); r };
```

---

## Clean Code

- **One conversion site per direction.** A single `to_c_string` / `from_c_string` helper, not scattered encode/decode calls.
- **Encode ownership in the type or name.** `OwnedCStr` vs `BorrowedCStr`, or `must_free_with_demo_free` in the name/comment.
- **Wrap handles in a safe type** with a destructor (`Drop`/`IDisposable`/`__del__`) that calls the paired free exactly once.
- **Keep `unsafe`/`DllImport` blocks tiny and audited.** The rest of the code should never see a raw pointer.
- **Centralize the C declarations** so type sizes (`int32_t`, `size_t`) are stated once and reviewed.

---

## Best Practices

- State the encoding explicitly at the boundary; never assume the C side's charset matches yours.
- Always force C struct layout (`#[repr(C)]`, `Sequential`, ctypes `Structure`); never trust default layout, especially in Rust.
- Map integers to fixed-width types; avoid language `long` for C `long` unless you've confirmed LP64 vs LLP64.
- Specify `bool` width explicitly (`MarshalAs(UnmanagedType.I1)`, etc.).
- Pin for the shortest possible window; prefer `fixed`/critical-array scopes over long-lived pinned handles.
- For returned pointers, encode the ownership convention in code (a wrapper type that frees in its destructor, or a comment + matching free call).
- Add `GC.KeepAlive` (or equivalent) whenever a native side stores or uses a pointer past the managed object's last managed use.
- Validate buffer lengths on both sides; pass length alongside every pointer.

---

## Edge Cases & Pitfalls

- **`long` size flip** between Linux and Windows silently corrupts struct reads and argument values.
- **Interior NUL** truncates a C string; Rust's `CString::new` errors on it — don't `unwrap()` blindly on untrusted input.
- **Packed C structs** (`#pragma pack(1)`) need matching `Pack`/`_pack_`; otherwise your offsets gain phantom padding.
- **Critical-array misuse:** calling back into the JVM, allocating, or blocking while holding a `GetPrimitiveArrayCritical` pointer can deadlock or break GC.
- **Pinning leaks:** a `GCHandle.Alloc(Pinned)` never `Free()`d permanently pins and fragments the heap.
- **Returning a pointer into a moved/freed buffer:** zero-copy where the source is dropped or unpinned right after the call.
- **`bool` width mismatch:** reading a 1-byte C `_Bool` as a 4-byte managed BOOL reads three garbage bytes.

---

## Common Mistakes

- Using your language's `long` for C `long` and shipping it cross-platform.
- Calling plain `free` on memory that needs the library's paired free function (allocator mismatch).
- Forgetting `GC.KeepAlive` and seeing intermittent "object collected" crashes only under load.
- Holding a JNI critical array too long, or doing JVM calls inside the critical window.
- Relying on Rust's default struct layout for FFI.
- Decoding a returned `char*` but also freeing a library-owned one (double-free / freeing static memory).

---

## Tricky Points

- A `CStr` borrows; a `CString` owns. Mixing them up is the difference between "read it" and "free it."
- `GetPrimitiveArrayCritical` may or may not copy; you cannot assume zero-copy, only that GC is constrained while you hold it.
- CPython's reference-counting GC doesn't move objects, so Python pinning is mostly about keeping the *refcount* up, not preventing relocation — different from Java/.NET.
- A status-code function may leave the out-parameter *uninitialized* on failure; reading it after a nonzero status is itself a bug.
- Go's pinning model is a *rule about pointer retention*, not an API call in the .NET sense — "C must not retain Go pointers."

---

## Apply it

1. Find a real component where **Data Marshalling & Memory Layout** affects an interface or dependency.
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

- Which boundary is most affected by Data Marshalling & Memory Layout?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
