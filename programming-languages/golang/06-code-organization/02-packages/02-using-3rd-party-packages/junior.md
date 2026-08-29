# Using Third-Party Packages — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Using Third-Party Packages** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### `go get` is the verb for "change my dependencies"

There are exactly four things `go get` does:

1. **Add** a new dependency: `go get github.com/google/uuid`
2. **Upgrade** an existing dependency: `go get github.com/google/uuid@latest`
3. **Pin** to a specific version: `go get github.com/google/uuid@v1.3.0`
4. **Remove** a dependency: `go get github.com/google/uuid@none` (or delete the import and run `go mod tidy`)

That is the whole API. Every other dependency change is a variation on these four.

### Three things change when you run `go get pkg`

1. **The module cache** under `~/go/pkg/mod/...` gets a frozen, read-only copy of the version.
2. **`go.mod`** gains (or updates) a `require` line: `require github.com/google/uuid v1.6.0`.
3. **`go.sum`** gains cryptographic hashes proving "the bytes I built against were exactly these bytes."

Commit `go.mod` and `go.sum` to git. The cache is local to your machine and is regenerated on demand.

### Importing is independent from `go get`

You can write `import "github.com/google/uuid"` in your source file *first*, then run `go mod tidy` — Go figures out which version you need, downloads it, and updates `go.mod` and `go.sum` for you. Many engineers prefer this workflow over remembering `go get` flags.

`go get pkg` and `go mod tidy` are two roads to the same place. Both are fine.

### Semantic versioning expectations

Library authors who use semver promise:

- **Patch bumps** (`v1.2.3` to `v1.2.4`) — bug fixes only. Safe to upgrade.
- **Minor bumps** (`v1.2.3` to `v1.3.0`) — new features, no breaking changes. Safe to upgrade.
- **Major bumps** (`v1.x.x` to `v2.x.x`) — breaking changes. Read the changelog before upgrading.

In Go, a major version bump above 1 also changes the **import path**. `v2` of a library at `github.com/foo/bar` is imported as `github.com/foo/bar/v2`. This is unusual and protects you from accidentally pulling breaking changes.

### `pkg.go.dev` is your map

For any third-party package, the page at `https://pkg.go.dev/<import path>` shows:

- The package's documentation, generated from comments in the source.
- The list of functions, types, and constants.
- Example code blocks (often runnable in the browser).
- A list of tagged versions.
- A "Imported By" count — a rough popularity signal.
- Links to the source repository, license, and README.

If you cannot find a package on `pkg.go.dev`, it either does not exist or has a typo in its import path.

---

## Code Examples

### Example 1 — Adding `uuid` and using it

```bash
go get github.com/google/uuid
```

`go.mod` after the command:

```
module example.com/myapp

go 1.22

require github.com/google/uuid v1.6.0
```

`go.sum` (excerpt):

```
github.com/google/uuid v1.6.0 h1:NIvaJDMOsjHA8n1jAhLSgzrAzy1Hgr+hNrb57e+94F0=
github.com/google/uuid v1.6.0/go.mod h1:TIyPZe4MgqvfeYDBFedMoGGpEw/LqOeaOT+nhxU+yHo=
```

Source `main.go`:

```go
package main

import (
    "fmt"

    "github.com/google/uuid"
)

func main() {
    id := uuid.New()
    fmt.Println(id)
}
```

Run it:

```bash
go run .
# 7c4e9b00-4c10-4c2c-8a7e-2cbd0f3a9b21
```

That is the full workflow. One `go get`, one `import`, one function call.

### Example 2 — Pinning to a specific version

```bash
go get github.com/google/uuid@v1.3.0
```

`go.mod`:

```
require github.com/google/uuid v1.3.0
```

You just downgraded (or pinned). Run `go build` to verify nothing breaks.

### Example 3 — Pinning to a commit hash

If a fix is on `main` but not yet released, you can pin to a commit:

```bash
go get github.com/google/uuid@abcdef123456
```

`go.mod` will show a pseudo-version:

```
require github.com/google/uuid v1.6.1-0.20240101120000-abcdef123456
```

Use this sparingly. Pseudo-versions are awkward to reason about and signal "I am ahead of the latest tag."

### Example 4 — Pinning to a branch

```bash
go get github.com/google/uuid@main
```

This resolves to the latest commit on the `main` branch and produces a pseudo-version. Avoid in production — branches move under your feet.

### Example 5 — Upgrading to the latest

```bash
go get github.com/google/uuid@latest
```

Equivalent to `go get -u github.com/google/uuid` for that one package. Updates `go.mod` to whatever the highest tagged release is.

