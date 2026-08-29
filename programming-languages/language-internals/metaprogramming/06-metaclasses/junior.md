# Metaclasses — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Metaclasses** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. "Everything Is an Object" — Including Classes

In Python, integers are objects, strings are objects, functions are objects, and **classes are objects**. This is not a figure of speech. You can do everything to a class that you can do to any other value:

```python
class Dog:
    def bark(self):
        return "woof"

x = Dog            # assign the class to a variable — no parentheses, no instance
print(x)           # <class '__main__.Dog'>
animals = [Dog]    # put it in a list
print(x().bark())  # call x like a class, get an instance, call its method -> "woof"
```

`Dog` (no parentheses) is the class object itself. `Dog()` (with parentheses) *calls* that object to produce an instance. The class is a value; the instance is another value; calling the first gives you the second.

### 2. Every Object Has a Class — So What Is the Class of a Class?

The function `type(x)` tells you the class of any object:

```python
type(42)        # <class 'int'>
type("hi")      # <class 'str'>
type(Dog())     # <class '__main__.Dog'>
```

Apply the same rule to the class object `Dog` itself:

```python
type(Dog)       # <class 'type'>
```

The class of `Dog` is `type`. The class of `int` is `type`. The class of `str` is `type`. **`type` is the metaclass of almost every class in Python.** It is the factory that builds classes.

```text
   instance  ----type()-->   class   ----type()-->   metaclass
     dog                      Dog                       type
   "hello"                    str                       type
      42                      int                       type
```

### 3. `type` Has Two Jobs (and Two Call Shapes)

This trips up everyone at first. `type` is *one* built-in, but you call it two different ways:

**Call shape A — with one argument:** "tell me the class of this object."

```python
type(42)        # <class 'int'>
```

**Call shape B — with three arguments:** "*build a brand-new class* for me."

```python
Dog = type("Dog", (), {"bark": lambda self: "woof"})
#          name    bases  namespace (methods/attributes)

d = Dog()
print(d.bark())   # "woof"
```

Those two lines build a class *exactly* equivalent to writing `class Dog:` with a `bark` method. The three arguments are:

1. **name** — the class's name as a string (`"Dog"`).
2. **bases** — a tuple of parent classes (`()` means just inherit from `object`).
3. **namespace** — a dict of the class's contents: methods, class attributes.

The lesson: **the `class` statement is syntax sugar.** Under the hood, Python collects the name, the bases, and the body into a namespace dict, and calls the metaclass (`type`) to manufacture the class. A metaclass is "the thing Python calls to turn a `class` block into a class object."

### 4. Class Creation Happens Once, Early

When does a class get *built*? Not when you make instances. It is built **the moment the `class` statement runs**, which is usually when the module is first imported.

```python
print("before")

class Dog:
    print("class body running!")   # this prints during import, immediately

print("after")
```

Output:

```text
before
class body running!
after
```

The class body executes *once*, top to bottom, at import time. This is the moment a metaclass gets to intervene — it is the "construction time" of the class itself. Compare:

- `__init__` runs every time you make an **instance**.
- A metaclass's work runs once, when you make the **class**.

### 5. You Rarely Need to Write One

