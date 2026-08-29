# Module Versioning — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Module Versioning** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### A version is a string with three numbers

`v1.2.3` means major=1, minor=2, patch=3. Read it left-to-right; bigger numbers on the left win in comparisons. `v1.10.0` is *newer* than `v1.9.99` — these are not decimal numbers.

### The `v` is part of the syntax

`v` is not optional, not capitalised, not stylistic. The Go toolchain sees `1.2.3` and treats it as garbage. It sees `v1.2.3` and parses it as a version. This is the single most common first-time mistake — both for tagging your own module and for pinning someone else's.

### A tag in Git becomes a version in Go

```bash
git tag v0.1.0
git push --tags
```

Two commands. Now `v0.1.0` of your module exists. Anyone with the URL can:

```bash
go get example.com/yourmodule@v0.1.0
```

There is no `go publish`. There is no registry to upload to. The Git tag *is* the publish.

### `MAJOR` carries the breaking-change promise

Semver compresses your release notes into a number. The audience reads only the number:

| You bumped... | Consumers expect... |
|---------------|---------------------|
| **PATCH** (`v1.2.3` → `v1.2.4`) | Bug fixes only. Safe to upgrade without reading the changelog. |
| **MINOR** (`v1.2.3` → `v1.3.0`) | New features, possibly internal performance improvements. No removals. Safe to upgrade. |
| **MAJOR** (`v1.x.x` → `v2.0.0`) | Breaking changes. Read the changelog. Possibly rewrite calls. |

Break the contract — bump major when you should have bumped minor, or rename a function in a patch release — and consumers stop trusting your numbers. You do not get the trust back.

### `v0.x.x` is the "I am still figuring it out" zone

While your module is at `v0`, you are excused from the no-breaking-changes rule. `v0.1.0` to `v0.2.0` may break the API completely. The community knows this; new projects start at `v0` for a reason.

The moment you tag `v1.0.0`, the floor changes. From then on, breaking changes mean a new major.

### `v2+` requires a path change

This is the rule that surprises everyone the first time. When you bump to `v2`:

- The module path in `go.mod` must end with `/v2`: `module github.com/alice/csvkit/v2`.
- Consumers must change their imports to include `/v2`.
- You tag `v2.0.0` on the same repo, but it lives at a "new" import path.

`v0`, `v1` — no path suffix. `v2`, `v3`, ... — path suffix mandatory. We dig into this rule in [middle.md](middle.md) and [senior.md](senior.md). For now: know it exists, know it bites if forgotten.

### `go.mod` records every dependency's version

Open any `go.mod` and you will see lines like:

```
require (
    github.com/google/uuid v1.6.0
    github.com/spf13/cobra v1.8.0
    github.com/stretchr/testify v1.9.0
)
```

Each line says: "I want exactly this module at exactly this version." When you build, the toolchain finds those exact versions in the cache, hashes them against `go.sum`, and links them in. Versions are not negotiable at build time; they are decided when the line is written.

---

## Code Examples

### Example 1 — Tagging a fresh module

```bash
mkdir hello && cd hello
go mod init github.com/alice/hello
cat > hello.go <<'EOF'
package hello

// Greet returns a greeting for name.
func Greet(name string) string { return "Hello, " + name + "!" }
EOF

git init
git add .
git commit -m "initial"
git tag v0.1.0
git push origin main --tags
```

`v0.1.0` of `github.com/alice/hello` now exists. Anyone with the URL can run `go get github.com/alice/hello@v0.1.0`.

### Example 2 — A `go.mod` after `v0.1.0`

```
module github.com/alice/hello

go 1.22
```

That is the whole file. Module path, Go version. No `require` lines (no dependencies yet). Versioning lives in Git, not in `go.mod`.

### Example 3 — Bumping to `v0.2.0` after adding a feature

```go
// hello.go (additive change: new exported function)
package hello

func Greet(name string) string { return "Hello, " + name + "!" }

// GreetFormal returns a more polite greeting.
func GreetFormal(name string) string { return "Good day, " + name + "." }
```

```bash
git add hello.go
git commit -m "add GreetFormal"
git tag v0.2.0
git push --tags
```

Even though `v0` does not require strict semver, you can still follow it — and you should. Habits formed at `v0` make `v1` easier.

### Example 4 — Bumping to `v1.0.0`

You have iterated enough. The API feels right. You commit to it.

```bash
git tag v1.0.0
git push --tags
```

