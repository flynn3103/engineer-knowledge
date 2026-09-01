# Language Security Internals — Professional

Rust’s ownership blocks broad memory-unsafety classes but `unsafe` remains a review boundary. LLVM CFI and ARM pointer authentication constrain control-flow attacks. V8 isolates and WebAssembly linear memory provide software isolation, while Spectre shows speculation can bypass architectural boundaries.

Govern unsafe code inventory, compiler hardening, sandbox escapes, dependency provenance, and patch latency. Further reading: Spectre paper, LLVM CFI design, Rust unsafe-code guidelines, and V8 sandbox documentation.
