# Intermediate Representations — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Intermediate Representations** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The IR is a contract with three audiences (and time)

An owned IR answers to:

- **Producers** — every front end that emits it. They want expressiveness and stability of the *input* contract; a breaking IR change forces every front end to update in lockstep.
- **Consumers** — every analysis/transform pass and every back end. They rely on invariants (SSA holds, types are sound, the CFG is well-formed, dominators are valid here). Weakening an invariant can silently break dozens of passes that assumed it.
- **Persisted artifacts** — if you serialize IR (LLVM bitcode, a cached MIR, a Wasm module), *past versions of yourself* are now a consumer. A `.bc` produced six months ago by an older compiler may be linked today (ThinLTO, distributed/cached builds). This forces **backward-compatibility policy** and **auto-upgrade**.

The professional discipline is to treat these as a *versioned interface*, not an implementation detail. LLVM, for instance, guarantees that older bitcode loads into newer LLVM (with auto-upgrade rewriting deprecated constructs); the textual `.ll` form is explicitly *less* stable, which is itself a deliberate contract decision (text is for humans and tests, bitcode is the durable wire format).

### 2. Information has a location and a cost

Every optimization needs certain facts, and facts live at certain altitudes:

- **Loop structure** is obvious in high-level IR, recoverable (via loop analysis) in mid-level CFG/SSA, and *gone* once lowered to flat machine code. So loop optimizations must run before that information is lost — or be re-derived at cost.
- **Source-level types and aliasing intent** (e.g., C's strict aliasing, Rust's `&mut` exclusivity) are present at the front end and must be *encoded as IR metadata* (TBAA, `noalias`) to survive lowering, because the optimizer otherwise cannot prove two pointers don't alias.
- **Overflow/UB facts** (`nsw`, `nuw`, `poison`) are front-end knowledge encoded into the IR so the mid-level optimizer can exploit them soundly.
- **Profile data** (branch weights, call counts) is metadata threaded through so PGO/FDO passes can prioritize.

The architectural question for any IR feature is therefore: **does this information need to survive to the pass that uses it, and if so, is it carried as a first-class construct, as droppable metadata, or re-derived by analysis?** Getting this wrong means either an optimization that can never fire (information lost too early) or an IR bloated with facts nobody consumes.

### 3. Verification, canonicalization, and the correctness budget

At scale, correctness is engineered, not hoped for:

- **Verifier** — enforces invariants after every transform in debug/CI builds. The non-negotiable floor.
- **Canonicalization** — collapses equivalent IR into one form (e.g., `x + 0 → x`, constants on the right, a single canonical loop shape) so downstream passes handle fewer cases and pattern-matching is reliable. MLIR makes canonicalization a first-class, per-op concept.
- **Translation validation / formal tooling** — tools like **Alive2** check that LLVM peephole optimizations are semantically correct (including UB/poison semantics), and **Csmith**-style random program generators feed **differential testing** across optimization levels and compilers. These catch the miscompiles that slip past unit tests.

A professional treats the verifier + canonicalizer + differential/translation-validation tooling as a *correctness budget*: how much of it you can afford to run continuously, and where you spend it (every commit vs nightly fuzzing).

### 4. The IR's memory/effect model is part of its semantics

Beginners think of an IR as "instructions." A production IR must precisely define **side effects, ordering, atomics, and aliasing**, because every "can I move/delete this?" optimization is a question about effects. LLVM encodes this through memory attributes, `atomic` orderings mirroring the C/C++ memory model, `noalias`/`readonly`/`readnone`, and TBAA metadata. Get the effect model wrong and the optimizer will, entirely "correctly" per the IR's stated rules, delete a volatile store or reorder across a fence — a real miscompile. The IR's semantics are *the contract for soundness*, and they must be written down, not folklore.

### 5. Extensibility as architecture: why MLIR exists

The pre-MLIR reality was that every domain that needed a higher-level abstraction (ML frameworks, hardware synthesis, polyhedral loop optimizers) either forked LLVM, bolted ad-hoc passes on, or built a private IR and a fragile bridge. MLIR's thesis: **make adding an IR level a supported, first-class operation.** A **dialect** is an independently-defined, independently-verified set of ops/types/attributes; dialects coexist in one module and lower into one another through shared infrastructure (rewrite patterns, a common verifier, a common pass manager, location/debug propagation). This turns "we need a new abstraction level" from a fork into a plugin. The professional lesson is not "use MLIR" but **design for extension**: assume someone will need a level you didn't anticipate, and make that addition cheap and verifiable rather than a fork.

