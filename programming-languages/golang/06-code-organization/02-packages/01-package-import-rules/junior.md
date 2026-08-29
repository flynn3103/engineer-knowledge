# Package Import Rules — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Package Import Rules** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### Imports are by *path*, not by *name*

When you write:

```go
import "fmt"
```

Go does **not** search for "a package called fmt." It looks up the *import path* `fmt` in its known locations (the standard library, the module cache). Once it finds the source files, it reads the `package <name>` declaration inside them — and *that* is the name you use in your code.

For the standard library, path and name happen to match (`fmt` is the path, `fmt` is the name). For third-party code, they almost always match by convention. But they do not have to match, and a few important packages exploit this. Always remember:

- The **path** (`"github.com/x/y/y"`) tells Go *where to find the bytes*.
- The **name** (`y` or whatever the source declares) tells you *what to write in code*.

### The package name is whatever the source files say it is

Every `.go` file in a package starts with `package <name>`. That name is the only name you can use to refer to the package's exports — unless you alias it. The convention (almost universally followed) is that the name matches the last segment of the import path. So `net/http` → `http`. So `github.com/alice/cool/greet` → `greet`.

The notable exceptions you will meet early:

- `gopkg.in/yaml.v3` → package name `yaml` (the version suffix `v3` is path-only).
- `golang.org/x/sync/errgroup` → package name `errgroup`.
- `github.com/jackc/pgx/v5/pgxpool` → package name `pgxpool` (the `v5` is path-only).

When in doubt, open the source. The first non-comment line of any `.go` file in the package tells you the name.

### `import` is per file, not per package

Every `.go` file has its own `import` block. If two files in the same package both need `fmt`, both files import `fmt`. There is no shared "imports for this package." Imports are file-local.

### You can alias an import

```go
import foo "github.com/alice/another-foo"

foo.Bar()
```

Reasons to alias:

- **Two packages collide.** You import `crypto/rand` and `math/rand`; one of them must be aliased.
- **The package's natural name is awkward.** Some legacy packages have ugly names; an alias makes call sites readable.
- **Disambiguation in tests.** `import myfoo "..."` clarifies which `foo` you mean when test fixtures are involved.

Aliasing is **local to the file**. It does not rename the package globally; another file in the same package can give it a different alias or use no alias at all.

### Blank imports run `init()` for side effects

```go
import _ "github.com/lib/pq"
```

You are not going to call any function named `pq.Something`. You are saying: "I want this package's `init()` to run." The classic example is database drivers: importing `github.com/lib/pq` registers the `postgres` driver with `database/sql`, after which you can call `sql.Open("postgres", ...)`.

Blank imports are the *only* way to use a package solely for side effects without the compiler complaining about an unused import.

### Dot imports merge the namespace

```go
import . "fmt"

Println("hello")
```

This works. It is also **strongly discouraged** outside test files because it makes call sites unreadable — readers cannot tell at a glance which package an identifier came from. The two acceptable contexts are:

- **Inside `_test.go` files** that test the package itself, where dot-importing helper packages is sometimes idiomatic.
- **DSL-style libraries** that explicitly invite this style (rare; the Ginkgo testing framework is the famous example).

In all other contexts: do not use dot imports.

### `internal/` enforces visibility by path

A directory named `internal/` anywhere in your module creates a visibility boundary. Code under `internal/` can only be imported by code rooted at the *parent* of that `internal/` directory. The Go compiler enforces this — it is not a convention, it is a rule.

```
github.com/alice/cool/
├── go.mod
├── main.go                       <-- can import internal/db
├── cmd/
│   └── server/main.go            <-- can import internal/db
├── internal/
│   └── db/db.go                  <-- restricted package
└── pkg/
    └── public/public.go          <-- can import internal/db
```

But `github.com/bob/anothertool` *cannot* import `github.com/alice/cool/internal/db`. The toolchain refuses.

### Cyclic imports are forbidden

If A imports B, B cannot import A — directly or transitively. Go compiles each package once, and a cycle would mean neither can be compiled first. The compiler stops you with a clear error. The fix is always either (a) break the dependency by extracting a common type into a third package, or (b) merge the two packages.

