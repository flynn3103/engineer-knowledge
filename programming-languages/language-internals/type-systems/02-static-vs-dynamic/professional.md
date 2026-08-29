# Static vs Dynamic Typing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Static vs Dynamic Typing** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why Static Types Make Code Faster

A statically known type is *information the compiler can spend*. With it, several optimizations become possible that are hard or impossible without it:

- **No runtime type checks/tags.** If the compiler *knows* `x` is an `int`, it emits an integer `add` directly — no "what type is `x`? does it support `+`? dispatch to its `__add__`" at runtime. Dynamic languages do exactly that dispatch on *every* operation.
- **Unboxed representations.** A statically typed `int` can live in a register or a flat array slot as raw bytes. A dynamically typed `int` is often **boxed** — a heap object with a type tag — so arrays of them are arrays of pointers (cache-hostile, allocation-heavy).
- **Field access by fixed offset.** A static `struct`/class has a known layout; `p.x` compiles to "load from `p + 8`." A dynamic object is typically a hash map of names → values; `p.x` is a dictionary lookup (until a JIT optimizes it — see hidden classes).
- **Monomorphization & inlining.** Knowing concrete types lets the compiler generate a specialized copy of a generic function and **inline** it, removing call overhead and enabling further optimization. This is why Rust/C++ generics are zero-cost and Java's erased generics (boxed, virtual dispatch) often aren't.
- **Devirtualization.** Static type info lets the compiler prove which concrete method a call resolves to and inline it, eliminating the vtable indirection.

The headline: **static typing converts runtime decisions into compile-time facts, and facts are free at runtime.**

### 2. What Dynamic Typing Pays — and How JITs Claw It Back

Naively interpreted, dynamic code pays a tax on every operation: read both operands' type tags, look up the operation, possibly box/unbox, dispatch. A property access `obj.x` is a hash lookup. This is real, and it's why a naive interpreter (CPython) is ~10–100× slower than native for tight numeric loops.

But the modern story is **JIT recovery**, and a professional must explain it:

- **Hidden classes / shapes / maps (V8, SpiderMonkey, HotSpot for objects):** the JIT observes that objects created the same way share a layout, assigns them a *hidden class* with **fixed field offsets**, and turns `obj.x` from a dict lookup into a single offset load — *as fast as a static field access* — as long as the object's shape is stable.
- **Inline caches (ICs):** at a call/access site, the JIT caches "last time, the receiver was hidden-class H and the method was at offset N." If the next receiver matches (the *monomorphic* common case), it skips the lookup entirely. Sites stay fast while *monomorphic*; they degrade through *polymorphic* (a few shapes) to *megamorphic* (many shapes → back to slow lookup).
- **Speculative type specialization + deopt:** the JIT compiles a hot loop assuming the types it has observed (e.g., "this array holds only small ints"), producing near-native code. If an assumption is violated (someone puts a string in the array), it **deoptimizes** back to the interpreter and recompiles. PyPy and V8 live on this.

The professional synthesis: **a warm JIT on type-stable dynamic code approaches static-language speed. The gaps that remain are (a) warmup cost, (b) the boxing/cache-locality penalty for heterogeneous data, (c) megamorphic sites, and (d) the JIT's inability to assume stability the way a static compiler can *prove* it.** "Dynamic is inherently slow" is wrong; "dynamic makes peak, predictable, low-warmup performance harder" is right.

### 3. The Empirical Question: Do Static Types Reduce Bugs?

This is the most-debated and most-folklore-ridden claim in the whole topic. The honest professional answer: **the evidence is mixed but trends positive, with the strongest signal for large, long-lived, collaborative codebases — and every study has methodological caveats.**

What the literature actually shows:

