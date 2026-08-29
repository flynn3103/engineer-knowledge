# Supply-Chain Integrity — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Supply-Chain Integrity** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### Your dependencies are your code, security-wise

The single most important idea: **importing a package is morally equivalent to copying its source into your repository.** Once `github.com/some/lib` is in your `go.mod` and you call its functions, its code runs in your process, reads your memory, makes network calls under your identity, and ships in your binary. The fact that it lives in a different GitHub repo does not make it someone else's responsibility at runtime.

So the question "is this dependency safe?" is really "would I be comfortable shipping this code if I had written it myself?"

### The chain has many links

When you `go get github.com/gin-gonic/gin`, you do not pull one package. You pull Gin, plus everything Gin imports, plus everything *those* import. A small `go.mod` with three `require` lines can expand to fifty modules in the full build list. Each of those fifty is a place an attacker could hide.

Run this to see the full set:

```bash
go list -m all
```

Every line is a module that contributes code to your build. Every line is part of your trust boundary.

### `go.sum` makes downloads tamper-evident

The first time Go downloads a module version, it computes a hash of its contents and records it in `go.sum`:

```
github.com/google/uuid v1.6.0 h1:NIvaJDMOsjHA8n1jAhLSgzrAzy1Hgr+hNrb57e+94F0=
github.com/google/uuid v1.6.0/go.mod h1:TIyPZe4MgqvfeYDBFedMoGGpEw/LqOeaOT+nhxU+yHo=
```

Every later build re-checks the downloaded bytes against this recorded hash. If even one byte changed — because a proxy was compromised, a network was tampered with, or a maintainer force-pushed a different version under the same tag — the build **fails loudly** instead of silently compiling the attacker's code.

`go.sum` is not a wish-list of versions (that is `go.mod`). It is a **cryptographic receipt**: "these exact bytes are what we used."

### The checksum database catches the harder attack

`go.sum` protects you *after* the first download. But what about the first download itself? What if the attacker serves you bad bytes the very first time, so the bad hash gets recorded?

That is what the **checksum database** (`sum.golang.org`, configured via `GOSUMDB`) defends against. It is a global, public, append-only, tamper-evident log of module hashes. When Go fetches a module version for the first time, it asks the checksum database what hash *everyone else* recorded for that version. If your bytes do not match the global record, Go refuses.

Because the log is append-only and cryptographically verifiable (it is a Merkle-tree transparency log, like Certificate Transparency for TLS certificates), an attacker cannot quietly insert a fake hash for one victim without it being globally visible.

We recap the proxy and sumdb only briefly here — the dedicated page [05-module-proxy-and-checksum-db](../05-module-proxy-and-checksum-db/junior.md) covers their mechanics in depth.

### `govulncheck` tells you which known holes you are exposed to

Hashes prove your dependencies are *unchanged*. They do not prove your dependencies are *safe*. A dependency can be exactly the bytes everyone agreed on — and still contain a known security bug.

`govulncheck` closes that gap. It compares your dependency set against the Go vulnerability database and reports the vulnerabilities that apply to you. Its standout feature: it does **symbol-level** analysis. It does not just say "you depend on a vulnerable version of library X." It says "you depend on a vulnerable version of X, *and your code actually calls the vulnerable function.*" If the vulnerable function exists in your dependency tree but nothing in your code path reaches it, `govulncheck` tells you that too — so you do not waste time on threats you are not exposed to.

```bash
go install golang.org/x/vuln/cmd/govulncheck@latest
govulncheck ./...
```

### Fewer, well-chosen dependencies = smaller attack surface

Every dependency is a link in the chain. Every link is a potential point of failure. The simplest, most powerful supply-chain practice available to a junior engineer is: **add fewer dependencies, and choose them carefully.** A 10-line utility function you copy into your own code is not a supply-chain risk. A 10-line utility you pull as a one-function dependency drags in a whole module — and its future updates, and its own dependencies — into your trust boundary forever.

---

## Code Examples

### Example 1 — Seeing your full trust boundary

```bash
# Direct dependencies only:
go mod edit -json | grep -A2 Require

# The complete build list — everything that ships in your binary:
go list -m all

# Count how many modules you actually depend on:
go list -m all | wc -l
```

A small CLI might show 1 direct dependency and 15 total. Those 15 are your supply chain.

### Example 2 — Inspecting `go.sum`

```bash
cat go.sum
```

```
github.com/google/uuid v1.6.0 h1:NIvaJDMOsjHA8n1jAhLSgzrAzy1Hgr+hNrb57e+94F0=
github.com/google/uuid v1.6.0/go.mod h1:TIyPZe4MgqvfeYDBFedMoGGpEw/LqOeaOT+nhxU+yHo=
```

