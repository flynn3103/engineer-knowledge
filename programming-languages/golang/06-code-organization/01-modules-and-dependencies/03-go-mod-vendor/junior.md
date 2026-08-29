# `go mod vendor` — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **`go mod vendor`** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### What `go mod vendor` actually does

Mechanically, the command performs five steps:

1. Reads `go.mod` to learn which modules and versions you depend on.
2. Reads `go.sum` to verify the integrity of the source it is about to copy.
3. Walks the import graph of your module to determine which *packages* (not whole modules) are actually needed for a build.
4. Copies the source of those packages from the module cache into a new top-level folder named `vendor/`, preserving the import path layout.
5. Writes a manifest at `vendor/modules.txt` that records what was copied.

That is all. It does not download anything new (the cache is already populated; `go mod tidy` did that). It does not modify `go.mod`. It does not run tests.

### `vendor/` is a snapshot, not a live mirror

Once `vendor/` exists, it does not auto-update. If you run `go get example.com/foo@v1.5.0` and bump a dependency, the *new* version is in the module cache, but the *old* version is still in `vendor/`. Your build will silently use the old vendored copy until you re-run `go mod vendor`.

This is by design. Vendoring is the act of "freezing" a snapshot of your dependencies at a point in time. The freezing is valuable — but it requires manual refresh.

### Auto-detection: vendor wins when present

Since Go 1.14, when the toolchain runs `go build`, `go test`, `go vet`, etc., it checks whether a `vendor/` directory exists at the module root. If yes, it behaves *as if* you passed `-mod=vendor` — meaning it reads source from `vendor/` and refuses to download anything.

To force the toolchain to ignore `vendor/`, pass `-mod=mod`:

```bash
go build -mod=mod ./...
```

But if `vendor/` exists, you almost never want to ignore it. The whole point of having it is to use it.

### Only imported packages are vendored

A dependency module might contain dozens of packages. `go mod vendor` only copies the packages your module's import graph actually reaches. If you import `github.com/some/lib/foo`, you get `foo/` and any package `foo/` imports — but not unrelated sibling packages of the same module.

This keeps `vendor/` smaller than a naive "copy the whole dependency" approach. It also means the contents of `vendor/` change when *your* imports change, even if `go.mod` does not.

### Test files are *not* vendored by default

Files ending in `_test.go` belonging to dependencies are not copied into `vendor/`. The reasoning: you are vendoring to build *your* program, not to re-run *their* tests. If you do need test sources for some reason, pass `-e` and inspect — there is also a long-form `-include-tests`-style invocation in some tooling, but the default is "no test files."

### Order matters: tidy first, then vendor

The canonical sequence is:

```bash
go mod tidy
go mod vendor
```

`go mod tidy` decides which modules are required and updates `go.mod`/`go.sum`. `go mod vendor` then reads those files and copies bytes. If you reverse the order, `vendor/` may include stale dependencies or omit needed ones.

### What gets committed to Git

This is the question every team eventually argues about. The standard answer is:

- **Yes, commit the entire `vendor/` directory.** That is the entire point — reproducible, no-network, no-surprises builds.
- **Yes, also commit `go.mod` and `go.sum`.** They are not redundant; they remain the canonical source of "what versions did we ask for."
- **Yes, commit `vendor/modules.txt`.** It is part of `vendor/`.

If you are not going to commit `vendor/`, do not vendor in the first place.

---

## Code Examples

### Example 1 — Vendoring a single-dependency module

Start fresh.

```bash
mkdir hello
cd hello
go mod init example.com/hello
```

Now write a `main.go` that uses `github.com/google/uuid`:

```go
package main

import (
    "fmt"

    "github.com/google/uuid"
)

func main() {
    id := uuid.New()
    fmt.Println("new id:", id)
}
```

Tidy and vendor:

```bash
go mod tidy
go mod vendor
```

Now look around:

```bash
$ ls
go.mod  go.sum  main.go  vendor

$ ls vendor
github.com  modules.txt

$ ls vendor/github.com/google/uuid
CHANGELOG.md  LICENSE  README.md  doc.go  hash.go  ...
```

