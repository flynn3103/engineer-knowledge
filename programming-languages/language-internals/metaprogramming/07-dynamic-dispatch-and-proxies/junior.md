# Dynamic Dispatch & Proxies — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Dynamic Dispatch & Proxies** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A method that runs vs. a call that's intercepted

Picture an ordinary class:

```text
class Calculator:
    def add(self, a, b): return a + b
```

When you call `calc.add(2, 3)`, the *named* method `add` runs. There is a body. You can read it.

Now picture an object with **no `add` method at all**, but with one special hook:

```text
class Magic:
    def __getattr__(self, name):
        return lambda *args: f"you asked for {name} with {args}"
```

When you call `magic.add(2, 3)`, Python can't find a method `add`, so it calls the hook `__getattr__("add")`, which *manufactures* a function on the spot. The behavior of `add` was **synthesized at runtime** — nobody wrote it. That is the heart of this topic.

### 2. The proxy: one object standing in for another

A **proxy** wraps a **target** and intercepts everything:

```text
   caller  ──►  PROXY  ──►  TARGET (real object)
                  │
                  ├─ before: log, check permission, start timer
                  ├─ forward the call
                  └─ after: stop timer, cache result, log result
```

From the caller's side, the proxy looks *exactly* like the target — same methods, same interface. The caller doesn't know it's talking to a stand-in. That transparency is the whole point: you can slip a proxy in front of any object and add behavior without changing the caller or the target.

### 3. The three things a proxy can do with a call

Every intercepted call gives the proxy three choices:

| Choice | What it means | Example |
|--------|---------------|---------|
| **Forward** | Pass the call to the target unchanged | A transparent wrapper |
| **Augment** | Do extra work before/after forwarding | Logging, timing, caching, transactions, retries |
| **Block / replace** | Don't forward at all; return something else or throw | A security proxy that denies access; a mock that returns a canned value |

### 4. Why this is "metaprogramming"

You are writing code that operates on *calls and method names as data*, not code that hard-codes each method. One small `invoke`/`__getattr__`/`method_missing`/`get`-trap handles **any** method — including methods that don't exist yet. The behavior is generated, not declared. That's the metaprogramming angle: programs writing (the effect of) program parts at runtime.

### 5. The interface vs. class distinction (Java preview)

In Java this split matters a lot. The built-in `java.lang.reflect.Proxy` can only proxy **interfaces** — it generates a class implementing your interfaces and routes every call to one `InvocationHandler`. To proxy a **concrete class** (no interface) you need a library (CGLIB, ByteBuddy) that *subclasses* the class at runtime. Keep this in your head: **JDK proxy = interfaces only; library proxy = subclass a class.**

### 6. The big first trap: self-invocation

A proxy wraps `realObject`. The proxy intercepts external calls. But what happens when a method *inside* `realObject` calls **another of its own methods** via `this`? The call goes straight to the real method — it never goes back out through the proxy. So the augmentation (logging, the transaction) **does not happen** for the internal call. This is the single most surprising proxy bug for juniors, and it bites real Spring applications constantly. We'll see it concretely below.

---

## Code Examples

We'll build the same idea — **a logging proxy that wraps a real object and prints every method call** — in four languages.

### JavaScript — the `Proxy` object

```javascript
const realService = {
  greet(name) { return `Hello, ${name}`; },
  add(a, b) { return a + b; },
};

const loggingProxy = new Proxy(realService, {
  get(target, prop, receiver) {
    const orig = Reflect.get(target, prop, receiver);
    if (typeof orig !== "function") return orig;
    return function (...args) {
      console.log(`-> calling ${String(prop)}(${args.join(", ")})`);
      const result = orig.apply(target, args);
      console.log(`<- ${String(prop)} returned ${result}`);
      return result;
    };
  },
});

loggingProxy.greet("Ada");   // logs the call, forwards, logs the return
loggingProxy.add(2, 3);      // same
```