### `init()` runs once per package, depth-first

When you import a package, all packages it imports are initialised first, recursively. Each package's variable initialisers run, then each `init()` function runs (in source-file alphabetical order, then declaration order within a file). Then your package initialises. By the time `main` runs, every reachable package's `init()` has fired exactly once.

### `goimports` groups imports

`gofmt` only reorders within groups and won't *create* groups. `goimports` does both. The convention it implements:

```go
import (
    "fmt"           // group 1: standard library
    "net/http"
    "os"

    "github.com/alice/cool/greet"  // group 2: everything else
    "github.com/lib/pq"
)
```

Some projects use three groups (stdlib / module-internal / external), but the two-group convention is dominant. Configure your editor to run `goimports` on save and you stop thinking about it.

---

## Code Examples

### Example 1 — Importing the standard library

```go
package main

import "fmt"

func main() {
    fmt.Println("hello, world")
}
```

`"fmt"` is the import path. `fmt` is the package name. They match by convention.

### Example 2 — Importing your own sub-package

Module: `github.com/alice/cool` with this layout:

```
cool/
├── go.mod                  (module github.com/alice/cool)
├── main.go
└── greet/
    └── greet.go
```

`greet/greet.go`:

```go
package greet

import "fmt"

func Hello(name string) {
    fmt.Println("hello,", name)
}
```

`main.go`:

```go
package main

import "github.com/alice/cool/greet"

func main() {
    greet.Hello("Alice")
}
```

The import path is `<module path>/<sub-folder>`. The package name `greet` is what `greet.go` declares.

### Example 3 — Importing a third-party package

After `go get github.com/google/uuid`:

```go
package main

import (
    "fmt"

    "github.com/google/uuid"
)

func main() {
    fmt.Println(uuid.New())
}
```

Two import groups separated by a blank line: stdlib first, then third-party. `goimports` produces this layout automatically.

### Example 4 — Aliasing to resolve a collision

```go
package main

import (
    "fmt"
    crand "crypto/rand"
    mrand "math/rand"
)

func main() {
    _ = crand.Reader
    fmt.Println(mrand.Intn(100))
}
```

Without the aliases, both packages declare `rand` and the compiler refuses. Aliasing renames them locally.

### Example 5 — Aliasing a long or awkward path

```go
import (
    pq "github.com/jackc/pgx/v5/pgxpool"
)

func use(p *pq.Pool) { /* ... */ }
```

Here the package name is already `pgxpool`, but the developer wanted a shorter alias. Use sparingly — the original name is usually clearer.

### Example 6 — Blank import for a SQL driver

```go
package main

import (
    "database/sql"

    _ "github.com/lib/pq"
)

func main() {
    db, err := sql.Open("postgres", "postgres://localhost/mydb")
    _ = db
    _ = err
}
```

The blank import is **required**. Without it, `pq.init()` never runs, the `"postgres"` driver is never registered, and `sql.Open("postgres", ...)` returns "unknown driver" at runtime.

### Example 7 — Dot import (in a test, where it is acceptable)

`mypkg/example_test.go`:

```go
package mypkg_test

import (
    . "github.com/alice/cool/mypkg"
    "testing"
)

func TestStuff(t *testing.T) {
    if Greet("a") != "hello, a" {
        t.Fail()
    }
}
```

The dot import lets the test file write `Greet` instead of `mypkg.Greet`. This is one of the few places it is idiomatic.

### Example 8 — A failed cyclic import

`a/a.go`:

```go
package a

import "github.com/alice/cool/b"

func A() { b.B() }
```

`b/b.go`:

```go
package b

import "github.com/alice/cool/a"

func B() { a.A() }
```

`go build`:

```
import cycle not allowed
package github.com/alice/cool/a
        imports github.com/alice/cool/b
        imports github.com/alice/cool/a
```

Fix: extract the shared type or interface into a third package, e.g. `c`, that both `a` and `b` import.

### Example 9 — A failed `internal/` import

