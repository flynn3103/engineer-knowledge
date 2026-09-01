# FFI and Interoperability — Professional

CPython’s C API distinguishes borrowed and owned references; JNI adds local/global references and thread attachment; Rust uses `repr(C)` but still requires aliasing and lifetime invariants; WebAssembly component interfaces trade native ABI freedom for sandboxed portability.

Dashboards track boundary latency, copies, native memory, and crash rate. Runbooks include symbolization and version rollback. Further reading: System V ABI, CPython C API, JNI specification, Rustonomicon FFI, and WebAssembly component model.