- **The most-cited industrial result** (Gao, Bird, Barr, *To Type or Not to Type*, ICSE 2017): they took public JavaScript bugs that had fixes, stripped the fix, and asked whether adding **TypeScript or Flow** annotations would have caught the bug at compile time. Result: **~15% of the public bugs in their corpus were detectable by types.** That's a meaningful fraction *and* it's only the bugs that (a) were public, (b) had a clear fix, and (c) are the *kind* a type checker catches — it's a lower bound on one slice, not "types cut bugs by 15%."
- **Controlled experiments are genuinely mixed.** Several small lab studies (Hanenberg et al. and others) found *no* significant development-time advantage for static typing on small tasks, and sometimes a *cost*. Others found benefits for *maintenance*, *API discovery*, and *fixing type errors faster*. The signal is weak and task-dependent at small scale.
- **The effect grows with scale and lifetime.** Where studies and industry reports converge is that static typing's payoff is **superlinear in codebase size, team size, and code age** — exactly the regime where you can't hold the whole program in your head and the compiler's whole-program check substitutes for the reviewer who's left the company. The bug-catching value of "the compiler lists every caller affected by this rename" is hard to measure in a 2-hour lab task and enormous in a 5-year codebase.

The defensible professional statement: *"Types don't reliably make a 200-line script better, and the controlled evidence at small scale is mixed. For large, long-lived, multi-team systems, the weight of evidence and near-universal industry behavior favors static checking — primarily through refactoring safety, API documentation, and catching the `null`/wrong-shape class of error before production."* Never oversell it; never cite "15%" without its caveats.

### 4. The Industry Trend: Dynamic Languages Bolting On Static Checking

The market has voted, and the vote is one-directional:

- **TypeScript over JavaScript** — now the default for serious frontend/Node work; JS-without-types is increasingly the exception in large orgs.
- **mypy / Pyright over Python** — type hints (PEP 484) went from experimental (2014) to ubiquitous; Dropbox (mypy's birthplace), Instagram, and others run strict checking at scale.
- **Sorbet over Ruby** — Stripe built it for a multi-million-line monolith because the dynamic discipline stopped scaling with the team.
- **Hack over PHP** — Meta's gradually-typed PHP dialect, born of the same pressure at facebook.com scale.
- **Flow** (Meta's JS checker), **TypeScript-checked JS** via JSDoc, **RBS/Steep** for Ruby — the same pattern repeats.

The *why* is the professional insight: these are all **large, long-lived, high-headcount** codebases where the costs dynamic typing defers (the production `undefined`/`None` crash, the terrifying refactor, the "what shape is this dict?" archaeology) **grew faster than the codebase**, while the benefits dynamic typing front-loads (fast prototyping) stopped mattering for code that's a decade old. The gradient points toward static *because the cost structure of large systems rewards paying early*. Crucially, they all chose **gradual** static typing — bolt-on, not rewrite — because the gradual guarantee (`middle.md`) made it economically feasible. Nobody migrates the other way because there's no analogous pressure pulling a large static codebase toward dynamic.

### 5. The Refactor Made Safe by Types (a Concrete Professional Win)

The single most reliable, least-disputed benefit of static typing in a large codebase is **refactoring safety**. Rename a field, change a function's signature, split a type — and the compiler produces an exhaustive list of every site that must change. In a dynamic codebase, you have grep, your tests, and prayer; a missed call site ships and crashes on the path your tests didn't cover.

```typescript
// Rename `User.name` -> `User.fullName`. The compiler flags ALL of these, statically:
function greet(u: User) { return `Hi ${u.name}`; }   // ERROR after rename — fix here
// ...and the other 412 call sites across the monorepo, before any of them runs.
```

The dynamic equivalent: `grep -r '\.name'` (false positives galore — every object has *some* `.name`), run the test suite (covers the paths it covers), deploy, and find the missed one in Sentry next Tuesday. This is why even teams that love dynamic prototyping reach for types once code calcifies — *refactoring is where the deferred cost comes due, and types are the prepayment.*

### 6. The Production Crash a Type Would Have Caught

The counterpart of the safe refactor is the crash that motivates the whole migration. Every large dynamic codebase has a graveyard of these:

```python
# The path nobody tested. find_account returns None for closed accounts.
acct = find_account(user_id)
balance = acct.balance          # AttributeError: 'NoneType' object has no attribute 'balance'
                                # Fires in prod, for closed accounts only, at month-end batch.
```

```javascript
// config.retries is sometimes undefined (older config format)
for (let i = 0; i < config.retries; i++) { ... }  // undefined -> loop never runs, silent data loss
// or: someObject.handler()  ->  "undefined is not a function"
```

A static system that **tracks nullability** (`strictNullChecks`, `Optional[Account]` + mypy, Kotlin `Account?`) turns each of these into a *compile error on the laptop*: "object is possibly `undefined`" / "`Account | None` has no attribute `balance`." The professional framing isn't "types prevent all bugs" — it's "types convert a specific, *very common, very expensive* class of bug (the unhandled empty/wrong-shape value on an untested path) from a 2 a.m. page into a red squiggle." That class is large enough, and that conversion valuable enough, to justify the migration cost in most large systems.

---

## Code Examples

### The performance gap, concretely (and the JIT closing it)

```python
# CPython, no JIT: every += dispatches on type tags, ints are boxed objects.
def sum_squares(n):
    total = 0
    for i in range(n):
        total += i * i      # each op: tag-check, dispatch, box/unbox, alloc
    return total
# ~10-50x slower than the equivalent C/Go/Rust loop, dominated by per-op dynamic dispatch.
```

```python
# PyPy (tracing JIT): observes total/i stay ints, specializes the loop to unboxed integer
# arithmetic, and runs within a small factor of native — same SOURCE, JIT recovered the cost.
```

```rust
// Rust: type known at compile time. Unboxed i64 in a register, no checks, monomorphized,
// auto-vectorizable. The compiler "spent" the static type to buy native speed for free.
fn sum_squares(n: i64) -> i64 {
    (0..n).map(|i| i * i).sum()
}
```

### Hidden classes / shapes: why object access *can* be fast in JS

```javascript
// V8 assigns a hidden class. Create objects the SAME way and `.x` becomes a fixed-offset load.
function makePoint(x, y) { return { x, y }; }   // all share hidden class C0 -> {x:0, y:8}
const pts = Array.from({length: 1e6}, (_, i) => makePoint(i, i));
let s = 0;
for (const p of pts) s += p.x;   // monomorphic site: IC caches offset -> ~static speed

// ...but break the shape and you fall off the fast path:
pts[500000].z = 1;               // new hidden class -> site goes polymorphic/megamorphic -> slow
```

The professional lesson encoded here: dynamic *peak* performance exists but is **fragile** — it depends on type/shape stability the programmer must maintain implicitly, whereas static typing *guarantees* the stability the optimizer needs.

### The nullability win, made static

```python
# mypy with strict optional: the crash becomes a build error.
from typing import Optional

def find_account(uid: int) -> Optional["Account"]:
    ...

acct = find_account(uid)
print(acct.balance)
# mypy error: Item "None" of "Optional[Account]" has no attribute "balance"
# -> forces:  if acct is not None: print(acct.balance)
```

```typescript
// strictNullChecks: same class of bug, same compile-time catch.
function find(id: number): Account | undefined { ... }
const a = find(id);
console.log(a.balance);   // TS error: 'a' is possibly 'undefined'
```

### The `any` flood anti-pattern (what a bad migration produces)

```typescript
// Migration done wrong: errors silenced with `any`/`@ts-ignore` to "finish" fast.
function process(data: any) {                  // any in
    // @ts-ignore
    return data.items.map((x: any) => x.value); // any out
}
// Type coverage report: "100% of functions annotated." Actual safety: ~zero.
// The build is green and the production crashes are identical to the untyped version.
```

---

## Coding Patterns

### Pattern 1: Migrate in strictness tiers, ratchet forward

Start the checker in its most permissive mode to get a green build, then enable strict flags (`strictNullChecks` first — highest ROI) module by module. Add a CI **ratchet**: the count of `any`/`type: ignore`/untyped functions may only decrease. Coverage climbs monotonically; nobody can regress it under deadline pressure.

### Pattern 2: Type the boundaries before the internals

Annotate public function signatures, module interfaces, and data models first — they constrain the most call sites and give the checker the most leverage. Internal locals can ride on inference.

### Pattern 3: Validate-and-narrow at every dynamic edge

External data (HTTP, JSON, DB rows, config) enters as `unknown`/`Any`; run it through a validator (Zod, pydantic, dataclasses + checks) into a precise type *once*, at the edge. This closes the erasure leak (`senior.md`) that would otherwise make your types decorative.

### Pattern 4: Keep object shapes stable for the JIT (dynamic perf)

When performance matters in dynamic code: initialize all fields in the constructor, don't add/delete properties after creation, keep arrays homogeneous, and keep hot call sites monomorphic. You're manually preserving the layout stability the JIT's hidden classes and inline caches depend on.

### Pattern 5: Invest in stub quality

A migration is only as safe as the types of the libraries you call. Use/maintain high-quality stubs (DefinitelyTyped, typeshed); a wrong stub is worse than no stub because it asserts a false guarantee the checker then trusts.

---

## Best Practices

- **Sell migrations on refactoring safety and the null/shape crash class, not on "fewer bugs" in the abstract.** Those are the defensible, evidence-backed, and viscerally-felt wins. Cite the TypeScript/Flow ~15% result *with* its caveats; don't pretend it's "15% fewer bugs."
- **Turn on strict null checking first.** It targets the single most common, most expensive runtime type crash and delivers the most safety per unit of migration effort.
- **Track `any` as technical debt with a budget.** A migration that floods `any` is theater. Measure real coverage (non-`any` data flow), not "percent annotated."
- **Don't promise performance you can't guarantee in dynamic code.** A JIT *can* hit near-native speed but won't *predictably* — if you need bounded, warmup-free latency, that's an argument for a statically typed language, not a JIT.
- **Match discipline to lifetime and scale.** Don't impose strict static typing on a throwaway script; don't run a 10-year platform on untyped dynamic code. Estimate where the system sits on the cost-curve crossover.
- **Make the migration incremental and reversible-safe.** Lean on the gradual guarantee: type module by module, keep the build green throughout, never big-bang.
- **Keep humans in the loop on the empirical claim.** The honest position is "mixed evidence at small scale, positive at large scale, strong industry signal." Anyone who tells you the research is settled in either direction hasn't read it.

---

## Edge Cases & Pitfalls

- **The `any` flood.** The most common migration failure: silence errors with `any`/`@ts-ignore` to ship, producing the *appearance* of types and *none* of the safety. Guard with coverage metrics and a ratchet.
- **Wrong stubs are worse than no stubs.** An incorrect `.d.ts`/`.pyi` makes the checker confidently endorse a falsehood — a silent unsound boundary. Audit critical stubs.
- **JIT warmup and tail latency.** A tracing JIT is slow until hot and can **deoptimize** mid-run, causing latency spikes — a real problem for short-lived processes (serverless) and latency-SLO services. Static/AOT code has no warmup.
- **Megamorphic call sites silently kill dynamic perf.** A site that sees many object shapes falls off the inline-cache fast path back to slow lookup — invisible in code, visible only in a profiler.
- **Erased annotations don't validate runtime input.** A perfectly typed Python/TS codebase still crashes on malformed external data unless you *validate* at the edge — the types were erased before that data arrived (`senior.md`).
- **Overselling the bug research backfires.** Quoting "types reduce bugs 15%" as settled fact invites a teammate who read the paper to discredit your whole argument. Lead with the caveats; you'll be more persuasive.
- **Static typing can slow a genuinely exploratory phase.** In the molten early design of a feature, fighting the checker over shapes that change daily is real friction — a legitimate reason to prototype dynamically and type later.
- **Migration touches culture, not just code.** Teams that prized dynamic terseness resist; the migration needs buy-in, tooling, and exemplar modules, or it stalls at 30% coverage and `any` everywhere.

---

## Apply it

1. Define the user or business outcome that **Static vs Dynamic Typing** should improve.
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

- Which measurable outcome justifies investing in Static vs Dynamic Typing?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
