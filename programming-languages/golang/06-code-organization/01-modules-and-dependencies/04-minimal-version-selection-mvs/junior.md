# Minimal Version Selection (MVS) — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Minimal Version Selection (MVS)** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### "Minimum version" means "the minimum that satisfies everyone"

This is the phrase that confuses everyone, so read it slowly.

A `require` line is not a request for *exactly* that version. It is a request for *at least* that version. `require example.com/foo v1.2.0` means: "I need `foo`, and it must be `v1.2.0` or newer — `v1.2.0` is my floor."

Now imagine three different places in your dependency graph each set a floor for the same module `foo`:

- Your `go.mod` says `foo v1.2.0`.
- A library you use says `foo v1.4.0`.
- Another library says `foo v1.3.0`.

Each of those is a *minimum*. To satisfy all three at once, the build needs a version that is at least `v1.4.0` (the highest floor). MVS picks exactly `v1.4.0` — the **highest of the minimums**. It does not go higher, even if `v1.9.0` exists on the internet. Nobody asked for `v1.9.0`, so `v1.9.0` is not used.

That is the entire algorithm in one sentence: **for each module, select the maximum version that anyone explicitly required.**

### MVS picks the *minimum* needed, not the *maximum* available

Other tools ask, "what is the newest version compatible with all the constraints?" Go asks, "what is the oldest version that everyone agreed is good enough?" The difference is enormous in practice:

- With a "newest" tool, running install today versus tomorrow can give you *different* versions, because a new release appeared overnight. Your build is a moving target.
- With MVS, the versions are fixed by the `require` lines in `go.mod`. A new release on the internet changes nothing until *you* edit a `require` line. Your build is frozen by your own files.

This is why Go does not need a separate lockfile (like `package-lock.json` or `Cargo.lock`). The `go.mod` files *are* the lock. The version numbers in them, plus the MVS rule, fully determine the build.

### The build list: one version per module

The output of MVS is the **build list**: a flat list with exactly one version for each module in your build. You can see it directly:

```bash
$ go list -m all
example.com/myapp
github.com/google/uuid v1.6.0
github.com/spf13/pflag v1.0.5
golang.org/x/sys v0.18.0
```

The first line (no version) is your main module. Every other line is a `(module, version)` pair MVS selected. Even if five different libraries each required a different version of `golang.org/x/sys`, this list shows just one — the highest minimum.

### Where the floors come from: `require` directives

Every `go.mod` in the graph contributes floors. Your own `go.mod`:

```
module example.com/myapp

go 1.22

require (
    github.com/google/uuid v1.6.0
    github.com/spf13/cobra v1.8.0
)
```

Each `require` line is a floor *you* set. But `cobra`'s own `go.mod` has its own `require` block, setting more floors. And those dependencies have dependencies, each with floors. MVS gathers every floor from every `go.mod` in the transitive graph, then for each module takes the maximum.

### `// indirect` requirements

You will see lines like this:

```
require (
    github.com/google/uuid v1.6.0
    golang.org/x/sys v0.18.0 // indirect
)
```

The `// indirect` comment means: "my code does not `import` this directly, but it ends up in my build anyway." Usually it is there to *raise a floor* — to make sure a transitive dependency is at least a certain version. MVS treats indirect requires exactly like direct ones: they are floors. The comment is just bookkeeping for humans and `go mod tidy`.

### Why this gives reproducible builds

Because the selected version of every module is fully determined by the `require` lines in the graph, two people who `git clone` the same repo get the **same build list**, today and years from now. No background updates. No "it worked on my machine because I installed yesterday." The version a build uses is a property of the committed files, not of the calendar.

---

## Code Examples

### Example 1 — Seeing the build list

Start with a small module.

```bash
mkdir mvsdemo
cd mvsdemo
go mod init example.com/mvsdemo
```

Add a dependency:

```bash
go get github.com/google/uuid@v1.6.0
```

Now print the build list:

```bash
$ go list -m all
example.com/mvsdemo
github.com/google/uuid v1.6.0
```

Two lines: your main module (no version), and the one dependency at the version MVS selected. Since only one floor exists for `uuid`, the selection is trivially that floor.

### Example 2 — The "highest of the minimums" in action

Suppose your `go.mod` ends up looking like this (after pulling in two libraries that both depend on `golang.org/x/text`):

