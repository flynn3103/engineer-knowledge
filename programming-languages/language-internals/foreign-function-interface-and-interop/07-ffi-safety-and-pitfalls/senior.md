# FFI Safety & Pitfalls — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **FFI Safety & Pitfalls** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Hazard Class 5: Threading & Reentrancy

This class is where FFI bugs become *intermittent* and therefore worst to debug. The boundary connects two threading worlds that do not share assumptions.

**The Python GIL.** CPython lets only one thread run Python bytecode at a time. Two rules follow for FFI:

- **Release the GIL around blocking or long native calls.** If a C function blocks (network, disk, a long compute) while holding the GIL, *every other Python thread is frozen* — and if that C call tries to call back into Python, you deadlock. `ctypes` releases the GIL around foreign calls by default; hand-written C extensions use the `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` macros.
- **Never touch a Python object without holding the GIL.** If native code (on a thread you released the GIL on, or a thread C created) manipulates `PyObject`s without re-acquiring the GIL (`PyGILState_Ensure`), it corrupts the interpreter. Refcount updates are not atomic under the boundary unless the GIL is held.

**JNI thread attach/detach.** A Java thread can make JNI calls freely. But a *native* thread — one the C library created — cannot touch the JVM until it calls `AttachCurrentThread` to get a valid `JNIEnv`, and must `DetachCurrentThread` before it dies. Forgetting to attach is a crash; forgetting to detach can leak or, on some JVMs, prevent shutdown. Critically, **a `JNIEnv*` is per-thread and must never be cached and reused on a different thread.**

**Which thread does the callback run on?** When you give a C library a callback, you must learn *which thread it will be invoked from*. The library may call back synchronously on your thread, or asynchronously from an internal worker thread, or from a thread pool. Each case has different rules: a callback from a foreign thread must attach to the JVM, must acquire the GIL, must not assume thread-local state from the calling thread exists.

**Calling back into the runtime from the wrong thread.** The recurring failure: native code invokes your callback from a thread the runtime does not know about, and the callback touches managed state as if it were on a managed thread. The defense is to make callbacks self-contained: attach/acquire as needed, do minimal work, and hand off to the runtime's own thread (e.g. post to an event loop, a Go channel, a Java executor) rather than doing managed work inline on the foreign thread.

**Signal-handler restrictions.** If a native library installs signal handlers, or if your FFI runs inside one, remember that almost nothing is safe inside a signal handler — not allocation, not most locks, not most runtime calls. A handler that calls back into a managed runtime is a latent deadlock or crash.

**Thread-safety of the native library itself.** Many C libraries are not thread-safe, or are thread-safe only with a per-context object. If two of your threads call a non-reentrant library concurrently, you corrupt its internal state. You must serialize access (a lock around the library) or give each thread its own context. Read the library's threading documentation as carefully as its memory documentation.

**cgo and the Go scheduler.** A cgo call blocks the OS thread it runs on for the call's duration; the Go scheduler moves other goroutines to other threads, but a flood of blocking cgo calls can exhaust the thread pool. Go also forbids passing Go pointers that themselves contain Go pointers into C (the cgo pointer-passing rules), precisely because the collector cannot track them across the boundary.

### Hazard Class 6: Resource Leaks & Robustness

**Native handle and reference leaks.** Every native resource acquired through FFI — file descriptors, library handles, JNI global references, allocated buffers — must be released on *every* path, including error paths. JNI is notorious here: **local references accumulate** within a long native method (e.g. a loop creating many Java objects), and if you do not delete them or manage a local frame, you hit the local-reference table limit and crash. **Global references leak** if you allocate them and never delete them — a slow memory growth that eventually OOMs a long-running service.

**RAII does not cross the boundary.** Your language's automatic cleanup (Rust `Drop`, C++ destructors, Python `__del__`, `try-with-resources`) does not run when control is on the C side, and C's cleanup does not run when control is on yours. You must bridge cleanup explicitly: a wrapper object whose destructor calls the C free function, registered so it runs even on the error path.

