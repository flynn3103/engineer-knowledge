# When NOT to Metaprogram — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **When NOT to Metaprogram** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. "Magic" = behavior you can't see at the call site

Read this code:

```python
@app.route("/users/<id>")
def get_user(id):
    return db.query(User).get(id)
```

Where does the URL `/users/123` *actually* get matched to this function? Not here. A decorator registered this function somewhere you can't see. Where does `id` come from — a string or an int? The framework decided. This isn't bad; web frameworks earn their magic. But notice the feeling: **the behavior is real, and it is not on the screen.** That feeling — "the framework knows but I don't" — is the cost of metaprogramming, paid in small installments every time you read the code.

The opposite is **explicit** code, where what happens is what you see:

```python
def get_user(id):
    return db.query(User).get(id)

router.add("GET", "/users/<id>", get_user)  # the wiring is right here
```

Same behavior. But now `router.add` is a line you can read, click into, and grep for.

### 2. The four costs magic adds

Every time you reach for metaprogramming, you are adding some amount of:

1. **Reading cost.** The next person (often future-you) has to hold the magic in their head to understand a plain-looking line.
2. **Debugging cost.** When it breaks, the stack trace runs through generated/reflected/proxied code. You **cannot set a breakpoint in code that doesn't textually exist.**
3. **Tooling cost.** Autocomplete goes blank. "Go to definition" lands nowhere. `grep` can't find a name that was built from string pieces at runtime. Refactoring tools can't follow it.
4. **Onboarding cost.** A new hire can read plain code on day one. Magic, they have to be *taught* — and if the teacher left, nobody can.

Plain code costs you a little more typing *now*. Magic costs everyone a little more *forever*. Multiply by team size and years and the math usually loses.

### 3. The decision ladder: prefer the simplest tool that works

When you feel the urge to metaprogram, walk *down* this ladder and stop at the first rung that solves your problem:

```text
plain code
  → a function
    → a generic / template
      → a tiny bit of reflection
        → code generation you can read
          → a macro
            → a metaclass / deep runtime magic
```

Each step down buys more power and pays more cost. Most problems are solved on the top three rungs. If you find yourself reaching for the bottom rungs, the honest question is: *am I solving a real, painful, repeated problem — or am I being clever?*

### 4. "Is the boilerplate actually painful — or just slightly repetitive?"

Repetition is not automatically bad. Three nearly-identical structs are easy to read, easy to change one at a time, and trivial to grep. A macro that generates them is harder to read, breaks `grep`, and means a change to one means understanding the macro. Ask: *would removing this repetition save real effort, or just make me feel tidier?* Slightly-repetitive-but-obvious usually beats clever-but-invisible.

### 5. Kernighan's warning

There is a famous line worth memorizing early:

> "Debugging is twice as hard as writing the code in the first place. Therefore, if you write the code as cleverly as possible, you are — by definition — not smart enough to debug it." — Brian Kernighan

Metaprogramming is the most concentrated form of "as cleverly as possible." Kernighan's point is not that you're dumb — it's that *everyone*, including future-you, is operating at reduced capacity when debugging at 3 a.m. Write the code so that the tired, confused version of you can still understand it.

---

## Code Examples

### Example 1 — Reflection where a `switch` is clearer (Python)

**The magic version:**

```python
def handle(event):
    # call a method named handle_<type> by string lookup
    method = getattr(self, "handle_" + event.type, None)
    if method:
        method(event)
```

This is clever. It is also: not grep-able (search `handle_click` finds nothing — the name was built from a string), not autocomplete-able, and silently does nothing if `event.type` is misspelled. A typo becomes a runtime no-op, not a compile error.

**The boring version:**

```python
def handle(event):
    if event.type == "click":
        self.handle_click(event)
    elif event.type == "hover":
        self.handle_hover(event)
    else:
        raise ValueError(f"unknown event type: {event.type}")
```

More lines. But every method is grep-able, the IDE finds them, an unknown type *fails loudly*, and a junior reads it top to bottom. For a handful of cases, this wins.

### Example 2 — A macro to save three lines (don't)

```text
// "Clever" macro, used once:
DEFINE_GETTER(name)   // expands to a getter for `name`

class User {
    DEFINE_GETTER(name)
}
```

To save one line, you have introduced a macro that: doesn't show up in "go to definition," produces confusing compiler errors, and must be learned by everyone. Just write the getter. **Metaprogramming to save three lines is almost never worth it.**

### Example 3 — A config file beats a DSL (most of the time)

You want users to describe a pipeline. Tempting: invent a tiny language.

```text
pipeline { fetch -> transform |> validate >> save }   # a custom DSL
```

Cute. Now *you* maintain a parser, error messages, an editor mode, and documentation for a language only your team speaks. Compare:

```yaml
# plain config — every tool on earth already reads YAML
steps:
  - fetch
  - transform
  - validate
  - save
```

The config is boring, universally tooled, and obvious. Reach for a DSL only when a config genuinely can't express what you need — and rarely even then.

---

## Coding Patterns

- **The boring-first pattern.** Always write the plain version *first*. If it's genuinely too repetitive after the third copy, *then* consider abstracting. You almost never regret starting plain.
- **The "make the wiring visible" pattern.** Prefer `router.add("GET", path, handler)` over a `@route` decorator when the team is small and the magic isn't paying for itself. Explicit wiring is grep-able and steppable.
- **The "fail loud" pattern.** If you must do a string/reflective lookup, always handle the miss with a loud error, never a silent no-op. A silent miss turns a typo into a ghost bug.
- **The "readable codegen" pattern.** If you must generate code, generate *readable source files that get committed*, not invisible runtime magic. People can open, read, and breakpoint generated files.

---

## Best Practices

- **Prefer the simplest tool that works.** Walk down the ladder; stop early.
- **Apply the rule of three.** Don't abstract two cases. Wait for the third real one.
- **Ask "would a junior get this in six months?"** If no, reconsider.
- **Ask "can I debug this at 3 a.m.?"** If no, reconsider.
- **Keep errors at compile time** when the language lets you. A compile error is cheap; a midnight runtime error is not.
- **Don't monkeypatch third-party libraries.** Wrap them in your own boring function instead. Patching someone else's code is magic that breaks on their next release.
- **Avoid stringly-typed dispatch** when a real symbol works. Let the compiler and IDE help you.
- **When in doubt, write it boring.** You can always add magic later; removing it after the team depends on it is much harder.

---

## Edge Cases & Pitfalls

- **"It's just one decorator" creep.** Each one looks harmless. Twenty of them, interacting, and nobody can trace what a request actually does. Magic accumulates; budget it.
- **The typo that compiles.** Stringly-typed and reflective code turns spelling mistakes into silent runtime failures instead of red squiggles. This is the single most common junior trap.
- **Copy-pasting magic you don't understand.** You find a clever decorator on Stack Overflow, paste it, it works — until it doesn't, and now you're debugging code you never understood. If you can't explain it, don't ship it.
- **Confusing "clever" with "good."** Clever code impresses for a day. Boring code that the whole team can maintain impresses for years. Aim for boring.
- **Removing repetition that wasn't hurting.** Three obvious copies are fine. Don't introduce a macro to satisfy a tidiness urge; you may be trading readable repetition for invisible coupling.
- **Forgetting future-you is a junior.** At 3 a.m., on a system you haven't touched in a year, *you* are the confused new hire. Write for that person.

---

## Apply it

1. Choose one small, known input for **When NOT to Metaprogram**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does When NOT to Metaprogram solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