`github.com/alice/cool/internal/db/db.go`:

```go
package db

func Query() string { return "data" }
```

In a *different* module, `github.com/bob/tool/main.go`:

```go
package main

import "github.com/alice/cool/internal/db"

func main() { _ = db.Query() }
```

`go build`:

```
use of internal package github.com/alice/cool/internal/db not allowed
```

The compiler rejects it because Bob's module is not rooted at `github.com/alice/cool`. Inside Alice's module, the same import works fine.

---

## Coding Patterns

### Pattern: Group imports stdlib-then-third-party

```go
import (
    "context"
    "fmt"
    "net/http"

    "github.com/google/uuid"
    "go.uber.org/zap"
)
```

Single blank line between groups. Run `goimports` on save and stop thinking about it.

### Pattern: Alias only when forced

Aliases are noise. Only alias when you must:

- Two packages share a name.
- The name conflicts with a local identifier.
- A test renames its subject for clarity.

If you find yourself aliasing for aesthetics, stop. The reader has to look up the alias.

### Pattern: Blank-import drivers in `main`, not in libraries

```go
// cmd/server/main.go  -- OK to blank-import here
package main

import (
    _ "github.com/lib/pq"
)
```

```go
// internal/db/db.go   -- AVOID blank imports here
```

A library that blank-imports a driver forces every consumer to take that dependency, even if they want a different driver. Keep driver registration at the application's entry point.

### Pattern: One sub-package per cohesive concern

If two sub-packages keep wanting to import each other, they probably want to be one package. Or they want a third package to share what they have in common. Either is fine; the cycle is the symptom that the design is not.

### Pattern: Hide internals under `internal/`

When a package is "implementation only, do not import from outside," put it under `internal/`. The compiler will police the boundary for you.

```
mymodule/
├── go.mod
├── api/             <-- public; importable by anyone
└── internal/
    └── secret/      <-- private; only mymodule can import
```

---

## Clean Code

- **No dot imports outside tests.** Ever.
- **Imports follow the canonical order.** stdlib, blank line, everything else. Let `goimports` enforce it.
- **No unused imports.** The compiler enforces this; do not silence it with blank imports just to "keep things in scope."
- **No commented-out imports.** Delete them. Git remembers.
- **Aliases are short, lowercase, and meaningful.** `pq` for `lib/pq`, not `Postgres_DB_Driver`.
- **Order long import lists alphabetically within each group.** `goimports` does this.
- **Prefer the shortest unambiguous import path.** Don't mix `gopkg.in/yaml.v3` and `gopkg.in/yaml.v2` in the same file unless you really mean to.

A clean import block is short, sorted, grouped, and silent — readers should not have to think about it.

---

## Error Handling

The compiler handles most import-related errors at build time. The messages you will see, and how to fix them:

### `imported and not used: "fmt"`

You added an import but never called any function from it. Fix: delete the import, or actually use it. If you genuinely need only the side effects, change to `_ "fmt"` (rare for stdlib).

### `undefined: somepkg`

You used `somepkg.Thing` but did not import the package. Fix: add the import, or correct the name.

### `import cycle not allowed`

A and B import each other. Fix: extract shared types into a third package, or merge.

### `use of internal package ... not allowed`

You tried to import an `internal/` package from outside its allowed subtree. Fix: move your code under the subtree, or ask the upstream maintainer to expose a public version of what you need.

### `package <name> is not in std (...)`

You wrote a typo or an unfound path. Fix: spell-check; run `go mod tidy`; verify the module is in `go.mod`.

### `cannot find package "..." in any of: ...`

The toolchain looked in known places and did not find the path. Fix: run `go mod tidy`, or add the dependency with `go get`.

### `redeclared in this block` after aliasing

Your alias collides with a local identifier. Fix: pick a different alias.

### Errors at runtime: `unknown driver "postgres"`

You forgot the blank import for `lib/pq`. Add `_ "github.com/lib/pq"` to your `main` package.

---

## Security Considerations

