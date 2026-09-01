# Supply-Chain Security — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Supply-Chain Security** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Supply-Chain Security
>
> *Most of your code isn't yours. Learn who you're trusting, and how that trust gets attacked.*

---

## Core Concept 1 — The chain: source, build, publish, consume

A dependency travels through four stages before it runs in your product. Each arrow is an edge an attacker can target:

```
  AUTHOR            REGISTRY              YOU
 ┌────────┐  push  ┌──────────┐  install ┌──────────┐  build  ┌──────────┐
 │ SOURCE │ ─────▶ │ PUBLISH  │ ───────▶ │ CONSUME  │ ──────▶ │ ARTIFACT │
 │ (git)  │        │ (npm/    │          │ (your    │         │ (deploy) │
 │        │        │  PyPI)   │          │  repo+CI)│         │          │
 └────────┘        └──────────┘          └──────────┘         └──────────┘
     ▲                  ▲                     ▲                    ▲
  compromise        account             dependency           build system
  the source        takeover            confusion /          compromised
  (xz backdoor)     typosquat           bad install          (SolarWinds)
```

- **The crucial mental shift:** you don't just trust the package you chose. You trust:
  - the author and their account credentials
  - the registry's integrity
  - the build that produced the artifact
  - every transitive dependency underneath — recursively
- A vulnerability or a backdoor anywhere in that tree is *your* vulnerability.
- "I only use popular, well-maintained packages" is **necessary but not sufficient**:
  - Popular packages have maintainers whose accounts get phished.
  - They pull in dozens of less-popular transitive deps you've never heard of.

---

## Core Concept 2 — You depend on strangers

Count your dependencies once and the scale becomes obvious:

```bash
# Node: how many packages are actually installed?
npm ls --all 2>/dev/null | grep -c '──'

# Go: list every module in the build graph
go list -m all | wc -l

# Python (poetry): everything in the lock
grep -c '^name = ' poetry.lock
```

- A modest web service routinely has **hundreds to thousands** of transitive packages.
- You read the code of maybe three of them. The rest you trust by reputation and momentum.
- Two consequences:
  1. **Attack surface is huge.** Any one of those packages can ship malicious code in its next release, and you'll pull it in the next time you update — automatically, if you use version ranges.
  2. **You inherit their security posture.** If a dependency leaks credentials, runs install scripts that exfiltrate environment variables, or hasn't patched a CVE, that becomes your problem at runtime.
- You can't audit everything. The goal is not zero trust — it's **bounded, reviewed, and observable trust**: know what you depend on, pin it, scan it, and add new dependencies deliberately.

---

## Core Concept 3 — Lockfiles pin what you actually got

- A `package.json` says `"lodash": "^4.17.0"` — *any* 4.x release from 4.17.0 up. That's a **range**.
- The same install on two different days, or on your machine vs CI, can resolve to different actual versions.
- Ranges are how a malicious new release silently enters your build.
- A **lockfile** records the *exact* version you resolved, plus a cryptographic hash of the package contents:

```jsonc
// package-lock.json (excerpt)
"node_modules/lodash": {
  "version": "4.17.21",
  "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
  "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZVGedAJv8XZ1tvj5FvKw=="
}
```

- That `integrity` hash is the heart of it:
  - On install, the package manager downloads the tarball, hashes it, and **refuses to proceed if the hash doesn't match.**
  - So even if the registry is compromised and serves you a tampered tarball, the lockfile catches it.
- Go does the same with `go.sum`:

```
golang.org/x/text v0.14.0 h1:ScX5w1eTa3QqT8oi6+ziP7dTV1S2+ALU0bI+0zXKWiQ=
golang.org/x/text v0.14.0/go.mod h1:18ZOQIKpY8NJVqYksKHtTdi31H5itFRjB5/qKTNYzSU=
```

- The `h1:` line is the hash of the module's *files*; the `/go.mod h1:` line is the hash of just its `go.mod`.
- When you build, Go verifies the downloaded module against these hashes.
- **`go.sum` does not say "this code is safe" — it says "this is the exact same code that was approved when the line was written."** It protects *integrity*, not *quality*.
- A backdoored module with a stable hash passes `go.sum` perfectly.

**The single most important junior habit:** commit your lockfile, and use the install command that *respects* it rather than re-resolving:

```bash
npm ci            # installs exactly from package-lock.json; fails if out of sync
# not: npm install (may update the lockfile)

go mod verify     # checks the module cache against go.sum
```

---

## Core Concept 4 — Scanning your dependencies for known holes