The `get` **trap** runs every time you read a property (including a method) off the proxy. `Reflect.get` is the "default behavior" helper: it does exactly what would have happened without a proxy. We wrap functions to log around them and leave plain values alone.

### Python — `__getattr__` (intercept only missing attributes)

```python
class LoggingProxy:
    def __init__(self, target):
        # Store target WITHOUT triggering __getattr__ later.
        object.__setattr__(self, "_target", target)

    def __getattr__(self, name):
        # Only called because LoggingProxy itself has no attribute `name`.
        attr = getattr(self._target, name)
        if not callable(attr):
            return attr
        def wrapper(*args, **kwargs):
            print(f"-> {name}{args}")
            result = attr(*args, **kwargs)
            print(f"<- {name} returned {result!r}")
            return result
        return wrapper

class RealService:
    def greet(self, who): return f"Hello, {who}"
    def add(self, a, b): return a + b

p = LoggingProxy(RealService())
p.greet("Ada")   # __getattr__("greet") fires; greet isn't on LoggingProxy
p.add(2, 3)
```

Key point: `__getattr__` is called **only when normal attribute lookup fails**. Because `LoggingProxy` has no `greet`, Python falls back to `__getattr__("greet")`, which forwards to the real target. If we had defined `greet` on `LoggingProxy`, the hook would *not* fire for `greet`.

### Java — `java.lang.reflect.Proxy` (interfaces only)

```java
import java.lang.reflect.*;

interface Service {
    String greet(String who);
    int add(int a, int b);
}

class RealService implements Service {
    public String greet(String who) { return "Hello, " + who; }
    public int add(int a, int b) { return a + b; }
}

public class Demo {
    public static void main(String[] args) {
        Service real = new RealService();

        Service proxy = (Service) Proxy.newProxyInstance(
            Service.class.getClassLoader(),
            new Class<?>[]{ Service.class },
            (InvocationHandler) (prox, method, methodArgs) -> {
                System.out.println("-> " + method.getName());
                Object result = method.invoke(real, methodArgs); // forward
                System.out.println("<- returned " + result);
                return result;
            });

        proxy.greet("Ada");
        proxy.add(2, 3);
    }
}
```

`Proxy.newProxyInstance` generates a brand-new class at runtime that implements `Service` and routes **every** method to the single `invoke` lambda. Note it requires the *interface* `Service` — you cannot proxy `RealService` directly this way.

### Ruby — `method_missing`

```ruby
class LoggingProxy
  def initialize(target)
    @target = target
  end

  def method_missing(name, *args, &block)
    if @target.respond_to?(name)
      puts "-> #{name}#{args}"
      result = @target.send(name, *args, &block)
      puts "<- #{name} returned #{result.inspect}"
      result
    else
      super  # let Ruby raise NoMethodError normally
    end
  end

  def respond_to_missing?(name, include_private = false)
    @target.respond_to?(name, include_private) || super
  end
end

class RealService
  def greet(who) = "Hello, #{who}"
  def add(a, b) = a + b
end

p = LoggingProxy.new(RealService.new)
p.greet("Ada")
p.add(2, 3)
```

`method_missing` fires for any message `LoggingProxy` can't answer itself. We forward to the target and log around it. The paired `respond_to_missing?` keeps `p.respond_to?(:greet)` honest — always define it alongside `method_missing`.

### The self-invocation trap (Java, conceptual)

```java
class OrderService {
    public void placeOrder()  { /* ... */ charge(); }   // internal call via `this`
    public void charge()      { /* meant to be "logged"/"transactional" */ }
}
```

If a proxy wraps `OrderService` to log/transact every method, calling `proxy.placeOrder()` *is* logged — but the internal `charge()` is a plain `this.charge()` that **never goes back through the proxy**, so it is **not** logged or transacted. Remember this; it's the #1 proxy gotcha and the senior levels return to it.

---

## Coding Patterns

### Pattern 1: Wrap-and-forward (the canonical proxy)

