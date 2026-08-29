# Module Proxy & Checksum Database — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Module Proxy & Checksum Database** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### Where dependencies come from: the proxy

When Go needs `github.com/google/uuid@v1.6.0`, it does not (by default) run `git clone https://github.com/google/uuid`. Instead it makes a few small HTTP requests to the proxy named in `GOPROXY`:

1. "What versions of this module exist?" → `GET .../github.com/google/uuid/@v/list`
2. "Give me the metadata for v1.6.0." → `GET .../github.com/google/uuid/@v/v1.6.0.info`
3. "Give me the `go.mod` file for v1.6.0." → `GET .../github.com/google/uuid/@v/v1.6.0.mod`
4. "Give me the source zip for v1.6.0." → `GET .../github.com/google/uuid/@v/v1.6.0.zip`

The proxy returns plain HTTP responses. There is no Git involved on your side. The proxy already did the Git work — cloned the repo, picked the tag, packaged the source — and cached the result for everyone.

### Why a proxy at all?

Three reasons, all of which benefit you even as a beginner:

- **Speed.** The proxy caches modules close to you. Fetching a zip is faster than cloning a whole Git history.
- **Availability.** If a GitHub repo is deleted, renamed, or goes offline, the proxy may still have a cached copy. Your build keeps working.
- **Immutability.** Once the proxy serves `v1.6.0`, those bytes never change. A Git tag *can* be moved by a malicious or careless author; a proxy version cannot.

### The module cache

After Go downloads a module from the proxy, it stores it on disk so it never has to download it again. That store is the **module cache**:

```bash
go env GOMODCACHE
# /Users/you/go/pkg/mod
```

The cache is shared across *all* your projects. If two projects use `uuid@v1.6.0`, it is downloaded once and reused. The cache is read-only — you are not meant to edit files in it. You can wipe it with `go clean -modcache` if it ever gets corrupted, and Go will re-download on the next build.

### What `go.sum` is

Look inside any module that has dependencies and you will find a `go.sum` file:

```
github.com/google/uuid v1.6.0 h1:NIvaJDMOsjHA8n1jAhLSgzrAzy1Hgr+hNrb57e+94F0=
github.com/google/uuid v1.6.0/go.mod h1:TIyPZe4MgqvfeYDBFedMoGGpEw/LqOeaOT+nhxU+yHo=
```

Each line records a **cryptographic hash** of some downloaded bytes. The first line hashes the module's *source zip*; the second hashes its *`go.mod` file*. Both are pinned to the exact version `v1.6.0`.

The point: every time Go reads a module out of the cache to build with, it re-hashes the bytes and checks them against `go.sum`. If they do not match — because the cache got corrupted, or somebody swapped the bytes — the build **fails loudly**. You are protected from silently building against tampered code.

### What the checksum database is

`go.sum` protects you against changes *after* the first download. But what about the *first* download? How do you know the bytes you got the very first time are the same bytes everyone else got?

That is the job of the **checksum database** (`sum.golang.org`). It is a global, public, append-only log. When Go downloads a module version for the first time, it asks the sumdb: "what is the official hash for `github.com/google/uuid@v1.6.0`?" The sumdb answers, Go compares that answer to the bytes it just downloaded, and only if they match does it write the hash into your `go.sum`.

The crucial property: the sumdb is **append-only and tamper-evident**. Once a `(module, version, hash)` entry is published, it can never be changed or deleted without everyone noticing. So if a malicious proxy tries to serve you different bytes than everyone else got, the sumdb hash will not match and your build will fail.

### How `go.sum` is built (the normal flow)

You almost never edit `go.sum` by hand. It is populated automatically:

```bash
go get github.com/google/uuid@v1.6.0
```

Behind that single command:
1. Go fetches the module from the proxy.
2. Go asks `sum.golang.org` for the official hash.
3. Go verifies the downloaded bytes against the sumdb hash.
4. Go writes the verified hash into `go.sum`.

From then on, the hash in `go.sum` is the source of truth. Future builds compare against it without needing the sumdb again.

### The three keywords you will see

In `go env` output, three special words appear:

- `direct` — at the end of `GOPROXY`, means "if the proxies before me don't have it, fetch directly from the source repo."
- `off` — means "do not download anything; fail if a module is missing."
- A real URL like `https://proxy.golang.org` — an actual proxy server.

A typical default:

```
GOPROXY=https://proxy.golang.org,direct
```

Read that as: "try the public proxy first; if it can't serve a module, fall back to fetching directly from the source repo."

---

## Code Examples

### Example 1 — Inspecting your current configuration