- Most real-world supply-chain pain isn't a clever backdoor — it's a *known* vulnerability you never patched.
- Public databases (the GitHub Advisory Database, OSV, the NVD) track which package versions have which CVEs.
- A **scanner** matches your installed versions against those databases.
- `osv-scanner` (free, from Google's OSV project) reads your lockfile directly:

```bash
# Install once, then scan a project by its lockfile
osv-scanner --lockfile=package-lock.json
osv-scanner --lockfile=go.mod
osv-scanner scan .          # auto-discovers lockfiles in the tree
```

- Typical output flags a package, the vulnerable version range, and the fixed version:

```
╭─────────────────────────────────────┬──────────┬───────────╮
│ OSV ID                              │ ECOSYSTEM│ PACKAGE   │
├─────────────────────────────────────┼──────────┼───────────┤
│ GHSA-jchw-25xp-jwwc (CVE-2024-…)   │ npm      │ tar       │
╰─────────────────────────────────────┴──────────┴───────────╯
```

- `grype` does the same for container images and directories:

```bash
grype dir:.                 # scan the current project
grype myorg/api:1.4.2       # scan a built container image
```

- **Dependabot** (GitHub) opens pull requests automatically when a dependency you use gets a security advisory — turning "we should patch that someday" into a reviewable PR in your inbox.
- **Junior takeaway:** a scanner finding is not noise to dismiss. It's a to-do. When CI flags a vulnerable dependency, the fix is usually a version bump — exactly what Dependabot proposes.

---

## Core Concept 5 — The cheap habits that stop most attacks

You don't need an enterprise program to dramatically shrink your risk. Five habits:

1. **Commit the lockfile and install from it.** `npm ci`, `go mod verify`, `pip install --require-hashes`. This neutralizes tampered downloads and surprise version drift.
2. **Add dependencies deliberately.** Before `npm install some-pkg`, ask: how popular is it? When was it last published? Does the name match what I meant (typo check)? Could I write this in 20 lines instead? `left-pad` taught the industry that an 11-line package can become a single point of failure.
3. **Run a scanner in CI.** Fail the build on new high-severity findings. `osv-scanner` is one command.
4. **Turn on Dependabot/Renovate.** Let the robots open the patch PRs; you just review and merge.
5. **Never ignore install-script warnings blindly.** Many ecosystems run arbitrary code at install time (npm `postinstall`, Python `setup.py`). That code runs with your shell's environment — including secrets. Be suspicious of unexpected install scripts.

These are the cyber-hygiene basics. The middle and senior tiers build SBOMs, provenance verification, and org-wide policy on top of this foundation — but the foundation is what stops the *common* attacks.

---

## Real-World Examples

- **left-pad (2016).** A developer unpublished an 11-line npm package, and thousands of builds across the ecosystem broke instantly — including major projects. Not an *attack*, but the clearest possible demonstration that tiny transitive dependencies are real dependencies, and that the registry is a runtime dependency of your build.

- **event-stream (2018).** A popular npm package was handed off to a new "maintainer" who had volunteered to help. That maintainer added a malicious transitive dependency designed to steal Bitcoin wallets. Lesson: *maintainer trust transfers silently*, and the danger was buried in a dependency-of-a-dependency, not the package you installed.

- **Typosquatting.** Attackers publish packages like `python3-dateutil` (real: `python-dateutil`) or `crossenv` (real: `cross-env`). One typo in an install command and you've run their code. Always double-check package names.

- **Dependency confusion (Alex Birsan, 2021).** A researcher uploaded packages to *public* registries using the same names as companies' *private* internal packages. Many build tools, told to fetch `internal-auth-lib`, preferred the higher-versioned public copy — and ran the researcher's code inside Apple, Microsoft, and dozens of others. Lesson: where your packages come from matters as much as their names.

- **xz/liblzma backdoor (2024).** A patient attacker spent ~two years building maintainer trust on the `xz` compression library, then slipped a backdoor into the release tarballs that targeted SSH. It was caught by luck (a Postgres engineer noticed a half-second SSH slowdown) days before it would have shipped widely. Lesson: even a thoroughly "trusted" upstream can be compromised through *people*, not code.

---

## Common Mistakes

- **Not committing the lockfile** (or `.gitignore`-ing it). Now everyone — and CI — resolves versions independently and unpredictably.
- **`npm install` in CI instead of `npm ci`.** The former can quietly mutate the lockfile and pull newer versions.
- **Dismissing scanner output** as "false positives" without reading it. Most findings are real, fixable version bumps.
- **Adding a dependency for a one-liner.** Every add expands the trust tree forever, including its transitive deps.
- **Copy-pasting install commands from random blogs** without checking the package name. This is exactly how typosquatting wins.
- **Assuming popular = safe.** event-stream and xz were both popular and trusted right up until they weren't.

---

## Apply it

1. Choose one small, known input for **Supply-Chain Security**.
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

- What problem does Supply-Chain Security solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
- Define the software supply chain and explain why every link is an attack surface.
- What is an SBOM, and what does it *not* give you?
- What does `go.sum` protect, and what doesn't it protect?
- What's the difference between a version range, a pinned version, and a hash-pinned dependency — what does each stop?
- What's the difference between `npm ci` and `npm install`, and why does it matter in CI?
- What is a VEX statement for?
