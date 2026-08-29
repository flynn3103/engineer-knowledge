# DSLs via Metaprogramming — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **DSLs via Metaprogramming** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Operator Overloading Captures Expressions as Data

In a normal program, `age > 21` computes a boolean *right now*. In a query DSL, `User.age > 21` must instead produce a **description** of the comparison — a small object — because you want to send `WHERE age > 21` to the database, not evaluate it in Python against nothing.

The trick is to make `User.age` an **object** (a `Column`) whose comparison operators are overloaded to **build nodes** instead of returning booleans:

```python
class Column:
    def __init__(self, name):
        self.name = name

    def __gt__(self, other):     # User.age > 21  ->  this runs
        return Gt(self, other)   # returns a NODE, not True/False

    def __eq__(self, other):
        return Eq(self, other)

    def __and__(self, other):    # cond1 & cond2
        return And(self, other)

class Gt:
    def __init__(self, left, right):
        self.left, self.right = left, right

class Eq:  # ...same shape
    def __init__(self, left, right): self.left, self.right = left, right

class And:
    def __init__(self, left, right): self.left, self.right = left, right
```

Now `User.age > 21` evaluates to `Gt(Column("age"), 21)` — an **expression tree node**. The DSL captured the *shape* of the comparison. Later, a separate function walks the tree and emits SQL. This is exactly how SQLAlchemy, Django's `Q` objects, and pandas masks work.

### 2. Walk the Tree to Compile It

Once the expression is a tree of objects, "running" the DSL means **traversing the tree** and producing output — SQL text, a NumPy mask, a gradient. Compiling our nodes to SQL:

```python
def to_sql(node):
    if isinstance(node, Column):
        return node.name, []
    if isinstance(node, (int, str)):
        return "?", [node]                 # parameterized -> no SQL injection
    if isinstance(node, Gt):
        l, lp = to_sql(node.left)
        r, rp = to_sql(node.right)
        return f"({l} > {r})", lp + rp
    if isinstance(node, And):
        l, lp = to_sql(node.left)
        r, rp = to_sql(node.right)
        return f"({l} AND {r})", lp + rp
    raise TypeError(node)

expr = (Column("age") > 21) & (Column("active") == True)
sql, params = to_sql(expr)
# ("((age > ?) AND (active = ?))", [21, True])
```

The DSL split cleanly into two halves: **build the tree** (operator overloading) and **interpret the tree** (a walker). Almost every expression DSL has this shape. Parameterizing literals as `?` is also where these DSLs *earn their keep* — they prevent SQL injection by construction.

### 3. The Boolean-Coercion Trap

Here is the trap that bites everyone the first time. Because `User.age > 21` returns an *object*, Python's `and`, `or`, and `if` do the wrong thing:

```python
# WRONG — Python's `and` calls __bool__ on the left operand and short-circuits:
(User.age > 21) and (User.active == True)   # returns just the RIGHT object!

# Python evaluates the left node's truthiness, finds it "truthy",
# and returns the right node — your AND is silently lost.
```

Python's keyword operators (`and`, `or`, `not`, `if`) are **not overloadable**; they coerce operands to bool. That is why these DSLs use the *bitwise* operators `&`, `|`, `~` (which *are* overloadable via `__and__`, `__or__`, `__invert__`) — and why you must wrap operands in parentheses, because `&` binds tighter than `>`:

```python
# RIGHT:
(User.age > 21) & (User.active == True)
```

SQLAlchemy, pandas, and Django all require `&`/`|` for exactly this reason. A subtler defense: override `__bool__` to raise, so `if User.age > 21:` fails loudly instead of silently lying.

### 4. Lambdas with Receiver: Type-Safe Nested Builders

Kotlin's headline DSL feature is the **lambda with receiver**, type `T.() -> Unit`. It is a block whose *implicit `this`* is a `T`. This is the statically-typed cousin of Ruby's `instance_eval` — but with full type checking and IDE autocomplete.