Build with vendoring (no internet needed):

```bash
go build .
./hello
# new id: 5b8c...
```

### Example 2 — Inspecting `vendor/modules.txt`

Open the file:

```bash
$ cat vendor/modules.txt
# github.com/google/uuid v1.6.0
## explicit; go 1.19
github.com/google/uuid
```

Decoding it line by line:

- `# github.com/google/uuid v1.6.0` — module path and version.
- `## explicit; go 1.19` — `explicit` means *your* `go.mod` mentions this directly; `go 1.19` is the dependency's required Go version.
- `github.com/google/uuid` — the import path of the vendored package.

A larger project will have dozens of these blocks.

### Example 3 — Forcing a non-vendored build

If for some reason you want to bypass `vendor/` and use the cache:

```bash
go build -mod=mod .
```

This is rarely useful in day-to-day work; mostly it is for debugging "is my vendor folder out of date?".

### Example 4 — Refreshing after a dependency bump

You decide to upgrade a dependency:

```bash
go get github.com/google/uuid@v1.6.0
go mod tidy
go mod vendor
git add go.mod go.sum vendor/
git commit -m "bump uuid to v1.6.0"
```

The three-command dance — `get`, `tidy`, `vendor` — is the standard refresh recipe.

### Example 5 — Cleaning up

If you decide vendoring is not for you:

```bash
rm -rf vendor
git add -A
git commit -m "stop vendoring deps"
```

The next `go build` will silently fall back to the module cache. Nothing else changes.

### Example 6 — A multi-import vendored project

```go
package main

import (
    "fmt"

    "github.com/google/uuid"
    "github.com/spf13/pflag"
)

func main() {
    name := pflag.String("name", "world", "who to greet")
    pflag.Parse()
    fmt.Printf("hello, %s — your id is %s\n", *name, uuid.New())
}
```

After `go mod tidy && go mod vendor`:

```
vendor/
├── github.com/
│   ├── google/
│   │   └── uuid/
│   └── spf13/
│       └── pflag/
└── modules.txt
```

The transitive dependencies of `pflag` would also appear, if any.

---

## Coding Patterns

### Pattern: tidy-then-vendor as a Make target

Most teams encode the dance in a Makefile or shell script:

```Makefile
.PHONY: deps
deps:
	go mod tidy
	go mod vendor
```

Then everyone says `make deps` instead of remembering two commands.

### Pattern: CI verification

CI should refuse to merge a PR whose `vendor/` is out of sync:

```bash
go mod tidy
go mod vendor
git diff --exit-code go.mod go.sum vendor
```

If `git diff --exit-code` returns non-zero, the contributor forgot to re-vendor.

### Pattern: `.gitignore` *does not* exclude `vendor/`

The most common newbie reflex is to add `vendor/` to `.gitignore`. **Do not.** That defeats the entire purpose. If you do not commit `vendor/`, you have all of vendoring's costs and none of its benefits.

### Pattern: Treat vendor changes like content changes

A pull request that bumps a dependency will touch hundreds of files. Reviewers should learn to focus on `go.mod` and `go.sum` — those tell the human story — and treat the `vendor/` diff as scaffolding generated from those.

---

## Clean Code

- **Always run `go mod tidy` before `go mod vendor`.** They form a pair.
- **Commit `go.mod`, `go.sum`, and `vendor/` together** in a single commit. Splitting them into separate commits leaves the repo in an inconsistent intermediate state.
- **Do not edit files inside `vendor/` by hand.** The next `go mod vendor` will overwrite your changes. If you must patch a dependency, use `replace` directives in `go.mod` (advanced topic).
- **Keep `vendor/` out of code coverage and lint reports.** Add explicit excludes:
  - `golangci-lint`: `--skip-dirs vendor`
  - `gofmt`: it skips `vendor/` automatically since 1.13.
- **Do not vendor and then partially commit.** The tree must be all-or-nothing.

---

## Error Handling

`go mod vendor` itself rarely fails, but its consumers (subsequent `go build`/`go test` calls) may.

### "inconsistent vendoring in <module>"

The most famous error. It means `vendor/modules.txt` does not match `go.mod`. Causes:

