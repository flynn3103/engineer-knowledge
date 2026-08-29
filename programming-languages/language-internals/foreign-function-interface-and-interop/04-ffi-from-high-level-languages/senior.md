# FFI from High-Level Languages — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **FFI from High-Level Languages** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Moving vs. non-moving GC determines whether raw pointers are safe

This single fact explains most of the divergence between FFI designs.

**CPython: non-moving + refcounted.** An object's address never changes for its lifetime. So a C extension can hold a raw `PyObject*` across calls — as long as it keeps the refcount up so the object isn't freed. Pointers are stable; the discipline is *lifetime*, not *location*.

**JVM and Go: moving collectors.** The GC compacts the heap by *relocating* live objects. An address you grabbed a microsecond ago may be stale after the next GC. Therefore neither runtime lets native code freely hold raw pointers into managed memory. The JVM gives you **handles** (jobjects) that the JNI layer translates; Go simply **forbids** passing Go pointers into C that C will retain.

The consequence: bindings for moving-GC runtimes need either **handles** (an indirection the runtime can update) or **pinning** (temporarily forbidding movement) whenever native code must see real bytes.

### 2. JNI: handles, reference scopes, and critical regions

JNI never hands native code a raw Java object address. It hands a **jobject** — an opaque handle the runtime can keep valid even as the GC moves the underlying object. Two scopes:

- **Local references** are valid only during the current native method call and freed automatically on return. There's a *limited table* of them; a native loop that creates thousands without freeing them overflows the local reference table.
- **Global references** survive across calls. You create them with `NewGlobalRef` and **must** `DeleteGlobalRef`, or they leak — and a leaked global ref also keeps the Java object alive, so it's a Java memory leak caused by native code.

For raw array access, JNI offers two tiers. `GetArrayElements` may copy. `GetPrimitiveArrayCritical` **pins** the array so C sees its actual bytes with no copy — but while pinned, the GC is effectively blocked, so you must do minimal work and call `ReleasePrimitiveArrayCritical` immediately. Holding a critical region across a blocking call or a callback is a recipe for stalling or deadlocking the collector.

Two more JNI gotchas seniors must know: the **`JNIEnv*` is per-thread** (never cache and reuse it on another thread), and **Java exceptions don't propagate automatically** — after a JNI call that might throw, you must `ExceptionCheck` and bail; ignoring a pending exception and continuing to call JNI is undefined behavior.

### 3. Project Panama (the Foreign Function & Memory API)

JNI's problems are real: hand-written C glue, per-binding `.so` files, boilerplate, and easy ref leaks. **Project Panama** (the `java.lang.foreign` FFM API, standard since Java 22) replaces it with a pure-Java, typed approach:

- **`Linker`** produces a `MethodHandle` bound to a native function, given its descriptor (argument and return layouts).
- **`MemorySegment`** is a typed, bounds-checked view of off-heap (or heap) memory — no more raw `void*` with no length.
- **`Arena`** scopes the lifetime of native memory; when the arena closes, the memory is freed deterministically.
- **Downcalls** (Java→native) are `MethodHandle.invoke`; **upcalls** (native→Java) wrap a Java method handle as a function pointer C can call.

The wins: no C compiler, no per-platform `.so` to ship, bounds-checked memory, deterministic deallocation, and lower per-call overhead than JNI because there's no `JNIEnv` round-trip. The cost: you describe layouts explicitly, and `unsafe`-equivalent operations are still possible (you can still mis-describe a signature and crash).

### 4. cgo: the goroutine-stack switch and the pointer rule

Go's FFI, **cgo**, has two senior-level realities.

**It's not a cheap call.** A normal Go function call is a few instructions. A cgo call must: switch from the goroutine's small, movable stack to a dedicated **system stack** (because C needs a real, fixed OS stack), coordinate with the Go scheduler (the goroutine is now "in a syscall-like state," so the scheduler may need another OS thread to keep other goroutines running), and switch back on return. The fixed overhead is on the order of tens of nanoseconds — negligible once, catastrophic in a tight loop calling C millions of times. This is the **cgo performance cliff**: code that's fine at low call rates falls off a cliff when the crossing becomes the hot path.

