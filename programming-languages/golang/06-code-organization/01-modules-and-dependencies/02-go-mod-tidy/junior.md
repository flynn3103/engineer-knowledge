# `go mod tidy` — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **`go mod tidy`** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### `go mod tidy` syncs `go.mod`/`go.sum` to your imports

That is the whole job. Imagine `go.mod` and your `import` lines as two lists. They should be the *same* list (with versions added). Tidy compares them and rewrites `go.mod` to match.

If your code imports `github.com/spf13/cobra`, `go.mod` ends up with a `require github.com/spf13/cobra vX.Y.Z` line. If you delete every `import` of `cobra`, the next `go mod tidy` removes that `require` line.

### It scans every `.go` file under the module root

Tidy walks the directory tree starting from the module root (where `go.mod` lives), reads every `.go` file (including `_test.go` files), parses each `import` block, and builds a set of *needed* import paths. That set is the source of truth.

It is purely static — it does not run your code, it does not even compile your code. It just reads imports.

### It populates `go.sum` with checksums

For every module in the build graph (direct *and* indirect), `go mod tidy` writes two lines to `go.sum`:

```
github.com/spf13/cobra v1.8.0 h1:...checksum...
github.com/spf13/cobra v1.8.0/go.mod h1:...checksum...
```

The first line hashes the module's source tree. The second hashes its `go.mod`. Both are needed for full reproducibility.

### It marks indirect-only dependencies with `// indirect`

A direct dependency appears in `go.mod` like this:

```
require github.com/spf13/cobra v1.8.0
```

An indirect one looks like this:

```
require github.com/inconshreveable/mousetrap v1.1.0 // indirect
```

The `// indirect` comment is **not** a stylistic flourish — it is a real piece of metadata that tooling reads. Tidy adds, removes, and maintains those markers automatically. Do not edit them by hand.

### It runs the full Minimum Version Selection algorithm

When two packages in your graph ask for two different versions of the same module, Go picks the *highest of the minimums*. Tidy resolves all of these constraints and writes the resulting versions into `go.mod`.

You do not have to understand MVS in depth as a junior. Just know: tidy makes a definite, deterministic choice, and writes it down.

### `go build` is *not* the same as `go mod tidy`

`go build` will sometimes auto-add a missing dependency to `go.mod` *just enough* to make the build succeed. But it will **not**:

- Remove unused dependencies
- Update `// indirect` markers correctly
- Write *every* checksum to `go.sum`

So a build that works today is not the same as a tidy `go.mod`. Always finish a session of import-changes with `go mod tidy` before committing.

---

## Code Examples

### Example 1 — Tidy on a fresh module after adding an import

```bash
mkdir myapp
cd myapp
go mod init example.com/myapp
```

Now create `main.go`:

```go
package main

import (
    "github.com/spf13/cobra"
)

func main() {
    cmd := &cobra.Command{Use: "myapp"}
    _ = cmd.Execute()
}
```

At this point `go.mod` does not know about cobra. Try to build and you may see:

```
main.go:4:5: no required module provides package github.com/spf13/cobra
```

Run:

```bash
go mod tidy
```

`go.mod` now contains:

```
module example.com/myapp

go 1.22

require github.com/spf13/cobra v1.8.0

require (
    github.com/inconshreveable/mousetrap v1.1.0 // indirect
    github.com/spf13/pflag v1.0.5 // indirect
)
```

And `go.sum` (a new file) has lines like:

```
github.com/inconshreveable/mousetrap v1.1.0 h1:...
github.com/inconshreveable/mousetrap v1.1.0/go.mod h1:...
github.com/spf13/cobra v1.8.0 h1:...
github.com/spf13/cobra v1.8.0/go.mod h1:...
github.com/spf13/pflag v1.0.5 h1:...
github.com/spf13/pflag v1.0.5/go.mod h1:...
```

Now `go build` succeeds.

### Example 2 — Tidy after removing an import

Take the previous module and edit `main.go` so it no longer uses cobra:

```go
package main

import "fmt"

func main() {
    fmt.Println("hello")
}
```

If you build now, it works — but `go.mod` still lists cobra. Run:

```bash
go mod tidy
```

`go.mod` shrinks to:

```
module example.com/myapp

go 1.22
```

Cobra and its indirect deps are gone. `go.sum` may still hold their entries for a while; subsequent `tidy` runs prune them as the build graph stabilises.

### Example 3 — Verbose mode

```bash
go mod tidy -v
```

Output (abridged):