- You edited `go.mod` (added/removed a `require`) without re-running `go mod vendor`.
- You hand-edited `vendor/modules.txt`.
- You merged a branch and the conflict resolution missed `vendor/`.

Fix:

```bash
go mod tidy
go mod vendor
```

### "missing go.sum entry"

You ran `go mod vendor` before `go mod tidy`, so `go.sum` has no hash for some module the import graph reached. Fix: tidy first.

### "package <X> is not in std (...)"

You imported a package that is not in any module listed by `go.mod`. Fix: `go get example.com/X` first, then `go mod tidy`, then `go mod vendor`.

### Network errors during `go mod vendor`

If your module cache is missing some versions, `go mod vendor` will try to download them. On a restricted network this fails. Fix: ensure you have network access *for the one-time vendoring step*, or pre-populate the cache from another machine.

### "vendor/modules.txt does not exist"

You created a `vendor/` folder by hand and Go is confused. Fix: delete the folder and re-run `go mod vendor` so it creates a real one.

---

## Security Considerations

- **Vendoring freezes a *known* snapshot.** That is good for reproducibility and bad for security: a CVE in a vendored dependency does not get patched until you re-vendor.
- **Code review benefits.** Vendoring forces every dependency change to appear as a diff in PR review. Malicious upstream changes become visible.
- **Supply-chain insulation.** A compromised proxy or a yanked package cannot affect your build if your `vendor/` already contains the trusted bytes.
- **Hash integrity is preserved.** `go.sum` still validates the cache bytes that get copied; you cannot vendor a tampered dependency without `go.sum` flagging it.
- **Do not store secrets in `vendor/`.** Obvious, but worth saying — the folder is committed to Git and in some industries treated as "third-party code only," so do not pollute it with internal artifacts.
- **Keep an eye on upstream advisories.** Run `govulncheck` or similar against your vendored tree on a schedule.

---

## Performance Tips

- **First `go mod vendor` is slow** (it copies thousands of files); subsequent runs only update what changed.
- **Build performance is *better* with vendoring** — Go does not have to consult the cache or proxy. For large projects this can shave seconds.
- **CI cache warmup is unnecessary.** With vendoring, you do not need to cache `$GOPATH/pkg/mod` between builds; the deps are in the repo.
- **Watch repository size.** A 200 MB `vendor/` slows down `git clone`. Use shallow clones in CI (`git clone --depth 1`) when possible.
- **`vendor/` is excluded from `go vet ./...` automatically** — vet skips vendored packages.

---

## Best Practices

1. **Always pair `go mod tidy` with `go mod vendor`.** Even if it feels redundant.
2. **Commit the entire `vendor/` directory.** Or do not vendor.
3. **Verify in CI** that `vendor/` is in sync with `go.mod`/`go.sum`.
4. **Document in your README** that the project is vendored and any contributor must run the tidy-vendor pair before pushing.
5. **Update vendored dependencies on a regular cadence.** Monthly is reasonable; never is dangerous.
6. **Do not mix vendored and unvendored modules in a workspace** — workspaces (`go.work`) and vendoring have specific interactions that are out of scope for junior level.
7. **Use `-mod=vendor` explicitly in CI** to be safe, even though it is the default when `vendor/` exists.
8. **Treat `vendor/` as read-only**. Patches go in `replace` directives, not in-place edits.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Forgetting to re-vendor after `go get`

You upgrade a dep, push, and CI fails with "inconsistent vendoring." Always: `go get` -> `go mod tidy` -> `go mod vendor` -> commit all four (`go.mod`, `go.sum`, `vendor/`, your code).

### Pitfall 2 — `.gitignore` containing `vendor/`

Common in projects that *used* to not vendor. The result: every developer vendors locally, but no one's `vendor/` is committed. Catastrophic — you have all the noise, none of the benefit.

### Pitfall 3 — Hand-editing `vendor/`

Every junior tries it: "I just want this one bug fix." A re-vendor erases your edit silently. Use `replace` in `go.mod` instead.

### Pitfall 4 — Vendoring then changing the import without re-vendoring

