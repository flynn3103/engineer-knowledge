# The Big Picture (Compiler Architecture) — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **The Big Picture (Compiler Architecture)** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## The Three-Stage Architecture

The canonical split:

- **Front end** — language-dependent. Lexing, parsing, semantic analysis (name
  resolution, type checking). Produces a typed AST / high-level IR. Knows
  everything about the *source language*, nothing about the *target machine*.
- **Middle end** — language- and target-independent. Operates on the IR: dataflow
  analysis and the bulk of optimization (inlining, constant folding, dead-code
  elimination, loop transforms). The portable heart of the compiler.
- **Back end** — target-dependent. Instruction selection, register allocation,
  instruction scheduling, target-specific peephole. Knows everything about the
  *machine*, nothing about the *source language*.

The discipline is that information flows downward and each stage speaks only to its
neighbors through a defined IR. The middle end never sees a token; the front end
never sees a register.

---

## The M×N Problem and the Shared IR

Why the split pays off: suppose you support **M** source languages and **N** target
architectures. A monolithic compiler-per-pair needs M×N implementations. Factor a
shared IR through the middle, and you need **M** front ends + **N** back ends =
**M+N**. Every optimization written once on the IR benefits every language and every
target.

This is the entire thesis of **LLVM**: a well-specified IR (typed, SSA, virtual
registers) as a "narrow waist" so that Clang (C/C++/Obj-C), Rust, Swift, Julia, and
dozens more share one optimizer and one set of backends. Add a backend for a new
chip and *every* LLVM language can target it; add a frontend for a new language and
it inherits *every* optimization and target for free.

---

## Real Toolchain Anatomies

- **LLVM/Clang:** Clang front end → **LLVM IR** → target backends. The IR is the
  product; `clang -emit-llvm -S` shows it.
- **GCC:** language front ends → **GENERIC** (language-independent tree) → **GIMPLE**
  (simplified, SSA form for optimization) → **RTL** (register transfer language, near
  the machine) → assembly. Three IRs, progressive lowering.
- **JVM:** `javac` is a *thin* front end (lex/parse/typecheck → **bytecode**); the
  heavy optimization happens later in the JIT (C1/C2) at runtime. The "compiler" is
  split across build time and run time.
- **V8:** parser → **Ignition** bytecode → **TurboFan/Maglev** optimizing JIT — a
  runtime pipeline driven by profiling.
- **rustc:** parse → AST → **HIR** (desugared) → **MIR** (borrow-check + dataflow +
  some optimization) → **LLVM IR** → LLVM backend. Rust reuses LLVM's middle/back end
  entirely.

Notice the recurring shape: a language-specific front producing a portable IR, then
a shared optimizer, then a target-specific back. Even the JIT-based runtimes follow
it; they just relocate stages to runtime.

A crucial distinction: the **driver** vs the **toolchain**. `gcc`/`clang` are
*drivers* — they orchestrate the preprocessor, the actual compiler (`cc1`), the
assembler (`as`), and the linker (`ld`). "The compiler" people invoke is usually the
driver coordinating several programs; the real compiler is one stage in a toolchain.

---

## Passes, Lowering, and the Narrow Waist

A modern compiler is organized as a sequence of **passes**, each a function
`IR -> IR` (analysis passes annotate; transform passes rewrite). **Lowering** is the
movement from higher, source-like IRs to lower, machine-like ones — GCC's
GENERIC→GIMPLE→RTL and rustc's HIR→MIR→LLVM-IR are lowering chains. Each level is
chosen so that some class of work is *easy* there (borrow-checking on MIR,
target-independent opts on a mid IR, register allocation on a low IR).

The "narrow waist" idea: keep the central IR small, well-specified, and stable, so
many producers and consumers can plug into it — the same architectural pattern as
IP in networking or POSIX in operating systems. **MLIR** generalizes this with
multiple coexisting IR "dialects" and progressive lowering between them, which is
why it underpins modern ML compilers.

Single-pass compilers (classic Pascal, some teaching compilers) do everything in one
sweep — fast, low-memory, but limited optimization and awkward forward references.
Multi-pass is the norm precisely because separating concerns enables the reuse and
optimization above.

---

## Best Practices

- **Respect the phase boundaries.** Don't let target details leak into the front end
  or source semantics into the back end; the IR contract is what keeps the compiler
  maintainable and reusable.
- **Reuse a mature middle/back end** (LLVM, Cranelift) when building a new language —
  you inherit decades of optimization and every target.
- **Pick IR levels by the work they enable**, not arbitrarily; each lowering should
  make some analysis natural.
- **Invest in diagnostics** as a first-class cross-cutting concern — Clang/Rust/Elm
  show error quality is a product feature, and it spans all front-end phases.

---

## Edge Cases & Pitfalls

- **Bootstrapping.** A compiler written in its own language needs an existing
  compiler to build the first version (then it self-hosts). Ken Thompson's
  *Reflections on Trusting Trust* shows a self-hosting compiler can hide a backdoor
  that survives even a clean source recompile — a sobering supply-chain lesson.
- **Cross-compilation.** Distinguish **build** (where the compiler is built),
  **host** (where it runs), and **target** (what it emits for). Confusing these is a
  classic source of broken cross builds.
- **Phase leakage.** The C "lexer hack" (the lexer needing symbol-table info) is a
  famous breach of the clean front-end layering.
- **Mistaking the driver for the compiler** when debugging — a flag may belong to
  `ld`, not `cc1`.

---

## Apply it

1. State the system invariant that **The Big Picture (Compiler Architecture)** must protect.
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

- Which invariant must remain true when The Big Picture (Compiler Architecture) fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