**No isolation: a native crash kills the process.** This is the robustness fact that drives architecture. There is no `try/catch` for a segfault in native code. One bug in one native call takes down the entire process — every request in flight, every other tenant. When the native code is **untrusted** (parsing attacker-controlled input) or **unstable** (a flaky third-party library, a GPU driver), the only robust answer is **out-of-process isolation**: run the native code in a separate process, talk to it over a pipe or socket, and when it crashes, restart just that process. You trade IPC overhead for blast-radius containment. (Expanded at the professional level.)

### The Discipline: A Thin, Audited Unsafe Boundary

Everything above argues for one architectural pattern, which the Rust community formalized but every language can apply:

1. **Confine unsafe operations to a small module.** All raw pointers, manual frees, type casts, and FFI declarations live in one place — the `unsafe`/`extern` layer. Nothing outside it touches a raw pointer.
2. **Validate everything at the boundary.** Null-check, bounds-check, validate enums and lengths, reject malformed input *before* it reaches C. The boundary assumes the outside (and untrusted input) is hostile.
3. **Expose a safe API.** Above the boundary, callers see ordinary safe types (a `String`, a `Vec`, an idiomatic error). They *cannot* trigger UB because the unsafe layer does not give them the tools to.
4. **Encode ownership in types.** A handle wrapper that frees in its destructor; a lifetime parameter that prevents using a borrowed buffer after it is freed; a non-`Copy` owning type so it cannot be double-freed.
5. **Document every contract.** Each unsafe function states its safety precondition ("`ptr` must be non-null and point to `len` valid bytes"). The reviewer checks the call sites against the contract.
6. **Test the boundary under sanitizers and checkers.** ASan/Valgrind for memory, TSan for threading, `-Xcheck:jni` for JNI, the cgo `cgocheck` and `-race` flags for Go. These catch what review misses.
7. **Minimize the surface.** Fewer FFI functions, simpler data, opaque handles over shared structs. Every function in the boundary is a function someone must audit.
8. **Isolate when robustness demands it.** For untrusted or unstable native code, put a process boundary around it.

The payoff: the dangerous code is small enough to prove correct and rarely changes; the safe code is large, idiomatic, and cannot misuse the boundary.

### Real Incidents (Defensive Lessons)

These are the shapes of real production failures; study them as failure modes to engineer against.

- **JNI reference leaks crashing services.** Long-running JVM services that create JNI global references in a native callback and never delete them grow memory until they OOM-kill — a slow, hard-to-attribute leak. A loop creating local references without a local frame hits the reference-table limit and crashes outright. The fix is disciplined reference management and `-Xcheck:jni` in CI.
- **`ctypes` `restype`/`argtypes` mistakes corrupting results.** Production Python code that omitted `restype` for a function returning a pointer or `size_t` read a truncated value and either crashed or silently produced wrong data on certain inputs. The fix is explicit, reviewed type declarations and tests across value ranges.
- **Panic/exception across FFI as UB.** Libraries exposing `extern "C"` functions that let a Rust panic or C++ exception unwind into a C caller exhibited crashes and corruption that varied by compiler and optimization level. The fix is `catch_unwind`/`catch(...)`/`recover` at every export.
- **GC-collected object used by native code.** .NET and JVM integrations where a managed object backing a native pointer was collected or moved mid-call crashed only under load (when the GC actually ran). The fix is `GC.KeepAlive`/pinning for the precise lifetime of the native use.

---

## Code Examples

### Example 1: Releasing and re-acquiring the GIL (CPython C extension)

```c
static PyObject *do_blocking_work(PyObject *self, PyObject *args) {
    long n;
    if (!PyArg_ParseTuple(args, "l", &n)) return NULL;

    long result;
    Py_BEGIN_ALLOW_THREADS          /* ✅ release the GIL: other Python threads run */
    result = expensive_native_call(n);   /* no Python objects touched here */
    Py_END_ALLOW_THREADS            /* ✅ re-acquire before touching Python again */

    return PyLong_FromLong(result); /* now safe to build a Python object */
}
```

The blocking call runs without the GIL so the rest of the program stays responsive; the GIL is re-acquired before any `PyObject` is created. Touching a `PyObject` between the two macros would corrupt the interpreter.

### Example 2: A native thread attaching to the JVM (JNI)

