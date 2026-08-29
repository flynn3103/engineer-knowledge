# When NOT to Metaprogram — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **When NOT to Metaprogram** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The five cost axes — name them, then weigh them

When someone proposes metaprogramming, score it on five axes. You don't need exact numbers; you need a shared vocabulary so the review is about engineering, not taste.

1. **Comprehension.** Can a competent teammate understand the *call site* without knowing the magic? If a plain-looking line silently does five hidden things, comprehension cost is high.
2. **Debuggability.** When it fails, where does the stack trace point? Into your code (good) or into `Proxy$$EnhancerBySpringCGLIB$$1a2b` (bad)? Can you set a breakpoint where the logic actually lives?
3. **Tooling.** Does autocomplete still work? Does "find all references" find the references? Can a rename refactor follow it? Can `grep "userName"` find the field if it's accessed via `getattr(obj, "user" + "Name")`? Each "no" is a tax on every future change.
4. **Performance.** Reflection is slower than direct calls. Proxies add indirection. Heavy compile-time metaprogramming (template/macro expansion) blows up build times. Reflection-heavy startup is slow (matters for serverless cold starts).
5. **Maintenance.** What happens on the next library upgrade? When the author leaves? When the language adds a feature the macro didn't anticipate? Magic that reaches into internals is fragile across version skew.

A proposal that scores badly on three or more axes is almost certainly not worth it. A proposal that scores badly on one but saves enormous, genuine pain might be.

### 2. The decision ladder, now with break-even

The ladder from junior level — `plain → function → generic → reflection → codegen → macro → metaclass` — is not just "prefer the top." Each rung has a *break-even point in cases*:

```text
1 case      → plain code. Always.
2 cases     → plain code, duplicated. (Rule of three: 2 might be a coincidence.)
3–5 cases   → a function or a generic. The cheapest real abstraction.
many cases  → reflection / codegen MAYBE, if the boilerplate is large & error-prone.
```

The mistake is jumping straight to the bottom rung at *one* case because it's interesting. The discipline is computing: *how many cases do I actually have, how painful is each, and does the abstraction pay back across all of them after subtracting its own cost?*

### 3. The anti-patterns, costed

- **Reflection where an interface/`switch` works.** If you have a closed set of types, an interface or a `switch` is faster, grep-able, autocomplete-able, and fails at compile time. Reflection here buys nothing and costs everything. Use reflection only for *genuinely open* sets you can't enumerate.
- **A DSL where a config or plain API works.** A DSL means you now own a language: a parser, error messages, an editor mode, docs, and a learning curve for every hire. Justified only when the domain is rich enough that config/API genuinely can't express it. For a list of steps, a YAML list wins.
- **Magic frameworks for a CRUD app.** Annotation-driven dependency injection, AOP, dynamic proxies — for ten endpoints and three tables? You've imported a framework's entire magic budget to save code you could read in an afternoon. The framework's complexity dwarfs your app's.
- **Clever macros nobody else can modify.** A macro that only its author understands has a bus factor of one. When they leave, the macro becomes a load-bearing mystery.
- **Monkeypatching third-party libs.** You're now coupled to that library's *private internals*. Their next patch release breaks you silently. Wrap, don't patch.
- **Stringly-typed dynamic dispatch.** `dispatch[event_name]()` where `event_name` is a string defeats the type checker and the IDE; a misspelling is a runtime failure, not a red squiggle.

### 4. Compile-time vs runtime failure — the cheapest difference you control

A huge, under-appreciated cost of magic is *when it fails*. Plain typed code fails at compile time: cheap, local, in your terms, before it ships. Reflection, stringly-typed dispatch, and dynamic proxies push failures to *runtime* — sometimes only on a specific code path, sometimes only in production. The same logical bug costs a red squiggle in the boring version and a 2 a.m. page in the magic version. When choosing, ask: *does this move my failure from compile time to runtime?* If yes, that's a heavy thumb on the scale toward plain code.

### 5. "Explicit is better than implicit"

The Zen of Python states it directly: *Explicit is better than implicit.* This is not a Python-only value — it's a general bias. Implicit (magic) behavior reads cleaner on the happy path and reads as a *mystery* on every other path. Go was designed around the same belief: deliberate minimalism, no exceptions hierarchy, no inheritance, long-resisted generics — not because the designers couldn't add power, but because they prized code being *obvious to a stranger* over code being clever. Whatever your language, when implicit and explicit both work, explicit ages better.

---

## Code Examples

### Example 1 — Costing reflection vs. an interface (Go)

**Magic:**

```go
// Dispatch by struct tag via reflection.
func Handle(msg any) {
    t := reflect.TypeOf(msg)
    m, ok := registry[t.Name()]   // string-keyed, runtime
    if ok {
        m(msg)
    }
    // silent no-op if not found
}
```

Cost: not grep-able (handlers keyed by string name), reflection overhead per call, silent failure on an unregistered type, and `registry` is populated by more magic elsewhere.

**Plain:**

```go
type Handler interface{ Handle() }

func Handle(msg Handler) { msg.Handle() }   // compile-checked, fast, obvious
```