```
module example.com/mvsdemo

go 1.22

require (
    github.com/libA v1.0.0   // requires golang.org/x/text v0.3.0
    github.com/libB v1.0.0   // requires golang.org/x/text v0.9.0
)
```

`libA`'s `go.mod` floors `x/text` at `v0.3.0`. `libB`'s floors it at `v0.9.0`. The build list shows:

```bash
$ go list -m golang.org/x/text
golang.org/x/text v0.9.0
```

MVS chose `v0.9.0` — the higher of the two minimums. Even if `golang.org/x/text v0.14.0` exists, it is not used: nobody required it.

### Example 3 — A new release upstream does NOT upgrade you

Imagine `github.com/google/uuid` releases `v1.7.0` tomorrow. You run a normal build:

```bash
$ go build ./...
$ go list -m github.com/google/uuid
github.com/google/uuid v1.6.0
```

Still `v1.6.0`. MVS does not see the new release as relevant — your floor is still `v1.6.0`. To move to `v1.7.0`, you must ask:

```bash
$ go get github.com/google/uuid@v1.7.0
$ go list -m github.com/google/uuid
github.com/google/uuid v1.7.0
```

Now the floor is raised, and the build list reflects it.

### Example 4 — Inspecting the module graph

The build list is the *result*. To see the raw floors that produced it, look at the graph:

```bash
$ go mod graph
example.com/mvsdemo github.com/spf13/cobra@v1.8.0
example.com/mvsdemo github.com/google/uuid@v1.6.0
github.com/spf13/cobra@v1.8.0 github.com/spf13/pflag@v1.0.5
github.com/spf13/cobra@v1.8.0 github.com/inconshreveable/mousetrap@v1.1.0
```

Each line is "A requires B." The left side is a module-at-version; the right side is the floor it sets. MVS reads all of these edges and computes one version per module from them.

### Example 5 — `go get foo@v1.2.3` raises a floor

The most common version-changing command:

```bash
$ go get github.com/spf13/pflag@v1.0.5
```

This sets (or raises) the floor for `pflag` to `v1.0.5` and writes it into your `go.mod`. The build list updates accordingly. You can pin to an exact version, a branch, or `@latest`:

```bash
go get github.com/spf13/pflag@v1.0.5     # exact version
go get github.com/spf13/pflag@latest     # newest tagged release
go get github.com/spf13/pflag@v1.0.4     # downgrade (lowers your direct floor)
```

### Example 6 — `go mod why` explains a dependency

When you wonder "why is this module even in my build?", ask:

```bash
$ go mod why golang.org/x/sys
# golang.org/x/sys
example.com/mvsdemo
github.com/spf13/cobra
golang.org/x/sys
```

The output is the import chain: your app imports `cobra`, which (transitively) needs `x/sys`. That is why it appears in the build list, and why a floor for it exists.

---

## Coding Patterns

### Pattern: let `go.mod` be the single source of truth

Do not keep a separate notes file of "which versions we use." `go.mod` plus `go list -m all` is authoritative. If you want a snapshot for a release, capture the output of `go list -m all`:

```bash
go list -m all > versions-at-release-v2.3.txt
```

### Pattern: upgrade deliberately, then tidy

Upgrading is a two-step habit:

```bash
go get example.com/foo@v1.5.0
go mod tidy
```

`go get` raises the floor; `go mod tidy` cleans up indirect requires that are no longer needed (or adds ones that now are).

### Pattern: verify the selected version after a change

After any `go get`, confirm what MVS actually selected — it may differ from what you typed if a higher floor exists elsewhere:

```bash
go get example.com/foo@v1.3.0
go list -m example.com/foo   # might show v1.5.0 if a dependency floors it higher
```

### Pattern: do not fight MVS with manual edits

Resist hand-editing version numbers in `go.mod` to "force" a version down below an existing floor. MVS will reselect based on the graph; a floor set by a dependency cannot be undone by lowering *your* line. Use `go get` (and, later, `exclude`/`replace` for advanced cases) instead.

---

## Clean Code

- **Keep your direct `require` lines meaningful.** They are floors you own. A floor higher than necessary forces newer versions on the whole graph; a floor lower than what you tested is a lie.
- **Run `go mod tidy` after every dependency change.** It keeps `// indirect` lines accurate and removes dead floors.
- **Do not commit a `go.mod` with floors you cannot explain.** If you cannot say why a `require` line exists, `go mod why` will tell you.
- **Prefer `go get` over editing `go.mod` by hand.** The tool keeps `go.sum` and indirect requires consistent; manual edits drift.
- **Commit `go.mod` and `go.sum` together.** The first fixes the versions (via MVS); the second verifies their bytes. They are a pair.