Here is the most important practical point at this level, and it comes from Tim Peters (author of much of Python's standard library):

> "Metaclasses are deeper magic than 99% of users should ever worry about. If you wonder whether you need them, you don't (the people who actually need them know with certainty that they need them, and don't need an explanation about why)."

You will *use* metaclasses indirectly all the time (every Django model, every `abc.ABC`). You will *write* one almost never. Modern Python (since version 3.6) added simpler tools — `__init_subclass__` and `__set_name__` — that cover most of what people used to reach for metaclasses to do. Recognizing a metaclass is a junior skill. Writing one is a "you'll know when" skill.

---

## Code Examples

### Example 1: Proving a class is an object

```python
class Dog:
    pass

# It's a value: assign, store, inspect.
ref = Dog
print(ref is Dog)        # True — same object
print(Dog.__name__)      # "Dog"
print(isinstance(Dog, object))  # True — classes are objects
print(isinstance(Dog, type))    # True — and their type is `type`
```

### Example 2: The class of common things is `type`

```python
print(type(int))      # <class 'type'>
print(type(str))      # <class 'type'>
print(type(list))     # <class 'type'>
print(type(object))   # <class 'type'>
print(type(type))     # <class 'type'>   <- type is its own type; the ladder ends here
```

### Example 3: Building a class without the `class` keyword

```python
def greet(self):
    return f"Hi, I'm {self.name}"

# Same as: class Person: ...
Person = type(
    "Person",                 # name
    (),                       # bases
    {"species": "human",      # class attribute
     "greet": greet},         # method
)

p = Person()
p.name = "Ada"
print(p.greet())     # "Hi, I'm Ada"
print(p.species)     # "human"
print(type(p))       # <class '__main__.Person'>
```

This is the single most clarifying exercise in the topic. The `class` statement and this `type(...)` call are interchangeable. The metaclass *is* the function being called.

### Example 4: Seeing class-creation time fire

```python
class Loud:
    print(">>> Loud is being built right now")
    x = 1
    print(">>> still building, x is set")

print(">>> Loud is finished")
# Notice: we never made an instance, yet two lines already printed.
```

### Example 5: Recognizing a metaclass in framework code (read-only)

You will see code like this and should now *recognize the shape* even if you can't yet write it:

```python
# Conceptually how an ORM's base looks (simplified):
class Model(metaclass=SomeMetaclass):
    ...

class User(Model):
    name = CharField()
    email = CharField()
```

The `metaclass=SomeMetaclass` part (or a base class that itself uses one) means: *something custom runs when `User` is defined* — it scans `name` and `email`, builds a table description, and registers `User`. You don't see `__init__` doing this because it happens at **class**-creation time, courtesy of the metaclass.

---

## Coding Patterns

At junior level the only "pattern" is **recognition**, not authorship.

**Pattern: spot the construction-time work.** When you see a base class with declared fields and surprising behavior, ask: *what runs when the subclass is defined?* Look for `metaclass=` in a base class, or an `__init_subclass__` method, or a class decorator above the class. One of those is doing the magic.

**Pattern: read with the ladder in mind.** When confused, write down the three rungs for the objects involved:

```python
type(obj)          # instance -> class
type(type(obj))    # class -> metaclass
```

Knowing *which rung* a piece of code operates on usually dissolves the confusion.

**Anti-pattern (avoid): reaching for `type(...)`-as-factory in normal code.** If you find yourself building classes dynamically with `type("Foo", ...)`, stop and ask whether a plain function, a closure, or a `dataclass` would do. It almost always would.

---

## Best Practices

- **Default to *not* writing one.** Prefer a normal class, then a class decorator, then `__init_subclass__`, and only then a metaclass — in that order of preference.
- **Recognize the construction-time clock.** When debugging "why did this happen at import?", remember the class body and any metaclass run *once, early*.
- **Trust frameworks.** When `class User(models.Model)` does magic, that's intended; you don't need to fight or fully decode it to use it.
- **When you must read metaclass code, find `__new__`/`__init__` on the metaclass.** Those are where class-creation customization lives (details in `middle.md`).
- **Keep the ratio in your head:** *metaclass : class :: class : instance.* It is the one fact that never lets you down.

---

## Edge Cases & Pitfalls

- **Confusing the metaclass with the base class.** `object` is the root of the *inheritance* tree (what you subclass). `type` is the root of the *metaclass* tree (what creates classes). They are different axes. `class Dog(Animal)` sets the base; `class Dog(metaclass=Meta)` sets the metaclass. (More in `middle.md`.)
- **Thinking the metaclass runs per-instance.** It doesn't. It runs once, when the class is created. `Dog()` does not re-run the metaclass.
- **`type(x)` vs `x.__class__`.** They usually agree, but `__class__` can be reassigned and lied to; `type(x)` is the honest answer. As a junior, just use `type(x)`.
- **Assuming every language works like Python.** Java and C# have class *objects* (reflection), but classes aren't created by a user-overridable metaclass at runtime the way Python's are. Ruby and Smalltalk have rich metaclass models that differ from Python's (covered in `professional.md`).
- **Editing the namespace dict by hand.** Beginners sometimes try to mutate a class's `__dict__` directly. It's a `mappingproxy` (read-only view) — you can't just assign into it. Set attributes on the class instead.
- **The infinite-ladder worry.** "If every object has a class, doesn't the metaclass need a metaclass forever?" No — the ladder terminates because `type(type)` is `type`. It is its own metaclass. The recursion stops; you don't need to chase it.

---

## Apply it

1. Choose one small, known input for **Metaclasses**.
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

- What problem does Metaclasses solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
