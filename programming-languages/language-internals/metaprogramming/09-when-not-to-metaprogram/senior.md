# When NOT to Metaprogram — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **When NOT to Metaprogram** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The magic-budget framework you apply in review

When a PR introduces metaprogramming, run it through a fixed gauntlet. If it doesn't clear *all* of these, it's a no — or a "make it boring."

1. **Is this framework-level or app-level?** Framework-level (written once, owned, tested, isolated at a boundary) can earn magic. App-level magic — reflection or a decorator threaded through business logic — almost never does. It scatters action-at-a-distance through the code people change most.
2. **Does it pay for itself many times over?** Not "does it save lines" — does it remove *large, painful, error-prone* work across *many* sites? If it saves 30 lines once, no. If it correctly serializes 400 types that would otherwise be hand-written and drift, maybe.
3. **Can we debug it in production?** Trace the failure path. Does the stack point into our code or into a proxy class? Can on-call set a breakpoint where the logic lives? If not, you're shipping a system that punishes its operators.
4. **Does it survive our build/deploy constraints?** AOT, native image, fast cold start, security sandboxes that forbid runtime codegen. If any are in your future, reflection-heavy magic is a landmine.
5. **Is the bus factor > 1?** If only the author can modify it, it's not done. Demand a second person who can change it confidently.
6. **Is there a non-magic alternative that's only slightly more code?** Explicit wiring, hand-written DI, readable committed codegen, a `switch`. If the boring version is only modestly longer, it wins — *modestly more code* is a price worth paying for *radically more debuggability*.

### 2. The narrow profile of justified metaprogramming

Magic earns its place when **all** of these hold simultaneously:

- The boilerplate is **large** (not three lines), **painful** (real cognitive/typing burden), **error-prone** (easy to get subtly wrong by hand), and **repeated across many sites**.
- It's a **genuine cross-cutting concern** — serialization, ORM mapping, request tracing, transaction boundaries — not a one-off.
- It lives at a **framework boundary**, owned and tested as infrastructure, with plain code inside.
- The team can **debug and modify it** — readable, second-maintainer, traceable.
- There's **no comparably-cheap non-magic alternative.**

Miss any one and the calculus tilts toward boring. This is a narrow band, and that's the point: the justified cases are real but *rare*, and most magic in most codebases is below this bar.

### 3. War story — trapped by the clever DSL

A team built a custom workflow DSL to describe business processes. For the first three processes it was elegant. Then the business asked for a conditional branch the grammar didn't support. Then a loop. Then a way to call out to a service mid-process. Each request meant *extending the language* — new grammar, new parser rules, new error messages, new editor support — and only the original author could do it confidently. He left. The DSL became a cage: the business couldn't get features because the team couldn't safely change the language. They eventually *replaced the DSL with plain functions* — each workflow became a readable Python/Go function calling normal helpers. They lost the "elegance" and gained the ability to ship. **Lesson:** a DSL trades a one-time authoring win for a permanent obligation to evolve a language. Unless the domain is rich and stable, that trade loses.

### 4. War story — debugging Spring annotation magic