```bash
go env GOPROXY
# https://proxy.golang.org,direct

go env GOSUMDB
# sum.golang.org

go env GOMODCACHE
# /Users/you/go/pkg/mod

go env GOPRIVATE
# (empty by default)
```

These four values tell you everything about where your modules come from and how they are verified.

### Example 2 — Watching a fetch happen

Start a fresh module and add a dependency with verbose output:

```bash
mkdir proxydemo && cd proxydemo
go mod init example.com/proxydemo
GOPROXY=https://proxy.golang.org,direct go get -x github.com/google/uuid@v1.6.0
```

The `-x` flag prints the commands Go runs. You will see it download from the proxy and verify against the sumdb, then write `go.sum`.

### Example 3 — Reading `go.sum`

After Example 2:

```bash
cat go.sum
```

Output:

```
github.com/google/uuid v1.6.0 h1:NIvaJDMOsjHA8n1jAhLSgzrAzy1Hgr+hNrb57e+94F0=
github.com/google/uuid v1.6.0/go.mod h1:TIyPZe4MgqvfeYDBFedMoGGpEw/LqOeaOT+nhxU+yHo=
```

Decoding it:
- `github.com/google/uuid v1.6.0 h1:...` — the SHA-256 hash of the module's *source zip*, base64-encoded, with the `h1:` algorithm prefix.
- `github.com/google/uuid v1.6.0/go.mod h1:...` — the hash of just the `go.mod` file for that version.

Two lines per module version: one for the zip, one for the `go.mod`.

### Example 4 — Poking the proxy with `curl`

You can speak the protocol by hand. The proxy is just HTTP:

```bash
# List all known versions
curl https://proxy.golang.org/github.com/google/uuid/@v/list

# Get metadata for a specific version (JSON)
curl https://proxy.golang.org/github.com/google/uuid/@v/v1.6.0.info
# {"Version":"v1.6.0","Time":"2024-01-12T20:25:00Z"}

# Get the go.mod for that version
curl https://proxy.golang.org/github.com/google/uuid/@v/v1.6.0.mod

# Get info about the latest version
curl https://proxy.golang.org/github.com/google/uuid/@latest
```

That is the entire surface a beginner needs to know: `/@v/list`, `.info`, `.mod`, `.zip`, and `/@latest`.

### Example 5 — Downloading the zip (and seeing its size)

```bash
curl -sO https://proxy.golang.org/github.com/google/uuid/@v/v1.6.0.zip
ls -lh v1.6.0.zip
# the actual module source, as a zip
```

This is exactly the bytes Go downloads and hashes. The `h1:` line in `go.sum` is the fingerprint of (the canonical form of) this file.

### Example 6 — Forcing direct mode (bypass the proxy)

```bash
GOPROXY=direct go get github.com/google/uuid@v1.6.0
```

With `GOPROXY=direct`, Go skips the proxy entirely and clones from the source repository (GitHub) itself. Slower, but sometimes necessary for testing or for repos the proxy cannot reach.

### Example 7 — Turning the network off

```bash
GOPROXY=off go build ./...
```

`GOPROXY=off` forbids any download. If everything you need is already in the cache, the build succeeds. If anything is missing, you get a clear error instead of a network call. This is how offline builds are forced.

---

## Coding Patterns

### Pattern: let the defaults work

For most beginner and even intermediate work, do nothing. The default `GOPROXY=https://proxy.golang.org,direct` and `GOSUMDB=sum.golang.org` are correct. Do not change them without a reason.

### Pattern: always commit `go.sum`

`go.sum` is part of your project. Commit it alongside `go.mod`:

```bash
git add go.mod go.sum
git commit -m "add uuid dependency"
```

Without `go.sum`, anyone who clones your repo loses the integrity guarantee and Go will re-fetch and re-verify from scratch.

### Pattern: configure `GOPRIVATE` for company code

If you import private modules (e.g. `github.com/mycompany/internal-lib`), tell Go they are private so it does not try the public proxy or sumdb:

```bash
go env -w GOPRIVATE='github.com/mycompany/*'
```

This single setting makes Go skip both the public proxy *and* the public checksum database for matching paths.

### Pattern: warm the cache before going offline

If you know you will lose network (a flight, an air-gapped build), pre-download:

```bash
go mod download
```

This populates the module cache with everything `go.mod` requires, so a later `GOPROXY=off go build` succeeds.

---

## Clean Code