### 6. Compile-time is a first-class output

Peak runtime performance is one axis; **compile time and predictability** are another, and for many users the dominant one. Cranelift exists because Wasm JITs and debug builds need *fast, predictable* compilation more than they need the last 10% of runtime speed. ThinLTO exists because monolithic LTO didn't scale to large programs. A professional IR architect treats compile-time, memory footprint of the IR, and determinism (reproducible builds) as outputs to be measured and budgeted — not afterthoughts. "The IR is 3x larger and constructs 2x slower but enables one more optimization" is a trade you must quantify, not assume.

---

## Architecting a Multi-Level IR

When you design the IR stack for a new compiler, the recurring decisions are:

1. **How many levels?** Too few and one IR juggles language-specific and machine-specific concerns (bugs, complexity). Too many and you pay for every lowering, verifier, and inter-level leak. GCC chose three; LLVM is effectively two (front-end-emitted LLVM IR + machine IR / SelectionDAG/GlobalISel), increasingly augmented by MLIR above it; rustc inserts MIR as an analysis level above LLVM IR. Decide by *which optimizations and analyses need which altitude*.

2. **Where does each analysis run?** Borrow checking → a high, control-flow-explicit level (MIR). Inlining/GVN/LICM → mid-level SSA. Register allocation/scheduling → low-level machine IR. Map each analysis to the altitude where its required information still lives.

3. **What's the SSA encoding?** φ-functions (LLVM, GIMPLE) vs block parameters (Cranelift, MLIR, Swift SIL). Block parameters compose better with generic argument handling and avoid special-casing φ in every pass.

4. **What's the stability contract per level?** In-memory IR can churn freely. A serialized level (bitcode, cached MIR, Wasm) needs a versioning + auto-upgrade policy. Decide *which* levels are persisted before you ship, because retrofitting stability is brutal.

5. **How is the effect/memory model specified?** Write down side-effect, ordering, atomic, and aliasing semantics explicitly. This is the soundness contract; folklore here causes miscompiles.

6. **How do you verify and test it?** Per-op verifiers, a module verifier, round-trip (print→parse→print) testing, differential testing across opt levels, and — if you can afford it — translation validation on the riskiest passes.

7. **Who owns it and how does it evolve?** A breaking IR change touches every producer and consumer. Establish an RFC/deprecation process before the IR has many stakeholders, not after.

---

## Code & Design Examples

### Example 1: Carrying alias intent across a lowering boundary (metadata)

A front end knows two pointers can't alias (Rust `&mut`, C `restrict`). If that knowledge isn't encoded, the mid-level optimizer must assume they might, and it can't reorder/eliminate loads:

```llvm
; Without noalias, the optimizer must assume %p and %q may overlap.
define void @copy(ptr %p, ptr %q) {
  ...
}

; With noalias, the load through %q can be hoisted/CSE'd across the store to %p.
define void @copy(ptr noalias %p, ptr noalias %q) {
  ...
}
```

The `noalias` attribute is front-end knowledge *encoded into the IR contract* so it survives to the pass that needs it. Drop it and a whole class of optimizations silently dies — an "altitude ledger" failure.

### Example 2: An effect fact that licenses (or forbids) a transform

```llvm
; A plain store can be eliminated if provably dead.
store i32 0, ptr %x

; A volatile store must NEVER be removed or reordered: it's an observable effect.
store volatile i32 0, ptr %x

; An atomic store participates in the memory model; ordering constrains motion.
store atomic i32 0, ptr %x release, align 4
```

The IR's effect model is what makes these three semantically different to the optimizer. A miscompile here (treating volatile as plain) is exactly the kind of bug the *written-down* memory model and the verifier exist to prevent.

### Example 3: A canonicalization that pays for itself downstream

