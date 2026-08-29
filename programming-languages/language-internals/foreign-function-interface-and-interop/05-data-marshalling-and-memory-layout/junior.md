# Data Marshalling & Memory Layout — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Data Marshalling & Memory Layout** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why Marshalling Exists at All

A number is a number. When you pass `42` to a C function, your runtime puts the integer `42` in a register and C reads `42`. No translation needed, because both sides represent a 32-bit integer identically.

But "the string hello" is not stored identically. In C it's six bytes: `h e l l o \0`. In Java it might be a `String` object with a length field and UTF-16 code units. In Python 3 a `str` is an object with its own internal encoding and a length. In Go a `string` is a struct of `(pointer, length)` with **no** NUL terminator. In Rust a `String` is `(pointer, length, capacity)`, UTF-8, and again **no** NUL terminator.

Five languages, five different byte layouts for the same idea. C can only read **one** of them — the `char*` shape. So before C can touch your string, *someone has to produce the C shape*. That production is marshalling.

### 2. The Three Big Mismatches

Almost all marshalling pain falls into three buckets:

| Mismatch | The problem in one line |
|----------|-------------------------|
| **Strings** | Different length conventions (NUL-terminated vs length-prefixed) and different encodings (UTF-8 vs UTF-16). |
| **Structs** | The fields have to sit at the *exact same byte offsets* on both sides, or every field after the first mismatch is garbage. |
| **Arrays / buffers** | You pass a pointer + a length, and the bytes must stay valid and not get moved by the GC during the call. |

Master these three and the rest is detail.

### 3. The C String: NUL-Terminated, No Length

A C string is just a pointer to bytes. C does not store the length anywhere. To find where the string ends, C functions like `strlen` **walk forward until they hit a zero byte**. That has two consequences a junior must burn into memory:

1. **If there is no NUL terminator, C reads off the end** of your buffer into whatever memory follows — garbage, a crash, or a security hole.
2. **If your string contains a zero byte in the middle** (binary data, some encodings), C thinks the string ends there.

```text
The word "hi" as a C string:
  +---+---+----+
  | h | i | \0 |     three bytes; the \0 IS the end marker
  +---+---+----+
```

Go and Rust strings have a length and **no NUL terminator**. So when you hand a Go or Rust string to C, you must produce a NUL-terminated copy (`C.CString` in Go, `CString::new` in Rust). Forgetting this is the single most common beginner FFI bug.

### 4. The Encoding Question

Even once lengths agree, the *bytes inside* may differ. "café" is:

- 5 bytes in UTF-8 (`c a f é`, where `é` is two bytes).
- 4 UTF-16 code units (8 bytes) on Java and the Windows "wide" APIs.

If C expects UTF-8 and you hand it UTF-16, or vice versa, you get **mojibake** — garbled text like `cafÃ©`. Rust strings are *always* UTF-8, which is convenient for C interop. Java strings are UTF-16 internally; you must explicitly encode to UTF-8 bytes before handing them to a UTF-8-expecting C function. The first rule of the encoding question: **always know which encoding the C side expects, and convert explicitly.**

### 5. Who Allocates, Who Frees — The Iron Rule

This rule causes more crashes than any other:

> **Memory must be freed by the same allocator that allocated it.**

If C's `malloc` allocated a buffer, C's `free` must release it. If Rust's allocator made a string, Rust must drop it. If you call `free()` on memory that Rust allocated, you mix allocators and corrupt the heap — usually crashing later, somewhere unrelated, making it maddening to debug.

This leads to the central ownership question for *every* pointer crossing the boundary:

- **Who allocated it?** (Which side's allocator made these bytes?)
- **Who frees it, and when?** (And do they call the *right* free function?)

Three common conventions you'll meet:

1. **Caller allocates, callee fills.** You give C a buffer you own; C writes into it; you free it. (Safest.)
2. **Callee allocates, caller frees with a paired function.** C returns a pointer; the library gives you a `free_thing()` you must call. *Never* use plain `free` unless the docs say to.
3. **Callee allocates, callee owns.** C returns a pointer to memory it manages; you must **not** free it. (e.g. `strerror`.)

When the docs are unclear about which of these applies, *stop and find out*. Guessing here means a double-free or a leak.

### 6. Structs Must Line Up Byte-for-Byte

A struct is just a contiguous block of bytes. C lays out fields in declaration order, with **padding** inserted so each field is aligned. If your language lays the same struct out differently — different field order, different padding, different field sizes — then when C reads "the second field," it reads the wrong bytes.

To match C, every language gives you a way to force C-compatible layout:

- Rust: `#[repr(C)]` on the struct.
- C#: `[StructLayout(LayoutKind.Sequential)]`.
- Python (ctypes): subclass `ctypes.Structure` and declare `_fields_`.
- Go: declare a struct mirroring the C one (cgo handles layout, but you keep field order/types matching).

A junior takeaway: **a struct that crosses the FFI boundary must use the C layout, never the language's default layout.** Rust's default layout in particular is *deliberately unspecified* — the compiler may reorder fields — so `#[repr(C)]` is mandatory.

### 7. The Garbage Collector Can Move Your Data

In Java, Go, Python, and C#, the GC may **move** an object in memory to compact the heap, or **free** it the moment it sees no more references. Both are catastrophic mid-FFI-call:

- If you pass C a pointer into a GC-managed array and the GC *moves* the array, C's pointer now points at stale or reused memory.
- If the only reference to an object lives in a C variable the GC can't see, the GC may *free* the object while C is still using it.

The cure is **pinning** (and keeping a reference alive): tell the GC "hands off this object until the call returns." Each runtime has its own mechanism — `fixed`/`GCHandle` in C#, `GetPrimitiveArrayCritical` in Java, the "C must not retain Go pointers" rule in Go. You'll meet these in detail in `middle.md`. For now: **GC-managed memory is not safe to hand to C unless you pin it.**

---

## Code Examples

We do the two "hello world" marshalling tasks in every language: **(A) pass a string to a C function that returns its length, and (B) pass a small struct to a C function that fills it in.** Assume this C side:

```c
// libdemo.c
#include <string.h>

// (A) reads a NUL-terminated UTF-8 string, returns its byte length.
size_t demo_strlen(const char *s) {
    return strlen(s);
}

// (B) a point, filled in by C.
typedef struct { int x; int y; } Point;

void demo_make_point(Point *p, int x, int y) {
    p->x = x;
    p->y = y;
}
```

### Python (ctypes)

```python
import ctypes

lib = ctypes.CDLL("./libdemo.so")

# (A) string. ctypes wants bytes (a NUL-terminated char*), NOT a str.
lib.demo_strlen.restype = ctypes.c_size_t
lib.demo_strlen.argtypes = [ctypes.c_char_p]

s = "café"
n = lib.demo_strlen(s.encode("utf-8"))   # encode str -> bytes explicitly
print(n)   # 5  (é is two bytes in UTF-8)

# (B) struct. Mirror the C layout with ctypes.Structure.
class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]

lib.demo_make_point.argtypes = [ctypes.POINTER(Point), ctypes.c_int, ctypes.c_int]

p = Point()
lib.demo_make_point(ctypes.byref(p), 3, 4)   # pass &p as an out-parameter
print(p.x, p.y)   # 3 4
```

Note the **explicit** `.encode("utf-8")`. A Python `str` is not bytes; ctypes refuses it. You choose the encoding.

### Go (cgo)

```go
package main

/*
#include <string.h>
typedef struct { int x; int y; } Point;
static void demo_make_point(Point *p, int x, int y) { p->x = x; p->y = y; }
*/
import "C"
import (
	"fmt"
	"unsafe"
)

func main() {
	// (A) string. Go strings have NO NUL terminator, so make a C copy.
	cs := C.CString("café") // allocates a C buffer; YOU must free it
	defer C.free(unsafe.Pointer(cs))
	n := C.strlen(cs)
	fmt.Println(n) // 5

	// (B) struct. cgo gives us C.Point with C's layout.
	var p C.Point
	C.demo_make_point(&p, 3, 4)
	fmt.Println(int(p.x), int(p.y)) // 3 4
}
```

`C.CString` allocates with C's allocator, so you free it with `C.free` — *the allocator must match*. The `defer C.free(...)` is the iron rule made concrete.

### Rust

```rust
use std::ffi::CString;
use std::os::raw::{c_char, c_int};

#[repr(C)] // mandatory: Rust's default layout is unspecified
struct Point { x: c_int, y: c_int }

extern "C" {
    fn demo_strlen(s: *const c_char) -> usize;
    fn demo_make_point(p: *mut Point, x: c_int, y: c_int);
}

fn main() {
    // (A) string. Rust String is UTF-8 but NOT NUL-terminated.
    // CString appends the NUL and rejects interior NUL bytes.
    let s = CString::new("café").unwrap();
    let n = unsafe { demo_strlen(s.as_ptr()) };
    println!("{n}"); // 5
    // `s` stays alive until here, keeping the pointer valid.

    // (B) struct, filled by C.
    let mut p = Point { x: 0, y: 0 };
    unsafe { demo_make_point(&mut p, 3, 4); }
    println!("{} {}", p.x, p.y); // 3 4
}
```

`CString` owns the buffer; when `s` drops, *Rust* frees it. We never let C free it. And `#[repr(C)]` is not optional — without it, the compiler is free to reorder `x` and `y`.

### Java (JNI sketch)

```java
public class Demo {
    static { System.loadLibrary("demo"); }

    // Java Strings are UTF-16. The native bridge must convert to UTF-8.
    public static native long strlen(String s);
    public static native int[] makePoint(int x, int y); // returns {x, y}

    public static void main(String[] args) {
        System.out.println(strlen("café")); // native side encodes to UTF-8 -> 5
        int[] p = makePoint(3, 4);
        System.out.println(p[0] + " " + p[1]); // 3 4
    }
}
```

```c
// JNI side: GetStringUTFChars hands you a UTF-8 (modified) C string.
JNIEXPORT jlong JNICALL Java_Demo_strlen(JNIEnv *env, jclass c, jstring s) {
    const char *cs = (*env)->GetStringUTFChars(env, s, NULL);
    jlong n = (jlong) demo_strlen(cs);
    (*env)->ReleaseStringUTFChars(env, s, cs); // pair every Get with a Release
    return n;
}
```

The JVM gives you the string as a C `char*` via `GetStringUTFChars`, and you **must** pair it with `ReleaseStringUTFChars`. Java has no raw struct layout, so structs are usually marshalled field-by-field (or via newer foreign-memory APIs).

### C# (P/Invoke)

```csharp
using System.Runtime.InteropServices;

class Demo {
    // The marshaller converts the C# string to a NUL-terminated buffer.
    [DllImport("demo", CharSet = CharSet.Ansi)]
    static extern nuint demo_strlen(string s);

    [StructLayout(LayoutKind.Sequential)] // match C field order/offsets
    struct Point { public int x; public int y; }

    [DllImport("demo")]
    static extern void demo_make_point(ref Point p, int x, int y);

    static void Main() {
        System.Console.WriteLine(demo_strlen("cafe")); // marshaller makes the char*
        var p = new Point();
        demo_make_point(ref p, 3, 4);
        System.Console.WriteLine($"{p.x} {p.y}"); // 3 4
    }
}
```

C#'s **marshaller** does a lot for you: `CharSet` controls the string encoding, `[StructLayout(LayoutKind.Sequential)]` forces C field order, and `ref` passes the struct by address as an out-parameter. The *attributes are the marshalling instructions.*

---

## Coding Patterns

### Pattern: Make a C string, free it on the same side

```go
cs := C.CString(goStr)        // C allocator allocates
defer C.free(unsafe.Pointer(cs)) // C allocator frees — match!
use(cs)
```

The `defer` (or `try/finally`, or RAII) guarantees the free runs even on error.

### Pattern: Caller allocates, callee fills (out-parameter)

```python
buf = ctypes.create_string_buffer(256)   # you own this
lib.fill_message(buf, 256)               # C writes into it
print(buf.value.decode("utf-8"))         # you read it; you free it (automatic here)
```

You control the buffer's lifetime — the safest ownership model.

### Pattern: Mirror the struct with explicit C layout

```rust
#[repr(C)]
struct Config { width: c_int, height: c_int, flags: u32 }
```

Always annotate; never rely on the default layout for an FFI struct.

### Pattern: Pair every "get" with its "release"

```c
const char *cs = (*env)->GetStringUTFChars(env, s, NULL);
// ... use cs ...
(*env)->ReleaseStringUTFChars(env, s, cs);
```

Every acquire of a native view of a managed object must have a matching release.

---

## Clean Code

- **Convert strings explicitly, at one place.** Have a single helper that turns your language's string into the exact C form (encoding + NUL). Don't sprinkle ad-hoc `.encode()` calls.
- **Name the ownership in the function name or a comment.** `must_free_with_xfree()` is clearer than hoping the caller reads the docs.
- **Keep the unsafe boundary tiny.** Wrap each C call in a thin, well-named safe function and never expose raw pointers to the rest of your code.
- **Mirror struct field order and document it.** Put a comment linking your struct to the exact C declaration it copies.
- **Free in the same scope you allocate**, using `defer`/`finally`/RAII so it survives early returns and exceptions.

---

## Best Practices

- Always know **which encoding** the C side expects (almost always UTF-8 on Linux/macOS; UTF-16 "wide" on many Windows APIs). Convert explicitly.
- Never pass a Go or Rust string straight to C — it has no NUL terminator. Build a `C.CString` / `CString` first.
- Never `free()` memory your language's runtime allocated, and never let your runtime free memory C allocated. Match the allocator.
- For each returned pointer, find out: *do I free this, and with what function?* If the docs don't say, don't free (you'll leak, which is safer than a double-free) — and ask.
- Always annotate FFI structs with the C-layout attribute (`#[repr(C)]`, `[StructLayout(Sequential)]`, ctypes `Structure`).
- When handing a GC-managed buffer to C, pin it (and keep a live reference) for the whole call.
- Treat opaque handles as opaque: pass them, store them, but never dereference or inspect their contents.

---

## Edge Cases & Pitfalls

- **No NUL terminator.** Passing a Go/Rust string's raw bytes to a C function that calls `strlen` reads off the end. Always NUL-terminate.
- **Interior NUL byte.** Binary data with an embedded zero looks "ended early" to C. Rust's `CString::new` even rejects this with an error — heed it.
- **Wrong encoding.** UTF-16 bytes handed to a UTF-8 function (or vice versa) produce mojibake, not a crash — easy to miss until a non-ASCII user complains.
- **Allocator mismatch.** `free`-ing Rust- or Go-allocated memory corrupts the heap. The crash appears much later, far from the cause.
- **Freeing a borrowed string.** Some C functions return a `char*` you must **not** free (it points into static or library-owned memory). Freeing it is a crash.
- **GC moved the buffer.** Without pinning, the collector can relocate your array mid-call, leaving C with a dangling pointer.
- **Struct field misalignment.** A struct laid out differently on the two sides reads garbage for every field after the first mismatch.

---

## Common Mistakes

- Passing a `str` where C wants `bytes` (and forgetting `.encode()` / `CString`).
- Forgetting to free a `C.CString` — a steady memory leak.
- Calling `C.free` on something C did *not* allocate, or library-owned memory.
- Relying on the default struct layout in Rust (unspecified — fields may be reordered).
- Assuming the GC will leave your buffer alone during a native call. It won't, unless you pin.
- Reusing or reading a buffer after the C side (or you) freed it.

---

## Tricky Points

- A Go `string` and a Rust `&str` carry their length and are **not** NUL-terminated; a C `char*` is NUL-terminated and carries **no** length. These are opposite designs.
- Rust strings are guaranteed UTF-8; Java strings are UTF-16; C makes no encoding promise — it's "just bytes," and the meaning is by convention.
- "Caller allocates" vs "callee allocates" changes *who frees*. Reading the function's documentation for this is not optional.
- The GC can free an object whose only remaining reference lives inside C — invisible to the collector. Keeping a live reference on the managed side is part of correctness, not a nicety.

---

## Apply it

1. Choose one small, known input for **Data Marshalling & Memory Layout**.
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

- What problem does Data Marshalling & Memory Layout solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
