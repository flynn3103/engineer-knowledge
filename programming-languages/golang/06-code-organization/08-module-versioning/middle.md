# Module Versioning — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Module Versioning** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Pseudo-Versions

A *pseudo-version* is a synthetic version Go invents when you reference a commit that has no tag. It looks like:

```
v0.0.0-20240612103515-abc123def456
```

Three pieces, separated by dashes:

| Piece | Meaning |
|-------|---------|
| `v0.0.0` | Base version. The most recent tag *before* this commit, or `v0.0.0` if none. |
| `20240612103515` | Commit timestamp in UTC, `YYYYMMDDHHMMSS`. |
| `abc123def456` | The first 12 hex characters of the commit hash. |

Go orders pseudo-versions like normal versions: the timestamp puts them in chronological order even though `v0.0.0-...` looks like the lowest possible version.

### When pseudo-versions appear

You did not tag the commit, but someone wrote `go get example.com/lib@<commit-or-branch>`. Examples:

```bash
go get example.com/lib@main
go get example.com/lib@abc123d
go get example.com/lib@HEAD
```

Each resolves to the latest commit on that ref. `go.mod` ends up with a `require` line like:

```
require example.com/lib v0.0.0-20240612103515-abc123def456
```

### Three flavours of base version

Pseudo-versions inherit a base from the nearest tag *behind* the commit:

| Situation | Pseudo-version base |
|-----------|---------------------|
| No tags at all | `v0.0.0-<ts>-<hash>` |
| Latest tag before is `v1.5.0`, commit is on `main` | `v1.5.1-0.<ts>-<hash>` |
| Latest tag before is `v1.5.0`, commit is on a release-branch with v2.x | `v2.0.0-...` (depending on where on the v2 line) |

The base matters because comparison and MVS rely on it. A pseudo-version of `v1.5.1-0.<ts>-<hash>` is greater than `v1.5.0` but less than `v1.5.1`.

### Computing a pseudo-version yourself

You usually do not — `go get @<ref>` does it for you. But for understanding:

```
v<base>-<timestamp>-<hash[:12]>
```

The timestamp is the *commit timestamp*, not the local clock. The hash is the first 12 hex characters of the commit SHA, lowercase.

### When to use pseudo-versions

| Use case | Recommended? |
|----------|--------------|
| Trying out a fix that is on `main` but not yet released | Yes, briefly |
| Pinning a never-tagged module | Necessary |
| Production dependency you control | No — tag a release instead |
| Production dependency you do not control | Avoid — open an issue and ask for a tag |

### What goes wrong

- **The branch moves.** `go get lib@main` today and tomorrow may resolve to different commits.
- **The hash you typed doesn't exist.** `go get lib@deadbeef` fails noisily.
- **Pseudo-version sorts in unexpected places.** A pseudo-version with base `v1.5.1-0.<ts>` beats `v1.5.0` in MVS — sometimes that is what you want, sometimes not.

---

## Pre-release Versions

A pre-release is a tagged version with a suffix:

```
v1.0.0-alpha.1
v1.0.0-beta.3
v1.0.0-rc.2
v1.2.3-pre.20240612
```

Format: `vMAJOR.MINOR.PATCH-SUFFIX` where `SUFFIX` is dot-separated identifiers. Each identifier may be alphanumeric or numeric.

### Ordering rules

Pre-releases sort *before* the corresponding release:

```
v1.0.0-alpha.1 < v1.0.0-alpha.2 < v1.0.0-beta.1 < v1.0.0-rc.1 < v1.0.0
```

Within a pre-release suffix, identifiers compare:

- Numeric identifiers numerically: `alpha.2 < alpha.10`.
- Alphanumeric identifiers lexicographically: `alpha < beta < rc`.
- Numeric < alphanumeric when they collide at the same position.

### `@latest` ignores pre-releases

```bash
go get example.com/lib@latest
```

Picks the highest *non-pre-release* tag. Consumers must explicitly ask:

```bash
go get example.com/lib@v1.0.0-rc.1
```

This is the safety net: a casual `go get -u` will not pull in a release candidate by accident.

### When to publish a pre-release

- **Major version dry runs.** Cut `v2.0.0-rc.1` two weeks before `v2.0.0`. Volunteers test it; you fix issues in `v2.0.0-rc.2`; you tag `v2.0.0` when stable.
- **Risky feature in a minor.** `v1.5.0-beta.1` lets early adopters try without committing the wider audience.

### When NOT to publish a pre-release

- For everyday bug fixes — just tag the release.
- As an alternative to `v0.x` — pre-releases are more confusing than `v0.x` for genuinely-experimental code.

