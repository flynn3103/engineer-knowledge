# Release Automation — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Release Automation** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Release Automation

*Get the human out of the release path: turn a merge into a published, versioned release with one command — or none at all.*

---

## Core Concept 1 — Why manual releases hurt

Picture the manual release. It is Friday. You open the project, edit `package.json` to bump `1.3.2` → `1.3.3`, paste a hand-written changelog, run `npm publish`, then tag git and push. It works — until it doesn't:

- **It is slow.** Twenty minutes of careful clicking that you dread, so you batch up changes and release rarely. Rare releases are huge, and huge releases are scary.
- **It is error-prone.** You forgot to bump the version. You published before tagging. You wrote the changelog from memory and missed three fixes. You ran the build on your laptop with a different Node version than CI.
- **It is irreproducible.** "How did we build 1.3.2?" Nobody knows. The exact commands lived in your terminal history, now gone.
- **It gates on one person.** The one engineer who knows the ritual is on vacation. Now nobody can ship a hotfix.

Automation fixes all four at once. The steps are written down (as code), they run the same way every time (on CI, not a laptop), anyone can trigger them, and the machine never forgets to tag.

> The deepest benefit is psychological: **automation makes releasing frequent because it makes releasing boring.** Frequent small releases are the single biggest lever for safe delivery.

---

## Core Concept 2 — What an automated release does

Every automated release tool, regardless of language, performs roughly the same sequence. Learn this shape once and you understand all of them:

```
merge to main
     │
     ▼
1. derive the next version   ← from commit messages or intent files
2. generate the changelog    ← grouped by change type
3. create a git tag          ← e.g. v1.4.0
4. build the artifacts        ← binaries, packages, images
5. sign + attest             ← prove who built it (advanced)
6. publish to a registry      ← npm, Docker Hub, GitHub Releases
7. create a GitHub release    ← notes + downloadable assets
8. notify                     ← Slack, email
```

Two properties make this trustworthy:

- **Each step is observable.** When step 6 fails, you see *which* step and why in the CI logs.
- **The pipeline is idempotent.** Re-running a release that already published version `1.4.0` must not publish it again. Tools enforce this by checking "does this version already exist?" before publishing.

As a junior, you do not need to build this pipeline from scratch. You pick a tool that does it for you. Your job is to feed it good input (clean commit messages) and wire it into CI.

---

## Core Concept 3 — Conventional commits as the input

How does a tool know whether your change is a `1.3.3` (a bugfix) or a `1.4.0` (a new feature) or a `2.0.0` (a breaking change)? It reads your **commit messages** — *if* you write them in a structured format called **Conventional Commits**.

The format is a one-line prefix:

```
<type>(<optional scope>): <description>

[optional body]

[optional footer]
```

The common types and what they do to the version:

| Commit prefix | Meaning | Version bump |
|---------------|---------|--------------|
| `fix:` | A bug fix | PATCH (`1.3.2` → `1.3.3`) |
| `feat:` | A new feature | MINOR (`1.3.2` → `1.4.0`) |
| `feat!:` or `BREAKING CHANGE:` footer | Breaking change | MAJOR (`1.3.2` → `2.0.0`) |
| `docs:`, `chore:`, `test:`, `refactor:` | No user-facing change | No release |

Examples:

```
feat(auth): add password reset flow
fix(api): handle null user in /profile endpoint
docs: fix typo in README
feat(api)!: rename `userId` field to `accountId`
```

That last one — the `!` — signals a breaking change and forces a MAJOR bump. The tool reads all commits since the last release, finds the *highest* bump implied, and that becomes your new version. The same commits become your changelog, grouped by type.

> This is the input contract. The discipline cost is real: everyone on the team has to write commits this way. The payoff is that the version and changelog become free, automatic, and never wrong. See [Changelogs and Release Notes](../02-changelogs-and-release-notes/README.md) for how the changelog gets shaped.

---

## Core Concept 4 — Your first semantic-release run

