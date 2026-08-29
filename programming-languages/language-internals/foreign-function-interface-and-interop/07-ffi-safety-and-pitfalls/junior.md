# FFI Safety & Pitfalls — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **FFI Safety & Pitfalls** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Boundary Is Where Safety Ends

Picture your program as a walled garden. Inside the wall, your language enforces rules: no reading off the end of an array, no using an object after it is gone, no type confusion. The FFI is a gate in that wall. Step through it into C, and the rules do not follow you. The C compiler trusts you completely — it assumes every pointer is valid, every length is correct, and every contract is honored. When that assumption is wrong, you get **undefined behavior**, not an exception.

The practical consequence: a bug introduced at the boundary may not crash at the boundary. C might scribble one byte past a buffer, corrupting some unrelated piece of data, and your program continues happily for another ten seconds before crashing somewhere that has nothing to do with the real bug. This is why FFI bugs are so painful — the symptom is far from the cause.

### 2. Who Frees What? (Ownership)

This is the single most important question in FFI, and it has exactly one correct answer per pointer: **whoever allocated it must free it, using the matching deallocator.**

When a C library hands you a pointer, you must read its documentation to learn one thing: *do I own this and must free it, or does the library still own it?* There are three common contracts:

- **The library owns it.** You must *not* free it. You may use it until some documented point (often "until you call the next function," or "until you close the handle"). Freeing it yourself is a double-free.
- **You own it; free it with the library's function.** Many libraries allocate with their own internal allocator and require you to call *their* free function (e.g. `sqlite3_free`, `png_destroy_read_struct`), not the generic `free`. Mixing them up corrupts the heap.
- **You own it; free it with `free`.** The library used plain `malloc`, so plain `free` is correct.

Getting this wrong produces leaks (you never free) or corruption (you free with the wrong allocator, or you free something the library still owns).

### 3. The Types Must Match Exactly

When you declare a foreign function in your high-level language, you are *promising* the compiler what the C function's signature looks like — its argument types and return type. The high-level runtime cannot verify this promise. If you say a parameter is a 4-byte integer but C reads it as an 8-byte one, C will read four bytes of garbage past your value. The program **compiles**, runs, and then corrupts data. There is no error message. This "compiles, then corrupts" failure mode is the second great hazard of FFI, right behind ownership.

### 4. A Crash on the C Side Kills Everything

Inside your managed language, an error throws an exception that you can catch. On the C side, a bad memory access does not throw — it sends a **segmentation fault** straight to your process, and the operating system kills the *entire program*. There is no `try/except` that saves you. One bug in one native call takes down your whole service. This lack of isolation is why people sometimes run risky native code in a *separate process* (more on that in higher tiers).

### 5. Null Is the C Way of Saying "Failure"

A huge fraction of C functions return a null pointer to mean "I failed" (allocation failed, file not found, parse error). C does not throw; it returns null and expects *you* to check. If you forget to check and use the pointer, you dereference null and crash. **Null-checking every pointer that crosses the boundary is non-negotiable.**

---

## Code Examples

The examples below are intentionally small and show the *shape* of the most common junior-level FFI mistakes, each next to its fix. They use Python `ctypes` and Go `cgo` because those are the most approachable, but the lessons are universal.

### Example 1: The null-check you must never skip (Python `ctypes`)

```python
import ctypes

libc = ctypes.CDLL("libc.so.6")

# strdup allocates a copy of the string and returns a char* (or NULL on failure)
libc.strdup.restype = ctypes.c_char_p
libc.strdup.argtypes = [ctypes.c_char_p]

ptr = libc.strdup(b"hello")

# ❌ DANGER: if strdup failed, ptr is None / null. Using it would crash.
# ✅ Always check before use:
if not ptr:
    raise MemoryError("strdup failed")

print(ptr)  # b"hello"

# ⚠️ strdup used malloc internally — WE now own this memory and must free it.
libc.free.argtypes = [ctypes.c_void_p]
# Note: because restype was c_char_p, Python already copied the bytes out,
# but the underlying malloc'd buffer still leaks unless we free the raw pointer.
```

The two lessons: **null-check the return**, and **understand who owns the result** (`strdup` allocates with `malloc`, so the caller must `free` it).

### Example 2: The wrong `restype` — compiles, then lies (Python `ctypes`)

```python
import ctypes
libc = ctypes.CDLL("libc.so.6")

# strlen returns size_t (8 bytes on a 64-bit system).
# ctypes DEFAULTS the return type to C int (4 bytes) unless you say otherwise.

# ❌ WRONG: no restype set. ctypes assumes int. For short strings it often
#    "works" by luck, then silently breaks for some inputs.
length_wrong = libc.strlen(b"hello")  # may be right today, by accident

# ✅ RIGHT: declare the real return type.
libc.strlen.restype = ctypes.c_size_t
libc.strlen.argtypes = [ctypes.c_char_p]
length_right = libc.strlen(b"hello")  # 5, reliably
```

This is the canonical `ctypes` trap: a missing or wrong `restype`/`argtypes` produces a value that is *sometimes* correct, which is far more dangerous than always wrong, because your tests pass.

### Example 3: Returning a pointer to a local — dangling on arrival (C, called from anything)

```c
/* ❌ BROKEN C function exposed over FFI */
const char *make_greeting(void) {
    char buffer[64];
    snprintf(buffer, sizeof buffer, "hello");
    return buffer;   /* buffer lives on the stack; it is GONE the instant we return */
}
```

When your high-level language calls `make_greeting` and reads the returned pointer, it is reading stack memory that has already been reused. Sometimes it prints "hello," sometimes garbage, sometimes it crashes — classic UB. The fix is to allocate on the heap and document that the caller must free it, or to have the caller pass in a buffer.

