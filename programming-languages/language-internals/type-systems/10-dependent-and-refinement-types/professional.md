# Dependent & Refinement Types — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Dependent & Refinement Types** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The economics: cost vs. avoided cost

Verification pays when **(expected cost of defects avoided) > (cost of verification)**. Both sides vary enormously:

- **Cost of verification** scales with depth (refinement < dependent), with *spec and proof engineering* (usually the dominant term — often far exceeding the code itself), and with *maintenance* as the code evolves. Liquid Haskell on one module might be days; a CompCert-class effort is person-years.
- **Avoided cost** scales with blast radius × defect probability. A crypto bug in a library shipping to a billion endpoints, or a kernel bug in a certified avionics stack, has astronomical expected cost. A bug in an internal dashboard does not.

This is why the same technique is *obviously correct* for HACL\* and *obviously wrong* for a marketing site. The professional doesn't ask "is verification good?" (it's neither good nor bad); they ask "does *this* system's blast radius justify *this* rung's cost?" For the vast majority of software, the answer lands below full proof — and that's the *right* answer, not a failure of nerve.

### 2. The gradient, rung by rung — and what each rung buys

```text
RUNG                              MECHANISM                       TYPICAL COST     TYPICAL FIT
-------------------------------------------------------------------------------------------
1. Ordinary types + tests         compiler + test suite           baseline         almost everything
2. Make-illegal-states-           sum types, newtypes,            low              every serious codebase
   unrepresentable                smart constructors
3. Mainstream "dependent-ish"     TS literal/template/branded     low–moderate     APIs, protocol states
                                  types; Rust const generics,
                                  type-state
4. Refinement types (SMT)         Liquid Haskell, Dafny, F*       moderate         bounds/arith-critical
                                  (one component)                                  modules, crypto helpers
5. Full dependent / proof         Idris, Agda, Coq, Lean, F*      high–very high   compilers, kernels,
   assistant                      (whole-system proof)                             crypto, avionics, math
```

Most teams should *climb to rung 2 or 3 and stop* — that captures a large fraction of the safety with negligible cost. Rung 4 is a targeted tool: drop it on the one module where bounds/arithmetic bugs would be catastrophic. Rung 5 is a multi-year institutional commitment, appropriate for a handful of artifacts on earth. **Knowing which rung a problem deserves is the core professional competency here.**

### 3. Rungs 2–3 in practice: the cheap, high-leverage wins

You don't need a verifier to get most of the *design* benefit. The same discipline — encode invariants in types — works in everyday languages:

- **Make illegal states unrepresentable.** Replace `(status: int, errorCode: int?)` with a sum type where each variant carries exactly the fields valid in that state. The compiler now rejects "success with an error code."
- **Branded / newtype refinement.** A `UserId` distinct from `OrderId` (even though both are `int`) prevents an entire class of argument-swap bugs. A `ValidatedEmail` produced only by a smart constructor means "is this validated?" is answered by the type, not a runtime check.
- **TypeScript literal & template-literal types.** `type Method = "GET" | "POST"` and template types like `\`/users/${string}\`` give a weak refinement flavor — the compiler restricts strings to a shape, catching typos at compile time.
- **Rust const generics & type-state.** `[T; N]` carries length in the type; the type-state pattern (`Connection<Open>` vs `Connection<Closed>`) makes "send on a closed connection" a compile error. These are genuine slivers of dependent/refinement thinking in a mainstream, production language.

These cost almost nothing and pay continuously. They are where 99% of teams should invest, and they're the bridge that makes the heavyweight tools comprehensible.

### 4. Rung 4 in practice: surgical refinement

Refinement types (Liquid Haskell, Dafny, F\*) shine when applied **surgically** to a component where arithmetic/bounds/aliasing bugs are the dominant risk:

- A **parser or codec** where length and offset arithmetic is bug-prone and security-relevant.
- A **ring buffer / allocator / index-heavy data structure** where off-by-one is catastrophic.
- A **crypto primitive** where constant-time and correctness matter.

The win: you keep your language and ecosystem, annotate the dangerous module, and let the SMT solver eliminate a bug class — *without* the person-years of a full proof. Liquid Haskell catching a real out-of-bounds in a `Data.Text`/bytestring-style routine is the archetype: a bounded, automated, high-value intervention. The cost is bounded too — when the solver can't discharge a VC, you strengthen the spec or add an assertion, not write an induction proof.

