# Metaclasses — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Metaclasses** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Writing a Metaclass = Subclassing `type`

```python
class Meta(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        print(f"Building class {name!r}")
        cls = super().__new__(mcs, name, bases, namespace)
        return cls

class Thing(metaclass=Meta):
    pass
# prints: Building class 'Thing'  -- at definition time, no instance made
```

`Meta.__new__` receives the *same three arguments* the `class` statement always assembles: the name, the bases tuple, and the namespace dict. You can inspect them, modify them, validate them, and then call `super().__new__` to actually build the class.

### 2. The Full Class-Creation Lifecycle

When `class Thing(Base, metaclass=Meta, **kwargs):` runs, Python performs these steps in order:

```text
1. Determine the metaclass (explicit metaclass=, or inherited from a base).
2. metaclass.__prepare__(name, bases, **kwargs)  -> returns the namespace mapping
3. Execute the class body, populating that namespace (defs, assignments).
4. metaclass.__new__(metaclass, name, bases, namespace, **kwargs) -> the class object
5. For each attribute that has __set_name__, call attr.__set_name__(cls, attrname).
6. metaclass.__init__(cls, name, bases, namespace, **kwargs)
7. __init_subclass__ of the parent is invoked (with the new subclass).
   (Steps 5 and 7 are part of type.__new__/__init_subclass__ machinery.)
8. Bind the resulting class object to the name `Thing`.
```

The two clocks again: steps 2–8 are **class-creation time** (once, at import). Later, `Thing()` is **instance-creation time** and goes through `Meta.__call__` (see Core Concept 5).

### 3. `__new__` vs `__init__` on a Metaclass

They mirror the ordinary-class versions, one level up:

```python
class Meta(type):
    def __new__(mcs, name, bases, namespace, **kw):
        # Use __new__ when you must change the namespace/bases
        # BEFORE the class exists (e.g. inject or rename members).
        namespace.setdefault("created_by", "Meta")
        return super().__new__(mcs, name, bases, namespace)

    def __init__(cls, name, bases, namespace, **kw):
        # Use __init__ when the class already exists and you just
        # want to inspect/register/validate it.
        super().__init__(name, bases, namespace)
        print(f"{name} now exists with attrs: {list(namespace)}")
```

Rule: **`__new__` to *shape* the class (rare); `__init__` to *react to* the finished class (common).** If you only need to read the class and register/validate it, `__init__` is enough and simpler.

### 4. `__prepare__` — Controlling the Namespace

Normally the class body fills an ordinary dict. `__prepare__` lets you supply a *different* mapping, so you can observe definition order or special-case assignments. The classic example is preserving order before dicts were ordered (pre-3.7), or building enums:

```python
class OrderedMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases, **kw):
        return collections.OrderedDict()   # or a custom recording dict

    def __new__(mcs, name, bases, namespace, **kw):
        cls = super().__new__(mcs, name, bases, dict(namespace))
        cls._field_order = [k for k in namespace if not k.startswith("__")]
        return cls
```

Since Python 3.7 plain dicts preserve insertion order, so `__prepare__` is rarely needed *just* for ordering — but it's the only hook that can intercept assignments *as they happen* in the body (e.g. forbidding duplicate names, as `enum` does).

### 5. `__call__` — Controlling Instance Creation

Here's a subtlety that surprises people. When you write `Thing()`, what actually runs? Because `Thing` is an instance of `Meta`, calling it invokes `Meta.__call__(Thing)`. That metaclass `__call__` is what *normally* orchestrates `Thing.__new__` and `Thing.__init__`. Override it to control how instances are made:

```python
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Config(metaclass=SingletonMeta):
    def __init__(self):
        self.value = 42

a = Config()
b = Config()
print(a is b)   # True — only one instance ever created
```

`super().__call__(*args, **kwargs)` is the line that does the *normal* "call `__new__`, then `__init__`." By intercepting before it, the metaclass controls instance creation for the whole class.

