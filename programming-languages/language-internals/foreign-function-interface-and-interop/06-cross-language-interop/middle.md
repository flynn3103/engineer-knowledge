# Cross-Language Interop — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Cross-Language Interop** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The C ABI Is Stable; The C++ ABI Is Not

When you compile C, the function `int add(int, int)` ends up in the binary under the symbol `add`, with a calling convention that has been stable for decades on each platform. Any language that can find a symbol named `add` and push two ints can call it. That stability is *the* reason C is the interop lingua franca.

C++ is different on purpose. To support **overloading** (`add(int,int)` and `add(double,double)` coexisting), the compiler **mangles** the name to encode the full signature. The mangled name isn't even standardized across compilers — MSVC and the Itanium ABI (GCC/Clang) mangle differently. Worse, C++'s richer features have *no agreed binary representation*:

- **Exceptions** unwind the stack using compiler-specific tables. An exception thrown in C++ cannot safely propagate across an FFI boundary into a language that doesn't understand that machinery.
- **vtables** (for virtual methods) have a layout the standard doesn't fix; two compilers can lay them out differently.
- **RTTI** metadata format varies.
- **Standard-library types** (`std::string`, `std::vector`) have *different internal layouts* between libstdc++, libc++, and MSVC's STL — and even between versions. Passing a `std::string` by value across two binaries built with different standard libraries is a recipe for corruption.

The blunt summary engineers repeat: **"C++ has no stable ABI."** You cannot reliably hand another language a C++ object and expect it to understand the bytes. So you don't.

### 2. The Flattening Pattern: `extern "C"` + Opaque Pointers

The standard cure is to **flatten the C++ API down to a C ABI**. You write a thin C-shaped wrapper whose every function is `extern "C"` (no mangling, no exceptions escaping, plain arguments), and you represent C++ objects to the outside world as **opaque pointers** — handles the caller holds but never looks inside.

The shape is always the same:

```text
new      ->  create the C++ object, return it as an opaque void*  (or typed handle)
method   ->  take the handle + plain args, call the real C++ method inside
free     ->  delete the C++ object behind the handle
```

This is why almost every cross-language-friendly C++ library ships a `..._c.h` header full of `extern "C"` functions taking a `Foo*` handle. The rich C++ lives *inside*; the boundary is boring, flat C.

### 3. Exceptions Must Not Cross the Boundary

A C++ exception that escapes an `extern "C"` function into non-C++ code is **undefined behavior**. So every wrapper function must *catch everything* and convert failures into a C-friendly signal — a return code, an error enum, or an out-parameter error string:

```cpp
extern "C" int thing_do(Thing* t, int x, char** err_out) {
    try {
        return t->doWork(x);              // real C++ may throw
    } catch (const std::exception& e) {
        *err_out = strdup(e.what());      // flatten to a C error channel
        return -1;
    } catch (...) {
        *err_out = strdup("unknown error");
        return -1;
    }
}
```

The exception is *absorbed at the wall*. The outside language sees only an int and a string — concepts every language understands.

### 4. Memory Ownership Is Now a Contract You Must Document

The moment a pointer crosses a language boundary, **two memory managers exist that don't know about each other**. C++ uses `new`/`delete` (or smart pointers); Python has a garbage collector; Go has its own GC. None of them tracks the others' allocations. So you must spell out, per function: *who allocates, who frees, and when.* The opaque-handle pattern makes this tractable: the rule becomes "whatever `thing_new` allocated, `thing_free` releases, and the caller promises to call `thing_free` exactly once." Violate it and you get a leak (never freed) or a double-free / use-after-free (freed twice or used after freeing) — the classic FFI crashes.

### 5. Automated Binding Generators: SWIG and cppyy

Writing the flattening shim by hand is fine for a small API. For a large library (hundreds of classes), you automate it.