```python
def __getattr__(self, name):
    attr = getattr(self._target, name)     # find it on the real object
    if not callable(attr):
        return attr
    def wrapper(*a, **k):
        # ...before...
        r = attr(*a, **k)                  # forward
        # ...after...
        return r
    return wrapper
```

Find it on the target, optionally wrap, forward. This shape repeats in every language.

### Pattern 2: Use the "default behavior" helper (JS `Reflect`)

In a JS trap, don't reimplement the operation by hand — call the matching `Reflect` method:

```javascript
get(target, prop, receiver) { return Reflect.get(target, prop, receiver); }
set(target, prop, val, receiver) { return Reflect.set(target, prop, val, receiver); }
```

`Reflect` mirrors every trap with the *exact default behavior*, so your proxy stays correct when you only want to augment one operation.

### Pattern 3: Always pair `method_missing` with `respond_to_missing?` (Ruby)

If `method_missing` answers a name, `respond_to?` must agree, or duck-typing checks elsewhere break:

```ruby
def respond_to_missing?(name, include_private = false)
  @target.respond_to?(name, include_private) || super
end
```

### Pattern 4: Guard `__getattr__`/`method_missing` against unknowns

Don't answer *everything* — forward to `super`/raise for names the target genuinely lacks, so a typo still fails loudly instead of returning a silent `nil`.

---

## Best Practices

- **Prefer the "only what's missing" hook** (`__getattr__`, `method_missing`) over the "every access" hook (`__getattribute__`) unless you genuinely need to intercept existing attributes too.
- **Keep the interceptor small and fast.** It runs for *every* call. No heavy work, no surprising side effects beyond the documented one.
- **Make the proxy transparent.** It should behave like the target for normal use; document the one thing it adds.
- **Fail loudly on truly unknown methods.** A proxy that silently swallows typos is a debugging nightmare.
- **Document that it's a proxy.** A reader who sees `userService` should be able to discover that it's wrapped with transactions/logging.
- **Don't rely on identity through a proxy.** `proxy == target` is usually false; `instanceof`/`isinstance` may not hold for the concrete class.
- **Be aware of self-invocation.** If internal calls must also be intercepted, you need a different design (we cover the fixes in higher levels).

---

## Edge Cases & Pitfalls

- **Self-invocation bypass.** `this.otherMethod()` inside a proxied object skips the proxy. The augmentation silently doesn't happen for internal calls.
- **`__getattr__` vs `__getattribute__`.** `__getattr__` fires only on *missing* attributes; `__getattribute__` fires on *all* of them and is easy to send into infinite recursion (if its body touches `self.x`, that's another access that re-calls it).
- **Infinite recursion in `__getattr__` too.** If `__getattr__` references `self._target` but `_target` was never set (e.g., set via normal assignment that *also* routed oddly), the lookup for `_target` itself triggers `__getattr__` again. Set it with `object.__setattr__` in `__init__`.
- **Silent typo swallowing.** `method_missing` (or a too-eager `__getattr__`) can "answer" `usr.naem` and return `nil`, hiding a misspelling. Always guard with `respond_to?`/an explicit allowlist.
- **Broken identity and equality.** A proxy is a different object than its target. `is`/`==`/`instanceof`/`isinstance` may give surprising answers. Don't use a proxy as a map key expecting target identity.
- **JDK proxy needs an interface.** `java.lang.reflect.Proxy` can't wrap a concrete class with no interface — you'll need CGLIB/ByteBuddy (covered later).
- **Confusing stack traces.** Errors inside a proxied call show generated frames (`$Proxy12`, `invoke`, lambda frames). They look alien the first time.
- **Forgetting `respond_to_missing?`.** Then `obj.respond_to?(:foo)` says `false` even though `obj.foo` works — duck typing elsewhere breaks.

---

## Apply it

1. Choose one small, known input for **Dynamic Dispatch & Proxies**.
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

- What problem does Dynamic Dispatch & Proxies solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