- **Blank imports run code at startup.** A blank-imported package's `init()` can do *anything*: open files, dial network, mutate global state. Audit what you blank-import. Never blank-import a package you have not vetted.
- **`internal/` is your enforcement boundary.** Put security-sensitive code (token signing, password hashing, raw secrets) under `internal/` so accidental external imports are impossible.
- **Typosquatting via paths.** `github.com/golamg/...` looks like `golang/...`. Always copy-paste import paths from the upstream README; never type third-party paths from memory.
- **Dot imports hide call sites.** A malicious dependency could shadow a stdlib name. Avoiding dot imports avoids this attack surface.
- **Aliases obscure dependencies.** A reviewer skimming for "what does this code call?" might miss a dependency hidden behind a creative alias. Prefer no alias when not needed.
- **Diamond dependencies amplify supply chain risk.** Your import + transitive imports = your real attack surface. Audit `go list -m all`, not just your direct imports.

---

## Performance Tips

- Imports themselves cost nothing at runtime — they are resolved at compile time. There is no `import` instruction in the binary.
- A package's `init()` runs once at program start. Heavy initialisation in an imported package's `init()` slows your startup. Profile cold starts if startup time matters (CLIs, serverless).
- Blank imports still run `init()`. If a package does network work in `init()`, blank-importing it makes your binary do that work too.
- More imports → larger binary. The Go linker is smart but cannot eliminate functions you have, in principle, made reachable. If binary size matters, audit imports.
- Cyclic-dependency hunting tools (`gomod-graph`, `goda`) can be slow on large modules; run them in CI, not on every save.

For most code, none of this matters — imports are essentially free.

---

## Best Practices

1. **Run `goimports` on save.** It groups, sorts, removes unused, and adds missing imports. Eliminates import-related code review nits.
2. **Match package name to last path segment.** Make life easy for readers.
3. **Alias only on collision or for clarity.** Aliases are noise; minimise.
4. **Never use dot imports outside tests.** Even in tests, prefer not to.
5. **Blank-import drivers in `main`, not in libraries.** Pushes the dependency choice to the application.
6. **Put unstable APIs under `internal/`.** Nothing prevents future breakage like preventing future imports.
7. **Resolve cycles by extracting common types.** Do not try to plaster over them with interfaces in the wrong package.
8. **Keep imports alphabetised within each group.** `goimports` does this; trust it.
9. **One blank line between import groups.** Two blank lines is wrong; zero is wrong.
10. **Read the package source when in doubt about the package name.** First non-comment line tells you.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Path looks right, name is different

```go
import "gopkg.in/yaml.v3"

yaml.v3.Marshal(...)   // ERROR: undefined yaml.v3
yaml.Marshal(...)      // CORRECT
```

The `v3` is part of the path, not part of the name. Always check the actual `package` declaration in the source.

### Pitfall 2 — `internal/` near the module root vs. deep

A package at `mymodule/internal/foo` is importable by every package in `mymodule`. A package at `mymodule/sub/internal/foo` is only importable by packages under `mymodule/sub/`. Where you put `internal/` controls who can see it.

### Pitfall 3 — Cycle through transitive imports

A cycle is forbidden even if it is not direct. A → B → C → A is a cycle just as much as A → A. Tools like `goda graph` help visualise this.

### Pitfall 4 — `init()` runs even for blank imports

Blank imports are not "passive." They run code. If a blank-imported package has a slow or failing `init()`, your program is affected.

### Pitfall 5 — Two packages in the same folder

You cannot have two `package` declarations in the same directory (with one exception: an `_test.go` file can declare `package foo_test`). Mismatched package names in one folder produce: `found packages foo (a.go) and bar (b.go)`.

### Pitfall 6 — Capital-letter modules and case sensitivity

`github.com/Alice/Repo` and `github.com/alice/repo` are different paths to the Go proxy, even though Git often treats them the same. Stick to lowercase.

### Pitfall 7 — Blank-importing a package twice

Harmless — `init()` only runs once per package per build. But it suggests you have not consolidated your imports.

### Pitfall 8 — Editor adds an unwanted alias

Some editors auto-alias when they think there is a collision. Check the import block before committing — a stray alias can confuse reviewers.