You add `import "example.com/foo/bar"` in code. Build fails: `bar` is not in `vendor/`. Fix: re-vendor. The folder is a snapshot, not magic.

### Pitfall 5 — Cross-platform line endings

On Windows, Git can normalize line endings inside `vendor/` and break diffs. Add to `.gitattributes`:

```
vendor/** -text
```

This tells Git to leave vendored files alone.

### Pitfall 6 — Submodule-style nesting

If you place a Go module inside another module (rare, advanced), `vendor/` only applies to the *outer* module. Inner modules are independent.

### Pitfall 7 — Build tags hiding required imports

A package guarded by `//go:build linux` may be needed on Linux but not on macOS. `go mod vendor` is supposed to handle build tags correctly — but if you vendor on macOS only, double-check that the linux-only deps were included. They should be; the algorithm is platform-aware.

### Pitfall 8 — IDE confusion

Some IDEs index `vendor/` and report duplicate symbols. Configure the IDE to treat `vendor/` as a vendored dependency tree (most modern IDEs do this automatically).

---

## Common Mistakes

- **Adding `vendor/` to `.gitignore`.** The single most common mistake. Defeats the purpose.
- **Running `go mod vendor` once and forgetting it forever.** Vendoring is a habit, not a one-time event.
- **Editing files in `vendor/` to "fix" a dependency.** Use `replace`. Or fork upstream.
- **Running `go mod vendor` without `go mod tidy` first.** Produces stale or incomplete vendor trees.
- **Forgetting to commit `vendor/modules.txt`.** Some scripts only `git add vendor/github.com/...` and miss the manifest.
- **Mixing `-mod=mod` and `-mod=vendor` between developers.** Pick one stance per project.
- **Vendoring a private module that was already in a private cache.** Sometimes wasteful; sometimes necessary. Decide deliberately.
- **Vendoring just to "see what is in there."** OK once, as a learning exercise; do not commit it.

---

## Common Misconceptions

> *"Vendoring downloads my dependencies for me."*

No. `go mod tidy` (or `go get`) downloads them. `go mod vendor` only *copies* what is already in the cache. If the cache is empty, `go mod vendor` will trigger downloads as a side effect, but that is incidental.

> *"`vendor/` replaces `go.mod` and `go.sum`."*

No. All three coexist. `go.mod` declares; `go.sum` proves; `vendor/` materializes. Removing `go.mod` would make the project not even a module.

> *"Vendoring includes test files."*

No. `_test.go` files of dependencies are excluded by default.

> *"Vendoring is deprecated; modules replaced it."*

No. Modules and vendoring are designed to coexist. Vendoring is fully supported and actively maintained.

> *"If I vendor, my project no longer needs internet."*

For builds, mostly true. For other operations (`go get` to update, `go mod download` to refresh) you still need internet. Vendoring isolates the *build* path.

> *"`vendor/` is the same as `node_modules/`."*

Spiritually similar, mechanically very different. `node_modules/` is a per-platform install with binaries; `vendor/` is a portable, source-only, pre-pruned snapshot.

---

## Tricky Points

- **Auto-detection requires `vendor/modules.txt` to exist** — a `vendor/` without that manifest is treated as broken, not as "use it."
- **`go mod vendor` skips packages from the standard library.** Std is part of the toolchain, not the module cache.
- **The `go` directive in `go.mod` interacts with vendoring.** A `go 1.14` directive enables auto-vendoring. Older directives (`go 1.13`) require explicit `-mod=vendor`.
- **The vendor folder's path layout mirrors import paths exactly.** `github.com/google/uuid` becomes `vendor/github.com/google/uuid/...`. There is no flattening.
- **Replace directives are honoured during vendoring.** If `go.mod` has `replace example.com/foo => ./local/foo`, the local copy is what gets vendored.
- **`go list -mod=vendor all` shows you what is vendored** — useful for debugging.
- **Removing a dependency means three steps:** delete the import, run `go mod tidy`, run `go mod vendor`. Skipping the last leaves dead code in `vendor/`.

---

## Apply it

1. Choose one small, known input for **`go mod vendor`**.
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

- What problem does `go mod vendor` solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
