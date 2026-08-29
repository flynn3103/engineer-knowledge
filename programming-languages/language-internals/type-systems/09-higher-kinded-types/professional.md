# Higher-Kinded Types — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Higher-Kinded Types** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The compiler's view: dictionary passing vs monomorphization

Why do HKTs cost what they cost? Look at how a compiler *implements* `f :: Monad m => m a -> ...`:

- **GHC / Scala (dictionary passing):** the constraint `Monad m` becomes a hidden argument — a *dictionary* (record of `flatMap`, `pure`, …). Generic code is compiled *once* and the right dictionary is passed at the call site. Cost lands at **compile time** (resolving which dictionary) and as **runtime indirection** (virtual-ish calls through the dictionary), not code bloat.
- **Rust / C++ (monomorphization):** generics are *specialized* per instantiation — one compiled copy per concrete `F`. No runtime indirection, but **binary size and compile time** grow with the number of instantiations. Now add a *type-constructor* variable `F<_>`: the instantiation space and the trait-resolution/coherence search both balloon. This is a core reason Rust judged HKTs not-yet-worth-it: the dictionary-passing escape hatch isn't its default, and monomorphizing constructor-generic code interacts badly with coherence and lifetimes.

So the *implementation strategy* predicts where the bill arrives: dictionary-passing languages pay in compile-time search + runtime indirection; monomorphizing languages pay in code size + resolution complexity — which is exactly why HKTs feel "free-ish" in Haskell and "intractable" in Rust.

### 2. Compile-time cost is the most underrated tax

In Scala especially, HKT-heavy code (deep implicit/given chains, typeclass derivation, large Cats/Shapeless usage) can dominate build times. Symptoms:

- Implicit resolution exploring large instance spaces; ambiguous-implicit errors that take minutes to surface.
- Typeclass derivation (auto-deriving `Functor`/`Monad`/`Eq`) expanding into large generated code at compile time.
- IDE responsiveness degrading on files dense with `F[_]` constraints.

This is a *real operating cost*: slower CI, slower local iteration, more developer frustration. Budget it. Measure build times before and after introducing a heavy typeclass stack; it is often the deciding factor independent of any runtime concern.

### 3. Runtime cost: transformers vs effect runtimes

Naive monad-transformer stacks (`ReaderT r (StateT s (ExceptT e IO))`) pay per-`bind` allocation and indirection at *each layer*. For hot paths this is measurable. The industry response:

