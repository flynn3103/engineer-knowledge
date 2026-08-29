# Dynamic Dispatch & Proxies — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Dynamic Dispatch & Proxies** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The generation pipeline: from "intercept" to a real class

A class proxy is a *new type* synthesized at runtime:

```text
ByteBuddy / CGLIB DSL
        │  (describe: subclass T, override methods, delegate to interceptor)
        ▼
   ASM emits a byte[]  (a valid .class image in memory)
        │
        ▼
   ClassLoader.defineClass  (loaded into a classloader, often a child/wrapper)
        │
        ▼
   Objenesis or constructor  → an instance materialized
        │
        ▼
   JIT compiles the hot interceptor path after warm-up
```

Consequences a senior must reason about: **metaspace pressure** (each generated class consumes metaspace; thousands of proxies/mocks can leak if classloaders aren't released), **warm-up cost** (the first calls are interpreted/slow), **classloader visibility** (the generated class must "see" the interfaces/types it references), and **named-module/`--add-opens`** issues on modern JDKs when reflecting into closed packages.

### 2. Reflective invoke vs MethodHandle vs direct override

Three forwarding mechanisms, increasing speed:

- **`Method.invoke`** — fully reflective, slowest, wraps target exceptions in `InvocationTargetException`. Fine for cold paths.
- **`MethodHandle` / `invokedynamic`** — typed handle resolved once, invoked nearly as fast as a direct call; the modern high-performance interception substrate.
- **Overridden method calling `super`** (CGLIB `invokeSuper`, ByteBuddy `@SuperCall`) — essentially a direct virtual call; fastest forward.

Production frameworks moved toward `MethodHandle`/generated dispatch precisely to keep interception off the slow reflective path.

### 3. JS proxy invariants (the spec's correctness contract)

A JS `Proxy` is not a free-for-all. The spec enforces **invariants** so a proxy can't lie in ways that would corrupt the language's guarantees:

- If a property is **non-configurable and non-writable** on the target, the `get` trap **must** return the same value.
- `getOwnPropertyDescriptor` can't report a non-configurable property as configurable.
- `deleteProperty` can't claim to delete a non-configurable property.
- `has` can't hide a non-configurable own property.
- `ownKeys` must include all non-configurable own keys and respect extensibility.

Violating an invariant throws `TypeError`. This is why `Reflect` matters: forwarding to `Reflect` automatically satisfies invariants. A senior building a proxy framework respects these or hits non-obvious throws on frozen/sealed objects.

### 4. The membrane pattern

A single proxy wraps one object. A **membrane** wraps a *graph*: whenever a proxied object returns another object (from a getter, method result, or argument going the other way), that object is *also* wrapped — recursively — so nothing un-proxied leaks across the boundary. Two requirements:

- **Identity preservation:** the same target wrapped twice must yield the same wrapper (cache in a `WeakMap`), or `===`/`is` comparisons inside the membrane break.
- **Shared revocation:** one `revoke()` disables the *entire* membrane at once (capability cutoff).

Membranes are how you sandbox untrusted code, build secure compartments, and implement transparent lazy/transactional boundaries over object graphs.

### 5. The metaobject protocols, compared

| Language | Lookup hook | "Everything" hook | Notes |
|----------|-------------|-------------------|-------|
| Python | `__getattr__` (missing) | `__getattribute__` (all) + **descriptors** | Methods are non-data descriptors; `property` is a data descriptor. |
| Ruby | `method_missing` | (no global one) + `respond_to_missing?` | `define_method` can *materialize* a real method after first miss (caching). |
| JS | `Proxy` `get` trap | `Proxy` `get`/`has`/etc. | Constrained by invariants; `Reflect` for defaults. |

The "synthesis" in *dynamic dispatch & proxies* is exactly the act of answering through these hooks for names that have no statically-written method.

### 6. Identity, equality, hashing, serialization — the collateral damage

Interception breaks the things that assume an object *is* itself:

- **`instanceof`/`isinstance`/`is_a?`** — a class proxy passes `instanceof Target` (it's a subclass) but a JDK interface proxy does **not** pass `instanceof RealClass`.
- **`equals`/`hashCode`** — Hibernate proxies override these to forward to the underlying entity; naive proxies break `Set`/`Map` membership.
- **Identity (`==`/`is`)** — a proxy is a different object; identity maps and `==`-by-reference checks misbehave. Membranes need the wrapper cache to restore *relative* identity.
- **Serialization** — serializing a proxy serializes the generated class, which the deserializer may not have. Frameworks register custom serializers or unwrap to the target first.
- **`getClass()`/`toString()`** — return the generated type name unless overridden, leaking implementation detail into logs.

---

## Code Examples

### ByteBuddy — generate a logging subclass at runtime

```java
import net.bytebuddy.ByteBuddy;
import net.bytebuddy.implementation.MethodDelegation;
import net.bytebuddy.implementation.bind.annotation.*;
import static net.bytebuddy.matcher.ElementMatchers.*;

public class Logged {
    public static class Interceptor {
        @RuntimeType
        public static Object intercept(@Origin String method,
                                       @SuperCall java.util.concurrent.Callable<?> zuper)
                throws Exception {
            System.out.println("-> " + method);
            try { return zuper.call(); }            // direct super call, not reflection
            finally { System.out.println("<- " + method); }
        }
    }

    static <T> Class<? extends T> proxyType(Class<T> type) {
        return new ByteBuddy()
            .subclass(type)
            .method(isPublic().and(not(isFinal())))   // only overridable methods
            .intercept(MethodDelegation.to(Interceptor.class))
            .make()
            .load(type.getClassLoader())
            .getLoaded();
    }
}
```

`@SuperCall Callable` captures a direct invocation of the original method — far faster than `Method.invoke`, and it never recurses into the proxy. `not(isFinal())` makes the seam explicit: final methods are not woven.

### Java — forwarding with a MethodHandle (faster than reflection)

```java
import java.lang.invoke.*;
import java.lang.reflect.*;

class HandleHandler implements InvocationHandler {
    private final Object target;
    private final java.util.Map<Method, MethodHandle> cache = new java.util.HashMap<>();
    HandleHandler(Object target) { this.target = target; }

    public Object invoke(Object proxy, Method m, Object[] args) throws Throwable {
        MethodHandle h = cache.computeIfAbsent(m, mm -> {
            try { return MethodHandles.lookup().unreflect(mm).bindTo(target); }
            catch (IllegalAccessException e) { throw new RuntimeException(e); }
        });
        return args == null ? h.invoke() : h.invokeWithArguments(args);
    }
}
```

Resolving the `MethodHandle` once and reusing it avoids the per-call reflective overhead and the `InvocationTargetException` wrapping that `Method.invoke` imposes.

### JavaScript — an identity-preserving membrane with shared revocation

```javascript
function makeMembrane(rootTarget) {
  const wrappers = new WeakMap();   // target -> wrapper, preserves identity
  let revoked = false;

  function wrap(target) {
    if (target === null || (typeof target !== "object" && typeof target !== "function")) {
      return target;                       // primitives cross unchanged
    }
    if (wrappers.has(target)) return wrappers.get(target);

    const handler = {
      get(t, prop, receiver) {
        if (revoked) throw new Error("membrane revoked");
        return wrap(Reflect.get(t, prop, receiver));   // wrap values crossing OUT
      },
      apply(t, thisArg, args) {
        if (revoked) throw new Error("membrane revoked");
        // unwrap args crossing IN, wrap the result crossing OUT
        return wrap(Reflect.apply(t, thisArg, args));
      },
    };
    const proxy = new Proxy(target, handler);
    wrappers.set(target, proxy);
    return proxy;
  }

  return { proxy: wrap(rootTarget), revoke() { revoked = true; } };
}

const realApi = { config: { name: "svc" }, getConfig() { return this.config; } };
const { proxy, revoke } = makeMembrane(realApi);
console.log(proxy.getConfig() === proxy.config); // true — identity preserved inside membrane
revoke();
// proxy.config now throws everywhere reachable through the membrane
```

This captures the three membrane essentials: transitive wrapping (the returned `config` is itself a proxy), identity preservation (the `WeakMap` makes the two views compare equal), and one-switch revocation.

### Python — a descriptor-based lazy proxy (synthesis on first access)

```python
class Lazy:
    """A descriptor that materializes the real value on first access, then caches it."""
    def __init__(self, factory):
        self.factory = factory
        self.name = None
    def __set_name__(self, owner, name):
        self.name = name
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = self.factory()                 # the expensive call happens HERE, once
        obj.__dict__[self.name] = value        # shadow the descriptor: future reads are direct
        return value

class Report:
    rows = Lazy(lambda: expensive_query())     # not run until report.rows is touched
```

This is the metaobject-protocol version of a virtual proxy: the descriptor intercepts the *first* read, synthesizes the value, then writes it into the instance dict so the descriptor is bypassed afterward — zero per-access overhead after warm-up.

### Ruby — `method_missing` that promotes to a real method (self-healing dispatch)

```ruby
class Lazy
  def initialize(loader) = @loader = loader

  def method_missing(name, *args, &blk)
    if @loader.respond_to?(name)
      # define a real method so the NEXT call skips method_missing entirely
      self.class.define_method(name) do |*a, &b|
        @loader.public_send(name, *a, &b)
      end
      @loader.public_send(name, *args, &blk)
    else
      super
    end
  end

  def respond_to_missing?(name, include_private = false)
    @loader.respond_to?(name, include_private) || super
  end
end
```

The first call to an unknown method falls into `method_missing`, which *materializes* a real method via `define_method`; every subsequent call dispatches directly. This is the standard trick to avoid paying the `method_missing` cost forever — the same idea as Python's descriptor caching above.

---

## Coding Patterns

### Pattern 1: Cache generated classes and handles

Generate one proxy class per (target type, advice) pair and reuse it; cache `MethodHandle`s per `Method`. Never regenerate per instance/call.

### Pattern 2: Forward to `Reflect` to satisfy invariants (JS)

Any trap that isn't a full override must end in `Reflect.<trap>(...)`. This is the only reliable way to honor non-configurable/frozen-property invariants.

### Pattern 3: Preserve identity in membranes with a `WeakMap`

`target → wrapper` cache so the same target always yields the same proxy. Without it, `===`/`is` inside the membrane silently breaks.

### Pattern 4: Promote dynamic dispatch to real methods after first use

Ruby `define_method` / Python descriptor caching: pay the synthesis cost once, then dispatch directly. Avoids permanent `method_missing`/`__getattribute__` overhead.

### Pattern 5: Override identity/equality deliberately

If callers compare or hash proxied objects, forward `equals`/`hashCode`/`==`/`__eq__` to the target (as Hibernate does) — or document loudly that you don't.

---

## Best Practices

- **Bound proxy generation.** Reuse generated classes; watch metaspace; release classloaders that own per-request proxies.
- **Prefer `MethodHandle`/`@SuperCall` over `Method.invoke`** on hot paths; reserve reflection for cold/setup code.
- **Always forward to `Reflect` in partial JS traps** to keep invariants intact.
- **Design membranes around identity and revocation up front** — retrofitting a `WeakMap` and revocation into a leaky boundary is painful.
- **Decide and document the identity story.** What does `==`/`instanceof`/serialization do through your proxy? Make it explicit.
- **Unwrap before serialization.** Serialize the target, not the generated class.
- **Mind named modules / `--add-opens`.** Reflective/bytecode access into closed packages fails loudly on modern JDKs.
- **Benchmark the megamorphic case.** A proxy that sees many concrete types at one call site can defeat the JIT's inline cache; measure, don't assume.

---

## Edge Cases & Pitfalls

- **Metaspace leak from runaway generation** — per-instance or per-request proxy/mocks pinning classloaders; OOM in metaspace.
- **JS invariant violations** — a `get` trap returning a different value for a non-configurable, non-writable property throws `TypeError`; sealing/freezing a target then proxying surprises people.
- **Membrane identity loss** — forgetting the wrapper cache → the same target appears as two different objects; `===` and `Set` membership break.
- **Private fields don't trap (JS)** — `#field` access uses an internal slot the `get` trap can't see; membranes can't fully wrap classes using private fields.
- **`MethodHandle` access on closed packages** — `IllegalAccessException`/`InaccessibleObjectException` under the module system without `--add-opens`.
- **Deoptimization on megamorphic proxied sites** — one generic call site handling many types loses inlining; throughput drops.
- **Serialization of proxies** — the deserializer lacks the generated class; serialize the unwrapped target or register a resolver.
- **`equals`/`hashCode` asymmetry** — `proxy.equals(target)` true but `target.equals(proxy)` false unless both sides cooperate; breaks `Set`/`Map`.
- **Descriptor/`define_method` shadowing surprises** — promoting to a real method changes future dispatch; if the target is later swapped, the cached method is stale.
- **Constructor side effects skipped** — Objenesis-created proxies never ran the constructor; fields the real logic relies on may be unset.

---

## Apply it

1. State the system invariant that **Dynamic Dispatch & Proxies** must protect.
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

- Which invariant must remain true when Dynamic Dispatch & Proxies fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