### Example 4: Allocator mismatch (Go cgo)

```go
/*
#include <stdlib.h>
#include <string.h>

char* make_copy(const char* s) {
    char* p = malloc(strlen(s) + 1);  // C's malloc
    strcpy(p, s);
    return p;                          // caller must free with C's free
}
*/
import "C"
import "unsafe"

func Copy(s string) string {
    cs := C.CString(s)                 // allocated by C's malloc
    defer C.free(unsafe.Pointer(cs))   // ✅ freed by C's free — matching allocator

    out := C.make_copy(cs)
    defer C.free(unsafe.Pointer(out))  // ✅ make_copy used malloc, so C.free is correct

    return C.GoString(out)             // copies bytes into a Go string (GC-managed)
}
```

The rule on display: **memory `malloc`'d in C is freed by C's `free`** — never by Go's garbage collector, and never by some *other* library's free function. `C.CString` and the strings `make_copy` returns are both C-allocated, so both are released with `C.free`.

### Example 5: Catch the panic before it crosses the boundary (Go cgo callback)

```go
//export Callback
func Callback() C.int {
    // C will call this. If a Go panic unwinds into C, behavior is undefined.
    defer func() {
        if r := recover(); r != nil {
            // ✅ swallow the panic at the boundary; never let it escape into C
            // log r, return an error code instead
        }
    }()

    doRiskyWork()   // might panic
    return 0
}
```

The principle generalizes to every language: **an exception, panic, or error native to your high-level language must not unwind across the boundary into C.** Catch it at the edge and convert it to an error code or a return value the C side understands.

---

## Coding Patterns

**Pattern 1: Always declare argument and return types.** Never let the FFI tool guess. In `ctypes` set `argtypes` and `restype`; in cgo and JNI the types come from the header, so include the *correct* header.

**Pattern 2: Null-check immediately.** The very next line after any FFI call that can return a pointer should check for null and convert it into an error in your language's own style (an exception, an error value).

**Pattern 3: Free with the matching deallocator, in a `finally`/`defer`/RAII.** Pair every allocation with its release, and use your language's "always runs" mechanism (`try/finally`, `defer`, `with`, RAII) so a release happens even on the error path.

**Pattern 4: Convert at the edge.** Copy C strings and buffers into native objects (a Python `bytes`, a Go `string`, a Java `String`) as soon as possible, then release the C memory. After that you are back in safe territory.

**Pattern 5: Catch your own exceptions at the boundary.** In any function C can call back into, wrap the body so no native-language exception/panic escapes into C.

---

## Best Practices

1. **Read the ownership documentation before you write a single line.** For every function: who allocates, who frees, with which deallocator, and until when is the pointer valid? Write the answer in a comment.
2. **Null-check every pointer that crosses the boundary, every time.** No exceptions.
3. **Set explicit types** (`argtypes`/`restype` in ctypes; correct headers in cgo/JNI). A guessed type is a future corruption.
4. **Run under a memory checker.** Run your tests under AddressSanitizer or Valgrind. These tools catch use-after-free, double-free, leaks, and buffer overruns *across* the boundary, where your language's own tools cannot see.
5. **Keep the boundary small.** The fewer FFI calls and the simpler the data crossing, the fewer places to get it wrong. A thin wrapper around a safe, native-language API is the goal.
6. **Never let an exception/panic escape into C.** Catch it at the edge.
7. **Copy data out, then free.** Get back into your safe language as fast as possible.

---

## Edge Cases & Pitfalls

- **The "works on my machine" type bug.** A wrong integer size or `restype` produces correct results for *some* inputs (small numbers, short strings) and corruption for others. Tests pass; production fails. Always declare types explicitly.
- **The garbage collector moves or frees your data mid-call.** If you hand a managed object's address to C and then the GC runs, the object may be moved or collected while C still uses the old address. (Pinning fixes this; covered in higher tiers.)
- **Pointer to a local.** A C function (or a buffer you allocate in your language) that returns or stores a pointer to stack memory leaves a dangling pointer the instant the frame returns.
- **Forgetting the null terminator.** C strings end with a `\0` byte. If you pass a buffer without one, C string functions read off the end until they hit a zero somewhere in unrelated memory.
- **Freeing with the wrong function.** `free`-ing memory that a library allocated with its own allocator, or vice versa, corrupts the heap. Symptoms appear later, far away.
- **Ignoring the return value.** A C function returns `-1` or null to signal failure and you sail past it, using a result that does not exist.
- **Encoding surprises.** Passing a Unicode string to a C function that expects bytes; the lengths and contents do not match what you think.

---

## Common Mistakes

1. **Skipping the null check** "because it always works in testing."
2. **Letting the FFI tool guess types** instead of declaring them.
3. **Double-freeing** — freeing a pointer the library still owns, or freeing the same pointer twice.
4. **Leaking** — never freeing C-allocated memory because you forgot you owned it.
5. **Freeing with the wrong deallocator** — plain `free` on memory the library wants you to release with *its* function.
6. **Letting an exception/panic unwind into C.**
7. **Debugging in the wrong place** — chasing the crash location instead of suspecting the boundary.

---

## Tricky Points

- **"It worked" is not "it is correct."** Undefined behavior is allowed to look correct. A program with a real FFI bug can pass every test and still be one input away from corruption. Correctness in FFI is argued from the contracts, not observed from a green test run.
- **The error is silent by default.** C does not raise; it returns a sentinel (null, `-1`) and relies on you to check. Silence means you must be proactive.
- **The same word means different things on each side.** `int`, `long`, `bool`, and `char` do not have the same size or signedness in every language and on every platform. Never assume; declare.

---

## Apply it

1. Choose one small, known input for **FFI Safety & Pitfalls**.
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

- What problem does FFI Safety & Pitfalls solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