```kotlin
class Html {
    private val children = mutableListOf<String>()
    fun body(init: Body.() -> Unit) {       // takes a Body-receiver lambda
        val b = Body()
        b.init()                            // run block with `b` as `this`
        children += b.render()
    }
    fun render() = "<html>${children.joinToString("")}</html>"
}

class Body {
    private val children = mutableListOf<String>()
    fun p(text: String) { children += "<p>$text</p>" }
    fun render() = "<body>${children.joinToString("")}</body>"
}

fun html(init: Html.() -> Unit): Html {
    val h = Html()
    h.init()
    return h
}

val page = html {           // `this` is an Html here
    body {                  // `this` is a Body inside this block
        p("Hello")          // resolves to Body.p
        p("World")
    }
}
// <html><body><p>Hello</p><p>World</p></body></html>
```

Each `{ ... }` runs with a different receiver, so the call resolves to the right builder *and the compiler checks it*. This is how Kotlin HTML, Gradle's Kotlin DSL, Ktor routing, and (conceptually) Jetpack Compose let you write nested structure that reads like markup yet is fully typed.

### 5. `@DslMarker`: Stop Nesting Bugs

Receiver-lambda nesting has one nasty footgun: inside the inner `body { }`, the *outer* `Html` receiver is still in scope, so you could accidentally call `body { body { ... } }` (the inner `body` resolving to the outer `Html`). Kotlin fixes this with `@DslMarker`:

```kotlin
@DslMarker annotation class HtmlDsl

@HtmlDsl class Html { /* ... */ }
@HtmlDsl class Body { /* ... */ }
```

Now the compiler forbids calling an *outer* receiver's members from an inner scope of the same marker. The bug becomes a compile error. This is a small but important sign of DSL maturity: the language gives you tools to make the DSL safe, not just pretty.

### 6. Other Hosts, Same Ideas (Scala, Groovy)