[`semantic-release`](https://semantic-release.gitbook.io/) is the canonical fully-automated tool for the JavaScript ecosystem. You write conventional commits; it does *everything else* with zero version numbers ever typed by a human.

**Step 1 — install:**

```bash
npm install --save-dev semantic-release
```

**Step 2 — configure.** Create `release.config.js` in your repo root:

```js
// release.config.js
module.exports = {
  branches: ["main"],
  plugins: [
    "@semantic-release/commit-analyzer",    // reads commits → decides bump
    "@semantic-release/release-notes-generator", // builds the changelog
    "@semantic-release/changelog",           // writes CHANGELOG.md
    "@semantic-release/npm",                 // bumps package.json + npm publish
    "@semantic-release/github",              // creates the GitHub release
  ],
};
```

**Step 3 — run it in CI.** Add a GitHub Actions workflow at `.github/workflows/release.yml`:

```yaml
name: Release
on:
  push:
    branches: [main]

permissions:
  contents: write       # to push tags + create releases
  id-token: write       # for npm trusted publishing (no token needed)

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # semantic-release needs full history
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Now merge a PR whose commit is `feat: add CSV export`. On push to `main`, semantic-release runs, sees the `feat:`, bumps `1.3.0` → `1.4.0`, writes the changelog, tags `v1.4.0`, publishes to npm, and creates the GitHub release. You typed no version number anywhere. That is the whole point.

> Note `fetch-depth: 0`: a forgotten setting that causes the single most common first-time failure. The tool needs the *entire* git history to find the last release and read all commits since.

---

## Core Concept 5 — Your first goreleaser run

For Go projects, [`goreleaser`](https://goreleaser.com/) is the standard. It is tag-driven: *you* create the tag (often the only manual step you keep at first), and goreleaser cross-compiles, archives, signs, and publishes.

**Step 1 — install and init:**

```bash
go install github.com/goreleaser/goreleaser/v2@latest
goreleaser init      # creates a starter .goreleaser.yaml
```

**Step 2 — a minimal `.goreleaser.yaml`:**

```yaml
# .goreleaser.yaml
version: 2

builds:
  - main: ./cmd/mytool
    binary: mytool
    goos: [linux, darwin, windows]   # cross-compile for 3 OSes
    goarch: [amd64, arm64]

archives:
  - formats: [tar.gz]
    name_template: "{{ .ProjectName }}_{{ .Version }}_{{ .Os }}_{{ .Arch }}"

release:
  github:
    owner: myorg
    name: mytool
```

**Step 3 — trigger on a tag in CI** at `.github/workflows/release.yml`:

```yaml
name: Release
on:
  push:
    tags: ["v*"]        # runs only when you push a tag like v1.4.0

permissions:
  contents: write

jobs:
  goreleaser:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-go@v5
        with:
          go-version: stable
      - uses: goreleaser/goreleaser-action@v6
        with:
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Now to release, you run two commands locally:

```bash
git tag v1.4.0
git push origin v1.4.0
```

CI sees the tag, goreleaser builds six binaries (3 OSes × 2 architectures), archives them, generates release notes from your commits, and uploads everything to a GitHub Release. Before pushing a real tag, run `goreleaser release --snapshot --clean` locally to do a dry run — it builds everything but publishes nothing.

> The difference in trigger style matters. semantic-release decides the version *for* you from commits (push-to-main triggered). goreleaser expects *you* to decide the version by tagging. Both are valid; you'll learn when each fits at the middle tier.

---

## Real-World Examples

**A solo npm library.** You maintain a small utility package. You set up semantic-release once. From then on, every merged PR with a `fix:` or `feat:` automatically ships a new version to npm with a clean changelog. You never run `npm publish` again, never touch `package.json`'s version, never forget to tag.

**A CLI tool written in Go.** Your team ships a developer CLI. With goreleaser, a single `git tag v2.1.0 && git push --tags` produces binaries for macOS, Linux, and Windows on both Intel and ARM, plus a Homebrew formula so users can `brew install yourtool`. The release that used to take an afternoon now takes four minutes of CI.

**The vacation test.** The one person who knew the manual release is away. A critical bug needs a hotfix. Because releasing is now `merge a PR with a fix: commit`, *anyone* on the team ships the patch. The bus factor went from one to everyone.

---

## Common Mistakes

- **Shallow git checkout.** Forgetting `fetch-depth: 0` so the tool can't see history. The number-one first-run failure.
- **Inconsistent commit messages.** Half the team writes `feat:`, the other half writes "fixed stuff." The tool can't compute the right version. Add commitlint to enforce the format (covered at middle tier).
- **Bumping the version by hand anyway.** Editing `package.json`'s version while also running semantic-release — they fight. Let the tool own the version completely.
- **Publishing from your laptop "just this once."** This recreates every problem automation was meant to solve. The release should only ever happen on CI.
- **Skipping the dry run.** Pushing a real tag to "see if it works." Always `--snapshot`/dry-run first.

---

## Apply it

1. Choose one small, known input for **Release Automation**.
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

- What problem does Release Automation solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
