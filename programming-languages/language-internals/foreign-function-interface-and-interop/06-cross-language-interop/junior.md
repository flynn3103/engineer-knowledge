# Cross-Language Interop — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Cross-Language Interop** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A Program Becomes a Process; Processes Don't Share Memory

When you run `python app.py` or launch a compiled binary, the OS creates a **process**: a private chunk of memory plus a thread of execution. The crucial fact for interop: **two separate processes cannot see each other's variables.** If your Python process has a list `[1, 2, 3]`, a Java process running next to it has no way to "just read" that list. The bytes live in a memory area the OS keeps private.

That single fact splits the whole topic in half:

- If you want speed and direct data sharing, you must get the other language's code to run **inside your process**.
- If you can't (or don't want to), you must **send a copy of the data** to the other process.

### 2. In-Process: The Problem Is the "Handshake" (ABI)

Say you want to call a function `add(a, b)` from a library, in the same process. At the machine level, the caller and the function must agree on tiny details: *Where do I put the arguments — in which CPU registers? Where does the return value go? What is the function actually named in the compiled file?* These rules together are the **ABI**.

Here is the catch: **different languages and compilers have different ABIs.** A C++ compiler renames `add` to something like `_Z3addii` (this is *name mangling*). A function might expect a class layout that another language doesn't understand. So languages can't just call into each other blindly.

The universal solution is to agree on the **simplest possible ABI — the C ABI**. C functions have plain names, plain arguments (numbers and pointers), and no hidden machinery. Almost every language can call a C function and expose itself *as if* it were C. That's why C is the "meeting point" of in-process interop: not because C is special as a language, but because its calling convention is the simple, stable thing everyone agreed on decades ago.

### 3. Out-of-Process: The Problem Is "How Do I Describe the Data?"

If the two languages run in separate processes, you can't share a function call at all. Instead you **send bytes**. But the sender's `User { name: "Ada", age: 36 }` and the receiver's idea of a user are different objects in different languages. So both sides must agree on a **wire format**: an exact byte layout for the data.

To avoid both sides writing fragile byte-pushing code by hand, you write a single **IDL** file describing the messages and operations, and a code generator produces matching code for each language. Send → serialize → transport → deserialize → receive. This is what gRPC, Thrift, and friends do.

### 4. The Core Trade-off: Speed vs. Isolation

This is the whole topic in one line:

| | In-process | Out-of-process |
|---|---|---|
| **Speed** | Very fast (function call, shared memory) | Slower (serialize + transport + deserialize) |
| **Isolation** | None — one crash kills everything | Strong — one side can crash alone |
| **Coupling** | Tight (same memory, same lifetime) | Loose (independent deploy, independent restart) |
| **Difficulty** | Subtle ABI/memory bugs | Schema and network handling |

You choose based on what you value more: raw performance and direct data sharing (in-process), or safety, independent deployment, and the ability to put the two halves on different machines (out-of-process).

### 5. The Spectrum (Preview)

It's not just two options — it's a *spectrum* from "fastest and most dangerous" to "slowest and most decoupled":

```text
fastest, most coupled                          slowest, most isolated
        ◄──────────────────────────────────────────────►
  Raw C-FFI   Polyglot VM      Wasm component       RPC / IPC
 (link a lib)  (shared GC,      (sandboxed,        (separate process,
              shared objects)    portable)          send messages)
```

You'll learn each of these in detail across the higher levels. For now, just hold the picture: there is a dial, and the dial trades speed for safety.

### 6. Why You Almost Never Write the Bytes by Hand

A beginner might think: "I'll just write the bytes myself." Don't. Hand-writing serialization or ABI glue is the source of endless bugs — one side adds a field, the other side reads garbage; one platform uses a different byte order; a string isn't null-terminated. The entire ecosystem of **binding generators** (SWIG, cppyy) and **IDL compilers** (protoc, Thrift) exists to generate that error-prone glue *correctly and automatically* from one source of truth.