---

## Build Metadata

Semver allows a `+meta` suffix:

```
v1.2.3+darwin.arm64
v1.0.0+20240612.commit-abc
```

Go *parses* build metadata but *ignores it for ordering*. `v1.2.3+a` and `v1.2.3+b` are the same version to MVS. In practice, build metadata is rarely used in Go modules — you can put metadata in your CHANGELOG instead.

---

## Upgrading Dependencies

Five common upgrade commands:

```bash
# Upgrade one dep to its latest tagged release
go get example.com/lib@latest

# Upgrade one dep to a specific version
go get example.com/lib@v1.6.0

# Upgrade all direct deps to the latest minor/patch within their majors
go get -u ./...

# Upgrade only patch versions
go get -u=patch ./...

# See what would be upgraded
go list -m -u all
```

`go list -m -u all` annotates each dep with the latest available version:

```
github.com/google/uuid v1.3.0 [v1.6.0]
github.com/spf13/cobra v1.7.0 [v1.8.0]
github.com/stretchr/testify v1.9.0
```

`[vX.Y.Z]` after the current version is the latest available. Lines without brackets are already up-to-date.

### Reading the diff

After `go get -u ./...`, `git diff go.mod` is your inspection point:

```diff
- require github.com/google/uuid v1.3.0
+ require github.com/google/uuid v1.6.0
```

The `go.sum` diff is much larger because hashes change. That is normal.

### Run tests after every upgrade

A semver-respecting library should not break you on a minor upgrade. Should-not is not will-not. Run `go test ./...` immediately. Roll back with `go get pkg@<previous>` if anything breaks.

### `go get -u` is transitive-aware

`go get -u ./...` upgrades the modules your *code* needs (direct dependencies). `go get -u=patch ./...` is the same but constrained to patch bumps. Indirect dependencies are bumped only as needed to satisfy the direct ones.

---

## Downgrading Dependencies

```bash
go get example.com/lib@v1.5.0   # downgrade if currently > v1.5.0
go get example.com/lib@v1.5.0~  # downgrade and pin "no higher than"
```

(The `~` query is a niche feature — it limits the version to v1.5.x. Most teams pin exact versions instead.)

Downgrading triggers MVS to re-evaluate. If another dep requires `v1.6.0`, MVS will pick `v1.6.0` regardless. Downgrade fights are a sign you have an underlying conflict.

---

## The `replace` Directive

`replace` redirects an import path to a different module path or version. It lives in `go.mod`:

```
replace github.com/foo/bar => github.com/myfork/bar v1.6.0
```

After this line, every reference to `github.com/foo/bar` in the build resolves to `github.com/myfork/bar v1.6.0`.

### Three common shapes

```
# 1. Redirect to a fork (same module path inside the fork)
replace github.com/foo/bar => github.com/myfork/bar v1.6.0

# 2. Redirect to a local path (for development against a sibling module)
replace github.com/foo/bar => ../bar

# 3. Pin to a specific version even if MVS would pick something else
replace github.com/foo/bar => github.com/foo/bar v1.5.0
```

### When to use `replace`

- **Working on two modules simultaneously.** Point your app at a local path while you iterate on the dependency.
- **Patching a critical bug in a dep that has not released.** Use a fork until the upstream cuts a release.
- **Working around a broken release.** Pin to a known-good version even when MVS wants newer.

### When NOT to use `replace`

- **As a permanent workaround.** A `replace` line in committed `go.mod` is a maintenance debt. Audit them quarterly.
- **In a library you publish.** `replace` directives in *your* `go.mod` are *not* respected by consumers — they only apply to the *main* module being built. A `replace` in a library is silent dead code; a `replace` in an application is the directive being used as intended.
- **To skip a version of your own module.** Use `retract` instead.

### Local-path replace

```
replace github.com/alice/lib => ../lib
```

The `go.mod` at `../lib` is read directly; no version is needed. This is the standard "I am editing both modules at once" workflow.

Once you ship, replace these lines with a tagged release:

```
replace github.com/alice/lib => github.com/alice/lib v1.7.0
```

Or remove the `replace` and pin via `require`:

```
require github.com/alice/lib v1.7.0
```

### `replace` does not propagate to downstream consumers

This is the single most-missed fact about `replace`. If you publish a library that contains `replace github.com/foo/bar => github.com/myfork/bar v1.0.0`, your consumers will *not* be redirected. They will pick `github.com/foo/bar` themselves. `replace` lines only apply when *your* module is the main module being built.

If you need to bake in a fork, change your imports to point at the fork directly. Or contribute the fix upstream.

