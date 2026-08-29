# FFI from High-Level Languages — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **FFI from High-Level Languages** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The calling convention: what "passing an argument" means

When you call `cos(0.0)`, there is no magic. On Linux/macOS x86-64, the **System V AMD64 ABI** says: the first floating-point argument goes in register `xmm0`, the function runs, and the `double` result comes back in `xmm0`. Integer arguments go in `rdi, rsi, rdx, rcx, r8, r9`, in that order; a seventh integer argument spills onto the stack. The integer return value comes back in `rax`.

Your FFI layer's job is to **place each argument in the right place according to this convention**, then jump to the function's address. `ctypes` builds this call dynamically using a library called **libffi**, which knows the ABI for every platform and can assemble an arbitrary call at runtime. A compiled extension (Cython, cgo, JNI glue) gets the C compiler to emit the call directly, which is why it's faster — there's no runtime call-assembly step.

The practical consequence: **the ABI is per-platform.** The same `ctypes` code calls differently on x86-64 Linux, ARM64 macOS, and 32-bit Windows. libffi hides this, but it's why type *sizes* matter — if you say `c_int` (32-bit) where the function expects `long` (64-bit on Linux), the argument lands in the register only half-filled, and the function reads garbage in the high bits.

### 2. Marshalling is where your time goes

Crossing the boundary requires converting representations, and conversions cost real work:

- **`int`/`float`:** cheap. A Python int that fits in a machine word, or a float, converts to a C `long`/`double` with a few instructions. Almost free.
- **Strings:** expensive. A Python `str` is UTF-something internally; a C `char*` is null-terminated bytes. Converting means **encoding + allocating + copying** the whole string. For a 10 KB string this is a 10 KB allocation and copy *per call*.
- **Arrays/buffers:** depends. If you can pass a *pointer to existing contiguous memory* (NumPy arrays expose their buffer this way), it's nearly free — no copy. If the runtime has to flatten or copy, it's O(n).
- **Structs:** you must lay them out to match the C struct exactly (field order, padding/alignment). A mismatch is silent corruption.

The headline rule: **the dominant cost of FFI in real code is usually marshalling, not the C function.** If a profiler shows your "fast C binding" is slow, suspect string/array conversion in the loop before you suspect the C code.

### 3. The GIL: why long C calls must release it

CPython has a **Global Interpreter Lock**: at any instant, only one thread runs Python bytecode. This is fine until you make a C call that blocks — a network read, a long computation, a `sleep`. If your C extension holds the GIL while blocking for 200 ms, **every other Python thread is frozen** for those 200 ms.

The fix is a CPython C-API idiom: release the GIL around the blocking native work, then reacquire it.

```c
Py_BEGIN_ALLOW_THREADS    /* releases the GIL */
result = slow_native_call();   /* other Python threads can now run */
Py_END_ALLOW_THREADS      /* reacquires the GIL before touching Python objects */
```

The rule is strict: **you may not touch any Python object while the GIL is released.** Between those two macros you may only do pure C work. This is exactly how libraries like `requests` (via the socket layer) and NumPy let other threads run during I/O or big computations — they drop the GIL while in C. With `ctypes`, calls release the GIL by default during the foreign call, which is convenient but means you have no Python-object access in there anyway.

### 4. Reference counting across the boundary

In a CPython C extension, every Python object has a **reference count**. The C-API hands you objects as either:

- a **new (owned) reference** — *you* must `Py_DECREF` it when done, or it leaks;
- a **borrowed reference** — someone else owns it; you must **not** `DECREF` it, or you cause a premature free and later crash.

Getting this wrong is the canonical native-extension bug. `Py_INCREF` one too few times and the object is freed while you still use it (crash). One too many and it never frees (leak). The C-API docs label every function's return as "new" or "borrowed" precisely because this is the thing people get wrong. Dynamic FFI (`ctypes`) sidesteps most of this by not handing you raw Python objects — another reason it's "safer but slower."

### 5. `ctypes` vs `cffi` vs Cython — the same goal, three trade-offs

- **`ctypes`** (stdlib): pure runtime, no compiler. You declare signatures by hand. Easiest to start, slowest per call, easiest to get type sizes wrong.
- **`cffi`**: you give it actual C declarations (it can even read a header). It can run in an "API mode" that compiles a small C shim, giving near-C-extension speed and far fewer type mistakes. Preferred for serious bindings.
- **Cython**: you write Python-ish code, it generates a full C extension. Best when you're writing *new* glue/algorithms, not just wrapping an existing library.

The choice is: how much speed and safety do you need versus how much build complexity can you accept?

---

## Code Examples

### Marshalling cost made visible (Python)

```python
import ctypes, time
libc = ctypes.CDLL("libc.so.6")
libc.strlen.argtypes = [ctypes.c_char_p]
libc.strlen.restype = ctypes.c_size_t

s = ("x" * 10_000).encode()   # encode ONCE, outside the loop

# Bad: re-encode every iteration (marshalling in the hot path).
t0 = time.perf_counter()
for _ in range(100_000):
    libc.strlen(("x" * 10_000).encode())   # allocates + copies 10 KB each time
bad = time.perf_counter() - t0

# Good: reuse the already-marshalled bytes.
t0 = time.perf_counter()
for _ in range(100_000):
    libc.strlen(s)
good = time.perf_counter() - t0

print(f"re-encode each call: {bad:.3f}s   reuse: {good:.3f}s")
# The "bad" version is dominated by string allocation, not by strlen.
```

