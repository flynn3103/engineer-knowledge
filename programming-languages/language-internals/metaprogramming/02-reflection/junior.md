# Reflection — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Reflection** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Two Halves: Looking vs. Doing

Reflection splits cleanly into two activities, and keeping them apart makes everything clearer:

- **Introspection (looking, read-only).** "What type is this object? List its fields. Does it have a method named `close`?" Nothing changes; you are just reading metadata. This is the safe, common half.
- **Intercession / dynamic invocation (doing).** "Set the field `name` to `'Ada'`. Call the method `save`." Now you are *acting* on the object by name, at runtime. More powerful, more dangerous, slower.

Almost every real use of reflection is *mostly looking, with a little doing at the end*: a JSON library looks at all the fields (introspection) and then reads each one's value (a tiny bit of intercession) to build the output.

### 2. It Happens at Runtime, Not Compile Time

This is the defining property. Normally, your compiler knows every name. If you misspell `user.nme`, it refuses to build. With reflection, the name is often a **string** (`getattr(user, "nme")`) or comes from data, so the compiler cannot check it. The mistake surfaces *while the program runs*, possibly only when that exact code path executes.

That trade is the soul of reflection: **you gain the ability to handle types you didn't know about when you wrote the code, and you lose the compiler's safety net.**

### 3. The Type Object: Your Entry Point

Every reflective journey starts by getting a handle that *represents a type*. It is itself a value you can hold in a variable and ask questions:

- **Java:** `Class<?> c = user.getClass();` then `c.getDeclaredFields()`, `c.getMethods()`.
- **Go:** `t := reflect.TypeOf(user)` then `t.NumField()`, `t.Field(i)`.
- **Python:** `type(user)` (or just `user.__class__`), then `dir(user)` and `user.__dict__`.
- **C#:** `Type t = user.GetType();` then `t.GetProperties()`, `t.GetMethods()`.

From that one handle you can reach everything else: fields, methods, constructors, and any metadata (annotations/tags) attached to them.

### 4. Reading and Writing a Field by Name

Once you have the type and an instance, you can read a field whose name you only have as text:

- **Python:** `getattr(user, "name")` reads it; `setattr(user, "name", "Ada")` writes it; `hasattr(user, "name")` checks existence.
- **Go:** `reflect.ValueOf(&user).Elem().FieldByName("Name")` — but writing has strict rules (see Pitfalls).
- **Java:** `Field f = c.getDeclaredField("name"); f.setAccessible(true); f.get(user);` / `f.set(user, "Ada");`
- **C#:** `t.GetProperty("Name").GetValue(user);` / `.SetValue(user, "Ada");`

### 5. Calling a Method by Name

The active extreme: you have a method name as a string and you invoke it.

- **Python:** `getattr(user, "save")()` — get the method, then call it.
- **Java:** `Method m = c.getMethod("save"); m.invoke(user);`
- **Go:** `reflect.ValueOf(user).MethodByName("Save").Call(nil)`
- **C#:** `t.GetMethod("Save").Invoke(user, null);`

### 6. Languages Sit on a Spectrum

Not all languages reflect equally:

- **Python** makes reflection *trivial and pervasive* — everything is an object, and inspecting objects is just normal Python.
- **Java** and **C#** have full, explicit reflection libraries (`java.lang.reflect`, `System.Reflection`) — powerful but verbose and ceremonious.
- **Go** has `reflect`, but the language *discourages* it: it is slow, unsafe, and verbose by design, used mostly inside libraries.
- **Rust** deliberately has **almost no runtime reflection.** Its philosophy is "zero-cost" — anything that costs runtime work you didn't ask for is suspect. Instead, Rust does the same jobs at *compile time* with macros and `derive` (see below).

---

## Code Examples

### Example 1: Introspection — listing fields and methods

**Python** (the most natural place to start):

```python
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def greet(self):
        return f"Hi, I'm {self.name}"

u = User("Ada", 36)

print(type(u))            # <class '__main__.User'>
print(type(u).__name__)   # 'User'
print(u.__dict__)         # {'name': 'Ada', 'age': 36}  -- the instance's fields
print(dir(u))             # every attribute & method name, as strings

# Read a field whose name is just a string:
print(getattr(u, "name"))           # 'Ada'
print(hasattr(u, "email"))          # False

# Call a method whose name is just a string:
print(getattr(u, "greet")())        # 'Hi, I'm Ada'
```

