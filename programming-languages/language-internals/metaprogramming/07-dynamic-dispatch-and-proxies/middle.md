# Dynamic Dispatch & Proxies — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Dynamic Dispatch & Proxies** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Interface proxy vs class proxy — the central fork

```text
JDK dynamic proxy (interface)        CGLIB / ByteBuddy (class)
──────────────────────────────       ──────────────────────────────
generates: class $Proxy0             generates: class Foo$$EnhancerBy...
implements: your interface(s)        extends:    Foo  (subclass!)
intercepts: interface methods        intercepts: overridable methods
can't proxy a class w/o interface    can't override final/private/static
route: InvocationHandler.invoke      route: MethodInterceptor.intercept
```

Spring decides automatically: if your bean implements an interface, it uses a JDK proxy by default; otherwise it uses CGLIB. (`proxyTargetClass=true` forces CGLIB even for interface beans.) Knowing which one you got explains a lot of "but it worked locally" bugs.

### 2. What you can and cannot intercept (the "seam")

A class proxy works by **overriding**. Therefore it cannot intercept:

- **`final` methods** — can't be overridden, so the interceptor never sees them.
- **`private` methods** — not part of the override surface; also invoked via `this`, so self-invocation rules apply.
- **`static` methods** — not virtual; no instance to wrap.
- **Constructors / field access** — a method proxy intercepts *methods*, not field reads.

An interface proxy is even narrower: only methods declared on the proxied interface are visible. Anything you call through the concrete type isn't proxied at all.

### 3. Self-invocation, mechanically

A proxy `P` wraps target `T`. External code holds `P`. `P.placeOrder()` runs advice, then forwards to `T.placeOrder()`. Inside `T.placeOrder()`, the call `charge()` is really `this.charge()` where `this == T` (not `P`). So it goes directly to `T.charge()` — the proxy `P` is never consulted, and the advice on `charge` (a second `@Transactional`, say) never runs.

Fixes you should know:
- Inject the bean into itself and call through the injected (proxied) reference.
- Use `AopContext.currentProxy()` (Spring) to get the proxy and call through it (requires `exposeProxy=true`).
- Split the two methods into **two beans** so the call crosses a proxy boundary.
- Use compile/load-time weaving (AspectJ) instead of proxies — weaving rewrites the call site itself, so even self-calls are advised.

### 4. The Python attribute protocol, ordered

When you write `obj.x`, Python runs roughly:

1. `type(obj).__getattribute__(obj, "x")` — the *always-called* entry point.
2. That default implementation searches data descriptors, the instance `__dict__`, then non-data descriptors / class attributes.
3. **Only if all of that raises `AttributeError`** does Python call `obj.__getattr__("x")` (if defined).

So `__getattr__` is the "fallback for missing names," and `__getattribute__` is the "intercept absolutely everything." `__setattr__` intercepts every assignment; `__call__` makes the instance itself callable. To build a proxy that forwards *everything* (even existing names) you override `__getattribute__` — and must be careful to use `object.__getattribute__(self, ...)` internally to avoid infinite recursion.

### 5. JS traps + `Reflect` as the forwarding default

A JS `Proxy` handler can define many traps; the common ones:

| Trap | Fires on | Default via |
|------|----------|-------------|
| `get` | `obj.x`, `obj.method` | `Reflect.get` |
| `set` | `obj.x = v` | `Reflect.set` |
| `has` | `"x" in obj` | `Reflect.has` |
| `deleteProperty` | `delete obj.x` | `Reflect.deleteProperty` |
| `apply` | `fn(...args)` (function target) | `Reflect.apply` |
| `construct` | `new Ctor(...args)` | `Reflect.construct` |
| `ownKeys` | `Object.keys`, spread | `Reflect.ownKeys` |

The discipline: in every trap you don't fully override, **return `Reflect.<trap>(...)`** so the default semantics are preserved. `Reflect` exists precisely so you don't reimplement object internals by hand (and so `set` correctly returns a boolean, `receiver` is threaded through, etc.).

### 6. The frameworks, decoded

- **Spring AOP** wraps beans in a proxy; `@Transactional`/`@Cacheable`/`@Async` are advice applied around the proxied methods. Self-invocation and final/private methods are the classic non-firing causes.
- **Mockito** generates a subclass (ByteBuddy) whose every method is intercepted to record the call and return a stubbed/`null`/default value. `when(mock.foo()).thenReturn(x)` programs the interceptor.
- **Hibernate lazy loading** returns a proxy (CGLIB/ByteBuddy) for an associated entity. The proxy holds only the id; the first method call triggers a SQL `SELECT`. If the session is closed by then, you get `LazyInitializationException`.

