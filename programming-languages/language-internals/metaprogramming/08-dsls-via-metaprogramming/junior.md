# DSLs via Metaprogramming — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **DSLs via Metaprogramming** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A DSL Lets Code *Describe* Instead of *Instruct*

Ordinary code tells the computer **how** to do something, step by step. A DSL lets you state **what** you want and leaves the *how* to the library. Compare describing a web route with plain instructions versus with a routing DSL:

Plain, imperative:

```python
router = Router()
route = Route()
route.method = "GET"
route.path = "/users/:id"
route.handler = show_user
router.routes.append(route)
```

DSL-flavored:

```python
router.get("/users/:id", show_user)
```

Both do the same thing. The second one **reads like the domain** — "GET this path, run this handler" — and hides the bookkeeping. That is the entire point of a DSL: make the *intent* obvious and the *mechanics* invisible.

### 2. Method Chaining: Each Call Returns Something to Call Again

The simplest DSL technique is **method chaining**, also called a **fluent interface**. The trick is almost embarrassingly small: **make each method return an object** (usually `self`/`this`, or a new object) so you can immediately call the next method on the result.

```python
class Query:
    def __init__(self):
        self._table = None
        self._conditions = []
        self._limit = None

    def from_(self, table):
        self._table = table
        return self            # <-- the whole trick: hand back self

    def where(self, condition):
        self._conditions.append(condition)
        return self            # <-- so the next .method() has something to chain onto

    def limit(self, n):
        self._limit = n
        return self

    def build(self):
        sql = f"SELECT * FROM {self._table}"
        if self._conditions:
            sql += " WHERE " + " AND ".join(self._conditions)
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        return sql
```

Now you can write:

```python
sql = Query().from_("users").where("active = true").limit(10).build()
# SELECT * FROM users WHERE active = true LIMIT 10
```

Each method does its small job, mutates the builder, and **returns `self`**. Because it returns `self`, the next method has an object to attach to. Remove the `return self` lines and the chain breaks instantly — the second call would be on `None`.

This shape — accumulate across chained calls, then produce a result with a final method — is the **builder pattern**, and it is the backbone of countless DSLs.

### 3. Blocks and Closures: Hand the Library a Chunk of Code

The second technique is to pass a **block** of code — a closure — that the library runs in a context it controls. This is how you get the `do ... end` style configuration you see everywhere.

In Python you pass a function:

```python
def configure_routes(setup):
    router = Router()
    setup(router)        # run the caller's block, giving it the router
    return router

app = configure_routes(lambda r: (
    r.get("/", home),
    r.get("/about", about),
))
```

Ruby makes this beautiful because blocks are part of the syntax:

```ruby
routes.draw do
  get "/",      to: "home#index"
  get "/about", to: "pages#about"
end
```

`routes.draw` takes the `do ... end` block and runs it. Inside the block you call `get`, and the library wires everything up. You wrote something that reads like a *list of routes*, not like object construction. That is a DSL, and the engine is just **"the library runs a block you handed it."**

### 4. Internal vs External — Know Which One You Are Looking At

The fastest way to tell them apart: **ask who reads the text.**

- If your tool's own parser reads a `.sql` file, a regex string, or a config grammar → **external DSL**. Someone wrote a lexer and parser.
- If the *host language's* parser reads it because it is valid Python/Ruby/Kotlin → **internal DSL**. The "language" is an illusion created by good API design plus metaprogramming.

`User.age > 21` looks like a query expression but is internal — Python parses it; a library decides what `>` *means* (that is operator overloading, covered in `middle.md`). `SELECT * FROM users` is external — a SQL parser reads it. This page lives entirely in the internal world.

### 5. The Honest Cost: Now You Have Two Languages

A DSL is not free. When you build one, the people using it must learn it **on top of** the host language. When it breaks, the error messages often talk about the *implementation* (`NoneType has no attribute 'where'`) instead of the *domain* ("you called `.where()` before `.from_()`"). That is the **"now you have two languages"** problem, and it is the single most common reason a DSL ends up worse than a plain function. The whole rest of this topic is, in part, about earning your DSL's keep.

---

## Code Examples

### Example 1: A fluent query builder (Python)

```python
class Query:
    def __init__(self):
        self._table = None
        self._cols = ["*"]
        self._where = []

    def select(self, *cols):
        self._cols = list(cols) or ["*"]
        return self

    def from_(self, table):
        self._table = table
        return self

    def where(self, cond):
        self._where.append(cond)
        return self

    def sql(self):
        if self._table is None:
            raise ValueError("from_() is required before sql()")
        cols = ", ".join(self._cols)
        q = f"SELECT {cols} FROM {self._table}"
        if self._where:
            q += " WHERE " + " AND ".join(self._where)
        return q

print(
    Query()
    .select("id", "name")
    .from_("users")
    .where("active = true")
    .where("age >= 21")
    .sql()
)
# SELECT id, name FROM users WHERE active = true AND age >= 21
```

Notice how the call site reads top-to-bottom like a query. Notice also the small bit of *good error design*: calling `.sql()` without `.from_()` raises a message in **domain terms** ("from_() is required"), not a `NoneType` crash. That courtesy is what separates a usable DSL from a frustrating one.

### Example 2: A configuration block (Python, passing a function)

```python
class Server:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 8080
        self.routes = []

    def route(self, path, handler):
        self.routes.append((path, handler))

def server(configure):
    s = Server()
    configure(s)         # run the caller's block against a fresh Server
    return s

def home():  ...
def about(): ...

app = server(lambda s: (
    setattr(s, "port", 9000),
    s.route("/", home),
    s.route("/about", about),
))

print(app.port, app.routes)   # 9000 [('/', <fn>), ('/about', <fn>)]
```