A `@Transactional` method wasn't rolling back on a checked exception. The code *looked* obviously correct. The reason lived entirely in invisible magic: Spring's default proxy rolls back on unchecked exceptions only, the proxy is bypassed on self-invocation (a method calling another `@Transactional` method on `this`), and the bean was being proxied by CGLIB in a way that interacted with the visibility of the method. None of this is at the call site. The fix took a senior half a day of *reading framework docs and source*, not reading the application code — because the behavior wasn't in the application code. **Lesson:** framework magic that's well-documented and widely understood (like Spring's) is still a comprehension tax; the difference is the framework is *worth* its budget for a large app. The same annotation in a 10-endpoint CRUD service would be all cost, no payoff. Magic's worth scales with the size of the problem it amortizes over.

### 5. War story — the reflection-heavy service that wouldn't AOT-compile

A service relied on runtime reflection for serialization and DI. It passed every test on the JVM. Two days before a launch that required GraalVM native image (for fast cold starts on a serverless platform), the native build failed: the closed-world AOT compiler can't see reflective accesses, so every reflected type needs explicit configuration, and the DI framework generated proxies at runtime that native image forbids. The team spent the launch window writing reflection config and swapping libraries instead of shipping. **Lesson:** reflection's flexibility *is* its incompatibility with AOT. If fast cold start, native image, or a no-runtime-codegen platform is anywhere in your roadmap, runtime magic is a debt that comes due all at once, at the worst time.

### 6. War story — the rewrite everyone was happier about

The metaclass that auto-wired everything (from middle level) was finally deleted. The senior who did it described the PR as "removing 200 lines of magic and adding 500 lines of boring." The team's reaction was relief: go-to-definition worked, breakpoints worked, new hires read the code instead of being tutored on it, and stack traces pointed at real files. The "more lines" were the cheap kind — obvious, greppable, steppable. **Lesson:** line count is a terrible proxy for complexity. 500 boring lines can be radically simpler than 200 magic ones. De-magicking is often a net win even when it adds code.

---

## Code Examples

### Example 1 — Hand-written DI beats annotation magic for a small service (Go-flavored pseudo)

**Magic (annotation/container DI):**

```text
@Component class OrderService { @Autowired Repo repo; @Autowired Mailer mailer; }
// container scans, reflects, wires at startup — invisibly, slowly, AOT-hostile
```

**Boring (explicit wiring at the composition root):**

```go
func main() {
    repo := NewRepo(db)
    mailer := NewMailer(cfg)
    orders := NewOrderService(repo, mailer)   // the entire dependency graph, visible
    server := NewServer(orders)
    server.Run()
}
```

The wiring is one readable function. No scanning, no reflection, no proxies, AOT-friendly, greppable, and a junior sees the whole graph at a glance. For most services, hand-wired DI at a composition root beats a container — the container's magic only starts paying off at a graph size most apps never reach.

### Example 2 — Readable committed codegen vs. invisible runtime reflection

When you *do* need to eliminate large boilerplate (say, serializers for 400 types), prefer **codegen that commits source files** over runtime reflection:

```text
//go:generate serializergen ./...     # produces user_gen.go, order_gen.go, ...
```

```go
// user_gen.go — committed, readable, breakpointable, diffed in PRs
func (u *User) MarshalJSON() ([]byte, error) {
    // generated, but it's real code you can open and step through
    ...
}
```

This clears the bar: it removes large/error-prone boilerplate, it's framework-level, it's AOT-friendly (no runtime reflection), and the output is *plain code a human can read and debug*. The reviewer sees exactly what ships. This is the "good" end of metaprogramming — automation whose output is still boring code.

### Example 3 — De-magicking a monkeypatch into a wrapper

**Magic (monkeypatch a third-party client):**

```python
import thirdparty
_orig = thirdparty.Client.request
def patched(self, *a, **k):           # reaches into someone else's class
    return _orig(self, *a, **k) + retry_logic()
thirdparty.Client.request = patched   # breaks on their next release
```

**Boring (wrap it):**

```python
class Client:                          # our adapter, our control
    def __init__(self): self._inner = thirdparty.Client()
    def request(self, *a, **k):
        return with_retries(lambda: self._inner.request(*a, **k))
```

The wrapper is explicit, decoupled from the library's internals, survives upgrades, and is the thing the rest of the code depends on. Monkeypatching is magic *at someone else's expense* — and you inherit the breakage.

---

## Coding Patterns

- **The composition root.** Wire dependencies explicitly in one place (`main`/bootstrap). Reach for a DI container only when the graph is genuinely large *and* you've felt the manual pain — not preemptively.
- **Codegen-over-reflection.** When automation is justified, generate committed, readable source. The output should be boring code a human can step through. This keeps AOT open and reviews honest.
- **Magic at the edge, boring in the core.** Confine any unavoidable magic to a thin framework boundary; keep business logic explicit. Magic must not leak into the code people change daily.
- **Wrap third-party behavior; never patch it.** Own an adapter; depend on the adapter.
- **The de-magicking refactor.** Periodically hunt for app-level magic with bus factor one and replace it with explicit code. Treat "added lines, removed magic" as a *win*, and say so in the PR.

---

## Best Practices

- **Make the magic budget explicit on the team.** Name it. "We spend our budget on the serialization layer; everything else stays explicit." Shared language prevents a thousand small over-reaches.
- **Require a second maintainer for any magic.** No bus-factor-one abstractions ship. If you can't staff a second, that's your answer.
- **Trace the 3 a.m. failure path in review.** Literally ask: where does the stack point when this breaks? If into a proxy/generated frame, push back.
- **Protect your AOT/cold-start future.** Treat runtime reflection and runtime codegen as debts against any native-image or serverless roadmap.
- **Prefer reversible decisions.** Boring first; you can add magic later. Reversibility is a feature.
- **Don't moralize — cost it.** Both "magic is always bad" and "magic is elegant" are lazy. Walk the framework, weigh lifetime cost, decide. Sometimes the answer is yes.
- **Reward de-magicking.** Make removing clever code a celebrated kind of contribution, not a thankless one. Teams imitate what gets praised.

---

## Edge Cases & Pitfalls

- **The "but the framework does it" defense.** Yes — and the framework is amortizing its magic over millions of users and a dedicated team. Your one-off app abstraction is amortized over your ten engineers. Scale changes the verdict.
- **De-magicking that loses a real invariant.** Some magic *enforces* something (e.g., "every entity is auto-registered, so none can be forgotten"). When you remove it, you must replace the *guarantee*, not just the code — often with a test or a lint rule. Don't trade magic for a silent footgun.
- **The senior who never met a clever trick they didn't love.** Seniority can curdle into showing off. The mark of real seniority is the *boring* PR. Watch yourself.
- **Over-correcting into anti-abstraction.** Refusing *all* metaprogramming leads to massive, drifting, hand-maintained boilerplate that's its own bug source. The justified cases are rare but real; honor them.
- **Magic that's load-bearing and undocumented.** The worst kind: critical, invisible, and only in one person's head. Prioritize de-magicking these *before* the author leaves, not after.
- **Confusing "widely used framework magic" with "my team's bespoke magic."** Spring/Rails magic at least has docs, Stack Overflow, and a community. Your in-house DSL has none of that. The bar for bespoke magic is far higher.
- **Performance magic in the wrong layer.** Reflection in startup wiring is fine; the same reflection in a per-request hot path tops the flame graph. The construct's acceptability is contextual — judge per call site, not in the abstract.

---

## Apply it

1. State the system invariant that **When NOT to Metaprogram** must protect.
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

- Which invariant must remain true when When NOT to Metaprogram fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