```text
Before canonicalization:        After:
  %a = add i32 0, %x              %a = %x            ; identity folded
  %b = mul i32 %y, 2             %b = shl i32 %y, 1  ; strength-reduced/canonical
  %c = icmp eq i32 %z, %w        (constant on a fixed side, commutative ops normalized)
```

By normalizing equivalent forms into one, every downstream pattern-matcher handles fewer cases and fires more reliably. MLIR elevates this to a per-op `fold`/`canonicalize` hook; LLVM does it in InstCombine/InstSimplify.

### Example 4: Auto-upgrade as the IR's deprecation shim

```text
Old bitcode (v14) references a now-removed intrinsic:  @llvm.foo.legacy(...)
New compiler (v18) on load:  auto-upgrade rewrites it -> @llvm.foo.v2(...)
Result: a 2-year-old cached .bc still links into today's ThinLTO build.
```

This single mechanism is what lets the *in-memory* IR evolve while the *on-disk* contract stays stable. Designing it in early is cheap; bolting it on after artifacts proliferate is not.

### Example 5: Choosing the analysis altitude (rustc MIR)

Borrow checking needs control-flow-explicit, simplified Rust with explicit moves/drops — so rustc lowers HIR→**MIR** specifically to host that dataflow, *then* lowers MIR→LLVM IR for codegen. The design choice is "create an analysis-purpose IR level at the altitude where the needed information (places, moves, drop points, lifetimes) is explicit," rather than trying to borrow-check the AST (too unstructured) or LLVM IR (too low; Rust types already erased).

---

## Coding Patterns

### Pattern 1: Per-op verifier + module verifier, always on in CI

```text
each op defines verify():   shape, types, operand counts, region constraints
module verifier:            SSA dominance, terminators, phi/block-arg arity,
                            type consistency across the whole module
CI: run verifier after EVERY pass in assert builds
```

### Pattern 2: Round-trip and differential testing in the pipeline

```text
round-trip:    IR --print--> text --parse--> IR' ; assert IR == IR'
differential:  for opt in {O0,O1,O2,O3}: run(program, opt) -> same observable result
fuzz:          Csmith-style generator -> compile at all opt levels -> compare
validate:      Alive2-style check on risky peepholes (UB/poison-aware)
```

### Pattern 3: Encode front-end knowledge as IR facts, not comments

```text
aliasing intent  -> noalias / restrict / TBAA metadata
overflow facts   -> nsw / nuw / poison
value ranges     -> !range metadata
profile data     -> branch_weights / function-entry counts
```

If the optimizer can't see it in the IR, it doesn't exist.

### Pattern 4: Lower progressively, reuse shared lowerings

```text
domain dialect -> structured-control-flow dialect -> llvm dialect -> LLVM IR
each arrow: small, separately tested, verifiable; reuse common patterns across dialects
```

### Pattern 5: Treat the serialized format as a versioned protocol

```text
on write: tag with format version
on read:  if older, run auto-upgrade rewrites to current
policy:   never silently change serialized semantics; deprecate, shim, then remove
```

---

## Best Practices

- **Write down the IR's semantics — especially the effect/memory model.** Soundness is a specification, not folklore. Volatile, atomic, aliasing, and UB must be defined, not assumed.
- **Run the verifier after every pass in assert/CI builds.** Convert miscompiles into localized assertions at the offending pass.
- **Keep an explicit altitude ledger.** Know where each fact is born, consumed, and destroyed; carry across lowerings only what's actually consumed downstream.
- **Make the serialized format a versioned contract with auto-upgrade.** Decide which levels persist *before* artifacts proliferate; never break old artifacts silently.
- **Invest in differential testing and (for risky passes) translation validation.** Csmith/Alive2-style tooling catches the bugs unit tests can't.
- **Canonicalize aggressively.** Fewer equivalent forms means simpler, more reliable downstream passes.
- **Budget compile time and IR memory as outputs.** Measure them; a "free" optimization that doubles compile time often isn't worth it.
- **Architect for extension.** Assume a new abstraction level will be requested; make it a dialect/plugin, not a fork.
- **Govern IR changes like an API.** RFCs, deprecation windows, migration shims; a breaking change touches every producer and consumer.
- **Propagate provenance/debug locations through every lowering.** Diagnostics, sanitizers, and reproducible debugging depend on the IR→source link surviving.