- **Cats-Effect `IO` and ZIO** provide a single, heavily optimized effect type with a fused interpreter — you get error, async, resource, and (via ZIO's `R`) environment capabilities without literally stacking transformers. ZIO's `ZIO[R, E, A]` bakes the three most common capabilities into one type.
- **`ReaderT IO` pattern** (a.k.a. "the ReaderT design pattern"): use a single concrete `IO` (or `RIO env`) instead of deep stacks, passing dependencies via a reader environment — much of the polymorphism, far less overhead.

Professional takeaway: the *abstraction* (effect-polymorphism) is separable from the *naive implementation* (transformer towers). Modern stacks keep the former and discard the latter. If you reject HKTs *because of transformer overhead*, you may be rejecting the wrong thing.

### 4. The human cost is usually the deciding one

For most teams the binding constraint is not CPU but people:

- **Readability / review:** a reviewer must hold the kind system, the typeclass laws, and the instance-resolution rules in their head to verify an `F[_]: Monad` function. Reviews slow down; subtle law violations slip through.
- **Onboarding:** a new hire fluent in Go/Java/Python but not typed FP faces weeks, not days, to be productive in a Cats/ZIO or `mtl` codebase. That is a real, recurring cost.
- **Hiring pool / bus factor:** the set of engineers who can *maintain* HKT-heavy code is a fraction of the general pool. If two people understand the effect stack and both leave, you have an unmaintainable core.

None of this argues HKTs are bad — fluent FP teams genuinely move faster with them. It argues that the decision is *sociotechnical*, and the human ledger usually outweighs the machine ledger.

### 5. Library design: hide the machinery, stabilize the surface

Shipping HKT-based APIs (whether you're writing Cats-style typeclasses or an fp-ts module) imposes design obligations:

- **Hide the encoding.** In TS/Kotlin, keep `Kind`/`URItoKind`/tag plumbing internal; expose signatures that read cleanly. Leaking `Kind<'Option', A>` into user error messages is a tax on *every* consumer.
- **Law-test instances.** Ship `Discipline`/QuickCheck law suites; an unlawful instance is a defect in every generic consumer.
- **Mind inference & binary compatibility.** HKT-heavy public APIs are inference-fragile (small signature changes break call-site inference) and, on the JVM, implicit/given changes can break binary compatibility. Treat the typeclass surface as a versioned contract.
- **Offer an off-ramp.** Provide concrete-effect conveniences (e.g. `IO`-specialized helpers) so users aren't forced into full polymorphism for simple tasks.

The best HKT libraries are the ones whose *users never have to think about kinds* — they call `traverse`, get an answer, and the higher-kindedness is invisible.

### 6. The decision framework

Put this in the architecture doc. Signals toward **adopt**:

- The team is fluent (or hiring specifically) in typed FP; the *primary* language has native HKTs.
- You have many effects/containers and the *same* operations recur across them — measurable duplication HKTs would remove.
- You need effect-swappability (prod `IO` vs pure test interpreter) as a first-class architectural goal.

Signals toward **contain-to-a-module**:

- A specific subsystem (parsing, validation, a streaming engine) benefits hugely, but the broader team isn't FP-fluent. Use HKTs inside, expose a plain API outward.

Signals toward **avoid (for now)**:

- The language lacks native HKTs and the encoding cost dominates (Rust today; Go always; native TS for most app teams).
- One effect, no foreseeable second; the generality would be speculative.
- Onboarding speed / broad hiring pool is a hard product constraint.
- Build-time budget is already tight and a heavy typeclass stack would worsen it.

Crucially, design so the bet is **reversible**: a `program[F[_]: Monad]` can be specialized to `IO` later (delete the constraint, fix call sites); a concrete program is harder to *generalize* but easier to *read*. Bias new code toward the cheaper-to-reverse direction given your confidence.

### 7. Why "just use plain generics / interfaces" often loses *and* often wins

The honest counter-argument to HKTs: most real duplication can be removed with ordinary interfaces, code generation, or a single concrete effect type, *without* asking the team to learn kinds. Where this wins: app codebases with a fixed effect and a non-FP team. Where it loses: when you genuinely need *one* `traverse`/validation/retry that works across many effects, hand-writing N copies (or N codegen targets) is its own maintenance burden, and the HKT version is strictly less code and less drift. The professional skill is telling these apart — and not reflexively reaching for either.

---

## Code Examples

### Measuring the reuse: N hand-written copies vs one `traverse`

```scala
// WITHOUT HKTs: one validation pass per effect, drifting over time.
def validateAllEither(xs: List[String]): Either[Err, List[Int]] = { /* ... */ ??? }
def validateAllFuture(xs: List[String]): Future[List[Int]]      = { /* ... */ ??? }
def validateAllOption(xs: List[String]): Option[List[Int]]      = { /* ... */ ??? }

// WITH HKTs: one function; the effect is a parameter.
import cats.Applicative, cats.syntax.all.*
def validateAll[F[_]: Applicative](xs: List[String])(check: String => F[Int]): F[List[Int]] =
  xs.traverse(check)
// Call it with Either, Future, Option, IO — no new code, no drift.
```

The ledger entry: three (soon five, soon seven) drifting copies vs one definition. If you *have* the effects, the HKT version is strictly less code and less bug surface. If you only ever need `Either`, the first `validateAllEither` is clearer and cheaper to onboard.

### The ReaderT / RIO pattern: polymorphism-lite, overhead-lite

```scala
// Instead of ReaderT r (StateT s (ExceptT e IO)) towers:
type App[A] = ReaderT[IO, AppEnv, A]   // one concrete effect + an environment

def handler(req: Req): App[Resp] =
  for {
    cfg  <- ReaderT.ask[IO, AppEnv].map(_.config)
    user <- ReaderT.liftF(db.lookup(req.userId))   // db is in AppEnv
    _    <- ReaderT.liftF(log.info(s"served ${user.id}"))
  } yield Resp(user)
```

You keep dependency-injection and composability, lose the per-layer transformer cost, and the code reads far more like ordinary `IO`. Many "we adopted Cats but it was too slow/complex" stories are really "we used naive transformer towers instead of this".

### Containing the encoding (TypeScript)

```typescript
// internal/hkt.ts  -- the ONLY file that mentions Kind/URItoKind
export interface URItoKind<A> { Option: Option<A>; Task: Task<A> }
export type URIS = keyof URItoKind<unknown>;
export type Kind<F extends URIS, A> = URItoKind<A>[F];

// app/orders.ts -- consumers see a CLEAN signature; no Kind noise leaks here.
import { processOrders } from '../lib/pipeline'; // pipeline.ts hides the F-plumbing
const result = processOrders(orders); // returns Task<Report>; HKTs invisible at call site
```

The discipline: the higher-kinded machinery lives behind a module boundary; application code and its error messages stay clean. Skip this discipline and *every* consumer pays the readability tax.

### The reversible bet, concretely

```haskell
-- Start concrete if uncertain:
runReport :: [Row] -> IO Report

-- Generalize ONLY when a second effect (e.g. a pure test interpreter) actually appears:
runReport :: Monad m => Sink m -> [Row] -> m Report
--   Specializing back to IO later: drop the constraint, inline the IO Sink. Cheap.
--   Going the other way (concrete -> generic) under deadline pressure: usually painful.
```

---

## Coding Patterns

### Pattern 1: Make the adopt/contain/avoid call explicitly, in writing

Put the decision in an ADR with the ledger: what duplication HKTs remove, the compile/runtime/human costs, the team's fluency, and the reversibility plan. Don't let HKT adoption happen by accretion of one clever PR at a time.

### Pattern 2: Prefer one optimized effect runtime over transformer towers

Reach for Cats-Effect `IO`/ZIO/`RIO env` rather than hand-stacking `StateT`/`ExceptT`. You keep effect-polymorphism's benefits and shed most of its runtime cost.

### Pattern 3: Quarantine the machinery behind a stable, plain API

Whether native or encoded, ensure the *kinds* and instance plumbing stay inside a module boundary. Application code and error messages should read as if HKTs weren't there.

### Pattern 4: Generalize on the second concrete use, not the first

Write concrete code until a *real* second effect/container appears, then lift to `F[_]`. This avoids speculative generality and keeps the cheap-to-reverse direction.

### Pattern 5: Budget and monitor build time as a first-class metric

Track CI and local compile times when introducing typeclass-heavy code. If a derivation/implicit-stack doubles build time, that cost is part of the decision — measure it, don't assume it away.

---

## Best Practices

- **Argue from the ledger, not aesthetics.** "It's elegant" and "it's astronaut nonsense" are both non-arguments. Name the concrete reuse and the concrete costs.
- **Match the strategy to the language.** Native HKTs in Haskell/Scala/PureScript: viable. Encoded HKTs in TS/Kotlin: only with strong justification and strict containment. Rust/Go: prefer GATs/concrete designs; don't emulate HKTs without a compelling library-grade reason.
- **Separate the abstraction from the naive implementation.** Want effect-polymorphism? Use a modern effect runtime, not a transformer tower, before concluding it's "too slow".
- **Treat the typeclass surface as a versioned contract.** HKT public APIs are inference-fragile and (on JVM) binary-compat-sensitive; review signature changes accordingly and law-test instances.
- **Optimize for the median maintainer, not the author.** If only the author can review a module, the abstraction has failed operationally regardless of its elegance.
- **Keep the bet reversible.** Bias toward the direction (generic vs concrete) that's cheaper to undo given your current confidence; document how to reverse it.
- **Measure build time and bus factor as explicitly as you measure runtime.** They're the costs that most often sink HKT adoption, and the ones teams most often forget to count.

---

## Edge Cases & Pitfalls

- **Adoption by accretion.** HKTs creep in one clever PR at a time until the core is unmaintainable by most of the team. Decide deliberately and document it; don't let it happen by default.
- **Blaming the abstraction for the implementation.** Rejecting effect-polymorphism because *transformer towers* were slow conflates two separable things. Try a fused effect runtime first.
- **Compile-time blowups in Scala.** Heavy implicit/given derivation can multiply build times and IDE latency. This is a deciding cost, not a footnote — measure it.
- **Inference fragility in public APIs.** A small change to an HKT signature can break call-site inference across many consumers. HKT public surfaces need extra-careful versioning.
- **Encoding leakage (TS/Kotlin).** Undisciplined `Kind<F,A>`/tag plumbing leaks into user-facing types and errors, taxing every consumer. Quarantine it or don't ship it.
- **Coherence surprises (Scala).** Lack of global coherence means conflicting `Monad[F]` instances can be in scope; generic code's behavior depends on which resolves. Pin instances; prefer single-instance discipline.
- **Speculative generality.** `program[F[_]: Monad]` with exactly one `F` ever used is pure tax. Generalize on the second real use, not in anticipation.
- **Bus-factor collapse.** Two experts build a beautiful effect stack; both leave; the core ossifies. The hiring/maintenance reality is part of the architecture, not a separate concern.
- **GAT/HKT conflation in Rust roadmaps.** Planning a "Functor abstraction" on top of GATs leads to a wall — GATs don't deliver constructor-genericity. Scope Rust designs to what GATs actually do.

---

## Apply it

1. Define the user or business outcome that **Higher-Kinded Types** should improve.
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

- Which measurable outcome justifies investing in Higher-Kinded Types?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