From this commit onwards:
- Patch: `v1.0.1`, `v1.0.2`, ... — bug fixes only.
- Minor: `v1.1.0`, `v1.2.0`, ... — new features.
- Major: `v2.0.0` — only if you are willing to change the module path.

### Example 5 — A patch release for a bug fix

```go
// before
func Greet(name string) string { return "Hello,  " + name + "!" } // bug: two spaces

// after
func Greet(name string) string { return "Hello, " + name + "!" }
```

```bash
git commit -am "fix double space in Greet"
git tag v1.0.1
git push --tags
```

API is unchanged. Behaviour matches the docs more closely. Patch is correct.

### Example 6 — A minor release for a new feature

```go
// new exported function — additive
func GreetMany(names []string) []string { ... }
```

```bash
git tag v1.1.0
git push --tags
```

Existing callers of `Greet` and `GreetFormal` are untouched. Minor bump is correct.

### Example 7 — Reading a `require` line

```
require (
    github.com/google/uuid v1.6.0
    golang.org/x/text v0.14.0
)
```

Translation:
- "I depend on `github.com/google/uuid` at exactly `v1.6.0`."
- "I depend on `golang.org/x/text` at exactly `v0.14.0`."

The build will fail loudly if those exact versions cannot be located.

### Example 8 — Looking at a tagged version remotely

```bash
go list -m -versions github.com/google/uuid
```

Output (excerpt):

```
github.com/google/uuid v1.0.0 v1.1.0 v1.2.0 v1.3.0 v1.4.0 v1.5.0 v1.6.0
```

Every tagged release of the module, sorted oldest-to-newest. Useful for "is there a newer version?" without leaving the terminal.

### Example 9 — The `v2+` import path

Suppose you bump `csvkit` to `v2`. Your `go.mod` becomes:

```
module github.com/alice/csvkit/v2

go 1.22
```

Note the `/v2`. Consumers now write:

```go
import "github.com/alice/csvkit/v2"
```

The repository URL on GitHub is unchanged (`github.com/alice/csvkit`), but the *import path* gains `/v2`. This is the rule that catches everyone the first time.

### Example 10 — A `go.mod` that depends on multiple majors

```
require (
    github.com/alice/csvkit v1.5.0
    github.com/alice/csvkit/v2 v2.0.0
)
```

Both can coexist in one binary, because Go treats them as different modules. Usually a code smell — you are migrating from v1 to v2 and you have not finished — but legal.

---

## Coding Patterns

### Pattern 1 — Start at `v0.1.0`, not `v0.0.1` and not `v1.0.0`

`v0.1.0` says "this is the first published thing, and I am still iterating." It gives you minor and patch room (`v0.1.1`, `v0.2.0`) without committing to stability. Going straight to `v1.0.0` on the first commit is a promise you cannot keep.

### Pattern 2 — Tag on `main`, not on a feature branch

Tags should point at a commit on the line of code people will see. Tagging a feature branch creates orphan versions that confuse consumers and tools.

### Pattern 3 — Bump deliberately, in a separate commit

A "release commit" is often:

```
chore(release): v1.2.0
```

Empty content (or just a CHANGELOG update). Tag immediately after. This makes the release point obvious in `git log`.

### Pattern 4 — Write down the change category before tagging

Ask yourself: "Is this change additive, a bug fix, or a breaking change?" The answer dictates which number bumps. Do not rush this — once tagged, the contract is set.

### Pattern 5 — Treat `v1.0.0` as a milestone

It deserves a CHANGELOG entry, a README "stable" note, and a public announcement. Most libraries do not skip from `v0.x` to `v1.0.0` casually.

---

## Clean Code

- **Use exact tags.** `v1.2.3`, not `1.2.3`, not `v1.2.3-final`, not `v1.2.3.0`. The Go toolchain only understands the canonical form.
- **One tag per release.** Do not create both `v1.0` and `v1.0.0` for the same commit; pick the canonical `vMAJOR.MINOR.PATCH`.
- **Annotated tags are fine but not required.** `git tag -a v1.0.0 -m "..."` adds a tag message; `git tag v1.0.0` does not. Both work for Go.
- **Sign tags if you can.** `git tag -s v1.0.0` produces a GPG-signed tag. This is good hygiene for serious projects.
- **Write a CHANGELOG.** Each release entry should list what changed in plain English, even for v0.

---

## Error Handling

Common version-related errors and what they mean.

### "invalid version: must begin with v"

```
go get github.com/foo/bar@1.2.3
go: github.com/foo/bar@1.2.3: invalid version: must begin with v
```

