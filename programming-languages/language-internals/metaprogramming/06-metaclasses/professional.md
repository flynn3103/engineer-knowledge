# Metaclasses — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Metaclasses** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Where Metaclasses Actually Ship

The legitimate, framework-level uses cluster tightly:

- **Declarative ORM/serialization bases.** Django `Model`, SQLAlchemy's declarative
  base, and pydantic v1 all used a metaclass to scan the class body at creation
  time, turn `name = CharField()` descriptors into mapped columns, build a registry,
  and wire up `Meta` options. The metaclass is what makes `class User(Model):` feel
  declarative.
- **Automatic subclass registration / plugin systems.** A base class whose metaclass
  records every subclass in a registry (so a factory can later look them up by name)
  — the canonical metaclass use before `__init_subclass__`.
- **Interface/ABC enforcement.** `abc.ABCMeta` is a metaclass; it makes
  `@abstractmethod` block instantiation of incomplete subclasses and powers virtual
  subclass registration (`register`).
- **API-shaping DSL bases.** Enum (`enum.EnumMeta`), namedtuple-ish builders, and
  some test frameworks use a metaclass to give a class body special semantics.

Notice the pattern: every legitimate use is **framework-level, not
application-level**. You write the metaclass once, thousands of user classes benefit,
and the magic is documented and owned. Application code almost never needs to author
a metaclass.

---

## The Modern Alternatives That Replaced Most Metaclasses

PEP 487 (Python 3.6) added two hooks that absorbed the majority of historical
metaclass use cases with far less magic:

- **`__init_subclass__(cls, **kwargs)`** — a classmethod on the *base* called every
  time a subclass is defined. Subclass registration, validation of subclass
  attributes, and per-subclass configuration (via class keyword arguments) no longer
  need a metaclass.
- **`__set_name__(self, owner, name)`** — called on a descriptor when the owning
  class is created, so a field object learns its own attribute name without the
  metaclass scanning the namespace.

Together these cover registration, descriptor naming, and subclass validation — the
three commonest reasons people reached for a metaclass. **Class decorators** cover
most of the rest (mutate/augment a class after creation), and they compose far
better. The professional default is therefore: `__init_subclass__`/`__set_name__`
first, class decorator second, metaclass only when you must intercept class creation
*itself* or control the class namespace via `__prepare__`.

Ruby's parallel story: `method_missing` + `define_method` and `included`/`inherited`
hooks cover most "class-level magic" without reaching for raw eigenclass surgery,
though Rails still leans on `class << self` and dynamic method definition heavily.

---

## Code Examples

The same subclass-registry, the metaclass way and the modern way:

```python
# Metaclass (pre-3.6 idiom) — heavy.
class PluginMeta(type):
    registry = {}
    def __new__(mcs, name, bases, ns):
        cls = super().__new__(mcs, name, bases, ns)
        if bases:                      # skip the base itself
            PluginMeta.registry[name] = cls
        return cls

class Plugin(metaclass=PluginMeta): ...
class CsvPlugin(Plugin): ...          # auto-registered

# Modern (3.6+) — no metaclass, same effect, readable.
class Plugin:
    registry = {}
    def __init_subclass__(cls, /, **kw):
        super().__init_subclass__(**kw)
        Plugin.registry[cls.__name__] = cls

class JsonPlugin(Plugin): ...         # auto-registered
```

If a reviewer sees `metaclass=` in new application code, the first question should be:
"why isn't this `__init_subclass__`?"

---

## Performance & Startup

- Metaclass `__new__`/`__init__` run **once per class**, at import time — so the cost
  is a *startup* cost, not a per-instance cost. A package that defines thousands of
  model classes through a scanning metaclass pays for all of it at import, which
  shows up as slow CLI startup and slow test collection.
- A metaclass `__call__` override *does* run per instance creation; getting it wrong
  (e.g. an over-clever singleton metaclass) adds overhead to every `Foo()`.
- Metaclasses defeat some static tooling: type checkers model `__init_subclass__`
  and dataclasses well but struggle with arbitrary metaclass-synthesized members, so
  heavy metaclass magic often means `# type: ignore` and lost autocomplete.

---

## Best Practices

- **Don't write one in application code.** Reach for `__init_subclass__`,
  `__set_name__`, or a class decorator first.
- **If a framework makes you subclass a metaclassed base, keep your class bodies
  boring** — the magic is the base's, not yours.
- **Always call `super().__new__`/`super().__init_subclass__`** so metaclasses
  compose (multiple-inheritance metaclass conflicts are real and ugly).
- **Document the class-creation-time behavior loudly** — the surprising part is that
  code runs at `class` definition, not at instantiation.
- **Prefer composition of one metaclass**; mixing two metaclasses across a class
  hierarchy raises `metaclass conflict` and forces you to hand-merge them.

---

## Edge Cases & Pitfalls

- **Metaclass conflict on multiple inheritance:** if two bases have unrelated
  metaclasses, Python refuses to create the derived class; you must define a metaclass
  inheriting from both. This bites when combining, say, an ABC with an ORM model.
- **`__prepare__` surprises:** customizing the class namespace (e.g. to an ordered or
  recording dict) changes what the class body sees — powerful and confusing.
- **Singleton-via-metaclass** is a classic over-engineering smell; a module-level
  instance or `functools.lru_cache` is simpler and testable.
- **Ruby `method_missing` traps:** it silently swallows typos (a misspelled method
  becomes a dynamic-finder attempt), hurts performance (every miss walks the lookup),
  and must be paired with `respond_to_missing?` or it breaks `respond_to?`, `Method`
  objects, and duck-typing checks.
- **Debugging:** a `class` statement that fails inside a metaclass produces a traceback
  pointing at class *definition*, which newcomers don't expect.

---

## Apply it

1. Define the user or business outcome that **Metaclasses** should improve.
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

- Which measurable outcome justifies investing in Metaclasses?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
