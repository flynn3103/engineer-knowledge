# Dependent & Refinement Types — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Dependent & Refinement Types** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Curry–Howard: the dictionary

The correspondence is a precise dictionary between logic and programming:

| Logic | Type theory |
|-------|-------------|
| proposition `P` | type `P` |
| proof of `P` | program (term) of type `P` |
| `P → Q` (implies) | function type `P -> Q` |
| `P ∧ Q` (and) | pair / product `(P, Q)` |
| `P ∨ Q` (or) | sum / `Either P Q` |
| `∀x. P(x)` | Pi type `(x : A) -> P x` |
| `∃x. P(x)` | Sigma type `(x : A ** P x)` |
| `True` | unit type (one trivial inhabitant) |
| `False` | empty type (no inhabitants) |
| `¬P` | `P -> False` |

To *prove* `P` is to *construct* a term of type `P`. To prove `∀ n. P n` is to write a (total) function taking `n` and producing a proof `P n`. To prove `∃ n. P n` is to produce a concrete `n` paired with evidence. **Proof = program** is not a metaphor here; it's the operational reality. Lean and Coq are literally programming environments where the things you build are proofs.

### 2. Equality as a type, and how you prove it

Propositional equality `x = y` is itself a type (a proposition). Its single constructor is `Refl : x = x` — reflexivity. You can build `Refl : a = b` only when `a` and `b` are *definitionally equal* (reduce to the same normal form). To prove a non-definitional equality (say `n + 0 = n`, which doesn't auto-reduce for variable `n`), you do **induction**: write a function that recurses on `n`, producing a proof in each case, using the inductive hypothesis. That function *is* the inductive proof. This is the bridge from the middle tier's "definitional equality runs out" to "so you write a proof by induction" — and that proof is just a total recursive program returning an equality term.

### 3. Totality is the load-bearing wall

Here is the crux that separates "fancy type system" from "trustworthy logic." Consider:

```idris
loop : a
loop = loop      -- typechecks if totality is OFF; "inhabits" EVERY type a
```

If `loop` is accepted, then `loop : False` — you've "proved" falsehood, and from `False` anything follows. Your entire proof system is now worthless. Therefore proof assistants **require totality**:

- **Termination.** Recursion must be well-founded — typically *structural*: each recursive call is on a structurally smaller argument. When that's not obvious, you supply a decreasing metric (well-founded recursion) or the checker rejects the function.
- **Coverage.** Pattern matches must be exhaustive; a missing case is a partial function, which is a hole in the logic.

Idris, Agda, Coq, and Lean all ship totality checkers. In Idris you can mark a function `total` and the compiler *verifies* it. **Soundness of the whole edifice rests on this.** When you "trust a Coq proof," part of what you're trusting is that nothing snuck a non-terminating term or an incomplete match past the checker. This is also why these languages feel restrictive: the same discipline that makes them sound makes general recursion and partiality awkward.

### 4. The trusted computing base, axioms, and escape hatches

A machine-checked proof is only as meaningful as what you must still *trust*. The **trusted computing base (TCB)** typically includes:

- The **kernel** of the proof checker (the small, audited core that validates proof terms).
- Any **axioms** you assumed (e.g. functional extensionality, classical logic, `UIP`). Each axiom you add is a promise you're not proving — and a *wrong* axiom makes the system unsound.
- The **specification** itself. A proof shows the code meets the spec; if the spec is wrong, the proof is worthless. *"Verified" means "verified against this spec,"* never "verified against your intentions."
- **Escape hatches** — Coq's `admit`/`Admitted`, Lean's `sorry`, F\*'s `assume` — which accept a goal *without* proof. Indispensable during development, catastrophic if they survive into a "complete" proof. Auditing a verified codebase means grepping for these.

A senior engineer evaluating a verification claim asks: *what's in the TCB, which axioms, any open `sorry`s, and is the spec the right one?* Those four questions separate real assurance from theater.

### 5. The proof-automation spectrum, concretely

```text
  interactive proof                                   SMT-automated refinement
  (Coq / Lean / Agda)                                 (Liquid Haskell / F* / Dafny)
        |                                                       |
  arbitrary theorems, deep math,                        pre/postconditions, invariants;
  full control; proofs by hand                          solver discharges VCs
  (tactics or terms)                                    automatically
        |                                                       |
  effort: high   power: unbounded                       effort: low   power: bounded
                                                         (decidable theories only)
```

- **Coq / Lean**: tactic-driven interactive proving. Used for CompCert (Coq), parts of mathlib (Lean), and deep mathematics. You pay in expert-hours; you can prove essentially anything.
- **Agda**: dependently typed programming with proofs-as-programs in *term* mode (less tactic automation, very direct).
- **F\***: dependent + refinement, with SMT (Z3) discharging most obligations and an interactive fallback for the rest. Powers HACL\* and miTLS.
- **Liquid Haskell**: refinement types bolted onto Haskell; SMT does the work; *refinement reflection* lets you reason about your own functions in the logic.
- **Dafny**: imperative verification with SMT; AWS uses it for critical components.

The architectural choice: **how much can the solver carry, and how much must humans prove?** More SMT = more scale, less depth. More interactive proof = more depth, less scale. Hybrid tools (F\*) try to get both, falling back to manual proof exactly where SMT gives up.

### 6. How verified systems are really built

Real-world verified software is not "write code, then prove it." It's **co-design**: the spec, the code, and the proof evolve together, often with significant restructuring to make proofs tractable.

- **CompCert** (Coq): a C compiler with a machine-checked proof of *semantic preservation* — the generated assembly behaves exactly as the C source specifies, for every program. The CSmith fuzzing study famously found bugs in GCC and Clang but *none* in CompCert's verified core. The compiler is *extracted* from Coq to OCaml.
- **seL4** (Isabelle/HOL): a microkernel with a refinement proof from abstract spec down to C, plus binary-level verification. ~10k lines of C, person-years of proof.
- **HACL\*** (F\*): a verified crypto library (used in Firefox, the Linux kernel, mozilla NSS). Proves memory safety, functional correctness against a math spec, and (some) side-channel resistance; extracted to C.
- **AWS** uses Dafny and F\* for critical components (e.g. cryptographic and authorization logic), where a single flaw is a fleet-wide security incident.

The recurring lesson: verification cost is dominated not by the code but by the **proof and spec engineering**, and it's justified only when a bug's cost is extreme — compilers, kernels, crypto, avionics.

---

## Code Examples

### Example 1: A proof as a program (Idris/Agda flavor)

```idris
-- Proposition: for all n, n + 0 = n.  Proof: induction on n.
-- The function IS the proof; its type IS the theorem.

plusZeroRight : (n : Nat) -> n + 0 = n
plusZeroRight Z     = Refl                       -- 0 + 0 = 0 holds definitionally
plusZeroRight (S k) = cong S (plusZeroRight k)    -- use IH: (k+0=k) => (S k + 0 = S k)
```

`Refl` proves the base case (both sides reduce to `Z`). The inductive step transports the hypothesis `k + 0 = k` through `S` via `cong`. The totality checker confirms the recursion is structural (on `k`), so this is a *sound* proof, not a `loop` in disguise.

### Example 2: From `False`, anything (why totality matters)

```idris
-- If we COULD inhabit False, we could prove any P:
exFalso : False -> a
exFalso x = absurd x      -- absurd : False -> a ; valid BECAUSE False is empty

-- The danger: a non-total `loop : False` would feed exFalso and "prove" everything.
-- Totality checking rejects `loop`, keeping False uninhabited and the logic sound.
```

### Example 3: A verified, total `head` with an explicit non-empty witness (Coq-ish)

```coq
(* head requires a proof that the list is non-empty; impossible to call otherwise *)
Definition head {A} (l : list A) (pf : l <> nil) : A :=
  match l return l <> nil -> A with
  | nil       => fun pf => match pf eq_refl with end   (* nil case is impossible *)
  | cons x _  => fun _  => x
  end pf.
```

The `nil` branch derives a contradiction from `pf` (a proof that `l <> nil`) and is thus eliminated — exhaustiveness satisfied without a runtime check.

### Example 4: SMT-discharged correctness with reflection (Liquid Haskell)

```haskell
{-@ reflect fac @-}             -- lift fac into the logic so Z3 can reason about it
fac :: Int -> Int
fac n = if n <= 0 then 1 else n * fac (n - 1)

-- A theorem proved by SMT + a tiny proof combinator, not by hand induction:
{-@ facPos :: n:Nat -> { fac n >= 1 } @-}
facPos :: Int -> Proof
facPos n
  | n <= 0    = trivial
  | otherwise = facPos (n - 1)   -- structural recursion; Z3 closes each step
```

Contrast with Example 1: here the *solver* discharges the arithmetic, and your "proof" is a recursion skeleton that guides it. Less control, far less effort — when the property stays in Z3's reach.

### Example 5: F\* — refinement + dependent + SMT, with a fallback

```fsharp
// A division whose type forbids a zero denominator; Z3 discharges the precondition.
let divide (a:int) (b:int{b <> 0}) : int = a / b

// A lemma F* proves automatically via SMT:
let rec sum_upto (n:nat) : nat = if n = 0 then 0 else n + sum_upto (n - 1)

val sum_formula (n:nat) : Lemma (sum_upto n == n * (n + 1) / 2)
let rec sum_formula n =
  if n = 0 then () else sum_formula (n - 1)   // induction; Z3 closes the arithmetic
```

F\* sits in the middle of the spectrum: SMT does most of the work, and when it can't, you drop into interactive proof — the model HACL\* uses at scale.

---

## Coding Patterns

**1. Spec → code → proof co-design.** Don't bolt proofs on; shape the code so the proofs are tractable from the start.

**2. Keep functions total and structurally recursive.** Reach for accumulators and well-founded measures so the termination checker stays happy.

**3. Push obligations to SMT, escalate to tactics at the gap.** In F\*/Liquid Haskell, let Z3 carry routine arithmetic; hand-prove only the residue.

**4. Minimize the TCB.** Avoid axioms where possible; isolate and document the ones you accept; treat every `admit`/`sorry`/`assume` as a tracked debt.

**5. Extract and test the boundary.** Verified core, but the I/O shell and FFI are unverified — keep that boundary thin and audited.

---

## Best Practices

- **Audit for soundness holes.** Grep for `admit`, `Admitted`, `sorry`, `assume`, `believe_me`, and every `Axiom` before trusting a development.
- **Write the spec as carefully as the proof.** Most "verified but wrong" outcomes are spec bugs, not proof bugs. Validate the spec independently (tests, review, redundant statements).
- **State the TCB explicitly.** A verification claim should ship with "what you must trust." If it doesn't, distrust it.
- **Prefer SMT for breadth, tactics for depth.** Match the tool to the obligation; don't hand-prove what Z3 closes in milliseconds, and don't ask Z3 to do deep induction.
- **Track proof-maintenance cost.** Proofs are brittle under refactoring; budget for re-proving when the code changes.
- **Erase and extract deliberately.** Confirm the runtime artifact carries no proof baggage and that extraction's TCB (the extractor itself) is accounted for.

---

## Edge Cases & Pitfalls

- **The `loop : False` trap.** Disabling totality (or using an unsound escape) collapses the logic — you can "prove" anything. Never trust a non-total proof artifact.
- **Inconsistent axioms.** Combining classical logic, impredicativity, and certain choice principles can yield inconsistency; adding axioms is not free.
- **Coverage holes that look exhaustive.** A match that *seems* complete but relies on an unproven impossibility can hide a partial function; the checker must *confirm* impossibility.
- **Spec drift.** Code and spec evolve; an out-of-date spec means the proof now guarantees the wrong thing.
- **SMT incompleteness mistaken for code bugs.** Z3 may fail on true nonlinear/quantified goals; the fix is reformulation or a manual lemma, not changing correct code.
- **TCB creep via extraction/FFI.** The extractor, the C compiler, and unverified glue are all in the real TCB even if the core is verified.
- **"Verified" marketing.** A proof of memory safety is not a proof of functional correctness is not a proof of side-channel resistance. Ask *which* property was proved.

---

## Apply it

1. State the system invariant that **Dependent & Refinement Types** must protect.
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

- Which invariant must remain true when Dependent & Refinement Types fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