- **Commit `go.sum`** in the same commit as the `go.mod` change that caused it. They are a pair.
- **Never hand-edit `go.sum`.** It is machine-generated. If it is wrong, regenerate with `go mod tidy` or `go mod download`.
- **Set `GOPRIVATE` once, globally**, with `go env -w`, rather than exporting it ad-hoc in every shell. That way it persists.
- **Do not disable the sumdb (`GOSUMDB=off`) to "fix" an error** unless you fully understand what you are giving up. The error is usually telling you something real.
- **Keep `GOPROXY` simple.** A single corporate proxy plus `direct`, or just the default. Long fragile chains are hard to debug.

---

## Error Handling

The errors you will actually meet as a beginner:

### `checksum mismatch`

```
verifying github.com/foo/bar@v1.2.3: checksum mismatch
	downloaded: h1:AAAA...
	go.sum:     h1:BBBB...
SECURITY ERROR
```

The bytes Go downloaded do not match the hash recorded in `go.sum`. Possible causes:
- The module cache got corrupted. Fix: `go clean -modcache` then rebuild.
- A dependency author force-pushed and changed a tag's contents (bad practice). Fix: investigate; do **not** blindly delete `go.sum`.
- Someone tampered with the download. Take it seriously — this is the security check working.

This is the most important error in this topic. The safe first move is `go clean -modcache && go mod download`. If it persists, investigate before overriding.

### `missing go.sum entry`

```
missing go.sum entry for module providing package github.com/foo/bar
	run 'go mod download github.com/foo/bar' or 'go mod tidy' to add it
```

You imported a package but `go.sum` has no hash for it. Fix:

```bash
go mod tidy
```

### `module ... reading https://proxy.golang.org/...: 404 Not Found`

The proxy does not have the module or version you asked for. Causes:
- A typo in the import path or version.
- A private module the public proxy can't see (you need `GOPRIVATE`).
- A version that was never published.

Fix the path/version, or set `GOPRIVATE` for private code.

### `verifying ...: ... 410 Gone` for a private module

You tried to fetch a private/internal module through the public proxy or sumdb. Fix:

```bash
go env -w GOPRIVATE='your.private.host/*'
```

### Network errors / timeouts

If `proxy.golang.org` is unreachable (firewall, outage, offline), fetches fail. Fix: use a reachable proxy, warm the cache in advance, or set `GOPROXY=off` if everything is already cached.

---

## Security Considerations

- **The sumdb defends against tampering, not against bad code.** It guarantees you get the *same* bytes everyone else got — not that those bytes are *safe*. A malicious-but-popular library will still have a valid checksum.
- **`go.sum` is a security file. Treat it as one.** A `checksum mismatch` is a `SECURITY ERROR` by design. Do not "fix" it by deleting `go.sum`.
- **Never set `GONOSUMCHECK` or `GOSUMDB=off` casually.** These disable verification. Doing so removes a key supply-chain protection.
- **Use `GOPRIVATE` for internal code** so private module paths never leak to the public proxy or sumdb. Leaking an internal module path can reveal product names, infrastructure, or unreleased features.
- **Commit `go.sum`.** A repo without `go.sum` gives every cloner a fresh trust-on-first-use moment, which is weaker than verifying against a pinned hash.
- **Be suspicious of instructions that disable verification.** A common attack vector is a README or script that tells you to turn off the sumdb to "make the build work."

The deeper supply-chain story is covered in [07-supply-chain-integrity](../07-supply-chain-integrity/README.md) — this topic is the integrity foundation it builds on.

---

## Performance Tips

- **The cache makes the second build fast.** The first fetch hits the network; after that, modules come from `$GOMODCACHE` instantly.
- **`go mod download` warms the cache** before a build, useful in CI to separate "download time" from "compile time."
- **A nearby proxy is faster than `direct`.** Cloning full Git histories (direct mode) is slower than fetching a cached zip from the proxy.
- **CI should cache `$GOMODCACHE`** between runs so it does not re-download every job. Most CI systems have a built-in Go cache step.
- **Do not wipe the module cache habitually.** `go clean -modcache` forces a full re-download next time. Reserve it for corruption.

---

## Best Practices

1. **Leave `GOPROXY` and `GOSUMDB` at their defaults** unless you have a concrete reason to change them.
2. **Always commit `go.sum`** alongside `go.mod`.
3. **Set `GOPRIVATE` for all internal module paths**, globally, with `go env -w`.
4. **Never delete `go.sum` to fix a checksum error.** Investigate first.
5. **Warm the cache (`go mod download`) before offline or air-gapped work.**
6. **Cache `$GOMODCACHE` in CI** to speed up repeated builds.
7. **Understand a `checksum mismatch` before overriding it** — it is a security signal.
8. **Use `curl` to inspect the proxy** when debugging "where did this come from?" questions; the protocol is simple and readable.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Deleting `go.sum` to silence an error