- **SWIG** reads your C/C++ headers plus a small interface file and **generates** the wrapper code and the target-language bindings (Python, Java, C#, Ruby, …) ahead of time. It handles the mangling and the handle plumbing for you, but you must teach it about ownership (`%newobject`), about which `std::` types to map, and about what to ignore. SWIG bindings are *generated artifacts* you build and ship.
- **cppyy** takes a different route: it uses a C++ interpreter (Cling) to bind C++ to Python **automatically at runtime** — no pre-generated wrappers, just `import cppyy; cppyy.include("foo.hpp")` and you can call the C++ as if it were Python. Powerful and ergonomic, at the cost of carrying an interpreter and some runtime overhead.

Both relieve you of hand-writing glue, but neither removes the underlying truths: you still owe an ownership contract, and exceptions/templates/`std::` types still need attention.

### 6. When In-Process Is Too Risky: Move to RPC

Sometimes the right move is to *stop sharing a process*. If the C++ code is crash-prone, or owned by another team, or you simply don't want a C++ memory bug to take down your Python service, you put it behind an **RPC boundary**. Now the contract isn't an ABI — it's an **IDL**. You describe the operations and messages in a `.proto` file, generate stubs, and call across a socket. You pay serialization + transport latency, and you gain **fault isolation**: the C++ process can segfault and your service just sees a failed request.

This is a real and common decision: **trade speed for a crash firewall.** A senior engineer makes it deliberately, not by default.

---

## Code Examples

### A complete `extern "C"` flattening of a C++ class

The C++ we want to expose:

```cpp
// counter.hpp
#include <stdexcept>
class Counter {
    long n_ = 0;
public:
    void add(long delta) {
        if (delta < 0) throw std::invalid_argument("negative delta");
        n_ += delta;
    }
    long value() const { return n_; }
};
```

The C façade (`extern "C"`, opaque handle, exceptions caught):

```cpp
// counter_c.cpp
#include "counter.hpp"
#include <cstring>

extern "C" {

typedef struct Counter Counter;        // opaque to the outside world

Counter* counter_new(void) {
    return reinterpret_cast<Counter*>(new ::Counter());
}

// returns 0 on success, -1 on error (writes message to *err if non-null)
int counter_add(Counter* c, long delta, char* err, int err_len) {
    try {
        reinterpret_cast<::Counter*>(c)->add(delta);
        return 0;
    } catch (const std::exception& e) {
        if (err && err_len > 0) {
            std::strncpy(err, e.what(), err_len - 1);
            err[err_len - 1] = '\0';
        }
        return -1;
    } catch (...) {
        return -1;
    }
}

long counter_value(const Counter* c) {
    return reinterpret_cast<const ::Counter*>(c)->value();
}

void counter_free(Counter* c) {
    delete reinterpret_cast<::Counter*>(c);
}

} // extern "C"
```

Build it into a shared library, then call it from Python with `ctypes` — Python never sees a C++ type, only the flat C surface:

```python
import ctypes

lib = ctypes.CDLL("./libcounter.so")
lib.counter_new.restype = ctypes.c_void_p
lib.counter_value.argtypes = [ctypes.c_void_p]
lib.counter_value.restype = ctypes.c_long
lib.counter_add.argtypes = [ctypes.c_void_p, ctypes.c_long,
                            ctypes.c_char_p, ctypes.c_int]
lib.counter_add.restype = ctypes.c_int
lib.counter_free.argtypes = [ctypes.c_void_p]

c = lib.counter_new()                 # opaque handle (an address)
err = ctypes.create_string_buffer(256)
assert lib.counter_add(c, 5, err, 256) == 0
assert lib.counter_add(c, -1, err, 256) == -1   # exception flattened to -1
print(err.value.decode())             # "negative delta"
print(lib.counter_value(c))           # 5
lib.counter_free(c)                   # WE must free what counter_new allocated
```

Read the ownership story: `counter_new` allocated, the Python side held an opaque address, and the Python side called `counter_free` exactly once. The C++ exception never crossed the wall — it became a `-1` and a string.

### Same library, but generated by SWIG instead of hand-written

A SWIG interface file points at the headers and lets the generator do the plumbing:

```swig
// counter.i
%module counter
%{
#include "counter.hpp"
%}
%include "counter.hpp"
```

```bash
swig -python -c++ counter.i        # generates counter_wrap.cxx + counter.py
# compile counter_wrap.cxx + counter.cpp into _counter.so
```

```python
import counter
c = counter.Counter()
c.add(5)
print(c.value())     # 5  — looks like native Python, glue is generated
```

SWIG generated the mangling-aware wrappers and the Python class. You still tell it about ownership and exceptions via SWIG directives for anything non-trivial, but you didn't hand-write a single `reinterpret_cast`.

### Crossing to out-of-process: gRPC with an IDL

Describe the contract once, language-neutrally:

```proto
// counter.proto
syntax = "proto3";
service Counter {
  rpc Add(AddReq) returns (AddRes);
}
message AddReq { int64 delta = 1; }
message AddRes { int64 value = 1; }
```

Generate stubs (`protoc`), implement the server (here Python), and a client in *any* language calls it as if local:

```python
# server side (sketch)
class CounterServicer(counter_pb2_grpc.CounterServicer):
    def __init__(self): self.n = 0
    def Add(self, request, context):
        if request.delta < 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "negative delta")
        self.n += request.delta
        return counter_pb2.AddRes(value=self.n)
```

```python
# client side (sketch) — could be Go, Java, C#, etc. instead
stub = counter_pb2_grpc.CounterStub(channel)
res = stub.Add(counter_pb2.AddReq(delta=5))   # an RPC that LOOKS like a call
print(res.value)                              # 5
```

Compare the two endings: in the FFI version, an error became a `-1` and you owned memory; in the gRPC version, an error became an `INVALID_ARGUMENT` *status* and there is no shared memory to own at all. Different contract, different failure language, different blast radius.

---

## Coding Patterns

### Pattern 1: The handle lifecycle (`new` / `op` / `free`)

Every exposed C++ object becomes exactly three (or more) C functions: one to create the handle, N to operate on it, one to destroy it. The caller's responsibility is symmetrical: every `new` it triggers, it must `free`.

### Pattern 2: Errors as return codes, never thrown across the wall

Reserve a return value (or an out-parameter) for failure. Catch *every* C++ exception inside the wrapper. The boundary speaks only in plain types: ints, strings, structs.

### Pattern 3: Pass primitives and buffers, not objects

Across an ABI boundary, send `long`, `double`, and `char*`/byte-buffer-with-length. Never pass a `std::string` or a `std::vector` by value — their layout isn't portable. Copy into a flat buffer at the wall.

### Pattern 4: Generate, don't hand-maintain, for large surfaces

For a handful of functions, hand-write the shim. For a large evolving library, adopt SWIG/cppyy so the binding regenerates when the headers change, rather than drifting out of sync.

### Pattern 5: When isolation matters more than speed, RPC the boundary

Wrap the foreign component in a tiny server with a `.proto` contract. Your code calls a generated stub. The foreign component is now a separate, restartable, crash-contained process.

---

## Best Practices

- **Keep the C++ entirely behind the wall.** No C++ type — not even `std::string` — should appear in an `extern "C"` signature.
- **Catch all exceptions in every wrapper function.** A single escaping exception is undefined behavior across the boundary.
- **Document ownership in the header, next to each function.** "Caller must call `counter_free`." Make the contract impossible to miss.
- **Match `std::` library and compiler if you ever do share C++ across binaries** — but prefer not to; flatten to C instead.
- **Pin and record the toolchain** (compiler, standard library, version). C++ ABI breaks between versions; reproducible builds matter.
- **For RPC, treat the `.proto` as the source of truth** and check it into version control; generate code in the build, never by hand.
- **Choose the binding tool by API size and language targets:** hand-shim (tiny), SWIG (large, multi-language), cppyy (Python, exploratory).
- **Default to RPC when another team owns the foreign code** — the contract and the crash firewall are worth the latency.

---

## Edge Cases & Pitfalls

- **An exception escapes an `extern "C"` function.** Undefined behavior; often a crash far from the cause. Always wrap the body in `try { ... } catch (...)`.
- **Passing `std::string`/`std::vector` across the boundary.** Their layout differs between libstdc++, libc++, and MSVC and between versions; the receiving side reads garbage. Flatten to `char*` + length.
- **Mixed standard libraries in one process.** Linking a binary built against libstdc++ with one built against libc++ and sharing C++ types between them silently corrupts memory.
- **Double-free / use-after-free across the boundary.** Calling `counter_free` twice, or using a handle after freeing it, crashes. The bug often surfaces much later than the misuse.
- **Leaking generated objects.** SWIG returns a new object but you didn't tell it ownership (`%newobject`); the wrapper never frees it. Memory grows silently.
- **Template instantiation mismatches.** A header-only template compiled differently on each side produces incompatible code; templates don't cross ABI boundaries by themselves.
- **Mangled-symbol "not found" at link time.** You forgot `extern "C"`, so the symbol the other language looks for (`add`) doesn't exist (the binary has `_Z3addii`).
- **Treating gRPC calls as free.** An RPC inside a tight loop multiplies serialization + network cost; designs that were "chatty" in-process become catastrophically slow out-of-process. Batch, or keep that path in-process.
- **No schema-evolution plan for the IDL.** Renaming or renumbering a protobuf field, or changing its type, breaks old clients. (Field-numbering discipline and evolution rules are a `senior.md`/`professional.md` topic — but the trap starts here.)
- **Callbacks that re-enter across the boundary.** A C++ callback that calls back into the managed language while the managed runtime holds locks (or its GC is running) can deadlock or corrupt state. Keep callbacks shallow and well-defined.

---

## Apply it

1. Find a real component where **Cross-Language Interop** affects an interface or dependency.
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

- Which boundary is most affected by Cross-Language Interop?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
