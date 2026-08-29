# The Big Picture (Compiler Architecture) — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **The Big Picture (Compiler Architecture)** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## The Build-vs-Buy Decision for a New Language

The pivotal architectural choice when building a language: **reuse a mature
middle/back end or write your own.**

- **Reuse LLVM** (Rust, Swift, Julia, Clang): you write only a front end and lowering
  to LLVM IR, and inherit a world-class optimizer plus every backend (x86, ARM,
  RISC-V, Wasm). Cost: LLVM is large, slow to build, and its compile times can
  dominate; you're coupled to its IR and release cadence.
- **Reuse Cranelift** (Wasmtime, some Rust debug builds): far faster compilation,
  fewer targets and optimizations — a good fit when *compile speed* beats peak codegen
  (JITs, debug builds).
- **Roll your own back end** (Go's compiler, V8, HotSpot): full control over compile
  speed, codegen, and runtime integration (GC, stacks), at the cost of doing
  instruction selection/regalloc/scheduling yourself for every target. Go did this
  deliberately for fast builds and tight runtime integration.

The decision hinges on: how many targets you need, whether peak performance or
compile speed dominates, how tightly the codegen must integrate with your runtime
(GC safepoints, stack maps), and team size.

---

## Where to Put the Optimizer: AOT, JIT, or Both

The same pipeline, relocated in time:

- **Pure AOT** (C/C++/Rust/Go): all stages at build time; fast startup, no warmup, no
  runtime codegen, AOT-friendly. No access to runtime profiles, so it relies on PGO
  (a training run) for profile-guided wins.
- **Pure JIT / mixed** (JVM, V8): a thin AOT front end to bytecode, then runtime
  optimization driven by real profiles (tiering, OSR, deopt). Peak throughput and
  adaptivity, but warmup cost and runtime codegen as an attack surface.
- **Both** (Spring AOT, GraalVM native-image, .NET ReadyToRun): pre-compile to reduce
  startup while keeping (or dropping) runtime adaptivity.

The cold-start and native-image pressures of serverless have pushed the industry
toward moving more work to build time — a live architectural debate your pipeline
design must answer based on deployment target and SLOs.

---

## Diagnostics as a Product

Error reporting is a cross-cutting concern that spans the whole front end, and at the
professional tier it's a *feature*, not an afterthought. Clang's caret diagnostics,
Rust's `rustc --explain` and suggestion-rich errors, and Elm's famously friendly
messages drove adoption. Engineering them requires: preserving accurate **source
spans** through every transformation, **error recovery** so one mistake doesn't abort
the whole compile (report many errors per run), suggested fixes, and stable error
codes. A compiler that fails fast with a cryptic message loses to one that explains
the problem and proposes a fix.

---

## Trust, Reproducibility & Supply Chain

- **Reproducible builds:** the same source + toolchain must produce bit-identical
  output, so binaries can be independently verified. This requires controlling
  nondeterminism (timestamps, paths, hash-map iteration order, parallelism) in the
  compiler — a real engineering effort (Debian, Go, and others invested heavily).
- **Trusting Trust:** Thompson's attack — a compiler binary that inserts a backdoor
  when compiling login *and* when compiling itself — means you can't fully trust a
  binary from its source alone. Diverse double-compilation (building with a second,
  independent compiler and comparing) is the known mitigation.
- **Toolchain provenance:** in regulated/secure contexts you must pin and verify the
  exact compiler, flags, and dependencies that produced a binary (SLSA, signed
  toolchains).

---

## Best Practices

- **Choose the middle/back end by your real constraint** (targets, compile speed,
  runtime integration), not by prestige.
- **Decide the AOT/JIT split from the deployment target and SLOs**, and revisit it as
  those change (e.g. adding native-image).
- **Treat diagnostics as a product** — invest in spans, recovery, and suggestions.
- **Make builds reproducible** and pin the toolchain for verifiable, secure releases.
- **Keep the IR contract stable** so front ends and back ends can evolve
  independently.

---

## Edge Cases & Pitfalls

- **LLVM compile-time tax:** reusing LLVM can make *your* compiler slow; some
  languages add a fast non-LLVM debug backend (Cranelift, Go-style) for iteration.
- **IR version skew:** coupling to an external IR (LLVM) means tracking its breaking
  changes across releases.
- **Cross-compilation foot-guns:** sysroot/triple/host-vs-target confusion silently
  produces wrong-arch binaries.
- **Nondeterminism leaking into output:** breaks reproducible builds; hunt down
  hash-ordering and timestamp sources.
- **Diagnostics regressions:** a refactor that drops source spans degrades every error
  message at once.

---

## Apply it

1. Define the user or business outcome that **The Big Picture (Compiler Architecture)** should improve.
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

- Which measurable outcome justifies investing in The Big Picture (Compiler Architecture)?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