```c
/* Called from a thread the C library created — the JVM does not know it yet. */
void on_native_event(MyContext *ctx, int code) {
    JNIEnv *env;
    JavaVM *vm = ctx->vm;

    /* ✅ attach: obtain a valid JNIEnv for THIS thread */
    if ((*vm)->AttachCurrentThread(vm, (void **)&env, NULL) != JNI_OK) return;

    jclass cls = (*env)->GetObjectClass(env, ctx->listener);
    jmethodID mid = (*env)->GetMethodID(env, cls, "onEvent", "(I)V");
    (*env)->CallVoidMethod(env, ctx->listener, mid, code);

    /* ✅ check for a pending Java exception before doing anything else */
    if ((*env)->ExceptionCheck(env)) {
        (*env)->ExceptionDescribe(env);
        (*env)->ExceptionClear(env);
    }

    (*env)->DeleteLocalRef(env, cls);           /* avoid local-ref accumulation */
    (*vm)->DetachCurrentThread(vm);             /* ✅ detach before the thread exits */
}
```

Three senior rules in one function: attach the foreign thread, check-and-clear the pending exception after a call that can throw, and detach before the thread dies.

### Example 3: Managing JNI local references in a loop (the leak that crashes)

```c
/* Creating many objects in one native call: local refs accumulate. */
for (int i = 0; i < count; i++) {
    /* ✅ bound the local-reference table with a frame per iteration */
    if ((*env)->PushLocalFrame(env, 16) != 0) return;

    jobject item = build_item(env, i);     /* creates local refs */
    process(env, item);

    (*env)->PopLocalFrame(env, NULL);      /* ✅ frees all locals from this frame */
}
```

Without the local frame (or explicit `DeleteLocalRef`), a long loop exhausts the local-reference table and crashes. This is a classic JNI production incident.

### Example 4: The audited boundary — thin unsafe layer, safe API (Rust)

```rust
// ---- the ENTIRE unsafe surface, small and validated ----
mod ffi {
    use std::os::raw::{c_char, c_int};
    extern "C" {
        pub fn parse_doc(input: *const c_char, len: usize) -> *mut Doc;
        pub fn doc_free(doc: *mut Doc);
        pub fn doc_title(doc: *const Doc) -> *const c_char;
    }
    pub enum Doc {}   // opaque: we never look inside
}

// ---- the safe API everyone above uses ----
pub struct Document(*mut ffi::Doc);   // owns the native resource

impl Document {
    pub fn parse(input: &[u8]) -> Result<Document, ParseError> {
        // ✅ validate at the boundary before touching C
        if input.is_empty() { return Err(ParseError::Empty); }
        let ptr = unsafe { ffi::parse_doc(input.as_ptr() as *const _, input.len()) };
        if ptr.is_null() { return Err(ParseError::Invalid); }  // ✅ null-check
        Ok(Document(ptr))
    }

    pub fn title(&self) -> String {
        let c = unsafe { ffi::doc_title(self.0) };
        if c.is_null() { return String::new(); }
        unsafe { std::ffi::CStr::from_ptr(c) }.to_string_lossy().into_owned()
    }
}

impl Drop for Document {
    fn drop(&mut self) {
        // ✅ RAII bridges cleanup across the boundary; freed exactly once
        unsafe { ffi::doc_free(self.0) }
    }
}
```

`Document` cannot be double-freed (it owns the pointer and frees once on `Drop`), cannot be used after free (its lifetime governs the pointer), and validates input before calling C. Callers above never see a raw pointer.

### Example 5: Serializing access to a non-thread-safe library (Go)

```go
var libMu sync.Mutex   // the C library is not thread-safe

func Process(data []byte) (Result, error) {
    libMu.Lock()                 // ✅ serialize: only one goroutine in the library
    defer libMu.Unlock()

    cData := C.CBytes(data)
    defer C.free(cData)          // ✅ matching free on all paths

    rc := C.lib_process(cData, C.size_t(len(data)))
    if rc != 0 {
        return Result{}, fmt.Errorf("lib_process failed: %d", int(rc))
    }
    return readResult(), nil
}
```