```
unused github.com/foo/bar
```

The `-v` flag prints every module that tidy *removed* from `go.mod`. Useful when you want to know what just happened.

### Example 4 — Continue on errors

```bash
go mod tidy -e
```

Without `-e`, tidy aborts on the first error. With `-e`, it presses on, fixing what it can. Useful when several imports are broken at once and you want a list rather than fixing them one by one.

### Example 5 — Tidy to a specific Go-language version

Since Go 1.17 the layout of `go.mod` (with separate direct/indirect blocks) is determined by the `go` directive. To force a particular target you can pass the older language flag (Go 1.21+):

```bash
go mod tidy -go=1.21
```

This rewrites `go.mod` so its `go` directive is `1.21`, which controls the indirect-dependency bookkeeping style. As a junior you will rarely need this — accept the default — but you should recognise the flag when you see it.

### Example 6 — Detecting drift in CI

A common CI step:

```bash
go mod tidy
git diff --exit-code go.mod go.sum
```

If tidy changes anything, the `git diff` exits non-zero and CI fails. The fix: run `go mod tidy` locally and commit the changes.

---

## Coding Patterns

### Pattern: Add import, run tidy, commit together

The unit of work is "import change + go.mod/go.sum change". Treat them as one commit:

```bash
# 1. Edit code, add import.
# 2. Run tidy.
go mod tidy
# 3. Stage and commit together.
git add main.go go.mod go.sum
git commit -m "Add cobra-based CLI"
```

Splitting these into two commits causes one of them to be broken by itself — bad for `git bisect` later.

### Pattern: Tidy before every push

A short habit: just before `git push`, run `go mod tidy` to catch any forgotten drift. It costs less than a second on a warm cache.

### Pattern: Tidy + diff in CI

Make CI fail if `go.mod` or `go.sum` are not tidy. A drifted `go.mod` is a latent bug; CI is the right place to enforce.

### Pattern: Use `go get` to pin a version, then tidy to clean up

```bash
go get github.com/foo/bar@v1.4.2
go mod tidy
```

`go get` adds (or upgrades) a specific version. Tidy then re-balances the rest of the graph and ensures all checksums are in `go.sum`.

### Pattern: After cloning, tidy is unnecessary; build is enough

If you `git clone` someone else's tidy repository and just want to compile, you do **not** need to run `go mod tidy`. Their `go.mod`/`go.sum` are already authoritative. `go build` will download the right versions and verify the checksums.

---

## Clean Code

- **Always commit `go.mod` and `go.sum` together** when imports change. Never one without the other.
- **Never edit the `// indirect` markers by hand.** Let tidy maintain them.
- **Do not delete `go.sum`** to "clean up." It will be re-created, but your `git diff` will be enormous and impossible to review.
- **Prefer `go get module@version` + `go mod tidy`** over editing `go.mod` directly to change a version.
- **Run tidy before each commit that touches `.go` files.** It is cheap and prevents drift.
- **Group `require` blocks logically.** Tidy keeps directs and indirects in separate blocks; do not re-order the blocks manually.

A clean Go module is one where `go mod tidy && git status` produces no diff.

---

## Error Handling

`go mod tidy` itself rarely "fails" silently — it produces explicit error messages. Here are the ones a junior will see most often.

### "no required module provides package <path>"

You have an `import "github.com/foo/bar"` but no module on the proxy claims to ship that path. Causes:

- Typo in the import path.
- The module was renamed or deleted.
- You are offline and the cache is empty.

Fix: check the import path on pkg.go.dev or the upstream repository.

### "missing go.sum entry for module providing package <path>"

`go.mod` says you need module X but `go.sum` does not have its checksum. Common after a partial merge or after someone hand-edited `go.mod`. Fix:

```bash
go mod tidy
```

### "ambiguous import: found package X in multiple modules"

Two modules in your graph both claim to ship the same import path. Often happens when a module was forked and renamed but old references survive in transitive deps. Fix is usually a targeted `go get` to upgrade the offending consumer.

### "module declares its path as: A but was required as: B"

You (or your dependency) require a module by one path while the module's own `go.mod` declares a different path. Either the module was renamed, or there is a `replace` directive missing/wrong. Fix is to use the module's canonical path.

### "verifying module: checksum mismatch"

The bytes the proxy returned do not match the hash in `go.sum`. This is either a serious security signal or, more commonly, a corrupted local cache. Try:

```bash
go clean -modcache
go mod tidy
```

If it persists, do not silence the error — investigate.