### 6. The Modern Alternatives (Use These First)

Most real-world reasons to write a metaclass are better served by PEP 487 hooks or a class decorator.

**`__init_subclass__`** — runs on the *base* whenever a subclass is defined. No metaclass needed:

```python
class Plugin:
    registry = {}
    def __init_subclass__(cls, /, key=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.registry[key or cls.__name__] = cls   # auto-register every subclass

class JSONPlugin(Plugin, key="json"):
    pass

print(Plugin.registry)   # {'json': <class 'JSONPlugin'>}
```

**`__set_name__`** — lets an attribute learn the name it was assigned to, at class-creation time:

```python
class Field:
    def __set_name__(self, owner, name):
        self.name = name           # the descriptor now knows it's "title"
    def __get__(self, obj, objtype=None):
        return obj.__dict__.get(self.name)

class Article:
    title = Field()                # __set_name__ called with name="title"
```

**Class decorator** — receives the finished class, returns a modified one:

```python
def register(cls):
    REGISTRY[cls.__name__] = cls
    return cls

@register
class Handler:
    ...
```

The competent move: reach for these three before a metaclass. A metaclass is justified mainly when you need to affect instance creation (`__call__`), control the namespace mapping (`__prepare__`), or impose a metaclass-level interface across an entire class hierarchy.

---

## Code Examples

### Example 1: Auto-registration — metaclass vs the lighter way

```python
# --- The metaclass way (works, but heavier) ---
class RegistryMeta(type):
    registry = {}
    def __init__(cls, name, bases, ns, **kw):
        super().__init__(name, bases, ns)
        if bases:                      # skip the base itself
            RegistryMeta.registry[name] = cls

class BaseA(metaclass=RegistryMeta): pass
class Foo(BaseA): pass
print(RegistryMeta.registry)          # {'Foo': <class 'Foo'>}

# --- The __init_subclass__ way (preferred) ---
class BaseB:
    registry = {}
    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        cls.registry[cls.__name__] = cls

class Bar(BaseB): pass
print(BaseB.registry)                 # {'Bar': <class 'Bar'>}
```

Same outcome; the second needs no metaclass and is obvious to any reader.

### Example 2: Enforcing a class invariant at definition time

```python
class RequiresTableName(type):
    def __new__(mcs, name, bases, ns, **kw):
        if bases and "table_name" not in ns:
            raise TypeError(f"{name} must define `table_name`")
        return super().__new__(mcs, name, bases, ns)

class Model(metaclass=RequiresTableName): pass

class User(Model):
    table_name = "users"      # OK

# class Broken(Model): pass  # -> TypeError at import: must define table_name
```

The same check via `__init_subclass__` (preferred unless you need metaclass behavior):

```python
class Model2:
    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if "table_name" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define `table_name`")
```

### Example 3: A singleton via `__call__`

```python
class SingletonMeta(type):
    _cache = {}
    def __call__(cls, *a, **kw):
        if cls not in cls._cache:
            cls._cache[cls] = super().__call__(*a, **kw)
        return cls._cache[cls]

class Logger(metaclass=SingletonMeta):
    def __init__(self):
        print("constructing Logger")   # prints only once

x, y = Logger(), Logger()
print(x is y)    # True
```

This is the one case where a metaclass is genuinely the natural fit — controlling *instance* creation for a whole class. (Even so, many teams prefer a module-level singleton or a factory function for clarity.)

### Example 4: `__set_name__` — descriptors that know their name

```python
class Column:
    def __set_name__(self, owner, name):
        self.name = name
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)
    def __set__(self, obj, value):
        obj.__dict__[self.name] = value

class Row:
    id = Column()
    email = Column()

r = Row()
r.email = "a@b.com"
print(r.email)             # a@b.com
print(Row.email.name)      # "email" — learned at class-creation time
```

Before PEP 487 (3.6), making each `Column` learn its attribute name required a metaclass to scan the namespace. `__set_name__` removed that need.