If the C library keeps global state and is not reentrant, the mutex is the difference between correct results and silent corruption under concurrency.

---

## Coding Patterns

**Pattern 1: One unsafe module, everything else safe.** Confine all FFI and raw-pointer code to a single, small, reviewable module.

**Pattern 2: Own the handle in a wrapper type with a destructor.** Free exactly once on all paths; make the type non-copyable so it cannot be double-freed.

**Pattern 3: Validate at the edge.** Null-check, bounds-check, validate enums and lengths before C sees the data.

**Pattern 4: Attach/acquire in every foreign-thread callback.** JNI attach + exception check, or `PyGILState_Ensure`, then do minimal work and hand off to a runtime-owned thread.

**Pattern 5: Bound JNI local references.** Use local frames in loops; delete globals explicitly.

**Pattern 6: Serialize or partition non-thread-safe libraries.** A lock around the library, or one context per thread.

**Pattern 7: Isolate untrusted/unstable native code in a separate process.** Contain the crash.

---

## Best Practices

1. **Know which thread every callback runs on,** and attach/acquire accordingly.
2. **Release the GIL around blocking native calls; never touch Python objects without it.**
3. **Attach native threads to the JVM, check-and-clear exceptions, detach before exit; never share a `JNIEnv` across threads.**
4. **Manage JNI references** with local frames and explicit global deletion.
5. **Confine unsafe code to a thin, validated boundary; expose a safe API; encode ownership in types.**
6. **Bridge cleanup explicitly** with wrapper destructors that run on all paths.
7. **Run TSan, ASan/Valgrind, `-Xcheck:jni`, `-race`/`cgocheck`** in CI.
8. **Isolate untrusted or unstable native code out-of-process.**
9. **Minimize the FFI surface;** prefer opaque handles.

---

## Edge Cases & Pitfalls

- **Cached `JNIEnv` reused on another thread.** A `JNIEnv*` is per-thread; reusing it elsewhere is UB. Always fetch it from `AttachCurrentThread` on the current thread.
- **Callback re-enters a non-reentrant library.** The library calls your callback, and your callback calls back into the library while it is mid-operation. If the library is non-reentrant, this corrupts it.
- **GIL deadlock.** Native code holds the GIL and blocks waiting on a Python thread that needs the GIL. Release before blocking.
- **Signal handler calls the runtime.** A handler that allocates or locks (e.g. calls back into managed code) deadlocks or crashes; signal handlers are restricted to async-signal-safe operations.
- **cgo thread exhaustion.** Many simultaneous blocking cgo calls consume OS threads; the Go runtime may spawn many threads or stall. Bound concurrency.
- **Global reference leak in a callback.** A native callback that creates a JNI global reference per event and never deletes it slowly OOMs the service.
- **Cleanup skipped on the error path.** An early return between acquire and release of a native handle leaks it. Use `defer`/RAII/`finally`.

---

## Common Mistakes

1. Touching managed state (Python objects, Java objects) from a foreign thread without acquiring/attaching.
2. Caching and reusing a `JNIEnv*` across threads.
3. Holding the GIL across a blocking native call.
4. Accumulating JNI local references in a loop; leaking global references.
5. Calling a non-thread-safe C library concurrently without serialization.
6. Letting cleanup be skipped on an error path.
7. Spreading raw FFI calls throughout the codebase instead of confining them.
8. Running untrusted native parsers in-process and being surprised by a crash.

---

## Tricky Points

- **Intermittent by nature.** Threading and GC FFI bugs reproduce only under specific timing or load, so green tests prove little. Sanitizers and stress tests under TSan are how you find them.
- **"Thread-safe" has fine print.** A library may be thread-safe only with one context per thread, or only for read operations. Read precisely.
- **The callback's thread is the library's choice, not yours.** Never assume the callback runs on the thread that registered it.
- **Out-of-process is sometimes the *only* correct answer.** For genuinely untrusted input, no amount of in-process care removes the fact that one bug crashes everything.

---

## Apply it

1. State the system invariant that **FFI Safety & Pitfalls** must protect.
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

- Which invariant must remain true when FFI Safety & Pitfalls fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
