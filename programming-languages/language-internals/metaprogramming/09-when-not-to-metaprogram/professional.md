# When NOT to Metaprogram — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **When NOT to Metaprogram** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## The Magic Budget

Treat a codebase as having a finite **magic budget** — a tolerance for indirection that
isn't visible at the call site. Every reflection call, annotation, proxy, metaclass, and
macro spends some of it. Frameworks already spend a large chunk (Spring, ORMs, DI). When
the budget is overdrawn, the symptoms are predictable: people stop trusting the code,
debugging slows, onboarding takes months, and "I don't know how this works, but don't
touch it" becomes the team's relationship to its own system.

The budget framing reframes the decision from "can I metaprogram this?" (almost always
yes) to "is this worth the magic it spends, given how much is already spent?" — a much
better question.

---

## The Real Costs, Priced Out

- **Comprehensibility.** Behavior moves away from the call site (action-at-a-distance).
  A reader sees `save(user)` and cannot tell that an annotation three layers up opens a
  transaction, validates fields, and fires events. The code no longer tells you what it
  does.
- **Debuggability.** You can't breakpoint code that doesn't textually exist (generated,
  reflected, proxied). Stack traces fill with `$$Proxy`, `invoke0`, macro-expansion
  frames. Failures move from compile time to runtime — discovered in production, not CI.
- **Tooling.** Autocomplete, "go to definition," "find usages," and automated refactors
  all rely on static structure. Reflective/stringly-typed/dynamic code is invisible to
  them; `grep` can't find a method name that's assembled at runtime.
- **Error messages.** Macro and template errors are notoriously in implementation terms;
  reflective failures say "NoSuchMethod" with no hint where the contract broke.
- **Performance & startup.** Reflection/proxy overhead per call; annotation scanning and
  metaclass execution inflate startup — a direct hit in serverless/CLI contexts.
- **Maintenance & staffing.** The clever construct is fragile across library upgrades and
  unmaintainable once its author leaves. It raises the experience bar to touch the code.

These are not hypotheticals; they are the standard failure modes that make "we rewrote
the magic as plain code and everyone was happier" a recurring industry story.

---

## The Decision Framework

Prefer the simplest tool that works, escalating only when the previous rung genuinely
fails:

**plain code → a function → a generic/parameterized type → a tiny bit of reflection →
code generation (readable output) → a macro → a metaclass/heavy runtime magic.**

Ask, in order:

1. **Is the boilerplate actually painful, or just slightly repetitive?** The rule of three
   — don't abstract until you've seen it three times. Mild repetition is cheaper than the
   wrong abstraction.
2. **Would a junior understand it in six months?** If not, the magic had better be
   framework-level and well-documented.
3. **Can you debug it at 3am in production?** If the failure mode is opaque, that's a veto.
4. **Does it fail at compile time or runtime?** Prefer techniques that fail fast.
5. **Is there a non-magic alternative** (explicit code, readable codegen, hand-wired DI)
   that's only slightly more verbose? Usually verbosity is the cheaper cost.
6. **Is it app-level or framework-level?** Framework-level magic that serves thousands of
   usages can justify costs that app-level magic cannot.

---

## Anti-Patterns Seen in Production

- **Metaprogramming to save three lines.** A macro/metaclass/reflection trick that
  replaces a small, clear, repetitive block — net negative.
- **Reflection where polymorphism works.** A reflective dispatch table where an interface
  + a `switch`/map would be statically checked and faster.
- **A DSL where a config file or plain API would do.** Bespoke second language for static
  data.
- **Magic frameworks for a CRUD app.** Heavyweight reflective/DI machinery where explicit
  wiring would be shorter and clearer.
- **Monkeypatching third-party libraries.** Fragile across upgrades, invisible to readers,
  a maintenance time bomb.
- **Stringly-typed dynamic dispatch.** Building method/field names from strings, defeating
  every tool and turning typos into runtime errors.

---

## When Metaprogramming IS Justified

The mirror image keeps this honest. Reach for it when:

- The concern is genuinely **cross-cutting** (transactions, logging, serialization) and
  the alternative is the same boilerplate in hundreds of places.
- It's **framework-level**, owned, documented, and serves many usages — not a one-off in
  app code.
- The boilerplate it eliminates is **large, painful, and error-prone** (hand-writing
  serialization for 200 types, wiring a big DI graph by hand).
- The abstraction **pays for itself many times over** and you can still debug it.
- You're using a **compile-time** technique (derive macro, codegen, annotation processor)
  whose output is readable and whose errors are caught at build time.

---

## Best Practices

- **Default to boring.** Make the team prove a metaprogramming technique is worth its
  magic, not the reverse.
- **Push magic down into framework/library layers** that are owned and documented; keep
  application code explicit.
- **Prefer compile-time, readable-output techniques** over runtime, opaque ones.
- **Budget the magic** — be aware how much indirection the codebase already carries.
- **Write the boring version first**; reach for magic only when the boring version is
  demonstrably worse at scale.

---

## Apply it

1. Define the user or business outcome that **When NOT to Metaprogram** should improve.
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

- Which measurable outcome justifies investing in When NOT to Metaprogram?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
