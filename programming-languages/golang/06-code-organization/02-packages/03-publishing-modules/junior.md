# Publishing Modules — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Publishing Modules** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### Publishing = pushing + tagging

Forget "registries." A Go module is published when two conditions hold:

1. The module's source code lives at a public URL that matches its module path. If `go.mod` says `module github.com/alice/hello`, then `https://github.com/alice/hello` must be a real, public Git repository whose contents include `go.mod` at the root.
2. A Git tag with the right shape (`vMAJOR.MINOR.PATCH`) points to a commit in that repository.

That is the entire mechanical definition.

### Git tags ARE module versions

This is the load-bearing fact of the whole topic: **a Go module's version is a Git tag.** Not a setting in a config file, not an entry in a database — a Git tag.

```bash
git tag v0.1.0
git push --tags
```

After those two lines run successfully, the version `v0.1.0` of your module exists. Anyone, anywhere, can now write:

```bash
go get github.com/alice/hello@v0.1.0
```

and the Go toolchain will fetch the contents of the commit your `v0.1.0` tag points at.

### The `v` prefix is non-negotiable

Go reads `v0.1.0`. It does **not** read `0.1.0`. A tag without the `v` prefix is invisible to the Go module system. This is the single most common first-time publishing mistake.

### The proxy discovers your module on first `go get`

You do not "register" your module anywhere. The first time *anyone* runs `go get example.com/yourmodule@v0.1.0`, the Go toolchain forwards the request to `proxy.golang.org`. The proxy:

1. Looks the module up in its cache (it is not there — first time).
2. Resolves the module path to a Git host (`github.com/...`, `gitlab.com/...`, etc.).
3. Clones or fetches the tag `v0.1.0`.
4. Computes the module's checksum.
5. Reports the checksum to `sum.golang.org`.
6. Caches the bytes, forever.

After step 6, the module is "in the index." Future `go get` requests for that version are served from the cache, even if you delete the original repository (yes — that has implications, see Edge Cases & Pitfalls).

### `pkg.go.dev` indexes you after first download

`pkg.go.dev` is a separate service from the proxy. It watches the proxy for new modules and indexes their documentation. Within minutes to hours of your first `go get`, your module appears on `pkg.go.dev/<module-path>` with auto-generated docs and your README rendered as the front page.

### Semantic Versioning, in 30 seconds

The version `MAJOR.MINOR.PATCH` encodes intent:

- **MAJOR** changes when you break the API. Renaming, removing, or changing the signature of an exported symbol is a major change.
- **MINOR** changes when you add a backward-compatible feature. New exported function, new field on a struct that has no constructor, new package — these are minor.
- **PATCH** changes when you fix a bug without changing the API. Performance improvements, internal refactoring, and bug fixes are patches.

Go enforces a stricter rule on top of semver: **once you publish `v2.0.0` or later, your module path must end with `/vN`** (where `N` is the major version number). This is called the *Semantic Import Versioning* rule.

### `v0` is the "I'm still figuring it out" zone

While your version is `v0.x.y`, you are excused from the stability promise. You can break the API at every minor release if you want. The community knows this and treats `v0` modules as experimental.

The moment you tag `v1.0.0`, you are promising to follow semver strictly. No surprise breaking changes; only at `v2`, `v3`, etc.

---

## Code Examples

### Example 1 — Publishing a tiny `hello` library (first publish workflow)

Suppose you have written a one-function library locally:

```
hello/
├── go.mod      ← module github.com/alice/hello
└── hello.go
```

Contents of `hello.go`:

```go
// Package hello provides a friendly greeting function.
package hello

// Greet returns a polite hello aimed at name.
func Greet(name string) string {
    return "hello, " + name
}
```

Step 1 — create the public repository on GitHub at `https://github.com/alice/hello`.

Step 2 — push your code:

```bash
git init
git add .
git commit -m "Initial release: Greet function"
git branch -M main
git remote add origin https://github.com/alice/hello.git
git push -u origin main
```

Step 3 — tag and push the first release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Step 4 — anyone (including you, from another machine) can now run:

```bash
go get github.com/alice/hello@v0.1.0
```

That is publishing.

### Example 2 — Verifying the publish worked

After the tag push, wait about a minute, then visit:

```
https://pkg.go.dev/github.com/alice/hello@v0.1.0
```

If the page loads with your `Greet` function listed, you are published. If it says "Module not found," `pkg.go.dev` has not yet indexed your module. Force the index by running `go get` once from your terminal — that hits the proxy, which causes pkg.go.dev to pick it up.