### Errors when offline

If `GOPROXY=off` (or you are simply offline), tidy fails when it needs a module not in the local cache. Fix is to populate the cache while online or set up a local mirror.

---

## Security Considerations

- **`go.sum` is a tamper-detection device.** Tidy populates it and the toolchain verifies every download against it forever after. Do not delete it; do not silence checksum errors.
- **Checksum DB.** By default, `go mod tidy` cross-checks new entries against `sum.golang.org`. You can disable this (`GOSUMDB=off`) but doing so weakens supply-chain security. As a junior, leave it alone.
- **Private modules.** If your module pulls from a private repository, configure `GOPRIVATE` (and possibly `GONOSUMCHECK`) so tidy does not leak the path to the public proxy. Consult your team's docs.
- **Network leak.** Running tidy on confidential code can leak the names of your dependencies (and possibly your own module path) to `proxy.golang.org` and `sum.golang.org`. For internal-only code, use a private proxy.
- **Typosquatting risk.** A subtle typo in an import path (`github.com/golamg/...` vs `github.com/golang/...`) can pull in a malicious lookalike. Tidy will *happily* download what you asked for. Read your imports.
- **Don't ignore checksum mismatches.** They are the loudest signal you will ever get that something has gone wrong. Investigate every one.

---

## Performance Tips

- **Warm cache wins.** First run after a fresh clone is slow; subsequent runs are fast. The module cache lives in `$GOMODCACHE` (usually `$HOME/go/pkg/mod`).
- **Use a corporate proxy** if your team shares dependencies. `GOPROXY=https://corp-proxy,...` cuts internet round-trips dramatically.
- **Don't run `go mod tidy` in a tight loop in CI.** It is idempotent — once is enough per build.
- **Vendor for the build hot path.** If your CI runs many builds per minute, `go mod vendor` (see [03-go-mod-vendor](../03-go-mod-vendor/junior.md)) makes builds fully offline and fast. Run tidy beforehand, then vendor.
- **Keep `go.mod` minimal.** Tidy already does this for you; the point is, do not manually pad it.
- **Use `-e` only when you need it.** It does extra work. The default fail-fast mode is faster on healthy modules.

---

## Best Practices

1. **Run `go mod tidy` after every change to imports.** Make it muscle memory.
2. **Commit `go.mod` and `go.sum` together.** Same commit. Always.
3. **Never hand-edit `// indirect` comments** — tidy owns them.
4. **CI must enforce a tidy module.** A diff after `go mod tidy` should fail the build.
5. **Use `go get module@version` to pin or upgrade specific versions**, then tidy to settle the graph.
6. **Trust the toolchain over the documentation in your head.** When in doubt about `go.mod` content, run tidy and read the output.
7. **Do not ignore tidy warnings.** They almost always indicate a real problem.
8. **Keep your Go version reasonably current.** Tidy's behaviour improves substantially across Go versions; staying within one or two minor versions of the latest release pays off.
9. **Tidy *before* `go test ./...` in CI.** A drifted `go.mod` can cause tests to fail for non-test reasons.
10. **Document any non-default flags** (like `-go=1.21` or `-compat=1.20`) in your project's CONTRIBUTING file so future contributors know what to do.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Build added a require but tidy removed it

You ran `go build`, it auto-added a require line. You then ran `go mod tidy` and the line vanished. Usually this means the build added the dep for one platform/build-tag and tidy considers the file irrelevant on the current build. The fix is to ensure tidy considers all relevant files — see Pitfall 4.

### Pitfall 2 — Conditional imports under build tags

A file guarded by `//go:build linux` is invisible to tidy when you run on macOS — *unless* you tell tidy otherwise. By default, modern Go (`1.17+`) considers all build tags in tidy. But on older Go versions you may need:

```bash
go mod tidy -compat=1.17
```

Or explicitly:

```bash
GOOS=linux go mod tidy
```

When in doubt, run on every supported `GOOS`/`GOARCH`.

### Pitfall 3 — Test-only imports

Imports that appear only in `_test.go` files **are** tracked by tidy. They appear in `go.mod` as `// indirect` if they are needed only by tests of other modules in your graph. Do not assume "test imports do not count."

### Pitfall 4 — A folder excluded by `.go` ignore patterns

Tidy walks the directory tree but ignores certain folders (e.g. anything starting with `.` or `_`, plus `testdata/`). If you keep example code in `testdata/`, those imports are invisible to tidy. This is intentional but surprises new users.