Each module version gets two lines:
- `...h1:...` — the hash of the module's source tree (the zip contents).
- `.../go.mod h1:...` — the hash of just that module's `go.mod` file.

Both are verified on every build. You never edit this file by hand; the toolchain manages it.

### Example 3 — Verifying integrity explicitly

```bash
# Re-check every module in the cache against go.sum:
go mod verify
```

Expected output:

```
all modules verified
```

If a cached module's bytes were tampered with after download, this command reports the mismatch.

### Example 4 — Running govulncheck for the first time

```bash
go install golang.org/x/vuln/cmd/govulncheck@latest
govulncheck ./...
```

A clean result:

```
No vulnerabilities found.
```

A finding looks like:

```
Vulnerability #1: GO-2023-1840
    A flaw in ... allows ...
  More info: https://pkg.go.dev/vuln/GO-2023-1840
  Module: github.com/affected/dep
    Found in: github.com/affected/dep@v1.2.0
    Fixed in: github.com/affected/dep@v1.2.1
    Example traces:
      your-module/internal/handler.go:42:13: calls dep.Vulnerable
```

The `Example traces` line is the gold: it shows the exact spot in *your* code that reaches the vulnerable function.

### Example 5 — A vuln that exists but you do not call

```
=== Informational ===

There is 1 vulnerability in modules that you require that is not
imported by a called function. You may not be affected.

Vulnerability #1: GO-2022-0646
  Module: github.com/some/lib
    Found in: github.com/some/lib@v0.4.0
    Fixed in: github.com/some/lib@v0.4.1
```

This is the "Informational" section. The vulnerable code is in your tree, but nothing you call reaches it. Lower priority — but worth fixing on your next routine update.

### Example 6 — Configuring a private module correctly

If you import `git.mycompany.internal/team/lib`, the public proxy and sumdb cannot (and should not) see it:

```bash
# Tell Go this namespace is private: skip the proxy and sumdb for it.
go env -w GOPRIVATE='git.mycompany.internal,*.mycompany.internal'
```

Now `go get git.mycompany.internal/team/lib` fetches directly over your authenticated Git connection, and Go does not leak the path to `sum.golang.org`.

### Example 7 — A minimal CI check

```yaml
# .github/workflows/supply-chain.yml
name: supply-chain
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: '1.23' }
      - name: Verify go.sum
        run: go mod verify
      - name: Scan for vulnerabilities
        run: |
          go install golang.org/x/vuln/cmd/govulncheck@latest
          govulncheck ./...
```

Three small steps and every push is now checked for tampering and known vulnerabilities.

---

## Coding Patterns

### Pattern: scan before you ship

Make `govulncheck ./...` part of your definition of "done." Run it locally before opening a PR; enforce it in CI. A green scan is a precondition for merge.

### Pattern: review the diff on every dependency bump

When you bump a version, look at what actually changed:

```bash
go get github.com/some/lib@v1.4.0
go mod tidy
# Inspect what the version change pulled in:
git diff go.mod go.sum
```

A bump that adds five new transitive modules deserves a closer look than a patch-level bump that changes nothing else.

### Pattern: pin, do not float

Always commit `go.mod` and `go.sum`. They pin exact versions. Never rely on "latest" resolving the same way tomorrow as today. Reproducibility is a security property.

### Pattern: prefer copying tiny utilities over importing them

If a dependency is a single small function, consider writing it yourself. The "left-pad" lesson: a trivial dependency is still a full link in the supply chain, with all the risk and none of the leverage.

### Pattern: keep `GOPRIVATE` accurate

Set `GOPRIVATE` (or `GONOSUMDB`/`GOINSECURE` as appropriate) for every private namespace, and no more. Over-broadening it (see Pitfalls) silently disables protections for code that should be checked.

---

## Clean Code

- **Commit `go.sum` always.** Treat a missing or `.gitignore`d `go.sum` as a bug. It is your tamper-evidence record.
- **Run `go mod tidy` before committing** so `go.mod`/`go.sum` reflect exactly what you use — no stale or phantom dependencies hiding in the chain.
- **Do not disable security to make an error go away.** `GONOSUMCHECK`, `GONOSUMDB=*`, or `GOFLAGS=-insecure` "fix" the symptom by removing the guard. Almost never the right move.
- **Keep CI checks fast and mandatory.** A `govulncheck` step that everyone skips because it is slow or flaky protects nothing.
- **Name the reason for any exception.** If you must suppress a finding, document *why* in code or config, not in someone's memory.

---

## Error Handling