### Example 3 — Bumping to v1.0.0 (the stability promise)

After a few weeks of use, you decide your `Greet` API is stable. You tag a v1:

```bash
git tag v1.0.0
git push origin v1.0.0
```

`go.mod` does **not** change. The module path is still `github.com/alice/hello`. Only major versions `>= 2` change the module path.

Users now do:

```bash
go get github.com/alice/hello@v1.0.0
```

You are now bound by semver: future `v1.x.y` releases must be backward compatible.

### Example 4 — Releasing a v2 with a breaking change

Six months later, you decide `Greet` should return an error if the name is empty. That is a breaking API change. You must publish a `v2`.

Step 1 — change the module path in `go.mod`:

```
module github.com/alice/hello/v2

go 1.22
```

Step 2 — update internal imports inside the module to use the new path (if any).

Step 3 — make the breaking change in `hello.go`:

```go
// Package hello provides a friendly greeting function.
package hello

import "errors"

// Greet returns a polite hello, or an error if name is empty.
func Greet(name string) (string, error) {
    if name == "" {
        return "", errors.New("name is required")
    }
    return "hello, " + name, nil
}
```

Step 4 — commit and tag:

```bash
git add .
git commit -m "v2: Greet now returns error on empty name"
git tag v2.0.0
git push origin main v2.0.0
```

Users who want the new version write:

```go
import "github.com/alice/hello/v2"
```

`v1` users keep working, untouched. `v1` and `v2` are independent.

### Example 5 — Retracting a bad release

You realise `v1.2.0` introduced a critical bug. You release `v1.2.1` immediately. But you also want `go get` users to skip `v1.2.0`. Edit `go.mod`:

```
module github.com/alice/hello

go 1.22

retract v1.2.0  // critical bug in Greet, use v1.2.1 or later
```

Commit, tag `v1.2.2` (the retraction itself is a release), push:

```bash
git add go.mod
git commit -m "Retract v1.2.0 due to Greet bug"
git tag v1.2.2
git push origin main v1.2.2
```

Anyone running `go get -u` will now see a warning that `v1.2.0` is retracted and pick `v1.2.1` (or later) instead.

### Example 6 — A minimal LICENSE file

Create `LICENSE` at the module root:

```
MIT License

Copyright (c) 2024 Alice Example

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS"...
```

Without this file, `pkg.go.dev` displays a "no license" warning and many users will refuse to depend on your module.

### Example 7 — A minimal README

Create `README.md`:

```markdown
# hello

A tiny library that greets people.

## Install

    go get github.com/alice/hello@latest

## Usage

    import "github.com/alice/hello"

    fmt.Println(hello.Greet("world"))
    // Output: hello, world

## License

MIT — see [LICENSE](LICENSE).
```

`pkg.go.dev` will render this as the front page of your module.

---

## Coding Patterns

### Pattern: Always start at v0

Tag your first release `v0.1.0`. Stay in `v0` until your API has been used by at least one outside project for a few weeks. This signals to the community "still in design." Once you are sure, tag `v1.0.0`.

### Pattern: One repository, one module path

The module path in `go.mod` and the URL of the Git repository must match. If `go.mod` says `module github.com/alice/cooltool`, the repository is `github.com/alice/cooltool`. Mismatch breaks `go get` with confusing errors.

### Pattern: Tag from the branch you want to publish from

```bash
git checkout main
git pull
git tag v1.0.0
git push origin v1.0.0
```

Tag from a clean, up-to-date `main`. Avoid tagging from feature branches by accident.

### Pattern: Add a CHANGELOG.md

For each release, append an entry:

```
## v1.2.0 — 2024-03-15
- Added: Greet now accepts a `lang` parameter.
- Fixed: trailing whitespace in output.
```

`pkg.go.dev` does not parse CHANGELOG, but humans browsing your repo will read it.

### Pattern: Version your README's install snippet

If your module is at `v2`, your README's install line must be:

```bash
go get github.com/alice/hello/v2@latest
```

Forgetting the `/v2` is a top-five complaint from new users.

---

## Clean Code

- **Lowercase, hyphenated module names.** `github.com/alice/csv-kit`, not `CsvKit` or `csv_kit`.
- **Top-of-file package comment.** Every package's main file should start with `// Package foo does X.` This becomes the package summary on pkg.go.dev.
- **Exported names get godoc comments.** Every exported function, type, constant, and variable needs a `// Name does X.` comment starting with the name itself.
- **README has install + usage in the first 30 lines.** Visitors decide whether to depend on you in seconds. Get to the point.
- **LICENSE is a plain `LICENSE` file at the root.** Not `LICENSE.txt`, not `license.md`. `pkg.go.dev` looks for canonical names.
- **Tags are immutable.** Never delete or move a published tag. If you must "fix" `v1.0.0`, release `v1.0.1` instead.