### Pitfall 5 — Replace directives changing the graph

A `replace` directive in `go.mod` redirects a module to a different source. Tidy honours replaces. If you remove a replace, the next tidy may pull the upstream version, which can change the graph dramatically.

### Pitfall 6 — Out-of-sync after a merge

Two branches each ran tidy; merging produces a `go.mod`/`go.sum` that no longer matches imports. Run tidy after every merge of a branch that touched imports.

### Pitfall 7 — Tidy on a sub-folder that is not the module root

`go mod tidy` operates on the *module*, not the current directory. Running it from `myapp/internal/` still tidies the module rooted at `myapp/`. That is correct, but new users sometimes expect a sub-folder mode. There isn't one.

### Pitfall 8 — Modules with no Go files

A module that contains only `.proto` files or `.md` files (and no `.go` files at all) confuses tidy: it has nothing to scan. Add at least one `.go` file (even an empty `package doc`).

---

## Common Mistakes

- **Editing `go.mod` to add a `require` line by hand.** Use `go get module@version` instead — it picks a real version and updates `go.sum`.
- **Deleting `go.sum` "to clean up."** Always wrong. The diff after the next tidy will be enormous and unreadable.
- **Forgetting to commit `go.sum`.** Other developers' builds will fail mysteriously.
- **Running tidy from a different folder than the module root.** Works (tidy figures it out), but confuses people watching your terminal.
- **Removing `// indirect` markers because they look ugly.** They are not decorative.
- **Running tidy *only* in CI and being surprised when local builds drift.** Run it locally too.
- **Assuming `go build` is enough.** It is not — tidy is.
- **Running tidy with `GOFLAGS=-mod=readonly`.** Tidy's whole job is to *write* `go.mod`. The flag combination is contradictory; some Go versions will refuse.
- **Ignoring the network roundtrip on a new machine.** First tidy in a fresh checkout pulls the cache; this is normal.

---

## Common Misconceptions

> *"`go mod tidy` upgrades my dependencies."*

No. Tidy keeps existing versions whenever possible. To *upgrade*, use `go get -u`. Tidy is conservative.

> *"`go mod tidy` is the same as `go get`."*

No. `go get` is for adding/removing/upgrading specific modules. Tidy reconciles the entire graph after the imports have changed.

> *"`go mod tidy` requires the internet."*

It can be satisfied by the local module cache if every needed version is already there. In practice it usually does hit the network, but a fully populated cache makes it offline-capable.

> *"`go.sum` only matters in CI."*

It matters in every build. The toolchain verifies hashes on every compile. CI just makes the failure visible.

> *"If `go build` succeeds, my `go.mod` is correct."*

Not quite. `go build` succeeds with a *minimal* `go.mod` that may be missing checksums for indirect deps. Tidy ensures the graph is *complete*.

> *"Indirect dependencies are not my problem."*

They become your problem the moment one of them has a CVE or a breaking bug. Tidy at least makes them visible.

> *"`go mod tidy` is destructive."*

It mutates `go.mod` and `go.sum`, but only in ways the toolchain can re-derive. The mutations are deterministic and version-controlled. The risk is exactly zero if you commit the result.

---

## Tricky Points

- **The `go` directive controls tidy behaviour.** Pre-1.17 modules listed every transitive in one block; 1.17+ split direct from indirect. Bumping `go 1.16` to `go 1.17` and running tidy reshapes `go.mod`.
- **`-compat` flag.** `go mod tidy -compat=1.17` ensures the resulting `go.mod` is buildable by Go 1.17. Useful for libraries with broad version support.
- **Tidy updates checksums for *every* module in the build graph**, including ones referenced only by `go.mod` files of dependencies. That is why `go.sum` is twice as long as you might expect.
- **Tidy can change between Go versions.** A `go.mod` tidy for 1.20 may differ slightly from one tidy for 1.22. CI on multiple Go versions can produce diffs. Standardise the Go version in CI.
- **A module without any imports needs no `go.sum`.** That file is created the first time tidy encounters a dependency.
- **Replace directives shadow tidy.** A `replace foo => ./local` keeps `foo`'s version frozen — tidy will not pull a different version for it.
- **Two `// indirect` lines for the same module are not allowed.** Tidy collapses them. If a merge produces duplicates, run tidy.
- **`go mod tidy` does not run `go vet`, does not run tests, does not check syntax.** It only looks at imports.

---

## Apply it

1. Choose one small, known input for **`go mod tidy`**.
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

- What problem does `go mod tidy` solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