Notice how *ordinary* this looks in Python. There is no special "reflection library" ceremony — inspecting objects is just Python.

**Go** (more explicit, via the `reflect` package):

```go
package main

import (
	"fmt"
	"reflect"
)

type User struct {
	Name string
	Age  int
}

func main() {
	u := User{Name: "Ada", Age: 36}

	t := reflect.TypeOf(u)   // describes the *type*
	v := reflect.ValueOf(u)  // wraps the *value*

	fmt.Println(t.Name(), t.Kind()) // User struct

	for i := 0; i < t.NumField(); i++ {
		f := t.Field(i)                 // a StructField (name, type, tag)
		fmt.Printf("%s = %v\n", f.Name, v.Field(i))
	}
	// Output:
	// Name = Ada
	// Age = 36
}
```

`reflect.TypeOf` gives you the type handle; `reflect.ValueOf` wraps the actual value. You almost always use them together.

### Example 2: Struct tags — the thing that makes JSON "just work" (Go)

```go
type User struct {
	Name  string `json:"user_name"`
	Email string `json:"email,omitempty"`
}
```

When you call `json.Marshal(u)`, the standard library *reflects* over `User`, reads each field's `json:"..."` **struct tag**, and uses it to decide the output key. That's why the field `Name` becomes `"user_name"` in the JSON — a library read a tag via reflection. You can read tags yourself:

```go
t := reflect.TypeOf(User{})
f, _ := t.FieldByName("Name")
fmt.Println(f.Tag.Get("json")) // "user_name"
```

This single mechanism powers JSON, YAML, database mapping (`db:"..."`), validation (`validate:"required"`), and more.

### Example 3: Dynamic invocation in Java

```java
import java.lang.reflect.*;

class User {
    private String name = "Ada";
    public String greet() { return "Hi, I'm " + name; }
}

public class Demo {
    public static void main(String[] args) throws Exception {
        User u = new User();
        Class<?> c = u.getClass();

        // Introspection: list declared fields
        for (Field f : c.getDeclaredFields()) {
            System.out.println(f.getType() + " " + f.getName());
        }

        // Read a private field by reflecting + breaking access control
        Field nameField = c.getDeclaredField("name");
        nameField.setAccessible(true);            // ignore 'private'
        System.out.println(nameField.get(u));     // "Ada"

        // Call a method by name
        Method m = c.getMethod("greet");
        System.out.println(m.invoke(u));          // "Hi, I'm Ada"
    }
}
```

The `setAccessible(true)` call is doing something significant: it asks the runtime to let you reach into a `private` field. That is convenient for libraries and dangerous for encapsulation — `middle.md` and `senior.md` discuss why.

### Example 4: C# reflection with attributes

```csharp
using System;
using System.Reflection;

class User {
    public string Name { get; set; } = "Ada";
    public string Greet() => $"Hi, I'm {Name}";
}

class Program {
    static void Main() {
        var u = new User();
        Type t = u.GetType();

        foreach (PropertyInfo p in t.GetProperties())
            Console.WriteLine($"{p.PropertyType} {p.Name} = {p.GetValue(u)}");

        MethodInfo m = t.GetMethod("Greet");
        Console.WriteLine(m.Invoke(u, null)); // "Hi, I'm Ada"
    }
}
```

### Example 5: Rust says "no" — and does it at compile time instead

Rust has no general runtime reflection. You cannot, in safe stable Rust, hand it an arbitrary value and ask "list your fields by name." Instead, the same jobs are done at **compile time** with macros. The Serde library is the classic example:

```rust
use serde::Serialize;

#[derive(Serialize)]   // a macro generates the serialization code at compile time
struct User {
    name: String,
    age: u32,
}

fn main() {
    let u = User { name: "Ada".into(), age: 36 };
    println!("{}", serde_json::to_string(&u).unwrap()); // {"name":"Ada","age":36}
}
```