### 5. Building and *maintaining* verified systems

The cost people forget is **maintenance**. Proofs are brittle: refactor the code and proofs break; tighten the spec and obligations reopen. A verified codebase has a standing tax:

- **Proof CI.** The proof must re-check on every change; broken proofs block merges exactly like failing tests.
- **Spec review as a first-class artifact.** Since "verified" means "verified against the spec," the spec needs independent scrutiny — redundant statements, model-based tests, adversarial review — because a spec bug is invisible to the proof.
- **TCB hygiene.** Track axioms, `assume`s, and the extraction toolchain; a verified core extracted by a buggy extractor and compiled by an unverified C compiler still trusts both. (This is why fiat-crypto and CompCert care so much about the *whole* pipeline.)
- **Expertise concentration.** Few engineers can maintain the proofs; bus-factor and onboarding are real operational risks.

Teams that succeed (Galois, AWS's automated-reasoning group, the seL4 foundation, the HACL\*/Project Everest teams) treat verification as a *sustained capability*, not a one-time effort.

### 6. Where the mainstream is heading

The frontier is **gradual** verification leaking into ordinary languages, so the cheap rungs get cheaper and a bit deeper:

- **Refinement-ish typing in mainstream stacks** (research and tooling around Scala refinement types, Liquid Haskell's maturation, Dafny's adoption at AWS).
- **Richer value-in-type features** (Rust const generics expanding; TypeScript's literal/template/conditional types growing more expressive).
- **SMT-backed assertions and contract checkers** that verify *some* obligations at build time without a full dependent type system.
- **Lean 4 doubling as a real programming language**, narrowing the gap between "proof assistant" and "language you'd ship."

The realistic trajectory is not "everyone writes Agda" but "everyday languages absorb the high-leverage, low-cost rungs (illegal-states-unrepresentable, branded types, const generics, surgical SMT), while full proof stays a specialist tool for catastrophic-blast-radius code." A professional bets on that gradient: invest heavily in the cheap rungs now, watch the expensive rungs get cheaper, and deploy them surgically when the economics flip.

---

## Code Examples

### Example 1: Rung 2 — illegal states unrepresentable (TypeScript, everyday)

```typescript
// BAD: status and error can contradict each other.
type ResultBad = { ok: boolean; data?: User; error?: string };

// GOOD: a discriminated union — "ok with an error" cannot be constructed.
type Result =
  | { kind: "ok"; data: User }
  | { kind: "err"; error: string };

function render(r: Result) {
  switch (r.kind) {
    case "ok":  return r.data.name;     // r.error doesn't exist here
    case "err": return r.error;         // r.data doesn't exist here
  }
}
```

No verifier, no SMT — just ordinary types capturing an invariant. This is rung 2, and it's where most teams get the highest return per hour.

### Example 2: Rung 3 — branded refinement via smart constructor (TypeScript)

```typescript
// A "branded" type: a string the compiler treats as distinct.
type Email = string & { readonly __brand: "Email" };

// The ONLY way to make an Email establishes the invariant:
function parseEmail(s: string): Email | null {
  return /^[^@]+@[^@]+$/.test(s) ? (s as Email) : null;
}

function sendTo(to: Email) { /* ... */ }

sendTo("oops");                 // ❌ compile error: string is not Email
const e = parseEmail(input);
if (e) sendTo(e);               // ✅ refinement established at the boundary
```

### Example 3: Rung 3 — type-state in Rust (compile-time protocol safety)

```rust
struct Open;
struct Closed;
struct Conn<State> { /* ... */ _state: std::marker::PhantomData<State> }

impl Conn<Open> {
    fn send(&self, _msg: &[u8]) { /* only Open conns can send */ }
    fn close(self) -> Conn<Closed> { Conn { _state: std::marker::PhantomData } }
}

// conn.send() after close() does NOT compile — the type changed to Conn<Closed>.
```

The protocol state lives in the type; illegal transitions are compile errors — a sliver of dependent thinking in a production language.

### Example 4: Rung 4 — surgical refinement on a risky routine (Liquid Haskell)

```haskell
-- Verify ONLY this index-heavy function; the rest of the app is untouched.
{-@ slice :: xs:[a]
          -> lo:{v:Int | 0 <= v && v <= len xs}
          -> hi:{v:Int | lo <= v && v <= len xs}
          -> [a] @-}
slice :: [a] -> Int -> Int -> [a]
slice xs lo hi = take (hi - lo) (drop lo xs)

-- A caller with a possible off-by-one is rejected at compile time by Z3,
-- without rewriting the codebase in a dependently typed language.
```

### Example 5: Rung 4 — Dafny verifying one algorithm (AWS-style)

```dafny
method BinarySearch(a: array<int>, key: int) returns (index: int)
  requires forall i, j :: 0 <= i < j < a.Length ==> a[i] <= a[j]  // sorted spec
  ensures 0 <= index ==> index < a.Length && a[index] == key
  ensures index < 0 ==> forall i :: 0 <= i < a.Length ==> a[i] != key
{
  var lo, hi := 0, a.Length;
  while lo < hi
    invariant 0 <= lo <= hi <= a.Length
    invariant forall i :: 0 <= i < lo ==> a[i] != key
    invariant forall i :: hi <= i < a.Length ==> a[i] != key
  {
    var mid := lo + (hi - lo) / 2;       // off-by-one & overflow shape — Dafny checks it
    if a[mid] < key { lo := mid + 1; }
    else if a[mid] > key { hi := mid; }
    else { return mid; }
  }
  return -1;
}
```

One method, fully specified and machine-verified — the surgical pattern AWS uses for critical components, no whole-system proof required.

---

## Coding Patterns

**1. Climb-then-stop.** Adopt rungs 2–3 everywhere by default; escalate to rung 4 only on identified high-risk modules; reserve rung 5 for catastrophic blast radius.

**2. Refine at the boundary, trust the interior.** Establish invariants once at I/O/parse boundaries via smart constructors; the verified/refined interior then runs guard-free.

**3. Isolate the verified core behind a thin unverified shell.** Keep FFI/I/O glue small and audited; verify the algorithmic heart.

**4. Treat specs as reviewed artifacts.** Version, review, and independently test specifications; a wrong spec defeats any amount of proof.

**5. Budget proof maintenance.** Put proofs in CI; expect re-proving on refactor; staff for it before committing.

---

## Best Practices

- **Decide by blast radius, not by taste.** Compute the consequence of a defect first; let it set the assurance ceiling.
- **Default to the cheap rungs.** Most reliability gains come from ordinary-type discipline, not proofs. Exhaust those first.
- **Apply heavy verification surgically.** One critical module, fully verified, beats a half-hearted whole-system attempt.
- **Account for the *whole* TCB.** Extraction toolchain, C compiler, axioms, `assume`s — verified core ≠ verified binary.
- **Independently validate the spec.** Redundant statements, model-based tests, adversarial review; the proof can't catch a wrong spec.
- **Sustain it or don't start it.** Verification is a standing capability (CI, expertise, spec review); a one-off proof rots.
- **Communicate honestly.** "We verified memory safety of module X against spec Y, trusting Z" — precise claims, not "it's proven correct."

---

## Edge Cases & Pitfalls

- **Over-verification.** The most common professional failure: pouring proof effort into low-blast-radius code, starving higher-value work. Calibrate.
- **The verified binary illusion.** A verified Coq core extracted and compiled by unverified tools still trusts those tools; the binary is only as trustworthy as the *whole* pipeline.
- **Spec rot.** Code evolves, spec doesn't; the proof now guarantees yesterday's behavior. Treat spec drift like a failing test.
- **Proof-bus-factor.** One person understands the proofs; they leave; the codebase becomes unmaintainable. Spread expertise or don't commit.
- **SMT brittleness in CI.** Refinement VCs can become flaky/slow as code grows; budget solver-tuning and resource limits.
- **Mistaking branded types for proofs.** Rung 3 tricks (TS branded types) are *unenforced at the value level* — a stray cast bypasses them. They're discipline aids, not guarantees.
- **"It's verified" overclaim.** Memory safety ≠ functional correctness ≠ side-channel freedom ≠ liveness. State exactly which property holds.

---

## Apply it

1. Define the user or business outcome that **Dependent & Refinement Types** should improve.
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

- Which measurable outcome justifies investing in Dependent & Refinement Types?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
