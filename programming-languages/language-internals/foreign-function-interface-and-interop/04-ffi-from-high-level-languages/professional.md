# FFI from High-Level Languages — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **FFI from High-Level Languages** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Upcalls are the dangerous direction

A **downcall** (managed→native) is controlled: your managed code initiates it, on a thread the runtime owns, at a moment of your choosing. An **upcall** (native→managed, i.e. a callback) inverts all of that. The native library decides *when* the callback fires, *on which thread*, and *with what locks held*. Three independent hazards follow:

- **Wrong thread.** The callback may run on a thread the native library created — a thread the runtime has never seen. Touching a managed object from an unattached thread is undefined behavior (JVM) or a crash/corruption (CPython without the GIL).
- **GC/relocation mid-callback.** In a moving-GC runtime, a callback that grabs raw pointers before the GC and uses them after is holding stale addresses.
- **Re-entrancy and locks.** The native library may hold an internal lock while invoking your callback. If your callback calls *back into* that library, you deadlock. If it blocks, you stall the library.

The professional rule: **treat every callback as running on a hostile, unknown thread with unknown locks held, until you've proven otherwise.** Do the minimum, attach correctly, and don't call back in.

### 2. Thread attachment: making a foreign thread safe to use

When native code wants to run managed code on a thread the runtime didn't create, the thread must be **attached** first.

- **CPython:** a non-Python thread must call `PyGILState_Ensure()` to acquire the GIL and register thread state, do its Python work, then `PyGILState_Release()`. Skipping this and touching a `PyObject*` from a foreign thread corrupts the interpreter.
- **JVM:** the thread calls `(*vm)->AttachCurrentThread(...)` to get a `JNIEnv*`, does JNI work, and `DetachCurrentThread()` before exiting (a thread that exits while attached can crash the JVM or leak). Crucially, the `JNIEnv*` is **per attachment/thread** — never reuse one captured on a different thread.
- **Go (callbacks into Go from C):** cgo supports `//export`ed Go functions callable from C, but the call must originate on a thread cgo can map to a goroutine; long-lived C threads calling exported Go functions need care, and you cannot store Go pointers across the boundary.
- **Panama (upcalls):** you wrap a Java `MethodHandle` as a native function pointer (an "upcall stub") bound to an `Arena`; the FFM API manages the thread state, but the stub's lifetime is the arena's, and calling it after the arena closes is a crash.

The unifying idea: **a foreign thread is invisible to the runtime until it announces itself, and it must un-announce itself before it dies.**

### 3. Exceptions and errors across the callback boundary

Native code has no concept of a Java/Python exception. If your callback throws and you let the exception propagate *into* C, behavior is undefined — the C library's stack unwinding doesn't know about it. So every callback must **catch everything at the boundary** and convert it to an error code or status the C side understands (often: set a flag, return a sentinel, and re-raise on the managed side later). Equally, after a JNI upcall you must `ExceptionCheck` and clear or handle a pending exception before doing more JNI work. "Let it propagate" is a downcall luxury; in upcalls it's a crash.

### 4. The distribution problem: shipping native code that loads everywhere

Most *customer-reported* FFI failures are not crashes in your code — they're "it won't import on my machine." The native artifact must load on the target's OS, architecture, libc, and security policy.

**Python wheels.** A wheel containing a `.so` is tagged with platform info (e.g. `cp311-cp311-manylinux_2_17_x86_64`). The **manylinux** standard pins a baseline glibc so one wheel runs across many distros. **`auditwheel`** (Linux) and **`delocate`** (macOS) *bundle the dependent shared libraries into the wheel* so the user doesn't need libssl/libjpeg installed. Forget this and the user gets "cannot open shared object file." Alpine (musl libc) needs a separate **musllinux** wheel; a manylinux wheel won't run there. ARM64 (Apple Silicon, AWS Graviton) needs its own wheels.

**JNI libraries.** The `.so`/`.dll`/`.dylib` must be on `java.library.path` (or loaded by absolute path, or unpacked from the JAR to a temp dir at startup — the common pattern, e.g. what SQLite-JDBC does). Name and architecture must match; a 64-bit JVM can't load a 32-bit library.

**Node addons.** N-API gives **ABI stability** across Node major versions, so a single prebuilt `.node` keeps working — a huge improvement over the old NAN/V8-API era where every Node upgrade forced a recompile. Tools like `prebuild`/`prebuildify` ship per-platform binaries so users don't need a compiler.

**Signing and policy.** macOS **notarization/Gatekeeper** will refuse to load an unsigned/unquarantined dylib; you must sign (and often notarize) native artifacts. Windows has its own driver/DLL signing concerns. On hardened Linux, SELinux/AppArmor can block loading from certain paths.

### 5. Versioning and ABI compatibility over time

A shipped binding is a long-lived ABI contract. If the native library bumps its ABI (changes a struct layout, a function signature), your binding silently corrupts unless rebuilt against the new headers. Professionals **pin the native dependency version**, rebuild bindings when it changes, and prefer libraries with explicit ABI-stability promises. N-API is the gold standard here for Node; for C libraries, SONAME versioning (`libfoo.so.2`) is the signal — link against the major you tested.

---

## Code Examples

### CPython: a foreign thread safely calling Python via the GIL