The supply-chain tooling fails in specific, recognizable ways. Each failure is usually *protecting* you.

### `verifying module: checksum mismatch`

```
verifying github.com/foo/bar@v1.2.0: checksum mismatch
        downloaded: h1:AAAA...
        go.sum:     h1:BBBB...
SECURITY ERROR
```

The bytes you just downloaded do not match what `go.sum` recorded. **Stop.** This means either the module was tampered with, the network was compromised, or (innocently) the upstream tag was force-pushed to different content. Do not "fix" it by deleting `go.sum`. Investigate. If you genuinely intended new content, regenerate `go.sum` deliberately with `go mod tidy` and review the change.

### `missing go.sum entry`

```
missing go.sum entry for module providing package github.com/foo/bar
        run 'go mod tidy' to add it
```

You imported something not yet recorded. Fix with `go mod tidy`. This is bookkeeping, not an attack.

### `checksum database lookup ... 410 Gone` for a private module

```
git.acme.internal/team/lib@v1.0.0: reading https://sum.golang.org/...: 410 Gone
```

Go tried to verify a *private* module against the *public* checksum database, which cannot see it. Fix by setting `GOPRIVATE` for that namespace (Example 6). Do **not** fix it by disabling the sumdb globally.

### `govulncheck` reports a vulnerability

This is not a tool error — it is the tool working. Read the trace, find the call site, and upgrade to the fixed version:

```bash
go get github.com/affected/dep@v1.2.1   # the "Fixed in" version
go mod tidy
govulncheck ./...                         # confirm it is gone
```

### `govulncheck: no Go files`

You ran it outside a module or in an empty directory. Run it from your module root with `govulncheck ./...`.

---

## Security Considerations

- **`go.sum` is tamper-evidence, not tamper-prevention.** It tells you something changed; it cannot stop a maintainer from publishing malicious code in the first place.
- **The checksum database does not vet code quality.** It records what was published. A malicious-but-consistent package passes it.
- **`govulncheck` only knows *catalogued* vulnerabilities.** A zero-day or an as-yet-unreported malicious package will pass. Absence of findings is not proof of safety.
- **Disabling protections is a security decision.** `GONOSUMDB`, `GONOSUMCHECK`, `GOINSECURE`, `GOFLAGS=-insecure` all reduce your defenses. Use them narrowly and deliberately, never globally to silence an error.
- **Private modules need `GOPRIVATE`,** or you risk either leaking internal paths to the public proxy/sumdb or failing builds. Set it precisely.
- **Updates are the riskiest moment.** Most supply-chain compromises arrive as a *new version* of a trusted package. Scan and review on every bump.
- **Transitive dependencies are easy to forget.** The package you imported is one link; the dozen it pulled in are the rest. `govulncheck` checks all of them.

---

## Performance Tips

- **`go mod verify` is fast and local** — it just re-hashes the cache. Run it freely in CI.
- **`govulncheck` is fast enough for CI** — typically seconds to low minutes, because it analyzes your call graph, not every line of every dependency.
- **Install `govulncheck` once and cache it** in CI rather than reinstalling on every job, to shave startup time.
- **The checksum database adds negligible latency** — it is consulted only on first download of a version, then `go.sum` handles the rest offline.
- **Scanning does not slow your *runtime*.** All of this is build-time and CI-time work; your shipped binary is unaffected.

---

## Best Practices

1. **Commit and never ignore `go.sum`.** It is your integrity record.
2. **Run `govulncheck ./...` in CI** and fail the build on actionable findings.
3. **Keep dependencies minimal.** The smallest supply chain is the safest.
4. **Review every dependency update** — read the `go.mod`/`go.sum` diff, do not bump blindly.
5. **Set `GOPRIVATE` for private namespaces** precisely; never disable the sumdb globally to work around it.
6. **Leave Go's defaults on.** `GOPROXY`, `GOSUMDB`, and `go.sum` verification are secure by default. Turning them off is the exception, with a documented reason.
7. **Pin versions; never rely on `latest` in production builds.** Reproducibility is security.
8. **Scan on a schedule, not just on change.** New CVEs land against code you already shipped.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Deleting `go.sum` to "fix" a checksum error

A checksum mismatch is a security signal. Deleting `go.sum` and regenerating it accepts whatever bytes you were just served — possibly the attacker's. Investigate first; regenerate only when you understand the cause.

### Pitfall 2 — Over-broadening `GOPRIVATE`

Setting `GOPRIVATE=*` or `GONOSUMDB=*` disables checksum-database verification for *every* module, public ones included. You meant to exempt one internal namespace; you accidentally turned off a global protection. Scope it tightly: `GOPRIVATE='git.acme.internal,*.acme.internal'`.