You forgot the `v`. Use `@v1.2.3`.

### "no matching versions for query"

```
go get github.com/foo/bar@v9.9.9
go: github.com/foo/bar@v9.9.9: no matching versions for query "v9.9.9"
```

That tag does not exist on the upstream. Run `go list -m -versions github.com/foo/bar` to see what is available.

### "module declares its path as ... but was required as ..."

```
require github.com/alice/csvkit/v2 v2.0.0
go: github.com/alice/csvkit/v2@v2.0.0: module declares its path as: github.com/alice/csvkit
```

The library's `go.mod` still says `module github.com/alice/csvkit` (no `/v2`), but you are trying to import `/v2`. The maintainer forgot to update the module path when bumping to v2. They need to fix it; you cannot.

### "checksum mismatch"

```
verifying github.com/foo/bar@v1.2.3: checksum mismatch
```

The bytes downloaded for `v1.2.3` do not match what `go.sum` recorded earlier. Possible causes: a maintainer force-pushed the tag (illegal), the proxy was tampered with (rare), or your local cache is corrupted. Try `go clean -modcache` and retry. If it persists, do not trust the source.

### Tag missing the `v`

```bash
git tag 1.2.3
go list -m github.com/me/lib@v1.2.3
go: github.com/me/lib@v1.2.3: no matching versions
```

Your tag is `1.2.3`. Go cannot see it. Re-tag as `v1.2.3` and push.

---

## Security Considerations

- **`go.sum` is your tamper detector.** Every version that appears in `go.mod` has a hash entry in `go.sum`. If anyone swaps the bytes for a published version, the hashes will not match and your build fails. Commit `go.sum`.
- **Never reuse a tag.** Force-pushing `v1.0.0` to a different commit is a supply-chain hazard. Some users will get the old bytes (cached); some the new. The proxy may even refuse the move. If you need to fix `v1.0.0`, ship `v1.0.1`.
- **Pin majors carefully.** A bot that auto-bumps minor versions of your dependencies is a small risk; one that auto-bumps majors is a large risk. Major bumps mean the API may have changed and the new code may behave differently.
- **Watch for typo-squat majors.** `github.com/foo/bar/v22` is not the same module as `github.com/foo/bar/v2`. Copy-paste import paths from authoritative sources.
- **Treat `v0` libraries with mild suspicion in production.** A `v0` library has no stability promise. That does not make it unsafe, but it does mean the next minor release may break your code. Read the README for the project's stance.

---

## Performance Tips

- **A bumped version invalidates the proxy cache for that path.** If you tag `v1.0.1`, the next `go get` populates the cache for `v1.0.1`. Existing builds that pin `v1.0.0` are unaffected.
- **Listing versions is one round-trip.** `go list -m -versions github.com/foo/bar` is a single proxy request; cheap, scriptable, useful in CI to detect drift.
- **A bigger version number is not slower.** `v1` and `v17` build at the same speed. Performance has nothing to do with the version string.
- **Pseudo-versions cost the proxy slightly more on first fetch** (it has to compute one), but for everyday work the difference is invisible.

---

## Best Practices

1. **Always use `v` prefix.** `v1.2.3`, never `1.2.3`.
2. **Tag on the canonical branch (`main` / `master`).** Not on feature branches.
3. **One tag per release.** No `v1.0`, no `v1.0.0-final`, just `v1.0.0`.
4. **Start at `v0.1.0`.** Iterate. Bump to `v1.0.0` only when you are ready to keep promises.
5. **Bump major only when you must.** Renaming a function for aesthetics is not a major-bump reason.
6. **Patch fixes bugs. Minor adds features. Major breaks. Stick to the pattern.**
7. **Tag annotated and (ideally) signed.** `git tag -a -s vX.Y.Z -m "..."`.
8. **Push tags explicitly.** `git push --tags` (or `git push origin vX.Y.Z`).
9. **Never move a tag.** Once it is pushed, it is forever.
10. **Write a CHANGELOG.** A short note per release saves future-you from rediscovery.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Forgetting the `v` in a tag

You ran `git tag 1.0.0`. From Git's perspective everything is fine. From Go's perspective, no `v1.0.0` tag exists for your module. Re-tag as `v1.0.0` and push. The bad tag can stay or be removed; Go ignores it either way.

### Pitfall 2 — Tagging the wrong commit

You tagged `v1.0.0` on a draft commit, not on the polished one. The fix is *not* to move the tag — it is to make a new commit and tag `v1.0.1`. Moving tags breaks the immutability promise.

