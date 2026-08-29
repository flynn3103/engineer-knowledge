# Reflection — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Reflection** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Go: `Type`, `Value`, and `Kind` are three different things

People conflate these and get confused. Keep them separate:

- **`reflect.Type`** answers *static* questions: name, kind, fields, methods, tags. It doesn't hold a value.
- **`reflect.Value`** wraps an *actual* value: you can read it (`.Int()`, `.String()`, `.Interface()`) and, if the rules allow, set it.
- **`Kind`** is the *category*. Two different named types (`type Celsius float64`, `type Meters float64`) have *different `Type`s* but the *same `Kind`* (`Float64`). When you write generic reflective code, you almost always switch on `Kind`, not `Type`.

```go
type Celsius float64
v := reflect.ValueOf(Celsius(36.6))
fmt.Println(v.Type())  // main.Celsius   (the named type)
fmt.Println(v.Kind())  // float64        (the category)
```

The "Laws of Reflection" (Go's own framing) are worth memorizing:

1. Reflection goes from interface value → reflection object (`TypeOf`, `ValueOf`).
2. Reflection goes from reflection object → interface value (`.Interface()`).
3. **To modify a reflection object, the value must be settable** — addressable and exported.

### 2. Go: addressability and settability — the rule that panics everyone

This is *the* Go reflection gotcha. Why does this panic?

```go
u := User{Name: "Ada"}
reflect.ValueOf(u).FieldByName("Name").SetString("Grace") // PANIC
```

Because `reflect.ValueOf(u)` makes a **copy** of `u`. The copy lives somewhere temporary with no address you can take — it is *not addressable*. Setting it would be writing into a value that's about to vanish, so Go forbids it. The fix is to reflect over a **pointer** and dereference with `Elem()`:

```go
u := User{Name: "Ada"}
v := reflect.ValueOf(&u).Elem()         // now addressable
v.FieldByName("Name").SetString("Grace") // works
fmt.Println(u.Name)                       // "Grace"
```

Two conditions for `CanSet()` to be true:

1. **Addressable** — you reflected through a pointer and called `.Elem()`.
2. **Exported** — the field name is capitalized. Unexported fields are *never* settable via reflection (and only readable in limited ways). This enforces Go's encapsulation even under reflection.

### 3. Java: `Class` is the root; everything hangs off it

From a `Class` you reach the four member kinds:

```java
Class<?> c = obj.getClass();      // or Foo.class, or Class.forName("...")
c.getDeclaredFields();            // Field[]
c.getDeclaredMethods();           // Method[]
c.getDeclaredConstructors();      // Constructor<?>[]
c.getAnnotations();               // Annotation[]
```

Know the `getX` vs `getDeclaredX` distinction cold:

- **`getFields()` / `getMethods()`** → only `public`, but includes inherited members.
- **`getDeclaredFields()` / `getDeclaredMethods()`** → every visibility, but *only this class* (not inherited).

To touch a non-public member you call `setAccessible(true)` — which the module system may reject (see `professional.md`). To create instances reflectively, prefer `Constructor.newInstance()` over the deprecated `Class.newInstance()`.

### 4. Python: it's all dictionaries, plus `inspect` for the polished view

Python reflection is two layers:

- **Raw layer:** `obj.__dict__` (instance attributes), `type(obj).__dict__` (class attributes/methods), `getattr/setattr/hasattr/delattr`, `dir()`, `vars()`. Everything is an object with a `__dict__`, so reflection is just dictionary access dressed up.
- **Polished layer — `inspect`:** higher-level helpers that hide the rough edges:
  - `inspect.signature(fn)` — parameters, defaults, annotations.
  - `inspect.getmembers(obj, predicate)` — filtered member listing.
  - `inspect.getsource(fn)` — the actual source text.
  - `inspect.isfunction`, `inspect.ismethod`, `inspect.isclass` — type predicates.
  - `type(obj).__mro__` — the resolution order across base classes.

Where Go and Java make you *opt in* to a reflection API, Python makes reflection the path of least resistance — which is why Python frameworks lean on it heavily.

### 5. C#: `Type` plus `MemberInfo` hierarchy

`obj.GetType()` returns a `Type`; from it you get `PropertyInfo`, `FieldInfo`, `MethodInfo`, `ConstructorInfo` (all `MemberInfo` subclasses). Binding flags control visibility:

```csharp
var flags = BindingFlags.NonPublic | BindingFlags.Instance;
FieldInfo f = t.GetField("_secret", flags);
f.SetValue(obj, 42);
```

`Activator.CreateInstance(t)` constructs instances reflectively.

### 6. The performance story (the whole reason `senior.md` exists)

A reflective access does work a direct access never does:

- **Lookup** — find the `Field`/`Method` by name (string hashing, table walks) unless cached.
- **Access checks** — verify visibility on each `invoke`/`get` (mitigated by `setAccessible`).
- **Boxing** — arguments and return values get wrapped in `Object`/`interface{}`, causing allocations.
- **No inlining** — the JIT/compiler can't see through a reflective call, so it can't inline, devirtualize, or specialize it.

Net effect: reflective field reads and method calls commonly run **10–100× slower** than direct ones, and allocate. The two universal mitigations are **caching the handle** and, in Java, upgrading to **`MethodHandle`** (covered in `senior.md`).

---

## Code Examples

### Example 1: A reflective struct copier in Go (settability in action)

```go
// CopyFields copies same-named exported fields from src to dst.
// dst must be a pointer to a struct.
func CopyFields(dst, src interface{}) {
	dv := reflect.ValueOf(dst).Elem() // addressable struct
	sv := reflect.ValueOf(src)
	if sv.Kind() == reflect.Ptr {
		sv = sv.Elem()
	}
	dt := dv.Type()
	for i := 0; i < dt.NumField(); i++ {
		name := dt.Field(i).Name
		sf := sv.FieldByName(name)
		df := dv.Field(i)
		if sf.IsValid() && df.CanSet() && sf.Type() == df.Type() {
			df.Set(sf) // only fires when addressable + exported + types match
		}
	}
}
```

Every guard here maps to a rule: `IsValid` (the field exists on src), `CanSet` (addressable + exported), and the type-equality check (no silent coercion).

### Example 2: Reading struct tags the way a serializer does (Go)

```go
func fieldKey(f reflect.StructField) string {
	tag := f.Tag.Get("json")
	if tag == "" || tag == "-" {
		return f.Name // default to field name
	}
	if comma := strings.IndexByte(tag, ','); comma >= 0 {
		tag = tag[:comma] // strip ",omitempty" etc.
	}
	return tag
}
```

This is essentially the first thing `encoding/json` does per field. Now the "magic" is fully demystified: it's tag parsing over reflected fields.

### Example 3: Java — direct vs. reflective, and the cache that saves you

```java
// SLOW: looks up the method on every call
public Object slowInvoke(Object target, String name) throws Exception {
    Method m = target.getClass().getMethod(name); // lookup each time
    return m.invoke(target);
}

// FAST(er): resolve once, reuse, and disable access checks
private final Map<String, Method> cache = new ConcurrentHashMap<>();

public Object cachedInvoke(Object target, String name) throws Exception {
    Method m = cache.computeIfAbsent(name, n -> {
        try {
            Method mm = target.getClass().getMethod(n);
            mm.setAccessible(true);   // skip access check on each invoke
            return mm;
        } catch (NoSuchMethodException e) {
            throw new RuntimeException(e);
        }
    });
    return m.invoke(target);
}
```

The lookup is the expensive part; caching the `Method` removes it. `setAccessible(true)` additionally skips the per-invoke access check. You're still paying for boxing and the lack of inlining — `senior.md` shows how `MethodHandle` reduces even that.

### Example 4: Python `inspect` for a real introspection task

```python
import inspect

def describe(obj):
    print("type:", type(obj).__name__)
    print("mro :", [c.__name__ for c in type(obj).__mro__])
    for name, member in inspect.getmembers(obj, inspect.ismethod):
        sig = inspect.signature(member)
        print(f"  {name}{sig}")

class Repo:
    def get(self, id: int) -> dict: ...
    def save(self, item: dict, *, upsert: bool = False) -> None: ...

describe(Repo())
# type: Repo
# mro : ['Repo', 'object']
#   get(id: int) -> dict
#   save(item: dict, *, upsert: bool = False) -> None
```

`inspect.signature` parsing parameters, defaults, and annotations is what powers CLI generators, RPC frameworks, and pytest fixtures.

### Example 5: A tiny dependency-injection move (Java)

```java
// Construct an object and fill a field annotated @Inject, by reflection.
Constructor<?> ctor = type.getDeclaredConstructor();
ctor.setAccessible(true);
Object instance = ctor.newInstance();

for (Field f : type.getDeclaredFields()) {
    if (f.isAnnotationPresent(Inject.class)) {
        f.setAccessible(true);
        f.set(instance, container.resolve(f.getType()));
    }
}
```

This 8-line sketch is the *entire idea* behind Spring's field injection: reflect, find annotated members, fill them.

---

## Coding Patterns

**Pattern 1: Resolve once, reuse forever.** Cache the `Field`/`Method`/`StructField` keyed by `(Type, name)` in a `ConcurrentHashMap` / `sync.Map`. Reflection is fine on setup, deadly per request.

**Pattern 2: Reflect through a pointer in Go.** If you intend to set anything, start from `reflect.ValueOf(&x).Elem()`. Make it a habit so you never hit the addressability panic.

**Pattern 3: Switch on `Kind`, not `Type`.** Generic reflective walkers branch on `reflect.Struct`/`Slice`/`Map`/`Ptr`. Handle `Ptr` by `Elem()`-ing and recursing.

**Pattern 4: Pre-flight every name.** Before `invoke`/`Set`, verify the member exists and types match; fail with a message naming the type and member.

**Pattern 5: `setAccessible(true)` once at cache time, not per call.** It both unlocks access and removes the per-invoke check — but do it during resolution, not in the hot path.

---

## Best Practices

- **Build a type-info cache.** Reflect a type once into a small struct (`[]fieldInfo{name, index, tag, kind}`) and iterate *that* on every request. This single move recovers most of the lost performance.
- **Keep the reflective core tiny and tested.** Concentrate `Set`/`invoke` in one module; everything else calls into it.
- **Prefer `getDeclaredX` + explicit visibility handling** over guessing which `getX` returns what.
- **In Go, treat unexported fields as off-limits.** You can't set them and shouldn't try; redesign instead.
- **Measure before and after caching.** A quick benchmark proves the win and guards against regressions.
- **Surface clear errors.** "no method `Save` on `*User`" beats a raw `NoSuchMethodException` three layers deep.

---

## Edge Cases & Pitfalls

- **Go `Set` panic on a copy.** Forgetting the pointer + `Elem()`. The #1 mistake.
- **Go unexported fields.** Readable in limited ways, never settable via reflection; `CanSet()` returns false.
- **Java `getMethods` vs `getDeclaredMethods`.** Looking for a `private` or inherited member in the wrong list returns nothing or the wrong thing.
- **`setAccessible(true)` may throw.** Under the module system it can fail with `InaccessibleObjectException` (see `professional.md`).
- **Boxing surprises.** Reflective numeric `set`/`get` boxes primitives; tight loops allocate heavily.
- **Stale cached handles.** If types are reloaded (hot reload, classloaders), a cached `Method` can dangle. Key caches by `Class`, and clear on reload.
- **Python `dir()` vs `__dict__`.** `__dict__` shows only instance attributes; `dir()` includes class/inherited members and dunder methods. Pick the right one for the question.
- **MRO surprises in Python.** `getattr` follows the MRO, so a subclass attribute can shadow a base one in ways that surprise reflective walkers.
- **Reflecting interfaces vs. concrete types (Go).** `reflect.TypeOf` on an interface value gives the *dynamic* type; a nil interface gives a nil `Type` — guard for it.

---

## Performance Notes

- **The cost is dominated by lookup + checks + boxing + no-inlining.** Caching removes lookup; `setAccessible` removes checks; `MethodHandle` (Java) reduces the rest.
- **Rule of thumb:** uncached reflective method call ≈ 10–100× a direct call; cached ≈ a few× to ~10×; `MethodHandle` (warmed up) can approach direct-call speed.
- **Allocations matter as much as cycles.** Boxed args/returns and reflective `[]Object` arrays churn the GC; in hot loops this often dominates.
- **Reflection at *startup* vs. *steady state*.** Many frameworks reflect heavily at boot (scanning classes, wiring DI). That doesn't hurt throughput but does hurt **startup latency** — a real problem for serverless/CLI (more in `professional.md`).
- **Benchmark honestly.** Warm up the JIT, run enough iterations, and compare against a direct-call baseline — not against an unrealistic best case.

---

## Apply it

1. Find a real component where **Reflection** affects an interface or dependency.
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

- Which boundary is most affected by Reflection?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