### Pitfall 9 — Test-only imports leak into production

If you import a testing helper from a non-`_test.go` file, you have just made your test framework a runtime dependency of your binary. Keep test-only imports inside `_test.go` files.

### Pitfall 10 — Aliasing the package to its own name

```go
import http "net/http"   // legal but pointless
```

The alias is the same as the default name. Some linters flag this. Just use `import "net/http"`.

---

## Common Mistakes

- **Importing by guessing.** Don't write `import "uuid"` and hope. Look up the real path.
- **Confusing package name with path.** Trying to call `gopkg.in.yaml.v3.Marshal` instead of `yaml.Marshal`.
- **Using `_` to silence "imported and not used" temporarily.** It "works" but loses you the compiler's safety. Either use the package or remove the import.
- **Trying to import a sub-folder by relative path.** `import "./sub"` does not work. Use the full path: `import "github.com/me/mod/sub"`.
- **Putting all packages under `internal/` "to be safe."** That kills reusability. `internal/` is for things that genuinely should not be public.
- **Adding an alias because the call site reads better.** It rarely does. Aliases are needed, not preferred.
- **Forgetting the blank line between import groups.** `goimports` would fix it; review tools complain about it.
- **Forgetting the blank import for SQL drivers.** Then debugging `sql: unknown driver "postgres"` for an hour.
- **Trying to break a cycle by adding interfaces in one of the cycling packages.** Move the interface to a third package; placing it in either of the original two does not fix the cycle.

---

## Common Misconceptions

> *"The package name is the last segment of the import path."*

By convention, yes. By rule, no. The package name is whatever the source files say. Convention covers 95% of cases; check the source for the rest.

> *"Imports work by relative path."*

They never do. There is no `import "./foo"`, no `import "../bar"`. Every import is a full, canonical path.

> *"`internal/` is just a naming convention."*

It is a *compiler-enforced rule*. The build literally fails if you violate it.

> *"Blank imports do nothing."*

They run `init()`. They can register drivers, allocate state, dial networks. They are anything but inert.

> *"Dot imports save typing and are therefore good."*

They save typing and destroy readability. Outside tests, they are universally discouraged.

> *"An import cycle can be fixed by aliasing."*

No. Aliasing renames; it does not break the dependency. The fix is structural — extract or merge.

> *"Tests are part of the package and so use the package's imports."*

A test file in `package foo` shares the package and its imports. A test file in `package foo_test` is a *separate* package and has its own imports — including, often, a non-blank import of `foo` itself.

> *"`goimports` and `gofmt` are interchangeable."*

`goimports` is `gofmt` plus import-list management. Use `goimports`.

---

## Tricky Points

- **Aliasing scope is per file.** `import foo "x"` in `a.go` does not let `b.go` (same package) write `foo.Bar` — `b.go` would still write `x.Bar` (or its own alias).
- **`init()` order across packages is determined by the import graph.** Within a package, `init()` order is determined by source-file alphabetical order, then declaration order in each file. Do not rely on this for correctness; use explicit ordering.
- **You can have multiple `init()` functions per file.** They run top-to-bottom. Most code has zero or one.
- **A blank import of a package that has *no* `init()` and no package-level vars with side effects does literally nothing.** The compiler still verifies the package compiles, but nothing runs.
- **Test imports are evaluated lazily.** A test-only dependency is not in your release binary. Run `go list -test -deps .` to see test-only imports.
- **`internal/` only applies inside modules.** A folder named `internal/` outside a Go module is just a folder — there is no rule to enforce.
- **Two packages with the same name from different paths can both be imported in one file** — *if* you alias one of them. They are different packages; only their default names collide.
- **`goimports` chooses imports for unresolved identifiers.** If you write `uuid.New()` without an import, `goimports` may add `github.com/google/uuid` *or* `github.com/satori/go.uuid` — based on what is in your module cache and `go.mod`. Always check what was added.

---

## Apply it

1. Choose one small, known input for **Package Import Rules**.
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

- What problem does Package Import Rules solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