---

## Code Examples

We'll do two tiny end-to-end examples: one **in-process** (Python calling C) and one **out-of-process** (one program sending a message to another). Keep both pictures side by side as you read.

### In-process: Python calls a C function (FFI)

First, a trivial C library:

```c
// mathlib.c  — compile to a shared library
int add(int a, int b) {
    return a + b;
}
```

Compile it into a shared object (`.so` on Linux, `.dylib` on macOS, `.dll` on Windows):

```bash
cc -shared -fPIC -o libmath.so mathlib.c
```

Now call it from Python using the built-in `ctypes` FFI — same process, no network:

```python
import ctypes

lib = ctypes.CDLL("./libmath.so")     # load the C library into THIS process
lib.add.argtypes = [ctypes.c_int, ctypes.c_int]
lib.add.restype = ctypes.c_int

print(lib.add(2, 3))                   # -> 5, a near-direct function call
```

Notice: there is no socket, no serialization, no second program. Python loaded the C code *into its own process* and called `add` almost like a normal function. We had to *declare the types* (`argtypes`, `restype`) because the boundary is the bare C ABI — Python and C must agree on "two ints in, one int out." That agreement is the whole job.

### Out-of-process: one program sends a message to another

Here the two halves are separate programs. They talk over a socket and agree on a simple text format (we'll use JSON — a beginner-friendly serialization).

The **server** (could be in any language; here Python):

```python
# server.py
import socket, json

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.bind(("127.0.0.1", 9000))
srv.listen()
print("listening on 9000")

while True:
    conn, _ = srv.accept()
    data = conn.recv(1024)
    request = json.loads(data)            # DESERIALIZE bytes -> dict
    result = {"sum": request["a"] + request["b"]}
    conn.sendall(json.dumps(result).encode())  # SERIALIZE dict -> bytes
    conn.close()
```

The **client** (a different process; could be a different language entirely):

```python
# client.py
import socket, json

cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cli.connect(("127.0.0.1", 9000))
cli.sendall(json.dumps({"a": 2, "b": 3}).encode())  # SERIALIZE + send
reply = json.loads(cli.recv(1024))                  # receive + DESERIALIZE
print(reply["sum"])                                 # -> 5
cli.close()
```

Same `2 + 3 = 5` result, but everything is different: two processes, a socket, and explicit **serialize → send → receive → deserialize**. The client never touches the server's memory. If the server crashes, the client just gets a connection error — it does not crash too.

> **Tip:** Real systems don't hand-write the JSON glue like this. They use an RPC framework (gRPC, Thrift) where you describe the messages once in an IDL and a generator writes both client and server stubs for you. The mechanics above are exactly what those frameworks automate.

### The same idea, but "the other language is C++"

If the library you wanted to call in-process were **C++** instead of C, the FFI example would *not* work directly, because C++ mangles names and has features (classes, exceptions) that the C ABI doesn't describe. The standard fix is a thin **C wrapper**:

```cpp
// wrapper.cpp
#include "fancy_cpp_lib.hpp"

extern "C" {                       // <- "expose these with the plain C ABI"
    int add(int a, int b) {        // a flat C-style function...
        return FancyMath().add(a, b);  // ...that calls the real C++ inside
    }
}
```

`extern "C"` tells the C++ compiler "name and call these functions the simple C way, not the C++ way." Now Python's `ctypes` can find `add` again. You'll study this pattern properly in `middle.md`; for now, just remember: **to reach C++ from another language, you usually flatten it to a C interface first.**

---

## Coding Patterns

### Pattern 1: The C-ABI shim (in-process)

To expose any language to others in-process, give it a flat C-style surface: simple functions, numbers and pointers only, no exceptions crossing the boundary.

```c
// Everything the outside world sees is plain C.
void*  thing_new(void);
int    thing_do(void* handle, int x);
void   thing_free(void* handle);
```

The `void*` is an **opaque handle** — the outside language holds it but never looks inside. You'll see why this matters in `middle.md`.

### Pattern 2: The IDL + generated stubs (out-of-process)

Describe the contract once; let a tool generate code for every language.

```proto
// add.proto  (Protocol Buffers IDL — language-neutral)
service Calculator {
  rpc Add(AddRequest) returns (AddReply);
}
message AddRequest { int32 a = 1; int32 b = 2; }
message AddReply   { int32 sum = 1; }
```

Run the generator (`protoc`) and you get a `Calculator` client and server in Go, Python, Java, etc. — all guaranteed to agree on the wire format.

### Pattern 3: Always declare the boundary types explicitly

Whether it's `ctypes` `argtypes`/`restype` or a `.proto` schema, **write down the exact types crossing the border**. The number-one beginner bug is a silent type mismatch (a 32-bit int read as 64-bit, a string read as a pointer). Make the contract explicit and machine-checked.

### Pattern 4: Keep the boundary small

Don't expose 200 functions or a deeply nested object graph across a language boundary. Define a *narrow* interface — a handful of operations with simple inputs and outputs. A small boundary is easier to get right, easier to version, and easier to move from in-process to out-of-process later.

---

## Best Practices

- **Default to the safer option.** When unsure, choose out-of-process (an API/RPC). Move to in-process only when you've measured a real performance need.
- **Never hand-roll serialization or ABI glue.** Use a generator (protoc, Thrift, SWIG, cppyy). Generated code is correct and stays in sync.
- **Make the contract a file, not folklore.** A `.proto` or `.h` header that both sides reference beats "the format is whatever the Python team last shipped."
- **Keep the interface narrow and the types simple.** Numbers, strings, and small structs cross boundaries cleanly; complex object graphs don't.
- **Flatten C++ to a C interface before exposing it.** Use `extern "C"` wrappers; don't try to call mangled C++ symbols directly.
- **Free what you allocate, on the side that allocated it.** Memory ownership across a language boundary is a top source of bugs (much more in `middle.md`).
- **Log on both sides of an out-of-process boundary.** When something fails, you'll want to see what the sender sent and what the receiver received.
- **Test the boundary with both languages.** A test that only exercises one side proves nothing about the agreement between them.

---

## Edge Cases & Pitfalls

- **"I'll just call the C++ function directly."** You usually can't — C++ name mangling means the symbol isn't named what you think. Use an `extern "C"` shim.
- **Silent type-size mismatches.** Declaring a C function's `int` as Python `c_long` (or vice versa) can read the wrong bytes and "work" by luck until it doesn't. Match types exactly.
- **Assuming in-process is always faster overall.** It's faster *per call*, but a crash that takes down the whole process can cost you far more than the latency you saved.
- **Forgetting that strings differ everywhere.** C strings end in a `\0` byte; many languages store a length instead; encodings (UTF-8 vs UTF-16) differ. A string is rarely "just a string" across a boundary.
- **Byte order (endianness).** Sending raw integer bytes between machines can break if they order bytes differently. Real serialization formats handle this; hand-rolled byte-pushing often doesn't.
- **Mixing up the two models.** Treating an out-of-process RPC call as if it were free (like an in-process call) leads to "chatty" designs that make thousands of network round-trips. Remember: every RPC pays the serialize-and-transport tax.
- **No versioning plan.** The day one side adds a field and the other hasn't updated is the day things break — unless your format was designed for evolution (a `senior.md`/`professional.md` topic).
- **One side crashes the other (in-process).** Because they share a process, a segfault in the C library kills your Python program too — there's no firewall between them. Isolation is exactly what out-of-process buys.
- **Forgetting to free, or freeing twice.** Across an FFI boundary the garbage collector of one language doesn't know about memory the other allocated. This is the single most common in-process interop bug; we'll dedicate real space to it in `middle.md`.

---

## Apply it

1. Choose one small, known input for **Cross-Language Interop**.
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

- What problem does Cross-Language Interop solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