### Pitfall 3 — Typosquatting in import paths

`github.com/sirupsen/logrus` is real; `github.com/Sirupsen/logrus` (capital S, an old redirect) and any near-miss are traps. Always copy import paths from the project's official page, never type them from memory.

### Pitfall 4 — Assuming `govulncheck` covers everything

It covers *catalogued* vulnerabilities in your *call graph*. It does not detect novel malware, license problems, or code quality. It is one layer, not the whole defense.

### Pitfall 5 — Ignoring the "Informational" section forever

A vuln you do not currently call is still in your tree. A future code change might start calling it. Clear informational findings on your regular update cadence; do not let them pile up.

### Pitfall 6 — Disabling the sumdb in CI for convenience

A CI step that sets `GONOSUMDB=*` or `GOFLAGS=-insecure` to make a flaky network "work" silently disables integrity verification for the whole pipeline. Fix the network or scope the exemption; do not blanket-disable.

### Pitfall 7 — Forgetting transitive dependencies exist

You audit your three direct dependencies and feel safe. The vulnerability is in one of the forty transitive ones. `go list -m all` and `govulncheck` see all of them; your manual review of `go.mod` does not.

### Pitfall 8 — Treating a version bump as risk-free

The most common real-world supply-chain compromise is a *malicious update to a previously trusted package*. "It was fine last week" is not evidence it is fine today. Re-scan after every bump.

---

## Common Mistakes

- **`.gitignore`-ing `go.sum`.** Removes your tamper-evidence. Always commit it.
- **Deleting `go.sum` to silence a checksum error.** Accepts unverified bytes.
- **Setting `GOPRIVATE=*` or `GONOSUMDB=*` globally.** Disables protection for everything to fix one private module.
- **Never running `govulncheck`.** The tool only helps if you run it.
- **Running `govulncheck` but ignoring findings.** A scan you do not act on is theater.
- **Typing import paths from memory.** Invites typosquats.
- **Bumping dependencies with `go get -u` and committing without review.** Blind acceptance of new code.
- **Auditing only direct dependencies.** Ignores the larger transitive surface.
- **Using `GOFLAGS=-insecure` to work around HTTPS issues.** Disables transport security.

---

## Common Misconceptions

> *"`go.sum` checks that my dependencies are safe."*

No. `go.sum` checks that your dependencies are *unchanged* from what was first recorded. Safe and unchanged are different properties. Malicious-but-stable code passes `go.sum`.

> *"If `govulncheck` finds nothing, I have no vulnerabilities."*

No. `govulncheck` finds *catalogued* vulnerabilities you *call*. Unreported issues, novel malware, and uncalled vulnerable code (which it reports separately, as informational) are different categories.

> *"The checksum database can see my private code."*

No, and it should not. Private modules must be exempted via `GOPRIVATE`. The public sumdb only knows public modules.

> *"Vendoring replaces the need for `go.sum` and scanning."*

No. Vendoring copies dependency source into your repo (see [03-go-mod-vendor](../03-go-mod-vendor/junior.md)) for offline, auditable builds. `go.sum` still verifies integrity, and you still need to scan the vendored code for vulnerabilities.

> *"Supply-chain attacks only happen to big companies."*

No. Automated attacks hit everyone who pulls dependencies. Small projects are *easier* targets because they rarely have checks in place.

> *"Once my dependencies pass a scan, I am done."*

No. New vulnerabilities are disclosed continuously against versions you already ship. Scanning is ongoing, not one-time.

---

## Tricky Points

- **`go.sum` has two lines per module version** — one for the source tree (`h1:`), one for the `go.mod` file (`/go.mod h1:`). Both are verified.
- **The sumdb is consulted only on the *first* download** of a version; after that `go.sum` handles verification offline.
- **`GOPRIVATE` is a convenience that sets several variables at once** — it implies `GONOSUMDB` and `GONOPROXY` for the listed patterns. Setting it correctly is usually all you need for private code.
- **`govulncheck` analyzes the call graph**, so the *same vulnerable dependency* can be "actionable" in one project and "informational" in another, depending on whether the vulnerable function is reached.
- **A checksum mismatch can be innocent** (an upstream force-push) or malicious. The tool cannot tell you which; you must investigate.
- **`go.sum` is not encryption.** It is hashing. Anyone can read it; that is fine. Its value is integrity, not secrecy.
- **Removing a dependency is a security improvement.** Fewer links, smaller surface. `go mod tidy` after deleting an import shrinks the chain.

---

## Apply it

1. Choose one small, known input for **Supply-Chain Integrity**.
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

- What problem does Supply-Chain Integrity solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