---

## Error Handling

MVS itself rarely errors — it is a deterministic computation. The errors you meet are *around* it.

### "missing go.sum entry for module providing package"

MVS selected a version, but `go.sum` has no hash for it. Cause: you edited `go.mod` without running tidy, or added an import. Fix:

```bash
go mod tidy
```

### "module ... found, but does not contain package ..."

A floor names a module that does not provide the package you import (often a version mismatch). Fix: `go get` the correct version, or correct the import path.

### "ambiguous import" / "found in multiple modules"

Two modules in the graph both claim to provide a package — usually a `v2` migration done halfway. Fix: ensure import paths use the right major-version suffix (`/v2`). MVS treats `foo` and `foo/v2` as *different* modules.

### `go: updates to go.mod needed; to update it, run: go mod tidy`

You built with `-mod=readonly` (the default since Go 1.16) and the build wanted to add or change a floor. MVS noticed an import with no satisfying `require` line. Fix: `go mod tidy`. The error is protective, not arbitrary.

### "version ... invalid: unknown revision"

You `go get`'d a version that does not exist as a tag. MVS cannot floor at a version it cannot resolve. Fix: check the available tags (`go list -m -versions example.com/foo`).

---

## Security Considerations

- **MVS will not auto-patch you.** A CVE fix in `v1.4.3` does *not* reach your build if your floor is `v1.4.0` and nothing in the graph raised it. You must `go get example.com/foo@v1.4.3` (or `go get -u`). This is the security cost of reproducibility.
- **Lower floors can hide vulnerabilities.** Because MVS picks the minimum that satisfies everyone, a build can sit on an old, vulnerable version indefinitely. Run `govulncheck ./...` regularly to surface this.
- **`go.sum` still protects the bytes.** MVS chooses *which* version; `go.sum` ensures the bytes you got for that version match what was recorded. A malicious proxy cannot swap in tampered code without `go.sum` flagging it.
- **Raising a floor is the patch mechanism.** To respond to an advisory, you raise the relevant `require` floor (directly or via an `// indirect` line) and re-tidy. The diff is reviewable.
- **Beware `replace` undermining selection.** A `replace` directive overrides MVS entirely for that module — handy for forks, but it means the selected version is no longer what the graph says. Audit `replace` lines carefully.

---

## Performance Tips

- **MVS is cheap.** Selection is a graph walk taking the max per module — no backtracking, no solver. It is not a build-time bottleneck.
- **The expensive part is *loading* the graph**, not selecting from it: fetching every dependency's `go.mod` to read its floors. Modern Go prunes this aggressively (module graph pruning, Go 1.17+) so it rarely loads the *whole* transitive graph.
- **A warm module cache makes graph loading instant.** Once `go.mod` files are cached locally, recomputing the build list is near-instant.
- **`go list -m all` is fast** because it just reports the already-computed build list; it does not re-download anything if the cache is warm.

---

## Best Practices

1. **Treat `require` lines as floors you own.** Set them to versions you actually tested against.
2. **Upgrade with `go get`, never by editing `go.mod` to force a version down.** MVS reselects from the graph; manual lowering below a floor does nothing.
3. **Run `go mod tidy` after every dependency change.** Keep indirect requires honest.
4. **Use `go list -m all` to confirm the selected versions** — the result of MVS, not your intent.
5. **Use `go mod why` to justify every dependency** before committing a `go.mod` change.
6. **Run `govulncheck` regularly**, because MVS will not patch you automatically.
7. **Commit `go.mod` and `go.sum` together**; the first selects, the second verifies.
8. **Remember `v2+` modules have a path suffix** (`/v2`). MVS treats different majors as different modules entirely.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Expecting the latest version

You add a dependency and are surprised it is not the newest release. MVS picks the *minimum* that satisfies the graph. If you want newer, raise the floor explicitly with `go get foo@latest`.

### Pitfall 2 — `go get foo@v1.9.0` but the build still uses something else

If a dependency floors `foo` *higher* than `v1.9.0`, MVS keeps the higher one. Conversely, if you `go get` a version *lower* than an existing floor, your direct require changes but the selected version may not drop. Always check `go list -m foo`.

### Pitfall 3 — Major versions are separate modules