`#[derive(Serialize)]` runs *while compiling* and writes out the exact code to serialize a `User` — no runtime field-walking, no metadata lookup, no cost you didn't ask for. The output is the same as a reflective serializer; the *mechanism* is completely different. Keep this contrast in mind: **reflection (runtime) and code generation (compile time) often solve the same problem.**

---

## Coding Patterns

**Pattern 1: Inspect first, act second.** Always do the read-only introspection (list fields, check a method exists) before any intercession. Don't blindly `invoke` a method you haven't confirmed exists.

```python
if hasattr(obj, "close"):
    getattr(obj, "close")()
```

**Pattern 2: Guard with `hasattr` / existence checks.** Because names aren't compiler-checked, defend against missing members explicitly.

**Pattern 3: Tags/annotations as configuration.** Instead of hard-coding behavior, read a struct tag or annotation and let it drive the logic (the JSON-key pattern). This keeps the mapping next to the data.

**Pattern 4: Keep reflection at the edges.** Use reflection in the *library/boundary* layer (parsing input, building output). Keep your core business logic plain, direct, and type-checked.

---

## Best Practices

- **Prefer not to.** If you can solve it with normal code, generics, or an interface, do that. Reflection is a last resort, not a default.
- **Introspect more, intercede less.** Reading structure is far safer than dynamically setting fields and calling methods.
- **Validate names early.** If you reflect on a method/field name, check it exists and fail with a clear message — don't let a cryptic runtime error leak out later.
- **Don't reach into `private` casually.** `setAccessible(true)` (Java) or touching `_internal` attributes (Python) couples you to another type's *secrets*, which can change without warning.
- **Centralize it.** Wrap reflective code in one small, well-tested module rather than scattering `getattr` / `invoke` calls everywhere.
- **Read the library's docs about tags/annotations.** Half of "reflection in practice" for a junior is just knowing which tag (`json:"..."`, `@JsonProperty`, `[JsonPropertyName]`) does what.

---

## Edge Cases & Pitfalls

- **The typo'd name.** `getattr(user, "nme")` doesn't fail at build time — it throws `AttributeError` at runtime, maybe only on a rare path. The compiler can't save you.
- **Go's settability rule.** This trips up *everyone*. `reflect.ValueOf(u).Field(0).Set(...)` **panics** because the value is a copy, not addressable. You must pass a *pointer* and call `.Elem()`: `reflect.ValueOf(&u).Elem().Field(0).Set(...)`. And the field must be exported (capitalized). More in `middle.md`.
- **Unexported / private members.** In Go, reflection can *read* some unexported fields but cannot *set* them. In Java you need `setAccessible(true)` — which may now be blocked by the module system (see `professional.md`).
- **Reflection sees the *runtime* type, not the *declared* type.** If a variable declared as `Animal` actually holds a `Dog`, reflection reports `Dog`. Usually what you want, but surprising the first time.
- **It's slow in a loop.** Reflecting once is fine; reflecting a million times in a hot loop is a performance bug. Cache the type/field/method handles (see `middle.md`).
- **Renaming breaks it silently.** If you rename a field `Name`→`FullName` but a JSON tag or a string somewhere still says `"name"`, nothing complains until data is wrong at runtime.
- **Static analysis goes blind.** Your IDE's "find usages" and dead-code detection can't see reflective calls, so code that *looks* unused may actually be vital.

---

## Common Mistakes

1. **Reaching for reflection too early.** Many "I need reflection" problems are solved more simply by an interface, a generic, or a `switch`/`match`. Try those first.
2. **Forgetting Go's pointer/`Elem()` rule** and getting a panic on `Set`.
3. **Ignoring exported-vs-unexported (Go) / public-vs-private (Java) rules** and being surprised when fields are invisible or unsettable.
4. **Not caching handles**, then wondering why the serializer is slow.
5. **Letting reflective typos become production runtime errors** instead of validating names up front.
6. **Assuming Rust can reflect like Python** — it can't; reach for `derive` macros instead.

---

## Apply it

1. Choose one small, known input for **Reflection**.
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

- What problem does Reflection solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