The most dangerous beginner reflex. A `checksum mismatch` is telling you bytes changed. Deleting `go.sum` removes the alarm, not the problem. Investigate instead.

### Pitfall 2 — Private modules without `GOPRIVATE`

You import `github.com/yourco/secret-lib`, run `go get`, and it fails trying to reach the public proxy or sumdb (which can't see private code). Fix: set `GOPRIVATE='github.com/yourco/*'`.

### Pitfall 3 — Forgetting to commit `go.sum`

You commit `go.mod` but not `go.sum`. A teammate clones, and their build re-fetches and re-verifies from scratch — weaker, and a source of "works on my machine" confusion. Always commit both.

### Pitfall 4 — Confusing `GOPROXY=off` with `GOPROXY=direct`

`off` means "no network at all; fail if missing." `direct` means "skip the proxy but still hit the source repo over the network." They are opposites in network behaviour.

### Pitfall 5 — Assuming the proxy clones from GitHub for you in real time

The proxy serves *cached, immutable* versions. If a brand-new tag was pushed seconds ago, the proxy may not have it yet. Usually it catches up within minutes.

### Pitfall 6 — Expecting `go.sum` to contain source code

It does not. It contains hashes only. The source lives in the cache and on the proxy.

### Pitfall 7 — A 404 from the proxy that is actually a typo

`module github.com/google/uudi/@v/list: 404` — read carefully; that is a misspelling of `uuid`. The proxy returns 404 for anything it cannot resolve, including typos.

### Pitfall 8 — Disabling the sumdb globally and forgetting

`GOSUMDB=off` removes a security check for *all* projects on your machine until you re-enable it. If you must disable it, do so narrowly and remember to revert.

---

## Common Mistakes

- **Deleting `go.sum` when you see a checksum error.** Almost always wrong. Investigate first.
- **Not setting `GOPRIVATE` for company code.** Causes fetch failures and can leak internal paths.
- **Setting `GONOSUMCHECK` or `GOSUMDB=off`** to make a build "work" without understanding the consequences.
- **Editing files inside the module cache.** It is read-only by design; edits will be detected as corruption.
- **Forgetting to commit `go.sum`.** Leaves teammates without integrity verification.
- **Confusing the proxy (`GOPROXY`) with the sumdb (`GOSUMDB`).** They are two different services with two different jobs.
- **Assuming `direct` means "no network."** It still uses the network — just the source repo instead of the proxy.
- **Wiping the module cache to "fix" unrelated problems.** Slows the next build down for no benefit.

---

## Common Misconceptions

> *"Go clones my dependencies straight from GitHub."*

No. By default Go fetches from the proxy (`proxy.golang.org`). It only clones directly when you use `direct` mode or for modules matching `GOPRIVATE`.

> *"`go.sum` stores my dependencies' code."*

No. `go.sum` stores cryptographic *hashes* of code, not the code itself. The code is in the module cache.

> *"The checksum database checks that my dependencies are safe."*

No. It checks that the bytes you got match the bytes everyone else got. It says nothing about whether the code is malicious or buggy.

> *"`GOPROXY=off` and `GOPROXY=direct` are the same."*

No. `off` blocks all downloads. `direct` skips the proxy but still downloads from the source repo over the network.

> *"I should disable the sumdb if I get a checksum error."*

No. That removes a security protection. The error almost always indicates a real problem (corruption, a moved tag, tampering). Investigate.

> *"The proxy can change a module's bytes after publishing."*

No. Proxy versions are immutable. Once `v1.6.0` is served, those bytes are fixed — and the sumdb guarantees it.

---

## Tricky Points

- **There are two `go.sum` lines per module version**: one for the `.zip` and one for the `/go.mod`. Both must verify.
- **The sumdb is consulted only on the *first* fetch** of a version (or when adding a `go.sum` entry). After that, `go.sum` is the local source of truth.
- **`GOPRIVATE` is a convenience that sets two other things**: it implies `GONOSUMDB` (skip the sumdb) and `GONOPROXY` (skip the proxy) for matching paths. You usually only need to set `GOPRIVATE`.
- **The proxy protocol is plain HTTP.** You can read it with `curl`. There is no special client needed.
- **`@latest` is its own endpoint**, separate from `/@v/list`. It returns the version Go would pick as "latest."
- **`off` fails the build if anything is missing; `direct` is a fallback, not a blocker.**
- **The `h1:` prefix is part of the format**, naming the hashing scheme. There is room for future `h2:` etc., but `h1:` is what you will see.

---

## Apply it

1. Choose one small, known input for **Module Proxy & Checksum Database**.
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

- What problem does Module Proxy & Checksum Database solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
