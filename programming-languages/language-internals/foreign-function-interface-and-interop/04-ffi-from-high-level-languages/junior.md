# FFI from High-Level Languages — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **FFI from High-Level Languages** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Two ways to cross the boundary

There are exactly two broad approaches, and almost every ecosystem offers one or both.

**(a) Dynamic FFI — describe the library at runtime.** You take an *existing* compiled shared library (say, the system's math library), load it from your high-level code, and *tell your runtime* what each function looks like: "`cos` takes one double and returns a double." No C compiler needed, no separate build step. The classic example is Python's `ctypes`. Other examples: .NET's `[DllImport]`, Ruby's Fiddle/FFI, LuaJIT's FFI.

**(b) Native extension modules — compile glue code.** You write a small amount of C (or Rust) that *knows about both worlds*: it speaks your high-level language's internal API on one side and calls the native library on the other. You compile this glue into a shared library that your runtime loads as a module. Examples: CPython C-API extensions (and tools like Cython/PyO3 that generate them), Java's JNI, Node.js native addons (N-API), Go's cgo, Rust's `extern "C"`.

The trade-off, in one line: **dynamic FFI is easy and needs no compiler but is slower and type-unsafe; native extensions are fast and integrated but need a build toolchain and more code.**

### 2. What a shared library actually is

A shared library is a file full of compiled functions, each reachable by a **symbol** (its name). On Linux it ends in `.so`, on macOS `.dylib`, on Windows `.dll`. When your program runs, the OS **loader** finds the library, maps it into your process's memory, and resolves symbols — so when you ask for the function `cos`, the loader hands back its address. From there, calling it is just "jump to this address with these arguments."

You already depend on dozens of these. On Linux, run `ldd $(which python3)` and you'll see `python3` is linked against `libc.so`, `libpthread.so`, and more. FFI is just *you* doing, deliberately and at runtime, what the loader already does for the program's own dependencies.

### 3. The boundary has no shared type system

Inside Python, a string is a rich object with a length, an encoding, and a reference count. Inside C, a string is just a pointer to bytes that ends in a zero byte. These are **not the same thing**. At the FFI boundary, *someone* has to convert — to **marshal** — between them. With dynamic FFI you describe the conversion (`argtypes`/`restype`); with native extensions you write the conversion code by hand.

This is where most beginner FFI bugs live. If you tell `ctypes` that a function returns an `int` when it actually returns a pointer (which is 64 bits on a modern machine), the value gets truncated and you read garbage — or crash.

### 4. Why an FFI mistake crashes the whole process

When pure Python code does something wrong — index out of range, divide by zero — the interpreter raises an exception you can catch. The interpreter is a referee that checks every move.

Native code has **no referee**. When you cross into C, you leave the interpreter behind. If the C function dereferences a bad pointer, the *CPU* faults and the *OS* kills your entire process with a **segmentation fault**. There is no exception, no stack trace from Python, no `finally` block. This is the single most important thing to internalize as a junior: **on the native side of FFI, mistakes are fatal, not recoverable.**

### 5. Who owns the memory?

In Python, Java, Go, and Node, you never `free` memory — a garbage collector or reference counter does it for you. In C, *you* allocate and *you* free. When a value crosses the boundary, a critical question appears: **who is responsible for freeing this?** If a C library hands you a pointer to a buffer it allocated, and you forget to call its `free` function, you leak memory. If you free it twice, you crash. Every FFI binding has to answer the ownership question for every value, and getting it wrong is one of the most common real-world FFI bugs.

---

## Code Examples

> Goal of this section: the **smallest real example** in several languages — calling a function that already exists in the system C library. We use `cos` from the math library because it's everywhere.

### Python with `ctypes` — call C `cos`

```python
import ctypes
import ctypes.util

# Find and load the system math library (libm).
libm_path = ctypes.util.find_library("m")   # "libm.so.6" on Linux, etc.
libm = ctypes.CDLL(libm_path)

# THE CRITICAL STEP: describe the C signature.
# C declaration is:  double cos(double x);
libm.cos.argtypes = [ctypes.c_double]   # one double in
libm.cos.restype = ctypes.c_double      # one double out

print(libm.cos(0.0))   # 1.0
print(libm.cos(3.141592653589793))   # -1.0
```

The two lines that set `argtypes` and `restype` are the entire game. They tell `ctypes` how to marshal the Python float into a C double and how to interpret the bytes that come back. **Leave them out and `ctypes` guesses `int`**, which truncates the double and gives you nonsense.

### Python — what happens when you get the types wrong

```python
import ctypes
libc = ctypes.CDLL("libc.so.6")

# C declaration:  char *strerror(int errnum);
# strerror returns a POINTER. If we don't say so, ctypes assumes int,
# truncates the 64-bit pointer to 32 bits, and we read garbage / crash.

libc.strerror.restype = ctypes.c_char_p   # CORRECT: returns a C string
print(libc.strerror(2))   # b'No such file or directory'

# Comment out the restype line above and you may get a wrong number
# or a SEGFAULT. No exception will be raised — the process just dies.
```

This is the canonical junior FFI bug: a forgotten or wrong `restype`/`argtype` silently corrupting data.

### Go with cgo — call C `cos`

```go
package main

/*
#include <math.h>
*/
import "C"
import "fmt"

func main() {
	// C.double and C.cos come from the preamble comment above.
	result := C.cos(C.double(0.0))
	fmt.Println(float64(result)) // 1
}
```

In Go, the `import "C"` with a comment *above it* (the "preamble") turns on **cgo**. The C functions become available as `C.cos`, and you convert Go types to C types explicitly (`C.double(...)`). Unlike Python, this is compiled — you need a C compiler installed, and the binary is no longer pure Go.

### Rust calling C `cos`

```rust
// Tell Rust about an external C function. The libm is linked by default.
extern "C" {
    fn cos(x: f64) -> f64;
}

fn main() {
    // Calling foreign code is `unsafe` — the compiler can't verify the
    // signature is right or that the function behaves.
    let r = unsafe { cos(0.0) };
    println!("{}", r); // 1
}
```

Rust forces you to wrap the call in `unsafe`, which is the language saying out loud: "I cannot protect you here; you are asserting this is correct."

### Node.js — the shape of a native addon

Node doesn't do dynamic FFI in core. Native code is shipped as a compiled **addon** using **N-API**. As a junior, the important takeaway is what *using* one looks like:

```javascript
// Someone wrote and compiled a native addon; you just require it.
const native = require('./build/Release/mymodule.node');
console.log(native.cosWrapper(0.0)); // 1
```

The `.node` file is a compiled shared library that Node loads like a normal module. The hard work (writing the C glue with N-API) lives inside it — covered in later tiers.

---

## Coding Patterns

### Pattern 1: Always declare the signature

For dynamic FFI, never call a C function before you have set both its argument types and its return type. Treat an undeclared call as a bug.

```python
lib.somefunc.argtypes = [ctypes.c_int, ctypes.c_char_p]
lib.somefunc.restype = ctypes.c_int
```

### Pattern 2: Validate before you cross

Do all your checking on the safe side. Once the value is in C, there's no second chance.

```python
def safe_call(n):
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative int")  # catchable, here
    return lib.process(n)  # only cross once the input is known-good
```

### Pattern 3: Wrap the unsafe call in a clean function

Expose a normal, idiomatic function to your callers; hide the FFI mechanics inside it.

```python
def cosine(x: float) -> float:
    return libm.cos(x)   # callers never touch ctypes
```

This "safe wrapper around an unsafe core" pattern appears in *every* language and is the single most important habit. Rust formalizes it; everyone else should imitate it.

---

## Best Practices

1. **Declare every signature explicitly.** No undeclared `ctypes` calls, ever.
2. **Cross the boundary as rarely as possible.** Push loops into C; don't call C in a Python loop a million times.
3. **Hide FFI behind a normal-looking API.** Callers shouldn't know native code is involved.
4. **Decide and document memory ownership** for every pointer that crosses: who frees, and when.
5. **Test on every platform you ship to.** A binding that works on Linux can crash on macOS or Windows because of type-size or library-name differences.
6. **Pin to a stable interface.** Prefer libraries with a stable C ABI; C++ name-mangling and templates do not cross FFI cleanly.
7. **Keep the native side tiny.** The less code runs without a safety net, the fewer fatal bugs.

---

## Edge Cases & Pitfalls

- **Forgetting `restype` for pointer-returning functions.** `ctypes` assumes `int`; a 64-bit pointer truncates to 32 bits → garbage or crash. *Always* set `restype`.
- **Passing a Python string where C wants bytes.** C strings are bytes (`b"..."`). A `str` must be encoded first, or `ctypes` will complain — or worse, on some setups, do the wrong thing.
- **Library not found at runtime.** "cannot open shared object file" means the loader couldn't locate the `.so`. It's a *deployment* problem, not a code problem — the library isn't on the search path.
- **Integer size mismatches.** A C `long` is 64-bit on Linux but 32-bit on Windows. Hard-coding `c_int` where the C side uses `long` corrupts values across platforms.
- **Assuming exceptions protect you.** `try/except` does **not** catch a segfault. Once C corrupts memory, your process is doomed.
- **The off-by-one in C strings.** C strings need a trailing zero byte. If you build a buffer one byte too small, the C function reads past the end.
- **Calling C in a tight Python loop.** Each `ctypes` call has overhead. A million tiny C calls can be slower than pure Python; the win comes from doing the *whole loop* in C.

---

## Apply it

1. Choose one small, known input for **FFI from High-Level Languages**.
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

- What problem does FFI from High-Level Languages solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