### Example 5: Reading the lifecycle order

```python
class Trace(type):
    @classmethod
    def __prepare__(mcs, name, bases, **kw):
        print("1. __prepare__"); return {}
    def __new__(mcs, name, bases, ns, **kw):
        print("3. __new__"); return super().__new__(mcs, name, bases, ns)
    def __init__(cls, name, bases, ns, **kw):
        print("4. __init__"); super().__init__(name, bases, ns)

class Demo(metaclass=Trace):
    print("2. class body runs")
# Output order: 1, 2, 3, 4
```

---

## Coding Patterns

**Pattern: Prefer `__init_subclass__` for registration/validation.** It's discoverable (lives on the base class, reads top-to-bottom), composes via cooperative `super().__init_subclass__(**kwargs)`, and needs no metaclass.

**Pattern: `__set_name__` for self-aware attributes.** Any descriptor/field that needs its own name should implement `__set_name__` rather than relying on a metaclass to scan the namespace.

**Pattern: Class decorator for one-off post-processing.** If you need to transform *specific* classes (not a whole hierarchy), `@decorator` is simpler and more explicit than a metaclass.

**Pattern: Metaclass only for `__call__`/`__prepare__` needs.** Reserve metaclasses for the genuinely type-level concerns: instance-creation control and namespace control.

**Pattern: Always call `super()`.** In metaclass `__new__`/`__init__` and in `__init_subclass__`, call the parent implementation. Skipping it breaks cooperative multiple inheritance and ABC machinery.

**Anti-pattern: A metaclass that only reads the class.** If your metaclass `__init__` just registers or validates without touching `__call__`/`__new__`/`__prepare__`, it should almost certainly be `__init_subclass__`.

---

## Best Practices

- **Climb the decision ladder; stop early.** `__init_subclass__` → `__set_name__` → class decorator → metaclass, in that order.
- **Use metaclass `__init__` (not `__new__`) unless you must mutate the namespace.** Reading and reacting is `__init__`'s job; reshaping is `__new__`'s.
- **Cooperate with `super()` everywhere** in the class-creation chain.
- **Document the "why."** A metaclass with a one-line comment explaining what couldn't be done more simply saves the next reader an hour.
- **Keep metaclass logic small and pure.** Heavy side effects at import time (network calls, file I/O) make import order fragile and tests slow.
- **Don't put per-instance logic on the class clock.** If it should run each time you make an object, it belongs in `__init__`/`__new__` of the class or in metaclass `__call__`, not in metaclass `__init__`.

---

## Edge Cases & Pitfalls

- **Forgetting `bases` is empty for the base class.** Registration code often runs for the abstract base too; guard with `if bases:` or check `cls.__dict__`.
- **`namespace` is mutated, not copied, in `__new__`.** If you pass it to `super().__new__`, later edits to your local copy won't matter; edit *before* the call.
- **`__init_subclass__` is implicitly a classmethod.** You don't (and shouldn't) decorate it; Python treats it specially. Its first parameter is the *subclass*.
- **Keyword arguments flow through the class statement.** `class Foo(Base, key="x")` passes `key="x"` to `__init_subclass__`/`__prepare__`/`__new__`/`__init__`. Accept and forward `**kwargs`.
- **`__call__` on the metaclass shadows the normal construction path.** If you override it and forget `super().__call__(...)`, instances won't get `__init__` run. A subtle, hard-to-spot bug.
- **Type checkers may not follow metaclass magic.** Members injected by a metaclass often appear "undefined" to mypy/Pyright. Sometimes you must add stubs or `# type: ignore`, which is a real cost in the metaclass-vs-decorator decision.
- **`__set_name__` runs only for attributes set in the class body.** Attributes added *after* class creation (e.g. `Cls.x = Field()` later) don't get `__set_name__` called automatically — you'd have to call it yourself.

---

## Apply it

1. Find a real component where **Metaclasses** affects an interface or dependency.
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

- Which boundary is most affected by Metaclasses?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