**Don't pass Go pointers to C (that C keeps).** Because Go's GC can move objects and reclaim them, C must not *store* a Go pointer past the call's return. The cgo pointer-passing rules are enforced (with `GODEBUG=cgocheck`): you may pass a Go pointer to C for the duration of the call, but C may not retain it, and the memory it points to must not itself contain Go pointers. If C needs to keep data, copy it into C-allocated memory (`C.malloc`) — which you then own and must free.

cgo also has knock-on costs seniors weigh: it **breaks easy cross-compilation** (you now need a C cross-toolchain, not just `GOOS`/`GOARCH`), inflates binary size, and complicates static linking. Many teams treat "introduce cgo" as a significant architectural decision, not a convenience.

### 5. Rust: the cleanest FFI, and the safe-wrapper pattern

Rust has no runtime GC and no relocation, so its FFI is the most direct of the four:

- **`extern "C" { fn foo(x: i32) -> i32; }`** declares a C function; calling it requires `unsafe` because the compiler can't verify the foreign side.
- **`#[repr(C)]`** on structs/enums forces C-compatible layout so they can cross the boundary.
- **`bindgen`** reads a C header and *generates* the `extern` blocks and `#[repr(C)]` structs automatically — the standard way to bind a large C library.
- **`cbindgen`** does the reverse: generates a C header *from* your Rust `extern "C"` functions, so C/other languages can call into your Rust.

The defining Rust idiom is the **safe-wrapper-over-unsafe-core** pattern: the raw `extern` calls live in a small `unsafe` module, and a hand-written safe API wraps them, encoding ownership and lifetimes in the type system (e.g., a struct whose `Drop` impl calls the C `free`, so leaks are impossible). This is exactly the pattern every other language *should* follow but only Rust *enforces* — and it's why Rust is increasingly the language people write the native core in (then bind to Python via PyO3, to Node via neon, to C via cbindgen).

---

## Code Examples

### JNI: local vs. global references and an exception check

```c
#include <jni.h>

JNIEXPORT void JNICALL
Java_Demo_work(JNIEnv *env, jobject self, jstring jname) {
    /* GetStringUTFChars returns a C string; may pin or copy. Must Release. */
    const char *name = (*env)->GetStringUTFChars(env, jname, NULL);
    if (name == NULL) return;             /* OutOfMemory pending */

    /* ... use name ... */

    (*env)->ReleaseStringUTFChars(env, jname, name);  /* required, or leak */

    /* If we called something that may throw, we MUST check before continuing. */
    if ((*env)->ExceptionCheck(env)) {
        return;   /* a Java exception is pending; do not keep calling JNI */
    }
}
```

### JNI critical region: zero-copy array access, kept tiny

```c
jbyte *buf = (*env)->GetPrimitiveArrayCritical(env, arr, NULL);  /* pins; blocks GC */
/* Do ONLY tight, non-blocking, no-JNI-call work here. */
long sum = 0;
jsize n = (*env)->GetArrayLength(env, arr);
for (jsize i = 0; i < n; i++) sum += buf[i];
(*env)->ReleasePrimitiveArrayCritical(env, arr, buf, 0);  /* unpin ASAP */
```

### Project Panama (FFM API): calling C `strlen` from pure Java

```java
import java.lang.foreign.*;
import java.lang.invoke.MethodHandle;

try (Arena arena = Arena.ofConfined()) {
    Linker linker = Linker.nativeLinker();
    MethodHandle strlen = linker.downcallHandle(
        linker.defaultLookup().find("strlen").orElseThrow(),
        FunctionDescriptor.of(ValueLayout.JAVA_LONG, ValueLayout.ADDRESS));

    MemorySegment cString = arena.allocateUtf8String("hello"); // off-heap, arena-scoped
    long len = (long) strlen.invoke(cString);                  // downcall
    System.out.println(len);                                   // 5
} // arena closes -> native memory freed deterministically
```

No C file, no `.so` of your own, no `JNIEnv`, and the memory is freed when the arena closes.

### cgo: copy data into C memory rather than passing a Go pointer C retains