Cost: each message type implements one method. That's it. The compiler guarantees completeness, the call is a direct dispatch, and a junior reads it instantly. **For a closed set of types, the interface wins on every axis.** Reflection is only justified when types are genuinely open and unknown at compile time.

### Example 2 — DSL vs. config, costed (pseudo)

**Magic — a custom rules DSL:**

```text
rule "high value" when amount > 1000 and country in ("US","UK") then flag
```

To ship this you now own: a lexer, a parser, error messages ("syntax error near `then`" — in *whose* terms?), an editor plugin, docs, and a test suite for the language itself. Bus factor: the author. Every new rule type means extending the grammar.

**Plain — config + a tiny evaluator:**

```yaml
- name: high value
  when: { amount_gt: 1000, country_in: ["US", "UK"] }
  then: flag
```

A few predicate functions evaluate this. Universally tooled (every editor reads YAML), errors are in plain validation terms, no grammar to maintain. A DSL is justified only when the rule space is genuinely too expressive for structured config — which is rarer than it feels when you're excited.

### Example 3 — The "rewrite the magic as boring code, everyone was happier" arc (Python)

A team had a metaclass that auto-registered every subclass into a global registry and injected methods based on class attributes. New hires couldn't trace where methods came from; stack traces pointed into the metaclass; `grep` found nothing.

**Before** (sketch):

```python
class Base(metaclass=AutoRegister):
    fields = ["id", "name"]   # methods get injected based on this, invisibly
```

**After** — explicit, boring:

```python
class User(Base):
    id: int
    name: str

    def to_dict(self):              # written out, visible, greppable, steppable
        return {"id": self.id, "name": self.name}

REGISTRY = {"user": User}           # registration is one explicit line
```

More lines. But go-to-definition works, breakpoints work, and onboarding dropped from "ask the one person who gets it" to "read the file." The magic saved typing; the rewrite saved the team.

---

## Coding Patterns

- **Score-before-you-build.** Before adding magic, write the five cost axes on a whiteboard and score the proposal. If three are red, stop.
- **Readable codegen over runtime magic.** If automation is justified, generate *committed source files* that humans can read, breakpoint, and diff in PRs — not invisible runtime behavior. The reviewer sees exactly what ships.
- **Wrap, don't patch.** Need to change a third-party lib's behavior? Wrap it in your own small, boring adapter you control and test. Never reach into its internals.
- **Enumerate before you reflect.** If the set of types/cases is knowable at compile time, use an interface, a `switch`, or a generated exhaustive map — not runtime reflection.
- **Keep the magic at the edge.** If you must have a magic layer (a framework boundary), keep it thin and at the system's edge, with plain, obvious code inside. Don't let magic leak into business logic.

---

## Best Practices

- **Make the trade explicit in the PR description.** "This adds reflection; here's the boilerplate it removes and the tooling/debug cost it adds." Force the team to weigh it consciously.
- **Default to compile-time failure.** Choose designs where mistakes are caught by the compiler, not discovered in production.
- **Respect the rule of three.** Don't abstract until the third real case; two can be a coincidence.
- **Measure the boilerplate before automating it.** Is it actually large and painful, or just slightly repetitive? Count the lines and the change-frequency.
- **Stay grep-able.** If a future engineer can't find all usages of a thing with a text search, you've made every future change more dangerous.
- **Watch your dependencies' AOT/native story.** If you might need GraalVM native image, iOS AOT, or fast cold starts, reflection-heavy magic becomes a liability long before you notice.
- **Name a second maintainer.** If only one person can modify the magic, it's not done. If you can't find a second, that's a signal the design is too clever.

---

## Edge Cases & Pitfalls

- **Magic that won't AOT-compile.** A reflection-heavy system can work fine on a JIT and then refuse to build as a GraalVM native image or run on a platform that forbids runtime codegen. You discover this late, under deadline. Reflection's flexibility is exactly what AOT can't see.
- **Version skew on internals.** Monkeypatches and macros that reach into library internals break silently on a minor upgrade. The bug surfaces far from the cause.
- **The cost is invisible to the author.** The person who wrote the magic *holds it in their head*, so to them the cost is near zero. The cost is real but lives entirely in *other people's* heads. This asymmetry is why authors consistently underestimate it — and why the decision needs a second opinion.
- **Performance cliffs in hot loops.** Reflection per call is fine in startup wiring and catastrophic in a hot path. The same construct is acceptable in one place and a profiler's top entry in another.
- **The slow build no one attributes.** Heavy compile-time metaprogramming (template/macro expansion) can quietly add minutes to every build for everyone, forever. Nobody connects the slow build to the clever macro.
- **"It's only used internally."** Magic in a shared library leaks its costs to every consumer, who can't see or step into it. Internal magic still has external comprehension cost.
- **Confusing flexibility you have with flexibility you need.** Reflection/DSLs are often justified as "future-proof." YAGNI: you usually don't need the flexibility, and you pay for it every day until the day you (don't) use it.

---

## Apply it

1. Find a real component where **When NOT to Metaprogram** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by When NOT to Metaprogram?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