The lesson: the C function (`strlen`) is trivial; the cost is the marshalling you do *around* it.

### Releasing the GIL in a C extension

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *do_slow_work(PyObject *self, PyObject *args) {
    long n;
    if (!PyArg_ParseTuple(args, "l", &n)) return NULL;

    long result;
    Py_BEGIN_ALLOW_THREADS          /* drop the GIL: pure C only below */
    result = 0;
    for (long i = 0; i < n; i++) result += i;   /* no Python objects here */
    Py_END_ALLOW_THREADS            /* reacquire before building a PyObject */

    return PyLong_FromLong(result); /* safe: GIL held again */
}
```

If you forgot the macros, this loop would freeze every other Python thread for its whole duration.

### Owned vs borrowed reference (the classic bug)

```c
/* PyList_GetItem returns a BORROWED reference. Do NOT DECREF it. */
PyObject *item = PyList_GetItem(list, 0);   /* borrowed */
/* ... use item ... */
/* Py_DECREF(item);   <-- BUG: would over-decref and corrupt refcounts */

/* PyLong_FromLong returns a NEW reference. You MUST DECREF it. */
PyObject *num = PyLong_FromLong(42);        /* owned */
/* ... use num ... */
Py_DECREF(num);                              /* required, or it leaks */
```

### Go cgo: explicit type conversion at the boundary

```go
package main

/*
#include <string.h>
*/
import "C"
import (
	"fmt"
	"unsafe"
)

func main() {
	// C.CString allocates a C buffer and copies — YOU must free it.
	cs := C.CString("hello")
	defer C.free(unsafe.Pointer(cs)) // ownership is yours; free it

	n := C.strlen(cs)
	fmt.Println(int(n)) // 5
}
```

Note the `defer C.free`: `C.CString` allocates with C's `malloc`, so the Go GC will *not* clean it up — you own it.

---

## Coding Patterns

### Pattern 1: Marshal once, cross once

Convert your data to the C representation *outside* the loop, and prefer one bulk call over many small ones.

```python
buf = bytes(my_data)          # marshal once
lib.process_all(buf, len(buf))  # single crossing for the whole array
```

### Pattern 2: Bracket every blocking native call with GIL release

In any C extension, if the native work is non-trivial and touches no Python objects, wrap it in `Py_BEGIN_ALLOW_THREADS`/`Py_END_ALLOW_THREADS`.

### Pattern 3: Match C integer types exactly

Use `ctypes.c_long`, `c_size_t`, `c_int32` etc. to match the C declaration's *actual* type, not "whatever looks like a number." Read the header.

### Pattern 4: Own-it-then-free-it for C allocations

When a C function allocates and returns a buffer, immediately arrange to free it (a `try/finally`, a Go `defer C.free`, a Rust `Drop` wrapper). Never leave the free to "later."

---

## Best Practices

1. **Profile the binding, not just the C library.** The slow part is often marshalling you wrote, not the foreign function.
2. **Prefer passing pointers to existing buffers over copying.** Zero-copy is the biggest single FFI speed lever.
3. **Release the GIL around blocking or long native calls** — and never touch Python objects while it's released.
4. **Annotate every reference as owned or borrowed** in comments; the bug is invisible otherwise.
5. **Pin integer types to the C declaration**, and test on 32-bit/64-bit and Linux/Windows if you ship cross-platform.
6. **Choose the tool for the job:** `ctypes` for a quick script, `cffi` for a real binding, Cython for new hot code.
7. **Keep the GIL-released region as small as possible** — just the blocking call, nothing else.

---

## Edge Cases & Pitfalls

- **Touching a Python object after `Py_BEGIN_ALLOW_THREADS`.** Classic latent crash; the object machinery isn't protected without the GIL.
- **DECREF-ing a borrowed reference.** Over-decrement frees an object still in use → later use-after-free crash, far from the cause.
- **Re-marshalling in a loop.** Encoding the same string every iteration turns an O(1) C call into an O(n) allocation storm.
- **`c_int` where C uses `long` on 64-bit Linux.** Truncation; works on Windows (where `long` is 32-bit), corrupts on Linux. Platform-dependent and nasty.
- **Forgetting to free a `C.CString`/`malloc`'d buffer.** The GC won't, because C owns it — steady leak.
- **Assuming the GIL makes compound C operations atomic.** It doesn't; the GIL is released across many C boundaries.
- **Struct padding mismatch.** Your `ctypes.Structure` must replicate the C struct's alignment exactly, or fields read from the wrong offsets.

---

## Apply it

1. Find a real component where **FFI from High-Level Languages** affects an interface or dependency.
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

- Which boundary is most affected by FFI from High-Level Languages?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