### Example 6 — Upgrading everything

```bash
go get -u ./...
```

Upgrade *all* direct dependencies of the current module to their latest minor/patch versions. Run your tests immediately after.

### Example 7 — Listing available updates

```bash
go list -m -u all
```

Output (excerpt):

```
github.com/google/uuid v1.3.0 [v1.6.0]
github.com/spf13/cobra v1.7.0 [v1.8.0]
github.com/stretchr/testify v1.8.4
```

The `[vX.Y.Z]` after the current version is the latest available. Lines without brackets are already up-to-date.

### Example 8 — Removing a dependency

Delete the import statement from your code, then:

```bash
go mod tidy
```

The `require` line and the `go.sum` entries vanish. No special command needed.

Or, explicitly:

```bash
go get github.com/google/uuid@none
```

Both work; `go mod tidy` is the cleaner habit.

### Example 9 — Using `cobra` for a CLI

```bash
go get github.com/spf13/cobra@latest
```

```go
package main

import (
    "fmt"

    "github.com/spf13/cobra"
)

func main() {
    root := &cobra.Command{
        Use:   "hello",
        Short: "Says hello",
        Run: func(cmd *cobra.Command, args []string) {
            fmt.Println("hello, world")
        },
    }
    root.Execute()
}
```

### Example 10 — Postgres driver (`pq`)

```bash
go get github.com/lib/pq
```

```go
import (
    "database/sql"

    _ "github.com/lib/pq" // imported for side effect: register driver
)

db, err := sql.Open("postgres", "postgres://...")
```

The leading underscore is the **blank import** — used purely to register the driver with `database/sql`. It is a common pattern for SQL drivers.

---

## Coding Patterns

### Pattern: Import then tidy

The smoothest workflow for adding a dep:

1. Open your editor.
2. Type the import: `import "github.com/google/uuid"`.
3. Use it: `id := uuid.New()`.
4. Save.
5. From the terminal, run `go mod tidy`.

`go mod tidy` does what `go get` would have done, plus removes any unused requires in the same pass. Many engineers never type `go get` for *adding* — only for upgrading or pinning.

### Pattern: Pin during development, upgrade deliberately

Once you have a stable version, leave it alone. Schedule a "dependency upgrade" task once a month or once a sprint, run `go get -u ./...`, run all tests, fix breakage, and commit. Random mid-feature upgrades are a recipe for confusing bugs.

### Pattern: One commit per dependency change

When you add or upgrade a dependency, commit `go.mod` and `go.sum` together as a separate, focused commit:

```
chore(deps): add github.com/google/uuid@v1.6.0
```

This makes it trivial to bisect or revert.

### Pattern: Read the README before importing

Spend two minutes on the project's README and the first paragraph of `pkg.go.dev` documentation before committing to a library. The cost is two minutes; the savings are hours.

### Pattern: Prefer fewer, larger libraries over many small ones

A single well-maintained library (like `cobra` for CLIs) beats stitching together five tiny helpers. Each dependency is a future migration; minimize the count.

---

## Clean Code

- **Sort imports.** Most editors do this for you. The standard layout is: stdlib block, blank line, third-party block, blank line, local module block.
- **Do not alias imports unless you must.** `import uuid "github.com/google/uuid"` is unnecessary because the package is already called `uuid`. Aliases are for collisions or unreadable package names.
- **Comment the reason for an unusual pin.** If your `require` line is `github.com/foo/bar v1.2.3 // pinned: v1.3 has a memory leak`, future you will be grateful.
- **Keep `go.mod` minimal.** Run `go mod tidy` regularly. An untidy `go.mod` accumulates dead `require` lines.
- **Quote the import path exactly.** Copy-paste from `pkg.go.dev`; do not retype.

---

## Error Handling

`go get` fails in several common ways. Recognize them.

### "module not found"

```
go: github.com/foo/bar: module github.com/foo/bar: not found
```

Cause: typo in the import path, the repo is private and you have no auth, or it does not exist.

Fix: double-check the path on `pkg.go.dev`. For private modules, see middle-level docs.

### "no matching versions"

```
go: github.com/foo/bar@v9.9.9: no matching versions for query "v9.9.9"
```

Cause: the version you typed does not exist.

Fix: check the tags on the project's GitHub releases page or run `go list -m -versions github.com/foo/bar`.

### "ambiguous import"

```
ambiguous import: found package foo in multiple modules
```

Cause: two of your dependencies declare the same import path. Rare but possible with forks.