```c
/* Called from a thread the Python interpreter did NOT create. */
void native_callback(int value) {
    PyGILState_STATE g = PyGILState_Ensure();   /* attach + acquire GIL */

    PyObject *cb = get_saved_callable();         /* a global ref we stored earlier */
    PyObject *res = PyObject_CallFunction(cb, "i", value);
    if (res == NULL) {
        PyErr_Print();        /* a Python exception fired in the callback; handle it
                                 HERE — never let it propagate into C */
    } else {
        Py_DECREF(res);
    }

    PyGILState_Release(g);    /* release GIL + detach state */
}
```

### JNI: attaching a native thread, then detaching before exit

```c
JavaVM *jvm;  /* captured once at load time */

void *native_thread_main(void *arg) {
    JNIEnv *env;
    (*jvm)->AttachCurrentThread(jvm, (void **)&env, NULL);  /* get a JNIEnv */

    /* ... JNI work, with ExceptionCheck after calls that can throw ... */

    (*jvm)->DetachCurrentThread(jvm);   /* REQUIRED before the thread exits */
    return NULL;
}
```

### Panama: an upcall stub whose lifetime is the arena

```java
Arena arena = Arena.ofShared();
Linker linker = Linker.nativeLinker();

// Wrap a Java method as a C-callable function pointer.
MethodHandle target = MethodHandles.lookup()
    .findStatic(MyCallbacks.class, "onEvent",
                MethodType.methodType(void.class, int.class));
MemorySegment stub = linker.upcallStub(
    target, FunctionDescriptor.ofVoid(ValueLayout.JAVA_INT), arena);

// Pass `stub` to native code as a function pointer.
// CAUTION: once `arena` is closed, calling the stub from C crashes.
```

### Python packaging: bundling dependent libs into a wheel

```bash
# Build the wheel, then bundle its non-system .so dependencies INTO it,
# and tag it with a manylinux baseline so it runs across distros.
python -m build --wheel
auditwheel repair dist/mypkg-1.0-cp311-cp311-linux_x86_64.whl \
    --plat manylinux_2_17_x86_64 -w dist/

# macOS equivalent:
# delocate-wheel dist/mypkg-1.0-cp311-cp311-macosx_11_0_arm64.whl
```

### Node: an N-API addon is ABI-stable across Node majors

```c
#include <node_api.h>
/* Built against the stable N-API; the resulting .node keeps loading
   across Node 18, 20, 22... without recompilation. Ship one prebuilt
   binary per (os, arch) and users never need a compiler. */
napi_value Init(napi_env env, napi_value exports) { /* ... */ return exports; }
NAPI_MODULE(NODE_GYP_MODULE_NAME, Init)
```

---

## Coding Patterns

### Pattern 1: Attach-do-minimum-detach for every foreign thread

Wrap all managed work done from a foreign thread in attach/detach (JVM) or GIL ensure/release (CPython). Never leave a thread attached at exit.

### Pattern 2: Callbacks are catch-all and non-re-entrant

Every callback catches all exceptions at the boundary, converts them to a status the C side understands, does the minimum work, and never calls back into the library that invoked it.

### Pattern 3: Bundle the dependency closure into the artifact

Use `auditwheel`/`delocate` (Python), unpack-from-JAR (Java), or `prebuildify` (Node) so the user installs one self-contained artifact and needs nothing preinstalled.

### Pattern 4: Pin and rebuild against the native ABI

Pin the native dependency's major/SONAME, rebuild bindings on every bump, and ship a test that asserts the ABI version at load time.

### Pattern 5: Sign and notarize as a release step

Treat code signing (and macOS notarization) as a non-optional pipeline stage, with a smoke test that loads the signed artifact on a clean machine.

---

## Best Practices

1. **Acquire the GIL / attach the thread before touching any managed object from foreign code.** No exceptions.
2. **Detach every attached JVM thread before it exits**, and release every `PyGILState`.
3. **Catch every exception inside a callback**; never let it propagate into native stack unwinding.
4. **Keep callbacks minimal and non-re-entrant**; assume the library holds a lock while calling you.
5. **Build the full platform matrix** (OS × arch × libc × runtime version) and test loading on clean images.
6. **Bundle dependent shared libraries** into the shippable artifact; don't assume the customer has them.
7. **Sign and notarize native binaries**; verify on a quarantined machine.
8. **Pin the native ABI and rebuild on every change**; assert the version at load time.
9. **Prefer ABI-stable interfaces** (N-API, SONAME-versioned C libs, Panama) to minimize the rebuild/recompile burden.

---

## Edge Cases & Pitfalls

- **Callback on an unattached thread.** Touching managed objects → undefined behavior / corruption. Always attach first.
- **JVM thread exits while still attached.** Crash or leak; `DetachCurrentThread` is mandatory.
- **Exception thrown out of a callback into C.** Native unwinding doesn't know about it → undefined behavior.
- **Re-entrant callback deadlock.** Callback calls back into the library that holds a lock while invoking it.
- **Calling a Panama upcall stub after its arena closed.** Use-after-free crash.
- **manylinux wheel on Alpine (musl).** Won't load; needs a musllinux build.
- **Missing `auditwheel`/`delocate` step.** "cannot open shared object file" on the customer's machine.
- **Wrong architecture artifact.** 64-bit runtime can't load a 32-bit library; Apple Silicon needs ARM64 wheels.
- **Unsigned dylib on macOS.** Gatekeeper refuses to load it.
- **Native ABI bumped without rebuild.** Silent struct/layout corruption; nothing errors.
- **Caching a `JNIEnv*`/GIL thread-state across threads.** Both are per-thread; cross-thread reuse corrupts.

---

## Apply it

1. Define the user or business outcome that **FFI from High-Level Languages** should improve.
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

- Which measurable outcome justifies investing in FFI from High-Level Languages?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