`github.com/foo/bar` and `github.com/foo/bar/v2` are **different modules** to MVS. They can both be in your build list at once. There is no "conflict" — they coexist. This surprises people expecting one version of "bar."

### Pitfall 4 — `// indirect` lines you did not write

`go mod tidy` and `go get` add `// indirect` requires to raise floors for transitive dependencies. They are normal. Do not delete them by hand; tidy manages them.

### Pitfall 5 — Thinking MVS will downgrade for you

MVS never picks a version *below* a floor. If an old build worked with `v1.2.0` but a dependency now floors `foo` at `v1.5.0`, you get `v1.5.0`. To go lower, you must remove or lower the floor that forces it (sometimes impossible without `exclude`/`replace`).

### Pitfall 6 — Pseudo-versions look scary but are normal

Sometimes a floor is a long string like `v0.0.0-20230101120000-abcdef123456`. That is a *pseudo-version* — a stand-in for an untagged commit. MVS compares it like any other version. It is normal; do not panic.

### Pitfall 7 — `+incompatible` suffix

A module at `v2.0.0+incompatible` is a `v2` module that does *not* use the `/v2` path suffix (usually pre-modules code). MVS handles it, but it is a sign of an older dependency. Just know that `+incompatible` is part of the version string.

---

## Common Mistakes

- **Editing a version number down in `go.mod` to "downgrade,"** then being confused when the build list does not change (a higher floor in the graph wins).
- **Assuming `go build` upgrades dependencies.** It does not. Only `go get` (and `go get -u`) raise floors.
- **Deleting `// indirect` lines** thinking they are clutter. They are floors; tidy will re-add them.
- **Confusing the build list with the module graph.** The graph has *all* the edges/floors; the build list has *one* selected version per module.
- **Expecting a version range syntax** like `^1.2.0`. Go modules has none — a `require` is a single floor.
- **Forgetting that `v2+` needs a `/v2` import path,** then getting "ambiguous import" or "does not contain package."
- **Believing a new upstream release will fix your build.** It will not, until you `go get` it.

---

## Common Misconceptions

> *"Go uses the latest version of each dependency."*

No. Go uses the **minimum** version that satisfies all the floors in the graph — the highest of the minimums, never the latest available.

> *"I need a lockfile to get reproducible builds."*

No. `go.mod` plus MVS *is* the lock. The versions are fully determined by the `require` lines. `go.sum` verifies the bytes; it does not select versions.

> *"`go.sum` chooses my versions."*

No. MVS chooses versions; `go.sum` records hashes of the chosen versions' bytes for integrity checking.

> *"A `require` line pins an exact version."*

No. It sets a *minimum*. The selected version can be higher if something else floors it higher.

> *"If I `go get foo@v1.0.0`, my build uses v1.0.0."*

Only if no other floor in the graph is higher. If a dependency requires `foo v1.4.0`, MVS still selects `v1.4.0`.

> *"MVS solves a constraint puzzle like npm or Cargo."*

No. There is no SAT solver, no backtracking. MVS takes the maximum required version per module. That is why it is fast and deterministic.

> *"`v1` and `v2` of a module conflict."*

No. They are different modules (different import paths). Both can appear in the build list.

---

## Tricky Points

- **"Minimal" describes the *result*, not the *intent*.** MVS selects the *smallest* version that still satisfies every floor — which, across the graph, is the *largest* floor anyone set. Small relative to "latest available"; large relative to any single requirement.
- **The main module's floors usually win for direct deps.** Your `go.mod`'s `require` for a direct dependency is typically the highest floor for it, so you "control" its version — until a transitive dependency floors it higher.
- **Indirect requires exist mainly to raise floors.** When `go mod tidy` adds `// indirect`, it is recording a floor needed for reproducibility, often higher than any single dependency would set on its own.
- **The `go` directive matters.** `go 1.17+` enables module graph *pruning*, which changes *how much* of the graph MVS loads (not the result for a tidy module). More on this in middle/professional levels.
- **MVS never consults the latest tag list to make a decision.** It only ever looks at versions named in `go.mod` files in the graph. `@latest` resolves a tag *before* handing a concrete version to the floor logic.
- **Downgrading is a real, separate MVS operation** that may need to *remove* requirements that depended on the higher version — more subtle than upgrading.

---

## Apply it

1. Choose one small, known input for **Minimal Version Selection (MVS)**.
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

- What problem does Minimal Version Selection (MVS) solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