Fix: pin one of the conflicting modules to a version that does not include the duplicate, or use a `replace` directive (middle topic).

### Network errors during `go get`

```
dial tcp: lookup proxy.golang.org: no such host
```

Cause: no internet, corporate proxy, or `GOPROXY` misconfigured.

Fix: check connectivity. If behind a firewall, set `GOPROXY=direct` or to your company proxy.

### "verifying module: checksum mismatch"

```
verifying github.com/foo/bar@v1.2.3: checksum mismatch
```

Cause: the bytes you downloaded differ from what `go.sum` recorded earlier. Could be a corrupted cache, a tampered mirror, or a maintainer who force-pushed a tag (illegal in semver).

Fix: clear the cache (`go clean -modcache`) and retry. If it persists, do not trust the source.

---

## Security Considerations

- **Every dependency is code that runs.** When you import a library, its `init()` functions execute when your program starts. A malicious library could leak data, mine crypto, or open a backdoor.
- **`go.sum` is your tamper detector.** Never delete it. Commit it. Review changes to it in code review the same way you review changes to `go.mod`.
- **`govulncheck` is the official scanner.** Run it in CI:
  ```bash
  go install golang.org/x/vuln/cmd/govulncheck@latest
  govulncheck ./...
  ```
  It tells you if any of your transitive dependencies have known CVEs *and* whether your code actually calls the vulnerable function.
- **Pin majors carefully.** A `v1.x` dep is auto-bumped to the latest `v1.x` on `go get -u`. A `v2.x` requires changing the import path — Go protects you here.
- **Prefer libraries with reproducible, signed releases.** A library whose tags are signed (visible on GitHub releases page) is harder to tamper with.
- **Watch for typosquats.** `github.com/glang/...` is not `github.com/golang/...`. Always copy-paste import paths from official sources.
- **Avoid pinning to `main` in production.** A branch head can change at any moment, including to malicious code.

---

## Performance Tips

- **The download is one-time per machine.** After the first `go get`, subsequent builds use the cache and are network-free.
- **`go mod download` warms the cache before a build.** Useful in Docker images:
  ```dockerfile
  COPY go.mod go.sum ./
  RUN go mod download
  COPY . .
  RUN go build
  ```
  This means rebuilds skip dependency download as long as `go.mod` and `go.sum` did not change.
- **`GOPROXY=off`** disables the proxy and forces local-cache-only mode. Useful for air-gapped environments.
- **Bigger `go.sum` does not slow your builds** — it slows your `go mod tidy` slightly, but negligibly.
- **Avoid pulling in massive dependencies for tiny needs.** A library that pulls 50 transitive deps to give you one helper function bloats your binary by megabytes.

---

## Best Practices

1. **Always use `go mod tidy` before committing.** It keeps `go.mod` honest.
2. **Commit `go.mod` and `go.sum` together.** Never one without the other.
3. **Pin major versions; let minor/patch float (within a single major).** `v1` stays `v1`, but `v1.6.0` to `v1.7.0` is fine.
4. **Read `pkg.go.dev` before importing.** Spend two minutes; it pays back hours.
5. **Run `govulncheck` in CI.** A free safety net.
6. **Upgrade deliberately, on a schedule.** Not in the middle of a feature.
7. **Prefer libraries with >1 year of activity, recent commits, low open-issue count, and a clear license.**
8. **Avoid forks unless you have a reason.** Use the canonical repository.
9. **One commit per dependency change.** Easy to bisect.
10. **Keep transitive dep count low.** Watch `go.sum` line count over time. Sudden growth is suspicious.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Forgetting `@latest` or `@vX.Y.Z`

```bash
go get github.com/google/uuid
```

This is fine for a *new* dependency — it picks the latest. But if you already have `uuid v1.3.0` and want to upgrade, plain `go get` will not bump it. Use `go get pkg@latest` or `go get -u pkg`.

### Pitfall 2 — Major version 2+ requires path change

A library at `v2.0.0` of `github.com/foo/bar` is imported as `github.com/foo/bar/v2`. If you write `import "github.com/foo/bar"` and ask for `@v2.0.0`, Go refuses. This is a feature, not a bug — it forces you to update both the import path and the version in one go.

### Pitfall 3 — `// indirect` lines in `go.mod`

After `go mod tidy`, you may see:

```
require (
    github.com/google/uuid v1.6.0
    github.com/spf13/pflag v1.0.5 // indirect
)
```

`// indirect` means "I do not import this directly; one of my dependencies does." Do not delete these lines manually — `go mod tidy` will add them back. They are part of the lockfile.