Python's lambda is clumsy for multi-line config (you need the tuple trick), which is exactly *why* languages like Ruby and Kotlin invented nicer block syntax — a motivation `middle.md` builds on.

### Example 3: The same idea in Ruby, where blocks are first-class syntax

```ruby
class Server
  attr_accessor :port
  def initialize
    @port = 8080
    @routes = []
  end

  def route(path, &handler)
    @routes << [path, handler]
  end
end

def server(&block)
  s = Server.new
  s.instance_eval(&block)   # run the block *as if* its body were inside `s`
  s
end

app = server do
  self.port = 9000
  route("/")      { "home"  }
  route("/about") { "about" }
end
```

`instance_eval` runs the block with `self` set to the `Server`, so inside `do ... end` you can call `route(...)` and assign `self.port` directly — no `s.` prefix. This is *the* classic Ruby DSL trick and powers RSpec, Rake, and Rails routing. You do not need to master it now; just recognize the shape: **"the library runs my block inside an object it controls."**

### Example 4: A tiny test DSL (Python) so you see the pattern beyond queries

```python
class Suite:
    def __init__(self, name):
        self.name = name
        self.cases = []

    def it(self, description, body):
        self.cases.append((description, body))

    def run(self):
        print(f"# {self.name}")
        for desc, body in self.cases:
            try:
                body()
                print(f"  ok - {desc}")
            except AssertionError as e:
                print(f"  FAIL - {desc}: {e}")

def describe(name, define):
    s = Suite(name)
    define(s)
    s.run()

describe("addition", lambda s: (
    s.it("adds positives",  lambda: (_ := (2 + 2)) and (None if 2 + 2 == 4 else (_ for _ in ()).throw(AssertionError("nope")))),
    s.it("is commutative", lambda: None if 1 + 2 == 2 + 1 else (_ for _ in ()).throw(AssertionError("nope"))),
))
```

The lambda gymnastics above are deliberately ugly — they show the *limit* of Python for this style. In Ruby the same test DSL is clean:

```ruby
describe "addition" do
  it "adds positives" do
    raise "nope" unless 2 + 2 == 4
  end
end
```

This is RSpec's exact shape. The lesson: **the host language's syntax decides how pretty your DSL can be.** Picking the right technique for the right host is the craft we develop across the next tiers.

---

## Coding Patterns

**Pattern: return `self` for every chainable step.** Every method meant to be chained ends with `return self`. Methods that *finish* the chain (`.build()`, `.sql()`, `.run()`) return the finished product instead.

```python
def where(self, cond):
    self._where.append(cond)
    return self          # chainable

def build(self):
    return self._materialize()   # terminal: returns the product, not self
```

**Pattern: separate "configure" from "produce."** Accumulate state during the chain; do the real work only in the terminal method. Side effects mid-chain (writing to a DB inside `.where()`) make DSLs surprising and hard to test.

**Pattern: validate at the terminal step with domain-language errors.** Check required fields in `.build()` and raise messages a *user of the DSL* understands.

```python
def build(self):
    if self._table is None:
        raise ValueError("call .from_(table) before .build()")
    ...
```

**Pattern: a block receives the thing it configures.** Whether you pass a lambda (Python), a `&block` (Ruby), or a lambda-with-receiver (Kotlin, in `middle.md`), the consistent shape is *"library makes the object, runs your block against it, returns it."*

---

## Best Practices

- **Make it read like the domain, out loud.** If `query.select().from_("users").where(...)` reads like a sentence, you are on track. If it reads like setters, keep refining names.
- **Prefer a plain function until a DSL clearly earns its place.** Three chained calls are not yet a DSL; if a normal function is just as clear, ship the function.
- **Fail in the user's vocabulary.** Spend effort on error messages that name domain mistakes, not implementation crashes. This is the difference between a DSL people tolerate and one they like.
- **Keep the terminal step explicit.** A clear `.build()` / `.sql()` / `.run()` tells the reader "the chain ends here, now the work happens." Implicit, magic finalization confuses people.
- **Do not hide *too* much.** A DSL that conceals important behavior (silent retries, hidden network calls) trades readability for surprise. Hide plumbing, not consequences.
- **Document the chain order if it matters.** If `.from_()` must precede `.where()`, say so — and ideally enforce it with errors.

---

## Edge Cases & Pitfalls

- **Forgetting `return self`.** The most common beginner bug. The chain dies with `AttributeError: 'NoneType' object has no attribute 'where'`. Always return `self` from chainable methods.
- **Mutating shared builder state.** If `Query()` is created once and reused, chained calls accumulate across uses. Builders should be cheap and one-shot, or explicitly cloned.
- **Order-dependent chains with no guardrails.** If calling methods out of order silently produces wrong output (rather than a clear error), users will be bitten quietly. Validate.
- **Errors that leak the implementation.** `NoneType has no attribute` is the canonical leak. Catch the likely mistakes and re-raise in domain terms.
- **Side effects mid-chain.** A `.where()` that runs a query is astonishing. Keep the chain pure; do work in the terminal step.
- **Reaching for a DSL too early.** If you find yourself building a builder for something called twice, stop. A function is fine. DSLs pay off at scale and for readability, not for two call sites.
- **Python's weak block syntax.** Python lambdas are single-expression; multi-statement config blocks get ugly fast. Recognize this as a host-language limit, not a personal failing — and reach for a different technique or host when it bites.

---

## Apply it

1. Choose one small, known input for **DSLs via Metaprogramming**.
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

- What problem does DSLs via Metaprogramming solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