```go
package main

/*
#include <stdlib.h>
#include <string.h>
*/
import "C"
import "unsafe"

// WRONG idea: hand C a pointer into a Go slice that C will keep.
// RIGHT: copy into C-owned memory.
func storeInC(data []byte) unsafe.Pointer {
	p := C.malloc(C.size_t(len(data)))          // C owns this; GC won't touch it
	C.memcpy(p, unsafe.Pointer(&data[0]), C.size_t(len(data)))
	return p                                     // caller must C.free(p) later
}
```

### Rust: bindgen-style declaration + safe wrapper with Drop

```rust
use std::os::raw::c_char;

// (bindgen would generate these from a header.)
extern "C" {
    fn create_thing() -> *mut Thing;
    fn destroy_thing(t: *mut Thing);
    fn thing_value(t: *mut Thing) -> i32;
}
#[repr(C)]
struct Thing { _private: [u8; 0] } // opaque

// Safe wrapper: unsafe core, safe surface, leak-proof via Drop.
pub struct SafeThing(*mut Thing);

impl SafeThing {
    pub fn new() -> Self { SafeThing(unsafe { create_thing() }) }
    pub fn value(&self) -> i32 { unsafe { thing_value(self.0) } }
}
impl Drop for SafeThing {
    fn drop(&mut self) { unsafe { destroy_thing(self.0) } } // free runs automatically
}
```

A caller of `SafeThing` writes pure safe Rust and *cannot* forget to free or misuse the raw pointer.

---

## Coding Patterns

### Pattern 1: Handles for moving GCs, pins only briefly

Never cache raw addresses into JVM/Go heaps. Use handles; if you must touch raw bytes, pin (`GetPrimitiveArrayCritical`) for the shortest possible window and never block or call back inside it.

### Pattern 2: Copy across the boundary when ownership must transfer

If native code needs to *retain* data from a moving-GC runtime, copy it into native-owned memory (`C.malloc`, `Arena`) and track that ownership explicitly.

### Pattern 3: Safe wrapper over unsafe core (universal)

Confine `unsafe`/raw FFI to a small module; expose a type whose destructor (`Drop`, `__del__`, `AutoCloseable`/`Arena`) guarantees cleanup. Encode ownership in the type, not in comments.

### Pattern 4: Generate bindings, don't hand-write them

Use `bindgen` (C→Rust) or `cbindgen` (Rust→C) so declarations stay in sync with headers. Hand-written `extern` blocks drift and silently corrupt when the C side changes.

---

## Best Practices

1. **Know your GC's movement semantics before designing a binding** — it dictates handles vs. pointers.
2. **Keep JNI critical regions microscopic** — no blocking, no JNI calls, no upcalls inside them.
3. **Track every JNI global ref**; delete it deterministically, treat a leak as a Java leak.
4. **Prefer Panama for new Java native work**; reserve JNI for legacy or where Panama can't reach.
5. **Treat cgo as architecture**: measure call frequency, batch crossings, and weigh the cross-compilation cost.
6. **Never let C retain a Go pointer**; copy into C memory and own it.
7. **In Rust, push raw FFI into a tiny `unsafe` core** and wrap it with a `Drop`-backed safe type.
8. **Auto-generate bindings** and re-generate when headers change.

---

## Edge Cases & Pitfalls

- **Caching a `JNIEnv*` across threads.** It's per-thread; using it on another thread is undefined behavior.
- **Ignoring a pending Java exception** after a JNI call, then making more JNI calls — undefined behavior.
- **Local reference table overflow** in a native loop that creates many jobjects without freeing them.
- **Leaked global ref** that pins a Java object forever — a native-caused Java memory leak.
- **Blocking or calling back inside a critical region** — stalls or deadlocks the collector.
- **cgo in a hot loop** — the per-call stack switch becomes the dominant cost (the cgo cliff).
- **Passing a Go pointer to C that C stores** — GC moves/frees it, C now holds a dangling pointer.
- **Adding cgo and discovering cross-compilation broke** — you now need a C cross-toolchain.
- **Mis-describing a Panama `FunctionDescriptor`** — still crashes; the FFM API is safer but not magic.
- **Hand-written Rust `extern` block drifting from the C header** after a library upgrade — silent layout corruption; use `bindgen`.

---

## Apply it

1. State the system invariant that **FFI from High-Level Languages** must protect.
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

- Which invariant must remain true when FFI from High-Level Languages fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