---

## Edge Cases & Pitfalls

- **Information destroyed before its consumer runs** (the altitude-ledger bug): an optimization that *can never fire* because the lowering above it already discarded the needed fact. Silent, and shows up as "the compiler should have optimized this but didn't."
- **Effect-model misspecification**: treating a volatile/atomic/observable op as pure; the optimizer "correctly" eliminates or reorders it per the (wrong) rules. A genuine miscompile.
- **Serialized-format drift**: changing bitcode/Wasm/cached-MIR semantics without versioning; old artifacts now mean something different. Breaks caching, ThinLTO, distributed builds non-deterministically.
- **Verifier gaps**: an invariant assumed by many passes but not actually *checked*; a transform violates it and the failure manifests far downstream.
- **Metadata treated as load-bearing**: optimizers may drop metadata; if correctness (not just performance) depends on metadata that's allowed to vanish, you have a soundness bug. Metadata must be *droppable without changing meaning*.
- **Canonicalization loops / non-confluence**: two canonicalizers that undo each other, or a rewrite that never reaches a fixpoint — infinite compile or non-deterministic output.
- **Deopt/OSR vs aggressive reordering**: optimizing IR so freely that you can't reconstruct interpreter state at a deopt point; tier transitions and exceptions become unsound.
- **Cross-level type erasure**: an analysis needs a source-level type already erased at this altitude; either move the analysis up or carry the type as metadata.
- **Irreducible control flow at scale**: front ends emitting `goto`/computed-jump spaghetti that defeats reducible-loop assumptions; node-splitting blows up code size.

---

## Common Mistakes

1. Treating the IR as an implementation detail rather than a versioned, multi-audience contract.
2. Losing information (loop structure, types, alias intent) before the optimization that needs it can run.
3. Leaving the effect/memory model implicit, then shipping a volatile/atomic miscompile.
4. Shipping a serialized IR with no version field or auto-upgrade path.
5. Relying on metadata for correctness when metadata is allowed to be dropped.
6. Not running the verifier after every pass, then debugging a miscompile across the whole pipeline.
7. Skipping differential/fuzz testing and discovering miscompiles in the field.
8. Over-leveling the IR (too many altitudes) and drowning in lowering/verifier overhead.
9. Under-leveling (one IR for everything) and mixing language- and machine-specific concerns.
10. Forking the compiler to add an abstraction level instead of designing for extension.
11. Optimizing only for runtime, ignoring compile time / IR memory / determinism as outputs.
12. Breaking the IR-as-API contract without an RFC, deprecation window, or migration shim.

---

## Tricky Points

- **LLVM's stability contract is asymmetric**: bitcode is backward-compatible (old loads into new via auto-upgrade); textual `.ll` is deliberately *not* a stable interface. That asymmetry is a design choice (durable wire format vs human/test format), not an accident.
- **Metadata is, by definition, semantically inert** — droppable without changing meaning. The instant correctness depends on it, you've violated its contract.
- **Canonicalization must be confluent and terminating**, or you get non-deterministic builds or infinite loops; this is a real engineering constraint, not a nicety.
- **The effect model *is* the optimization contract.** Every "can I move/delete this?" reduces to "what effects does the IR say this has?" Misspecify effects and you've authorized miscompiles.
- **A new IR level is the most expensive kind of change** because it multiplies lowerings, verifiers, and the inter-level leak surface — yet sometimes it's exactly right (MIR for borrow check). The skill is knowing which.
- **Sea-of-nodes' optimization ceiling and its maintenance floor are the same property** (floating nodes). V8's Turboshaft retreat is the canonical "we paid too much for the ceiling" decision.
- **Reproducible builds constrain the IR**: any nondeterminism (hash-set iteration order, pointer-address-dependent decisions) leaks into output and breaks caching/bit-identical builds.
- **Provenance must survive lowering** for sanitizers, debuggers, and (increasingly) pointer-provenance semantics; an optimization that breaks provenance silently breaks tooling and, in some models, correctness.

---

## Apply it

1. Define the user or business outcome that **Intermediate Representations** should improve.
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

- Which measurable outcome justifies investing in Intermediate Representations?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