---

## Code Examples

### Java — JDK proxy, timing every interface method

```java
import java.lang.reflect.*;

interface Repo { String find(int id); void save(String s); }

class RealRepo implements Repo {
    public String find(int id) { return "row-" + id; }
    public void save(String s) { /* ... */ }
}

class TimingHandler implements InvocationHandler {
    private final Object target;
    TimingHandler(Object target) { this.target = target; }
    public Object invoke(Object proxy, Method m, Object[] args) throws Throwable {
        long t0 = System.nanoTime();
        try {
            return m.invoke(target, args);                  // forward
        } finally {
            System.out.printf("%s took %d ns%n", m.getName(), System.nanoTime() - t0);
        }
    }
}

@SuppressWarnings("unchecked")
static <T> T timed(Class<T> iface, T target) {
    return (T) Proxy.newProxyInstance(
        iface.getClassLoader(), new Class<?>[]{iface}, new TimingHandler(target));
}
```

`m.invoke(target, args)` is the reflective forward. Note `InvocationTargetException`: a checked exception thrown by the *target* arrives wrapped — unwrap `getCause()` to rethrow the real exception.

### Java — CGLIB-style class proxy (no interface needed)

```java
import net.sf.cglib.proxy.*;

class Service {           // concrete class, no interface
    public String hello(String n) { return "hi " + n; }
    public final String fixed() { return "cannot be proxied"; } // final!
}

Service proxy = (Service) Enhancer.create(Service.class, (MethodInterceptor)
    (obj, method, args, methodProxy) -> {
        System.out.println("-> " + method.getName());
        Object r = methodProxy.invokeSuper(obj, args);   // calls real super method
        System.out.println("<- " + method.getName());
        return r;
    });

proxy.hello("Ada");   // intercepted
proxy.fixed();        // NOT intercepted — final method, can't be overridden
```

`methodProxy.invokeSuper(obj, args)` is the CGLIB way to invoke the original method (the overridden `super`). Calling `method.invoke(obj, args)` here would recurse into the proxy forever.

### Python — full-transparency proxy via `__getattribute__`

```python
class TracingProxy:
    def __init__(self, target):
        object.__setattr__(self, "_target", target)

    def __getattribute__(self, name):
        # Use object.__getattribute__ for OUR OWN internals to avoid recursion.
        if name in ("_target", "__class__", "__init__"):
            return object.__getattribute__(self, name)
        target = object.__getattribute__(self, "_target")
        attr = getattr(target, name)         # forwards EVERYTHING, even existing names
        if callable(attr):
            def wrapper(*a, **k):
                print(f"-> {name}")
                return attr(*a, **k)
            return wrapper
        return attr

class Service:
    version = "1.0"
    def hello(self, n): return f"hi {n}"

p = TracingProxy(Service())
print(p.version)   # intercepted (a real class attribute) — __getattr__ would NOT see this
p.hello("Ada")     # intercepted
```

Contrast with `__getattr__`, which would *not* intercept `version` (it exists). This is the key middle-level distinction. The `object.__getattribute__` calls on our own internals are what break the recursion.

### Python — callable objects and `__call__`

```python
class RetryProxy:
    def __init__(self, fn, attempts=3):
        self.fn, self.attempts = fn, attempts
    def __call__(self, *a, **k):           # instance behaves like a function
        last = None
        for _ in range(self.attempts):
            try:
                return self.fn(*a, **k)
            except Exception as e:
                last = e
        raise last

flaky = RetryProxy(some_flaky_function)
flaky(42)   # runs RetryProxy.__call__
```

### JavaScript — validation + default forwarding with `Reflect`

```javascript
function validated(target, rules) {
  return new Proxy(target, {
    set(obj, prop, value, receiver) {
      const rule = rules[prop];
      if (rule && !rule(value)) {
        throw new TypeError(`invalid value for ${String(prop)}: ${value}`);
      }
      return Reflect.set(obj, prop, value, receiver);   // default behavior
    },
  });
}

const user = validated({}, { age: (v) => Number.isInteger(v) && v >= 0 });
user.age = 30;     // ok
user.age = -1;     // throws
```

### JavaScript — revocable proxy (capability you can switch off)

```javascript
const { proxy, revoke } = Proxy.revocable({ secret: 42 }, {});
console.log(proxy.secret);  // 42
revoke();
console.log(proxy.secret);  // TypeError: Cannot perform 'get' on a revoked proxy
```

