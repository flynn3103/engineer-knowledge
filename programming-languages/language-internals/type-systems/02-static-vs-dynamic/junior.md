# Static vs Dynamic Typing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Static vs Dynamic Typing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A Type Is a Promise

A type answers the question: *what can I do with this value?* If `x` is an `int`, you can add, subtract, compare. If `x` is a `string`, you can concatenate, slice, uppercase. The type is the contract. A **type error** is breaking that contract — asking a value to do something its type doesn't support, like `5.toUpperCase()`.

The interesting question is never *whether* type errors are caught. They always are, eventually — you can't actually uppercase the number 5; the machine has no instruction for it. The interesting question is **when**.

### 2. Static = Checked Before Running

In a static language, there is a separate **type-checking phase** that runs over your *entire source file* (or program) before any of it executes. The checker reads the code, works out the type of every variable and expression, and verifies every operation is legal. If anything is wrong, you get a compile error and **no runnable program is produced at all**.

```java
String s = "hello";
int n = s;          // COMPILE ERROR: incompatible types: String cannot be converted to int
```

This never runs. The build fails. You fix it and try again. The key property: **the error is found whether or not that line would ever have executed.** Static checking examines *all* the code, including the branch that only runs on February 29th.

### 3. Dynamic = Checked While Running

In a dynamic language, there is no separate type-checking phase. The program starts running, and at the moment each operation executes, the runtime checks: *does this value actually support this operation?* If yes, proceed. If no, raise an exception **right then**.

```python
s = "hello"
n = s + 5          # runs fine UP TO HERE, then: TypeError: can only concatenate str (not "int") to str
```

Two crucial properties follow:

1. **The error only appears when the line actually runs.** If `s + 5` lives inside `if user_is_admin and is_leap_year():`, you might not discover the bug for a year.
2. **Earlier code runs first.** The program does real work, possibly with side effects (writes a file, sends an email), and *then* crashes. There's no "the whole program is valid" guarantee.

### 4. Where Types Live: Variables vs Values

There's a subtle, important distinction:

- In a **static** language, the type is attached to the **variable** (or expression). `int count;` says: *this slot only ever holds integers.* The variable has a fixed type for its whole life; the type checker reasons about the slot.
- In a **dynamic** language, the type is attached to the **value**, and variables are just names that can point at anything. `count = 5` then `count = "hello"` is fine — `count` is just a label, and the *value* it points to carries the type.

This is why in Python you can write `x = 5; x = "hi"; x = [1,2,3]` with no complaint — `x` is not typed, the values are. In Java, `int x = 5; x = "hi";` is a compile error — `x` is permanently an `int`.

### 5. What Static Catches That Dynamic Doesn't (and Vice Versa)

**Static typing catches, before you run:**

- Typos in names: `usr.naem` when the field is `name`.
- Wrong argument types: passing a `string` where the function wants an `int`.
- Calling methods that don't exist on a type.
- (In some languages) forgetting to handle `null` / `None`.

**Static typing's price — it sometimes rejects valid programs.** A type checker is *conservative*: it must reject anything it can't *prove* safe. Some programs are actually correct but the checker can't see why, so it refuses them. You then either restructure the code or reach for an escape hatch (a cast). This is the trade: false alarms (rejecting good programs) in exchange for catching real ones early.

**Dynamic typing's strength** is exactly the flip side: it accepts everything and only complains about what actually goes wrong *as it goes wrong*. It never rejects a valid program for being un-provable. It's terse, flexible, and great for exploration. **Its weakness** is that a type bug on an unexercised path is invisible until that path runs — often in production.

### 6. Strong vs Weak Is a DIFFERENT Axis

This trips up almost everyone, so it gets its own section. **Static/dynamic is about *when* (compile time vs run time). Strong/weak is about *whether the language silently coerces types*.**

- **Strong typing:** the language refuses surprising implicit conversions. `"5" + 5` is an error (Python) — you must convert explicitly.
- **Weak typing:** the language happily coerces. `"5" + 5` becomes `"55"` (JavaScript) or `5 + "5"` becomes `10` in some contexts (PHP). C lets you treat an `int` as a pointer with a cast and read arbitrary memory — extremely weak.

The two axes are independent. Here's the grid:

| | **Strong** | **Weak** |
|---|---|---|
| **Static** | Java, Go, Rust, Haskell | C, C++ (casts let you reinterpret bytes) |
| **Dynamic** | Python, Ruby | JavaScript, PHP, Perl |

So "Python is strongly typed" and "Python is dynamically typed" are both true and *not contradictory*: Python checks types at runtime (dynamic) but refuses to silently coerce `"5" + 5` (strong). Don't let anyone tell you dynamic means weak — Python is a counterexample you'll use constantly.

### 7. The Canonical Crash: `null` / `None` / `undefined`

The single most common runtime type error in the world is calling a method on "nothing":

```python
user = find_user(id)   # returns None if not found
print(user.name)       # AttributeError: 'NoneType' object has no attribute 'name'
```

```javascript
const user = findUser(id);  // returns undefined if not found
console.log(user.name);     // TypeError: Cannot read properties of undefined (reading 'name')
```

In a dynamic language, this is a runtime crash that only happens when `find_user` actually returns nothing. A *static* type system that distinguishes "User" from "maybe-a-User" (like Rust's `Option<User>`, Kotlin's `User?`, or Haskell's `Maybe User`) can force you to handle the empty case **at compile time** — turning a 2 a.m. production page into a build error on your laptop. This is one of the strongest practical arguments for static typing, and you'll meet it again at every level.

---

## Code Examples

We'll write the same tiny program — *look up a user and greet them* — in a static language (Java, Go) and a dynamic one (Python, JavaScript), and watch where the bug surfaces.

### The bug: a typo in a field name

#### Python (dynamic) — runs, then crashes

```python
class User:
    def __init__(self, name):
        self.name = name

def greet(user):
    return "Hello, " + user.naem   # TYPO: should be .name

u = User("Ada")
print(greet(u))   # AttributeError: 'User' object has no attribute 'naem'
```

This program **compiles and starts running**. The typo is only discovered the instant `greet` executes the bad line. If `greet` were called only in an error-handling branch, the typo could ship to production unnoticed.

#### JavaScript (dynamic, weak) — even quieter

```javascript
const user = { name: "Ada" };
console.log("Hello, " + user.naem);   // "Hello, undefined"  — NO ERROR AT ALL
```

Worse than Python: reading a missing property returns `undefined`, so this *doesn't even throw* — it just prints `Hello, undefined` and carries on. The bug is completely silent.

#### Java (static) — won't compile

```java
class User {
    String name;
    User(String name) { this.name = name; }
}

class Main {
    static String greet(User user) {
        return "Hello, " + user.naem;   // COMPILE ERROR: cannot find symbol 'naem'
    }
}
```

The compiler refuses. You never get a runnable program with this typo. The error message points right at `naem` and you fix it in five seconds, before any user, any test, any deploy.

#### Go (static) — won't compile

```go
type User struct {
    Name string
}

func greet(u User) string {
    return "Hello, " + u.Naem   // COMPILE ERROR: u.Naem undefined (type User has no field or method Naem)
}
```

Same story. `go build` fails. The bug cannot reach runtime.

### The other bug: passing the wrong type

#### Python (dynamic, strong) — runtime TypeError

```python
def double(n):
    return n * 2

print(double("5"))   # prints "55"  — string repetition, NOT what we meant!
print(double(5))     # prints 10
```

Note Python is *strong* but *dynamic*: `"5" * 2` is a legal operation (string repetition), so there's no error — just a wrong answer. The dynamic checker can't know you meant numeric doubling.

#### Go (static) — won't compile

```go
func double(n int) int {
    return n * 2
}

func main() {
    fmt.Println(double("5"))   // COMPILE ERROR: cannot use "5" (string) as int value
}
```

The static type on the parameter (`n int`) makes this impossible. The wrong call is caught at the boundary.

### The famous `null`/`None`/`undefined` crash

#### Python (dynamic)

```python
def find_user(users, target_id):
    for u in users:
        if u["id"] == target_id:
            return u
    return None   # not found

user = find_user([], 42)
print(user["name"])   # TypeError: 'NoneType' object is not subscriptable
```

#### Rust (static, with `Option`) — forces you to handle "not found"

```rust
fn find_user(users: &[User], target_id: u32) -> Option<&User> {
    users.iter().find(|u| u.id == target_id)
}

fn main() {
    let user = find_user(&[], 42);
    // println!("{}", user.name);  // COMPILE ERROR: Option<&User> has no field `name`
    match user {
        Some(u) => println!("{}", u.name),
        None => println!("not found"),   // compiler MAKES you handle this
    }
}
```

The static type `Option<&User>` literally cannot be used as a `User` until you unwrap it and deal with the `None` case. The 2 a.m. crash becomes a compile error.

---

## Coding Patterns

### Pattern 1: Validate at the boundary (dynamic languages)

Dynamic languages don't check types for you, so check incoming data yourself at the edges of your program:

```python
def set_age(age):
    if not isinstance(age, int):
        raise TypeError(f"age must be int, got {type(age).__name__}")
    ...
```

Validate at the boundary (request handlers, file parsers, library entry points) and trust the data inside.

### Pattern 2: Let the type be the documentation (static languages)

```go
func SendEmail(to EmailAddress, subject string, body string) error
```

The signature tells you everything: it needs an `EmailAddress` (not just any string), a subject, a body, and it can fail. You don't need a doc comment to know how to call it.

### Pattern 3: Make "no value" explicit, not a landmine

Prefer types that encode emptiness — `Optional`, `Option`, `Maybe`, a nullable `User?` — over a bare value that might secretly be `null`. In dynamic languages, be explicit in your return contract and document it: "returns `None` if not found," then always handle `None`.

### Pattern 4: Convert explicitly, never rely on coercion

```python
total = int(quantity) * float(price)   # explicit, clear
```

Don't lean on weak-typing coercion even when the language offers it — it's the source of silent wrong answers. Being explicit reads the same in strong and weak languages.

---

## Best Practices

- **Know which two axes you're on.** Be able to place your language: static-or-dynamic, strong-or-weak. Python = dynamic + strong. C = static + weak. Don't conflate them.
- **In dynamic languages, lean on tests harder.** Tests are your only safety net for the bugs a compiler would otherwise catch. Aim to *execute* every branch.
- **In static languages, don't fight the checker with casts.** A cast (`(int)`, `as`, type-ignore) silences the checker and hands the risk back to runtime. Use sparingly.
- **Handle `null`/`None`/`undefined` at every boundary.** It's the #1 runtime crash. Never assume a lookup found something.
- **Let static types replace comments.** A good signature documents intent better than prose and can't go stale.
- **Add type checking incrementally to dynamic code.** If your Python or JS project is growing, adopt type hints / TypeScript — you don't have to convert everything at once (the "gradual" story, `middle.md`).
- **Don't rely on coercion for correctness.** Convert explicitly. Coercion is convenience, not a contract.

---

## Edge Cases & Pitfalls

- **"Dynamic means weak" — false.** Python and Ruby are dynamic *and* strongly typed. Don't repeat this myth in an interview.
- **"Static means no runtime type errors" — false.** Casts, reflection, deserialization, and `null` can all still blow up at runtime in a static language. Static *reduces* runtime type errors; it doesn't eliminate them.
- **The unexercised-branch trap.** In dynamic code, a type bug in a rarely-run branch is invisible until that branch runs. Your "it works" run proved nothing about the other branches.
- **JavaScript's silent `undefined`.** Reading a missing property gives `undefined` instead of throwing, so bugs propagate silently (`Hello, undefined`) until something downstream finally chokes.
- **Static typing rejects some valid programs.** When the checker says no but you're *sure* it's fine, the checker may simply be too conservative to prove it. Sometimes you're right; often you're missing a case it sees. Default to assuming the checker has a point.
- **`==` coercion in weak languages.** JavaScript's `0 == "0"` is `true`, `0 == ""` is `true`, `"0" == ""` is `false`. Use `===` (strict equality) to avoid the coercion maze.
- **Inferred types still mean static.** Go's `x := 5` has no written annotation but `x` is statically an `int` forever. "No annotations visible" does not mean "dynamic."
- **A REPL exists for static languages too.** Dynamic languages are famous for REPLs, but Scala, Haskell, and others have them. REPL-friendliness correlates with dynamic but isn't the definition.

---

## Apply it

1. Choose one small, known input for **Static vs Dynamic Typing**.
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

- What problem does Static vs Dynamic Typing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