### Pitfall 4 — Replacing a dep without committing the change

Some teams use `replace` directives during local development (e.g., to point a dep at a sibling folder). If those land in `go.mod` and get committed, *every* CI build breaks because the local path does not exist on the build machine. Keep `replace` directives out of committed `go.mod` unless they are intentional.

### Pitfall 5 — Outdated example code on Stack Overflow

The top Stack Overflow answer for "how to use library X" was probably written three years ago against `v1.x`. The library is now on `v3.x` with a different API. Always cross-reference with `pkg.go.dev` for the version you have.

### Pitfall 6 — Pulling in `cgo`-heavy dependencies

Some libraries (especially database drivers, image processing) pull in `cgo`. They build fine on your laptop but fail in your minimal Alpine Docker image because `gcc` and `musl` headers are missing. Read the README for `cgo` warnings before adding.

### Pitfall 7 — Upgrading one library breaks another

Library A pins `protobuf v1.30`. You upgrade library B, which now requires `protobuf v1.34`. Minimum Version Selection picks `v1.34`. Library A may not work with `v1.34`. This is rare for well-behaved libraries but real. Run your tests after every upgrade.

### Pitfall 8 — Forgetting to commit after `go get`

`go get` modifies `go.mod` and `go.sum`. Stage and commit them, or your teammates will not get the change. Many CI pipelines fail with `git diff --exit-code` if `go.mod` or `go.sum` would change after `go mod tidy`.

---

## Common Mistakes

- **Importing without running `go get` or `go mod tidy`.** The build fails; the fix is one command.
- **Running `go get pkg` and expecting it to also import the package.** It does not. You still have to write the `import` line.
- **Editing `go.mod` by hand to bump a version.** Works, but `go get pkg@version` is the safer habit because it also updates `go.sum`.
- **Pinning to `master` or `main`.** That is a moving target and will bite you.
- **Using `replace` to "fix" a missing version when the right answer is `go get pkg@version`.**
- **Adding a dependency for a five-line problem.** Sometimes the answer is to write the five lines yourself.
- **Ignoring CVEs.** `govulncheck` is fast and free. Run it.
- **Mixing major versions of the same library by mistake** — e.g., importing both `github.com/foo/bar` (`v1`) and `github.com/foo/bar/v2`. They are *different* modules to Go and your binary now contains both. Almost always a bug.

---

## Common Misconceptions

> *"`go get` runs my code."*

No. `go get` only downloads, hashes, and registers. It does not execute anything from the dependency. Execution happens when you `go run` or `go build` and the dependency's `init()` and other code runs as part of your binary.

> *"I have to commit the dependency source code."*

No. You commit `go.mod` and `go.sum`. The source lives in the module cache and is re-downloaded on demand. (Exception: `go mod vendor` opts you into committing source — a separate workflow.)

> *"`go.sum` is just a debug file."*

No. `go.sum` is your security boundary. Without it, an attacker who controls the module proxy can swap library bytes silently. With it, any tamper attempt fails the build.

> *"`go get -u` is safe."*

It is *usually* safe — minor and patch bumps should not break you. But "should not" is not "will not." Always run tests after `go get -u`.

> *"Bigger version number always means better."*

Not always. A `v3` library may have shed features you depended on. Read changelogs.

> *"Once a dependency is in `go.mod`, it stays forever."*

No. Delete the import, run `go mod tidy`, and the require line vanishes. Keeping `go.mod` lean is your job.

---

## Tricky Points

- **`go.mod` lists what you require; the *resolved* graph also includes transitives.** `go list -m all` prints the resolved graph (every module that ends up in the build).
- **Pseudo-versions sort like real semver.** `v0.0.0-20231012103515-abcdef123456` is older than `v0.1.0`. The leading `v0.0.0-...` is intentional.
- **The leading `v` in versions is mandatory.** `go get pkg@1.0.0` fails; `go get pkg@v1.0.0` succeeds.
- **`@latest` means latest *tagged* release, not latest commit.** If a project hasn't tagged in two years, `@latest` returns a two-year-old tag.
- **A package with no tags at all gets a pseudo-version.** Pre-`v1` projects are common in Go — not a red flag by itself, but check the README for stability claims.
- **`go get` with no module argument is a special case.** In modern Go, plain `go get` without a target is deprecated; use `go install` for installing tools.
- **Major-version paths require a `/vN` suffix only for `vN >= 2`.** `v1.x.x` does *not* use a path suffix.

---

## Apply it

1. Choose one small, known input for **Using Third-Party Packages**.
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

- What problem does Using Third-Party Packages solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