- **Scala** leans on **implicits** (auto-supplied conversions/parameters), **infix** method calls (`a should be (b)`), and **by-name parameters** (`def whenReady(body: => T)`) so a block runs lazily and possibly multiple times. ScalaTest and Akka config DSLs combine these.
- **Groovy** builders use dynamic `methodMissing`/`propertyMissing` plus closures with a *delegate* (Groovy's receiver). The original Gradle build DSL is a Groovy builder; `MarkupBuilder` generates XML/HTML the same way.

Different syntax, identical mental model: **capture structure or expressions, interpret later.**

---

## Code Examples

### Example 1: A pandas-style mask (operator overloading you already use)

```python
import numpy as np

class Series:
    def __init__(self, data): self.data = np.array(data)
    def __gt__(self, n):  return Series(self.data > n)   # elementwise -> mask
    def __and__(self, o): return Series(self.data & o.data)
    def __getitem__(self, mask): return self.data[mask.data]

price = Series([50, 150, 90, 200])
expensive = price[(price > 100)]      # array([150, 200])
```

This is precisely why pandas requires `df[(df.a > 1) & (df.b < 2)]` with parentheses and `&`: `df.a > 1` is a *mask object*, and Python's `and` would mis-handle it. Same trap, same fix as the query DSL.

### Example 2: A fluent + operator-tree query DSL combined

```python
class Table:
    def __init__(self, name): self.name = name
    def __getattr__(self, col): return Column(f"{self.name}.{col}")

class Query:
    def __init__(self, table): self.table, self._where = table, None
    def where(self, expr):
        self._where = expr
        return self
    def sql(self):
        base = f"SELECT * FROM {self.table.name}"
        if self._where is None: return base, []
        cond, params = to_sql(self._where)
        return f"{base} WHERE {cond}", params

User = Table("users")
q = Query(User).where((User.age > 21) & (User.active == True))
print(q.sql())
# ('SELECT * FROM users WHERE ((users.age > ?) AND (users.active = ?))', [21, True])
```

Two techniques cooperating: **chaining** for the query skeleton, **operator overloading** for the predicate. This division — fluent for structure, operators for expressions — is the SQLAlchemy/jOOQ blueprint.

### Example 3: Kotlin type-safe builder with marker (sketch)

```kotlin
@DslMarker annotation class FormDsl

@FormDsl class Form {
    val fields = mutableListOf<String>()
    fun text(name: String, init: Field.() -> Unit = {}) {
        val f = Field(name, "text"); f.init(); fields += f.render()
    }
    fun render() = "<form>${fields.joinToString("")}</form>"
}

@FormDsl class Field(val name: String, val type: String) {
    var required = false
    fun render() = "<input name='$name' type='$type'${if (required) " required" else ""}>"
}

fun form(init: Form.() -> Unit) = Form().apply(init).render()

val html = form {
    text("email") { required = true }
    text("nickname")
}
// <form><input name='email' type='text' required><input name='nickname' type='text'></form>
```

Note `Form().apply(init)`: `apply` is itself a standard-library function taking a receiver-lambda — the same mechanism, used to build the DSL entry point.

### Example 4: Scala-flavored infix matcher (sketch)

```scala
// `result shouldBe 42` reads like a sentence because `shouldBe` is an infix method.
implicit class ShouldOpsA {
  def shouldBe(expected: A): Unit =
    if (actual != expected) throw new AssertionError(s"$actual != $expected")
}

42 shouldBe 42         // infix call, no dots/parens
```

The `implicit class` auto-wraps any value so `actual shouldBe expected` compiles. This is ScalaTest's readability engine in miniature: implicits + infix.

---

## Coding Patterns

**Pattern: overloaded operator returns a node, never a value.** Comparison/arithmetic operators in an expression DSL construct tree nodes. Keep them pure and side-effect free.

**Pattern: two-phase split — build then interpret.** Phase one (overloading/receivers) builds a tree; phase two (a walker) interprets it. Keep them in separate functions/classes so each is testable alone.

**Pattern: parameterize literals on the interpret side.** When compiling to SQL, emit `?` placeholders and collect bound params — never string-interpolate user values. The DSL becomes an injection-prevention boundary.

**Pattern: guard boolean coercion.** Override `__bool__` to raise in Python expression DSLs so `if expr:` fails loudly. Require `&`/`|` and document it.

**Pattern: one builder type per nesting level (Kotlin).** `Html`, `Body`, `Field` — each level gets its own receiver type, marked with the same `@DslMarker`, so calls resolve correctly and the IDE guides users.

---

## Best Practices

- **Only overload operators whose domain meaning matches their usual meaning.** `>` for a comparison predicate: good. `+` for "merge two queries": questionable. Surprise is the enemy.
- **Force the safe operators and explain why.** Require `&`/`|` and parentheses; put the boolean-coercion trap in your README. Users *will* hit it otherwise.
- **Make trees inspectable.** Give nodes a readable `__repr__` so a developer can print an expression and see its structure when debugging.
- **Always `@DslMarker` your Kotlin builders.** It costs one annotation and prevents an entire class of silent nesting bugs.
- **Keep receiver builders cheap and throwaway.** They should accumulate and render, not hold long-lived state or perform I/O mid-build.
- **Decide where evaluation happens and make it obvious.** A clear terminal step (`.sql()`, `render()`, `build()`) signals "the tree is done; now we interpret it."

---

## Edge Cases & Pitfalls

- **`and`/`or`/`if` on expression objects (Python).** They coerce to bool and silently drop logic. Use `&`/`|`/`~`, parenthesize, and consider raising from `__bool__`.
- **Operator precedence surprises.** `&` binds tighter than `>`, so `a > 1 & b` parses as `a > (1 & b)`. Always parenthesize each predicate.
- **`__eq__` overload breaks hashing/sets.** If `Column.__eq__` returns a node (not a bool), the object is no longer usable as a dict key or in a set unless you also handle `__hash__`. Be deliberate.
- **NaN and three-valued logic leak in.** Dataframe/SQL comparisons with nulls/NaN do not behave like Python booleans; the DSL inherits the domain's logic, surprising users who expect Python semantics.
- **Receiver shadowing without `@DslMarker`.** Inner blocks can call outer-receiver methods, producing structurally wrong output with no error. Mark every builder.
- **Receiver-lambda capture leaks.** A `Html.() -> Unit` block can close over outer variables and mutate them; long-lived builders that retain such lambdas can leak memory or state.
- **Stringly-typed escape hatches.** When the operator DSL cannot express something (a weird SQL function), users drop to raw strings — reopening the injection hole the DSL was meant to close. Provide a safe, parameterized escape hatch.
- **Over-overloading.** A DSL that redefines ten operators with clever meanings becomes write-only. Restraint reads better than cleverness.

---

## Apply it

1. Find a real component where **DSLs via Metaprogramming** affects an interface or dependency.
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

- Which boundary is most affected by DSLs via Metaprogramming?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