---

## The `exclude` Directive

`exclude` tells MVS "never pick this version, even if some dep requires it":

```
exclude github.com/foo/bar v1.4.0
```

If MVS would otherwise pick `v1.4.0`, it picks the next-higher acceptable version instead. Used to avoid a known-broken release while letting normal upgrade semantics work.

Less common than `replace`. Use sparingly.

---

## The `retract` Directive

`retract` is the reverse of `exclude`: *you* (the publisher) declare a version of *your own* module should not be used.

```go
// in YOUR go.mod, on a tagged release after the bad one
module github.com/alice/csvkit

go 1.22

retract v1.4.0          // panics on empty input — use v1.4.1
retract [v1.3.0, v1.3.5] // wrong CSV escaping in headers
```

After consumers run `go list -m -u`, retracted versions are flagged:

```
example.com/lib v1.4.0 (retracted)
```

`@latest` skips retracted versions. Existing builds that pin a retracted version still work; the bytes remain accessible. Retraction is informational, not destructive.

A retracted version cannot be unretracted directly; you would have to ship another release that removes the retraction. (`retract` lines in the *latest* version are authoritative.)

---

## Module Resolution Walk-Through

Suppose your `go.mod` looks like:

```
module example.com/myapp

go 1.22

require (
    github.com/foo/bar v1.5.0
    github.com/baz/qux v0.7.0
)
```

And `github.com/foo/bar` v1.5.0 has its own `go.mod`:

```
require github.com/baz/qux v0.6.0
```

When you run `go build`, here is what the toolchain does:

1. Read your `go.mod`. Direct deps: `bar v1.5.0`, `qux v0.7.0`.
2. Read each direct dep's `go.mod`. `bar` requires `qux v0.6.0`.
3. **Build the requirement graph.** Two `qux` requirements: `v0.6.0` (transitive) and `v0.7.0` (direct).
4. **Apply MVS.** For each module, pick the highest version anyone requires. `qux` becomes `v0.7.0`.
5. **Resolve recursively.** Apply the same rule for `qux v0.7.0`'s dependencies, then theirs, until the graph is closed.
6. **Apply `replace` and `exclude`.** Any `replace` in *your* `go.mod` overrides the chosen version. `exclude` filters out forbidden versions.
7. **Validate `go.sum`.** Each chosen version's hashes must match `go.sum`. If `go.sum` lacks the version, error out (run `go mod download` or `go mod tidy` first).

Output: an exact, deterministic build graph. The same `go.mod` + `go.sum` produces bit-identical builds anywhere.

### Why MVS is "minimum"

The "Minimum" in MVS is misleading at first. It picks the *minimum version that satisfies all requirements*. In practice, that means the *highest required version* — because if anyone requires `v1.5.0`, then `v1.4.0` is no longer enough.

### Comparing MVS to npm's resolution

| Aspect | npm | Go modules |
|--------|-----|-----------|
| Version per package | One per node in tree (multiple copies allowed) | One per major (single global version) |
| Lockfile | `package-lock.json` | `go.sum` |
| Resolves to | Latest matching `^x.y.z` | Highest required `vX.Y.Z` |
| Determinism | Lockfile required | Always deterministic from `go.mod`+`go.sum` |

Go's model is simpler and more deterministic at the cost of flexibility (no two majors of the same module in the same closure — except via the `/vN` path trick).

---

## Major-Version Coexistence

Because v2+ uses a different import path, you can legally have:

```
require (
    github.com/alice/csvkit v1.5.0
    github.com/alice/csvkit/v2 v2.0.0
)
```

Both modules are in the build. Both have their own types. `csvkit.Reader` and `csvkit/v2.Reader` are *different types*. You cannot pass a `v1` `Reader` to a `v2` function or vice versa.

This is intentional. It lets a large codebase migrate from v1 to v2 file-by-file rather than all at once.

### Common patterns during a migration

- Pin the new module under `/v2` while keeping the v1 dependency.
- Migrate one package at a time.
- Once all internal callers use v2, remove the v1 require line.
- Run `go mod tidy` to clean up.

---

## Multi-Module Repositories

A single Git repository can host multiple modules. Each module has its own `go.mod` in its own subdirectory:

```
github.com/alice/tools/
├── cli/
│   ├── go.mod      (module github.com/alice/tools/cli)
│   └── main.go
└── lib/
    ├── go.mod      (module github.com/alice/tools/lib)
    └── lib.go
```

### Tagging in a multi-module repo

Tags must include the module subdirectory as a prefix:

```bash
git tag cli/v1.2.3      # tags github.com/alice/tools/cli at v1.2.3
git tag lib/v0.5.0      # tags github.com/alice/tools/lib at v0.5.0
git push --tags
```

A plain `v1.0.0` tag (no prefix) is interpreted as the version of a *root* module — only useful if `go.mod` is at the repo root.

### Why multi-module?

- A library with a separate CLI tool that has its own release cadence.
- A "tools" repo with several utilities each evolving at its own pace.
- A monorepo with stable libraries and experimental ones.

### Trade-offs

| Pros | Cons |
|------|------|
| Independent release cadence | More complex tagging |
| Separate dependency closures | More `go.mod` files to maintain |
| Smaller download per module | `replace` between sibling modules during dev |

For a single library, prefer one module. Multi-module is a power tool, not a default.

---

## Workflow Patterns

### Pattern 1 — Upgrade in a separate commit

```
$ go get -u ./...
$ go test ./...
$ git add go.mod go.sum
$ git commit -m "chore(deps): upgrade direct dependencies"
```

A focused commit makes it easy to bisect or revert.

### Pattern 2 — Pin a fix from `main` while you wait for a release

```bash
go get github.com/foo/bar@<commit-hash>
```

Add a comment explaining why:

```
require github.com/foo/bar v1.5.1-0.20240612103515-abc123def456 // pinned: waiting for v1.5.1 (fixes #142)
```

When the release lands:

```bash
go get github.com/foo/bar@v1.5.1
```

Remove the comment.

### Pattern 3 — Local development with a sibling module

```
replace github.com/alice/lib => ../lib
```

Use during development. Add to `.gitignore` if your team forbids committed local replaces, or commit it temporarily and remove before merge.

### Pattern 4 — Retract immediately after a bad release

If you tag `v1.4.0` and discover within minutes that it panics on empty input, ship `v1.4.1` with a retraction:

```
retract v1.4.0   // panics on empty input
```

Consumers running `go list -m -u all` see the retraction; new fetches skip `v1.4.0`.

### Pattern 5 — Pre-release a major bump

```bash
git tag v2.0.0-rc.1
git push --tags
```

Announce: "v2.0.0-rc.1 is up; please test." Two weeks later, after `rc.2` and `rc.3`, tag `v2.0.0`.

### Pattern 6 — Use `go mod tidy` before every commit

`go mod tidy` adds missing requires, removes unused ones, and rewrites `go.sum`. It is the canonical "clean up after dependency work" command. Make it a pre-commit habit.

---

## Common Mistakes

- **Committing a local-path `replace`.** CI breaks because the path does not exist on the build server.
- **Treating pseudo-versions as permanent.** A pseudo-version is a "wait for a tag" placeholder, not a long-term pin.
- **Using `replace` in a library and assuming consumers inherit it.** They do not.
- **Forgetting the `/v2` suffix when bumping major.** Build fails with "module declares its path as ...".
- **Releasing a pre-release as `@latest`.** Pre-releases are skipped by `@latest` queries; consumers cannot find them without explicit version pinning.
- **Multi-module repo with unprefixed tags.** `git tag v1.0.0` in a multi-module repo is ambiguous and may be ignored.
- **Retracting and then re-using the same version number.** A retraction does not free the version; the bytes are still there. Move to the next number.
- **Forgetting to push tags after creating them.** Local-only tags are invisible to consumers.

---

## Tricky Points

- **Pseudo-version base depends on the nearest tag *before* the commit, not after.** A commit between `v1.5.0` and `v1.6.0` produces base `v1.5.1-0.<ts>-<hash>`.
- **`replace` only affects the main module's build.** Library authors who use `replace` for tests must ensure those replaces do not leak into consumers' assumptions.
- **`retract` lines are read from the *latest* version of your module.** If you forget to add a retraction in `v1.4.1` and only add it in `v1.4.2`, `v1.4.2` is the source of truth.
- **`go mod tidy` may pick a different version than `go get` did.** Tidy applies MVS over the full graph; `go get` is more local.
- **Pre-release ordering surprises.** `v1.0.0-alpha.10 > v1.0.0-alpha.2` (numeric), but `v1.0.0-alpha.10 > v1.0.0-alpha.10a` (numeric < alphanumeric).
- **A pseudo-version on a `v0` module looks like `v0.0.0-<ts>-<hash>` even if real `v0.x.y` tags exist before** — only if the commit is *behind* every tag. Pseudo-versions track the *predecessor* tag.

---

## Apply it

1. Find a real component where **Module Versioning** affects an interface or dependency.
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

- Which boundary is most affected by Module Versioning?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