Revocable proxies are how you hand out a temporary capability and later guarantee no further access (the basis of the membrane pattern, covered at senior level).

### Ruby — dynamic finders (the ActiveRecord trick, in miniature)

```ruby
class Collection
  def initialize(records) = @records = records

  def method_missing(name, *args)
    if name.to_s =~ /^find_by_(\w+)$/
      field = $1.to_sym
      @records.find { |r| r[field] == args.first }
    else
      super
    end
  end

  def respond_to_missing?(name, include_private = false)
    name.to_s.start_with?("find_by_") || super
  end
end

people = Collection.new([{ name: "Ada", age: 36 }, { name: "Linus", age: 54 }])
people.find_by_name("Ada")   # => {name: "Ada", age: 36}, method synthesized from the name
people.find_by_age(54)       # => {name: "Linus", age: 54}
```

---

## Coding Patterns

### Pattern 1: Forward through the right "super" call

In a class proxy, forward to the *original* method, not back through the proxy:
- CGLIB: `methodProxy.invokeSuper(obj, args)`
- ByteBuddy with `@SuperCall`: invoke the captured `Callable`
- Never `method.invoke(obj, args)` on the proxy itself — infinite recursion.

### Pattern 2: Always restore default with `Reflect` (JS)

Override only the trap you need; delegate the rest to `Reflect.<trap>`. This keeps `receiver`, return-value contracts, and prototype chains correct.

### Pattern 3: Guard internal access in `__getattribute__`

Route your own bookkeeping attributes through `object.__getattribute__`/`object.__setattr__` so the proxy's machinery doesn't intercept itself into recursion.

### Pattern 4: Pair the missing-hooks

`method_missing` ↔ `respond_to_missing?` (Ruby). In Python, if you synthesize attributes via `__getattr__`, consider implementing `__dir__` so introspection/autocomplete still works.

### Pattern 5: Break self-invocation deliberately

When advice *must* apply to internal calls, cross a proxy boundary: separate beans, self-injection, `AopContext.currentProxy()`, or switch to AspectJ weaving.

---

## Best Practices

- **Know which proxy you got.** Log `bean.getClass()` once; `$Proxy` = JDK, `$$Enhancer`/`$$ByteBuddy` = class proxy.
- **Don't mark methods you want advised as `final`/`private`.** They silently escape class proxies.
- **Keep advice idempotent and cheap.** It runs on every call and is shared across many methods.
- **Unwrap `InvocationTargetException`.** Rethrow `getCause()` so callers see the real exception, not the reflection wrapper.
- **Prefer missing-only hooks** unless full transparency is required.
- **Use `Reflect` in JS traps** for any operation you don't fully replace.
- **Watch lazy-proxy lifetimes.** Access lazy associations inside the transaction/session, or fetch eagerly/with a DTO, to avoid `LazyInitializationException`.
- **Document the magic.** A reader should be able to find that a bean/object is proxied and what the advice does.

---

## Edge Cases & Pitfalls

- **`@Transactional` on a `private`/`final` method, or self-invoked** — advice doesn't run; no error, just no transaction.
- **JDK proxy and `getClass()`/`instanceof`** — the proxy is `$Proxy0 implements Repo`, not `RealRepo`. Code that downcasts to the concrete type breaks.
- **CGLIB final-method blindness** — overridable methods are advised; `final` ones silently aren't.
- **`__getattr__` won't see existing attributes** — if you expected to intercept a real field, you need `__getattribute__` (and its recursion discipline).
- **`__getattribute__` infinite recursion** — any `self.foo` inside it re-enters; always use `object.__getattribute__`.
- **JS `set` trap must return `true`** — a falsy return throws in strict mode (`'set' on proxy: trap returned falsish`). `Reflect.set` returns the right boolean.
- **`this`/`receiver` identity** — inside a method reached through a proxy, `this` may be the target, not the proxy (key to the self-invocation trap).
- **Mockito can't mock `final` by default** — needs the inline mock maker (ByteBuddy agent) to mock final classes/methods/statics.
- **Hibernate `LazyInitializationException`** — touching a lazy proxy after the session closes throws; a notorious detached-entity bug.
- **Swallowed typos** — an over-eager `method_missing`/`__getattr__` answers misspelled names; guard with `respond_to?`/allowlists.

---

## Apply it

1. Find a real component where **Dynamic Dispatch & Proxies** affects an interface or dependency.
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

- Which boundary is most affected by Dynamic Dispatch & Proxies?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