### Pitfall 3 — Skipping `v0` and going straight to `v1.0.0`

Nothing in Go forbids it, but if your API has not stabilised, you will regret it. Spend at least one round of `v0.x` releases before committing.

### Pitfall 4 — Bumping minor when the change is breaking

You renamed a function. You think it is a minor change because the *intent* is the same. It is not — your consumers' code no longer compiles. That is the textbook definition of a breaking change. Bump major.

### Pitfall 5 — Releasing `v2.0.0` without changing the module path

Tagging `v2.0.0` on a `go.mod` that still says `module github.com/alice/csvkit` produces an unusable release. Go's toolchain will reject it with "module declares its path as ... but was required as ...". The fix is to update the module path to include `/v2` and re-tag.

### Pitfall 6 — Tagging `v1` instead of `v1.0.0`

Some Git workflows use short tags like `v1` or `v1.0`. Go expects exactly three numbers. `v1.0` is not a Go module version. Always use `vMAJOR.MINOR.PATCH`.

### Pitfall 7 — Confusing release tag with annotation tag

`git tag v1.0.0` (lightweight) and `git tag -a v1.0.0 -m "..."` (annotated) both work for Go. The proxy does not care. Annotated tags are nicer for humans because they carry a message; pick one and be consistent.

### Pitfall 8 — Pushing without `--tags`

```bash
git tag v1.0.0
git push origin main
```

The branch is pushed. The tag is *not*. Consumers cannot find `v1.0.0` because no remote tag exists. Use `git push origin v1.0.0` or `git push --tags`.

---

## Common Mistakes

- **Writing `1.2.3` instead of `v1.2.3` in a `go get` command.**
- **Tagging on a branch other than `main` and forgetting which branch the tag lives on.**
- **Releasing a major bump as a patch because "the change feels small."**
- **Going from `v0` to `v1` without a CHANGELOG entry — consumers do not know what stabilised.**
- **Moving a tag after release because "we found a bug." (Make a new patch instead.)**
- **Forgetting `/v2` in the module path when bumping major.**
- **Pushing the branch but not the tag.**
- **Tagging a commit that does not build.**
- **Using `v1.0.0-rc1` (pre-release) and then never publishing `v1.0.0` — leaves consumers stuck on a release candidate.**

---

## Common Misconceptions

> *"`go.mod`'s `go 1.22` line is the version of my module."*

No. That line is the *minimum Go toolchain version* needed to build the module. The version of your module is whatever Git tag you push.

> *"Bigger version number means newer release, always."*

Mostly. Pre-release tags (`v1.2.3-alpha.1`) sort *before* the corresponding release (`v1.2.3`). Pseudo-versions can sit between two real versions.

> *"`v1.0` and `v1.0.0` are the same."*

Not to Go. Go expects `vMAJOR.MINOR.PATCH` — three numbers. `v1.0` is not a recognised Go module version.

> *"I have to use semver — Go enforces it."*

Go enforces the *format*. It does not enforce the *meaning*. Nothing stops you from breaking compatibility in a patch release. Consumers (and `go mod`) will be deeply confused, and your reputation will pay, but Go itself will not stop you. Discipline is on you.

> *"Once I publish `v1.0.0`, I can never break the API again."*

You can — but only by bumping to `v2.0.0` and changing the module path to `/v2`. The path change is the safety mechanism that lets `v1` and `v2` coexist.

---

## Tricky Points

- **The leading `v` is part of the version everywhere except in some prose.** Some docs write "version 1.2.3"; the toolchain wants `v1.2.3`. When in doubt, include the `v`.
- **Pre-releases sort before the matching release.** `v1.2.3-alpha.1 < v1.2.3 < v1.2.4-alpha.1`.
- **`v0.x.x` sorts below `v1.0.0-anything`.** Major dominates everything.
- **Comparing versions is left-to-right numeric, not string-lexicographic.** `v1.10.0` > `v1.9.99`.
- **Pseudo-versions are a Go invention, not part of upstream semver.** Looks like `v0.0.0-20240612103515-abc123def456`. We cover them in [middle.md](middle.md).
- **A tag that already exists upstream is **immutable** for you.** Do not retag; ship a patch.
- **The path to `v2+` modules contains `/v2`, but the *Git repo URL* does not.** The repo is still `github.com/alice/csvkit`; the *import* is `github.com/alice/csvkit/v2`.

---

## Apply it

1. Choose one small, known input for **Module Versioning**.
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

- What problem does Module Versioning solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