---

## Error Handling

### "go: github.com/alice/hello@v0.1.0: invalid version: unknown revision v0.1.0"

The tag does not exist on the remote. Cause: you ran `git tag v0.1.0` but forgot `git push --tags` (or `git push origin v0.1.0`). Fix:

```bash
git push origin v0.1.0
```

### "go: github.com/alice/hello: invalid version: unknown revision 0.1.0"

You created a tag without the leading `v`. Fix: delete the bad tag, create the right one.

```bash
git tag -d 0.1.0
git push origin :refs/tags/0.1.0
git tag v0.1.0
git push origin v0.1.0
```

### "module declares its path as: github.com/alice/hello/v2 but was required as: github.com/alice/hello"

You bumped to `v2` in `go.mod` but a consumer is asking for the bare path. They need to update their import to include `/v2`. The fix lives in *their* code.

### "module github.com/alice/hello@v0.1.0 found, but does not contain package ..."

You tagged a commit that does not include the package. Possibly you tagged before pushing all your code. Fix: push the missing files, then tag a new version.

### "verifying ...: checksum mismatch"

The bytes the proxy fetched do not match what your local clone has. Cause: someone moved a tag (yours or a transitive dependency's). Real-world fix: report it to the maintainer; never silently rotate tags yourself.

---

## Security Considerations

- **Never publish secrets.** API keys, passwords, `.env` files, internal hostnames — once a tag is up, the proxy has them forever.
- **Audit before tagging.** Review every file in the commit you are about to tag. `git diff v0.1.0..HEAD` (after you have an old tag) is your friend.
- **Use signed tags** in security-critical projects: `git tag -s v1.0.0`. Consumers can verify your GPG signature.
- **Watch for typosquatting against your name.** If you publish `github.com/alice/cooltool`, register `github.com/alice/cool-tool` and `github.com/alice/cool_tool` if you can — preventing impersonation is cheaper than fighting it.
- **The sumdb sees everything.** Anything you publish, even by accident, is permanently fingerprinted. Treat publication as a one-way door.
- **Removing a version from the proxy is a manual escalation.** It involves filing a request with the Go team and is reserved for legal or security reasons. Do not rely on it.

---

## Performance Tips

- Tagging is instant. The slowness is on first-`go get`, when the proxy fetches your repo. Keep your repository small to make that fast.
- A repository with hundreds of megabytes of binary assets makes every `go get` of your module slow. Move large assets out of the module root.
- Tagging often (small, frequent releases) is better than tagging rarely (large, dramatic releases). Smaller diffs mean easier review and faster rollback.
- The proxy caches forever; subsequent users see milliseconds. The first user pays the cost.

---

## Best Practices

1. **Start at `v0.1.0`.** Reserve `v1.0.0` for the day you are confident the API is stable.
2. **Always include a LICENSE.** Without one, your code is technically not freely usable.
3. **Always include a README.** It is the front page of your module on pkg.go.dev.
4. **Write godoc comments on every exported symbol.** Free, automatic, beautiful documentation.
5. **Tag from a clean, up-to-date main branch.** Never from a feature branch or with uncommitted changes.
6. **Push the tag explicitly with `git push origin v1.0.0`.** "It worked locally" is not a publication.
7. **For breaking changes, do `/v2`, never silently break.** It is the single most important rule.
8. **Add a CHANGELOG.md.** Humans appreciate context.
9. **Verify on pkg.go.dev within a day.** Browse your own module. Look at it the way an outsider does.
10. **Keep tags immutable.** No moving, no deleting. Use `retract` for mistakes.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Forgetting the `v` prefix

```bash
git tag 1.0.0  # wrong
git tag v1.0.0 # correct
```

A tag without `v` is invisible to Go. Fix the tag and push the corrected one.

### Pitfall 2 — Tagging without pushing

```bash
git tag v1.0.0
# you forgot to: git push origin v1.0.0
```

The tag exists on your laptop only. From the world's perspective, the version does not exist.

### Pitfall 3 — Mismatched module path and `/v2`

When bumping to `v2`:

- `go.mod` first line **must** end with `/v2`.
- The Git tag is `v2.0.0`, not `v2.0.0/v2`.
- The repository URL does not change — `github.com/alice/hello`, not `github.com/alice/hello/v2`.

A common mistake is to create a new repository called `hello-v2`. Don't. The `/v2` lives inside the module path of the existing repository.

### Pitfall 4 — Re-tagging a buggy release

```bash
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
git tag v1.0.0  # new commit, same tag name
git push origin v1.0.0
```

This works on Git, but the proxy and sumdb have already cached the old `v1.0.0`. They will refuse the new bytes (checksum mismatch). The "fix" looks like nothing changed for users. Use `v1.0.1` instead.

### Pitfall 5 — Accidentally publishing private code

Pushing a public repository with private secrets is a security incident. The fix involves rotating the secrets, not the repository — the proxy has cached the leaked bytes.

### Pitfall 6 — Tagging before the code is ready

You tag `v1.0.0` and discover an import path was wrong. The proxy has already cached the broken version. Fix: tag `v1.0.1` with the corrected code and add a `retract v1.0.0` directive.

### Pitfall 7 — A `go.mod` with no `go` directive

Older modules sometimes have a `go.mod` missing the `go` line. Modern Go tools will accept it but pkg.go.dev may complain. Add `go 1.x` and re-tag.

### Pitfall 8 — Module path mismatch with repo URL

If your `go.mod` says `module example.com/alice/hello` but the code lives at `github.com/alice/hello`, `go get example.com/alice/hello` will fail because Go cannot find the source.

---

## Common Mistakes

- **Tagging `1.0.0` instead of `v1.0.0`.** The most common publishing bug.
- **Forgetting `git push --tags` or `git push origin <tag>`.** Local tags are invisible to the world.
- **Going from `v1` to `v2` without renaming the module path.** Users will keep getting `v1` because the toolchain refuses to follow the major-version bump rule silently.
- **Editing a published tag.** Tags must be immutable. Use a new patch version to fix problems.
- **Skipping LICENSE.** Many shops auto-reject dependencies without one.
- **No package-level godoc comment.** pkg.go.dev shows a blank package summary.
- **Tagging from a feature branch.** The tag points at a commit that is not in `main`, leading to a confusing release history.
- **Publishing without verifying with `go get` from a clean cache.** Trust nothing about a release until you can `go get` it from a fresh machine.
- **Using `latest` in a production lockfile.** Always pin to a specific version.

---

## Common Misconceptions

> *"There is a `go publish` command."*

There is not. You publish by pushing to a public Git host and tagging.

> *"I have to register my module on pkg.go.dev."*

You do not. pkg.go.dev discovers modules automatically when they are pulled through the proxy.

> *"Once I delete my GitHub repository, my module is gone."*

It is gone from GitHub, but the proxy has cached it forever. Anyone who already has the version will keep working. Anyone trying to `go get` a *new* version will fail. Deletion is not a removal mechanism.

> *"I can fix a bad release by re-tagging it."*

You cannot. Tags are immutable from the proxy's perspective. Fix forward with a new patch version.

> *"`v0` versions are unstable, `v1+` versions are stable, but `v2`, `v3` are even more stable."*

`v2` is not "more stable" than `v1`. It is a different major version. Increasing the number does not mean increasing maturity — it means breaking compatibility.

> *"I have to switch to a new repository for `v2`."*

You do not. `v2` lives in the same Git repository, possibly on the same `main` branch, just with a `/v2` suffix in the module path.

> *"My module path can be anything because Go figures it out."*

It cannot. The module path must be the URL of a public repository. Mismatches break `go get`.

---

## Tricky Points

- **The proxy and the sumdb are eventually consistent with your Git host.** A tag pushed seconds ago may take up to a minute to appear when you `go get`. Patience.
- **`pkg.go.dev` indexes lazily.** If your module never gets a `go get`, it never appears on pkg.go.dev. Trigger indexing by running `go get` once yourself.
- **Pre-release tags exist.** `v1.0.0-rc1`, `v1.0.0-beta`, `v0.5.0-alpha+build.42` are valid. They sort below the corresponding stable release.
- **The `+incompatible` suffix is a fossil.** Pre-modules code that hit `v2` without renaming gets a synthetic `+incompatible` from the toolchain. New code should never need to think about this.
- **`go install path@latest`** for a CLI uses the highest tagged version. If your latest tag is `v0.x` and someone wants `v1+`, they must specify it explicitly.
- **`go get -u` does not cross major versions.** Going from `v1` to `v2` is a manual, deliberate import-path change.
- **A `go.mod` without a `go` directive will be auto-upgraded** on first toolchain interaction. Best to declare it explicitly.

---

## Apply it

1. Choose one small, known input for **Publishing Modules**.
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

- What problem does Publishing Modules solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
