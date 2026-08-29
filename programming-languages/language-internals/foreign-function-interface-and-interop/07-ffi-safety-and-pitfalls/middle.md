# FFI Safety & Pitfalls — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **FFI Safety & Pitfalls** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Hazard Class 1: Memory Ownership & Lifetime

This is the largest and most common class. It splits into several distinct failure modes.

**Allocator mismatch.** Heap memory must be freed by the *same* allocator family that allocated it. If a library allocates with its internal allocator (or with a different C runtime than yours — a real problem on Windows, where a DLL may link a different CRT than your program), then `free`-ing it with your `free` corrupts the heap. The defense: free with the function the library tells you to use (`sqlite3_free`, `g_free`, the library's own destructor), never assume plain `free` works.

**Double-free.** Freeing the same pointer twice corrupts the allocator's metadata; the second free, or a later allocation, blows up. This happens when two code paths both think they own the pointer, or when a "free" function is called and then a `defer`/destructor frees it again. The defense: a single, clear owner per pointer, and null the pointer after freeing where the language allows.

**Use-after-free across the boundary.** You free C-allocated memory, then keep using a pointer (or a wrapper object) that still references it. Particularly nasty when the high-level wrapper outlives the C resource. The defense: tie the lifetime of the wrapper to the C resource, so the wrapper cannot be used after the resource is freed.

**Dangling pointers to stack or freed memory.** A C function returns a pointer to a local; or you hand C a pointer into a buffer that your language frees before C is done. The defense: only pass pointers whose lifetime provably outlives the call, and never return pointers to locals.

**The contract must be documented.** Every function in your boundary should have a one-line ownership note: *who allocates, who frees, with what, valid until when.* This is not bureaucracy — it is the specification that makes the boundary auditable.

### Hazard Class 2: Type & ABI Mismatch ("compiles, then corrupts")

The high-level runtime cannot verify your declaration of a C function. A wrong declaration is accepted, runs, and corrupts memory silently. The sub-cases:

- **Wrong integer size.** Declaring a parameter as 4 bytes when C reads 8 (or the reverse). The classic is `long` and `size_t`: on Windows 64-bit (LLP64) `long` is 4 bytes, on Linux/macOS 64-bit (LP64) it is 8. Code that works on Linux corrupts on Windows.
- **Signedness.** Declaring `unsigned` where C uses `signed` (or vice versa) flips the interpretation of high values — a large positive becomes negative.
- **`bool`.** C `bool` is one byte; some FFI tools default to a 4-byte int. The three garbage bytes can be nonzero, making a "true/false" unpredictable.
- **Struct layout / padding.** If your declared struct does not match C's field order, sizes, and alignment padding, every field after the first mismatch is read from the wrong offset. Particularly easy to get wrong with mixed field sizes and platform-dependent padding.
- **Calling convention.** On 32-bit x86 especially, declaring the wrong convention (`cdecl` vs `stdcall`) corrupts the stack on every call. Less common on 64-bit, but still a Windows pitfall.

The unifying symptom of this class: it **compiles**, often **passes simple tests**, and corrupts on some inputs or platforms. The defense: declare exact types; prefer fixed-width types (`int32_t`, `uint64_t`, `intptr_t`) over `int`/`long`; mirror struct layout exactly (and prefer generated bindings over hand-written ones); test on every target platform, especially across LP64/LLP64.

### Hazard Class 3: Error Handling Across the Boundary

The two sides report errors in incompatible ways. C uses **return codes**, **null returns**, and **`errno`**. Your high-level language uses **exceptions**, **panics**, or **error values**. Three rules govern the crossing:

1. **Translate C errors into your language's idiom at the boundary.** A null return or `-1` becomes an exception or an `Err`. Do not propagate raw sentinels upward; callers should not have to know C conventions.

2. **Read `errno` correctly.** `errno` is only meaningful *immediately* after the failing call. Any intervening call — even something innocuous, even your own logging — may overwrite it. Capture it on the very next line, before anything else.

3. **Never let an exception/panic unwind across the boundary into C.** This is undefined behavior, full stop. A Rust panic propagating into C, a C++ exception escaping an `extern "C"` function, a Go panic crossing into C, a Java exception left pending across native code — all are bugs. The defense is to *catch at the edge*: Rust's `std::panic::catch_unwind`, C++'s `catch (...)`, Go's `recover()` in the exported function, and explicit JNI exception checks after every JNI call that can throw. Convert the caught error into a return code the other side understands.

### Hazard Class 4: The GC Versus Native Pointers

In a managed runtime, the garbage collector can **collect** an object that is no longer reachable, and some collectors (the JVM, .NET, Go in some cases) can **move** objects to compact the heap. Either is catastrophic if native code holds a raw pointer to that object's memory:

- **Premature collection.** You hand C a pointer derived from a managed object, then your only reference to that object goes out of scope. The GC sees it as unreachable, collects it, and now C is reading freed memory. The fix: keep the object alive across the native call. In .NET this is exactly what `GC.KeepAlive(obj)` is for — it does nothing but prevent the object from being collected before that point.
- **Object moved during the call.** Even if the object is still alive, a moving GC may relocate it, leaving C's pointer pointing at the old address. The fix: **pin** the object (`fixed` in C#, `GCHandle.Alloc(obj, GCHandleType.Pinned)`, `Get*ArrayElements`/critical sections in JNI, runtime pinning rules in Go) so the GC may not move it for the duration of the native use.

The general principle: **whenever native code holds a pointer into managed memory, you are responsible for keeping that memory both alive and stationary for exactly as long as the pointer is used.**

---

## Code Examples

### Example 1: Allocator mismatch and its fix (C library with a custom free)

```python
import ctypes

lib = ctypes.CDLL("./libthing.so")

# Suppose thing_serialize() returns a buffer allocated by the library's
# internal allocator, and the docs say "free with thing_free, not free()".
lib.thing_serialize.restype = ctypes.c_void_p
lib.thing_free.argtypes = [ctypes.c_void_p]

buf = lib.thing_serialize(obj)
if not buf:
    raise RuntimeError("serialize failed")
try:
    data = ctypes.string_at(buf, length)   # copy bytes out into Python's heap
finally:
    lib.thing_free(buf)   # ✅ matching deallocator — NOT ctypes' / libc's free
```

Using `libc.free(buf)` here would corrupt the heap, because the library did not allocate it with `malloc`.

### Example 2: Integer-size portability (the LP64/LLP64 trap)

```python
import ctypes

# ❌ FRAGILE: c_long is 8 bytes on Linux/macOS but 4 bytes on Windows.
# If the C function takes size_t, this is wrong on Windows.
lib.process.argtypes = [ctypes.c_long]

# ✅ ROBUST: use the type that matches the C declaration on every platform.
lib.process.argtypes = [ctypes.c_size_t]   # matches size_t everywhere
# For fixed widths, prefer c_int32 / c_uint64 to mirror int32_t / uint64_t.
```

The lesson: **prefer fixed-width and exact-semantic types** (`c_size_t`, `c_int32`, `c_uint64`) over `c_int`/`c_long`, whose width depends on the platform's data model.

### Example 3: Reading `errno` correctly (C, called from Python ctypes)

```python
import ctypes

libc = ctypes.CDLL("libc.so.6", use_errno=True)   # ✅ ask ctypes to capture errno
libc.open.restype = ctypes.c_int
libc.open.argtypes = [ctypes.c_char_p, ctypes.c_int]

fd = libc.open(b"/no/such/file", 0)
if fd == -1:
    err = ctypes.get_errno()          # ✅ read the captured errno, not a stale one
    raise OSError(err, "open failed")
```

Without `use_errno=True`, an intervening Python operation could overwrite `errno` before you read it, and you would report the wrong error. Capture it on the failure path immediately.

### Example 4: Stopping a panic at the boundary (Rust)

```rust
use std::panic::{catch_unwind, AssertUnwindSafe};

// This function is callable from C. A panic must NOT unwind into C.
#[no_mangle]
pub extern "C" fn compute(input: i32) -> i32 {
    let result = catch_unwind(AssertUnwindSafe(|| {
        do_work(input)   // might panic (e.g. index out of bounds, unwrap)
    }));

    match result {
        Ok(value) => value,
        Err(_) => -1,     // ✅ convert the panic into an error code for C
    }
}
```

Without `catch_unwind`, a panic propagating into the C caller is undefined behavior. The boundary converts it into a sentinel the C side understands.

### Example 5: Keeping a managed object alive across a native call (.NET)

```csharp
// Native function uses a pointer into the managed array while it runs.
byte[] data = GetData();

unsafe
{
    fixed (byte* p = data)          // ✅ pin: the GC may not move 'data' here
    {
        NativeProcess(p, data.Length);
    }
}                                    // unpinned after the block

// In a more subtle case where you pass a pointer that outlives a 'fixed' block,
// GC.KeepAlive ensures the object is not collected before this point:
GC.KeepAlive(data);
```

`fixed` pins the array so the GC cannot relocate it during the call; `GC.KeepAlive` prevents premature collection when the lifetime is harder to express. Both address Hazard Class 4.

### Example 6: Mirroring a struct layout exactly (Go cgo)

```go
/*
typedef struct {
    int32_t  id;       // 4 bytes
    int32_t  flags;    // 4 bytes  (placed here so the 8-byte field is aligned)
    double   weight;   // 8 bytes
} Item;
*/
import "C"

// cgo generates C.Item with the exact same layout from the header above.
// ✅ Let the tool mirror the layout from the real header — do not hand-roll
//    a Go struct with guessed field order or sizes.
func describe(it C.Item) {
    _ = int32(it.id)
    _ = float64(it.weight)
}
```

The safest defense against layout mismatch is to **generate** the binding from the actual C header (cgo, bindgen, SWIG) rather than transcribe field offsets by hand.

---

## Coding Patterns

**Pattern 1: Document ownership in a comment on every boundary function.** "Returns a buffer owned by the caller; free with `thing_free`. Valid until freed."

**Pattern 2: Generate bindings from the real header.** Use cgo, `bindgen`, SWIG, or P/Invoke source generators rather than hand-transcribing signatures and structs.

**Pattern 3: Translate errors at the edge.** C sentinel in, native exception/`Err`/null out. Capture `errno` immediately on the failure path.

**Pattern 4: Wrap every callback body in a catch.** `catch_unwind`/`recover`/`catch(...)`/JNI exception check, so nothing native-language escapes into C.

**Pattern 5: Pin or keep-alive any managed memory shared with native code,** for exactly the duration of the native use, and no longer.

**Pattern 6: Prefer opaque handles.** Have the C library give you a pointer you never dereference, and pass it back on each call. This eliminates struct-layout mismatch entirely for the handle.

---

## Best Practices

1. **Classify before debugging.** Identify the hazard class from the symptom.
2. **One owner per pointer; one free per allocation; matching deallocator.** Document it.
3. **Exact, fixed-width types.** Avoid `int`/`long`; use `int32_t`/`size_t`/`intptr_t` equivalents.
4. **Generate bindings** instead of hand-writing them where possible.
5. **Errno read immediately; errors translated at the boundary.**
6. **No exception/panic crosses into C.** Catch at the edge.
7. **Keep managed memory alive and pinned** while native code holds a pointer to it.
8. **Test under ASan/Valgrind, on every target platform.** Cross-platform CI catches LP64/LLP64 bugs.

---

## Edge Cases & Pitfalls

- **Windows CRT mismatch.** A DLL built against a different C runtime than your program has a *different* heap; `free`-ing across that boundary corrupts memory even though both are "the C `free`."
- **`errno` clobbered by logging.** You call the C function, log "call failed," *then* read `errno` — but logging already overwrote it. Read first.
- **Struct grows in a library update.** The library adds a field to a struct in a new version; your hand-written binding is now too small, and every read past the old end is wrong. Generated bindings + version pinning mitigate this.
- **Pinned too long.** Pinning prevents the GC from moving an object; pinning many objects for a long time fragments the heap and hurts GC performance. Pin narrowly.
- **Callback runs on a thread that cannot touch the runtime.** A C library invokes your callback from a thread it created; touching managed state from there without attaching/locking is a bug (covered in depth at senior level).
- **Sign extension on a small return.** A C function returns `char` (could be negative); naively widening it to a larger unsigned type yields a huge value.

---

## Common Mistakes

1. Using plain `free` on memory a library wants released with its own function.
2. Declaring `long` where the C side uses `size_t`, then porting to Windows.
3. Reading `errno` after an intervening call has overwritten it.
4. Letting a panic/exception unwind into C.
5. Handing the GC's movable memory to C without pinning, then crashing only when the GC happens to run.
6. Transcribing a struct layout by hand and getting the padding wrong.
7. Two owners freeing the same pointer.

---

## Tricky Points

- **"It passes on Linux" hides LP64/LLP64 bugs.** The same code corrupts on Windows because `long` changed size. Type bugs are platform-shaped.
- **GC bugs are timing-shaped.** They appear only when the collector happens to run during the native call — often rare in tests, common under production load.
- **`errno` is a moving target.** Its value is only trustworthy for one instant. Treat it like a volatile reading you must sample immediately.
- **A struct that "works" can still be wrong.** If the mismatch is in a field you do not currently read, the bug is latent until someone reads it.

---

## Apply it

1. Find a real component where **FFI Safety & Pitfalls** affects an interface or dependency.
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

- Which boundary is most affected by FFI Safety & Pitfalls?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
