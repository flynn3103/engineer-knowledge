# Registries & Distribution — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Registries & Distribution** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Registries & Distribution

*Where your artifacts live after the build, and how everyone else gets them.*

---

## Core Concept 1 — What a registry is

A registry is an HTTP service that does two jobs: **accept uploads** of artifacts and **serve downloads** of them. Different ecosystems have their own registries, but they all play the same role.

| Kind | Examples | Holds |
|------|----------|-------|
| Container / OCI | Docker Hub, GitHub Container Registry (GHCR), Amazon ECR, Artifactory | Container images |
| Language packages | npm, PyPI, crates.io, Maven Central, RubyGems, Go module proxy | Libraries |
| OS packages | apt repos, yum/dnf repos | `.deb` / `.rpm` system packages |
| Generic | Artifactory, Nexus, S3 buckets | Any file: binaries, zips, installers |

When you run `npm install express`, npm contacts the npm registry. When Kubernetes starts a pod, the node pulls the image from a container registry. The registry is the hand-off point between "we built it" and "someone runs it".

```bash
# Every install you've ever run hits a registry under the hood
npm install express          # -> registry.npmjs.org
pip install requests         # -> pypi.org
docker pull nginx            # -> docker.io (Docker Hub)
```

## Core Concept 2 — Coordinates: name, version, digest

To fetch an artifact you need to *address* it. Three pieces matter:

1. **Name** — what it is: `express`, `nginx`, `requests`.
2. **Version** — which release: `4.18.2`, `1.25.3`.
3. **Digest** — the exact bytes, as a hash: `sha256:e7c3f...`.

A **tag** is a friendly pointer. `nginx:1.25` is a name + tag. But here's the crucial fact you'll meet everywhere:

> **Tags are mutable. Digests are immutable.**

A tag like `latest` or `1.25` can be *moved* to point at new bytes tomorrow. A digest can never point at different bytes — change one byte and the hash changes. So when you want certainty about *exactly* what you're running, you reference the digest:

```bash
# By tag — convenient, but the bytes can change later
docker pull nginx:1.25

# By digest — pinned forever to these exact bytes
docker pull nginx@sha256:e7c3f...d91
```

You'll learn much more about why this matters in [middle.md](middle.md). For now: tags = friendly + changeable, digests = exact + permanent.

## Core Concept 3 — Publishing a container image

Publishing an image is `build` then `push`. The image name encodes the registry, namespace, and repository.

```bash
# Format: REGISTRY/NAMESPACE/REPO:TAG
# Build and tag for GitHub Container Registry
docker build -t ghcr.io/myorg/web-api:1.4.0 .

# Log in (use a token, not your password)
echo "$GHCR_TOKEN" | docker login ghcr.io -u myuser --password-stdin

# Push it
docker push ghcr.io/myorg/web-api:1.4.0
```

After the push, the registry returns the **digest** it stored. Copy it — deployments should reference the digest, not just the tag:

```
ghcr.io/myorg/web-api:1.4.0
  digest: sha256:9b2c4e...a17
```

Common registries and their host prefixes:

```bash
docker.io/library/nginx          # Docker Hub (default if no host given)
ghcr.io/myorg/web-api            # GitHub Container Registry
123456789.dkr.ecr.us-east-1.amazonaws.com/web-api   # Amazon ECR
```

## Core Concept 4 — Publishing a language package

Each language ecosystem has its own publish command, but the shape is the same: authenticate, then upload.

**npm** (JavaScript):
```bash
npm login                    # or set an automation token in CI
npm publish                  # reads name + version from package.json
```

**PyPI** (Python) — build a wheel, then upload with `twine`:
```bash
python -m build              # produces dist/*.whl and *.tar.gz
twine upload dist/*          # uploads to pypi.org
```

**crates.io** (Rust):
```bash
cargo login                  # paste your API token once
cargo publish                # packages and uploads the crate
```

**Maven Central** (Java) — deploy to a staging repo, then release:
```bash
mvn deploy                   # uploads to the staging repository
# then "release" the staging repo (via Sonatype/Nexus UI or plugin)
```

**Go** is the odd one out — there is **no push**. You don't upload Go modules. You just **tag your Git repo** and the Go module proxy fetches it from version control the first time someone asks for it:

```bash
git tag v1.4.0
git push origin v1.4.0
# Done. proxy.golang.org fetches it from your VCS when requested.
```

> The key thing: the name in your manifest (`package.json`, `Cargo.toml`, `pom.xml`) plus the version is your coordinate. Bump the version every release.

## Core Concept 5 — Pulling and authenticating

Pulling public artifacts usually needs no auth. Private ones need a token.

```bash
# Public — just works
docker pull nginx:1.25
npm install lodash

# Private — log in first
docker login ghcr.io                     # container registry
npm config set //registry.npmjs.org/:_authToken=$NPM_TOKEN
pip install --index-url https://user:token@pypi.mycompany.com/simple/ mylib
```

**Use tokens, not passwords.** A token can be scoped (read-only, or read+publish) and revoked without changing your password. In CI you set the token as a secret environment variable — never commit it to the repo.

Two permission levels you'll meet immediately:

- **Read** — pull/install. Often public or a low-privilege token.
- **Publish/write** — push new versions. Always guard this; a leaked publish token lets an attacker ship malicious versions under your name.

## Real-World Examples

**Example 1 — A web service image.** Your CI builds `ghcr.io/acme/checkout:2.3.1`, pushes it, and records the digest `sha256:1f0a...`. The Kubernetes manifest deploys `checkout@sha256:1f0a...`. Even if someone later re-tags `2.3.1`, your running cluster keeps the exact bytes it deployed.

**Example 2 — Installing a library.** A teammate adds `requests==2.31.0` to `requirements.txt`. On every machine and in CI, `pip install` fetches the *same* version from PyPI. The version number is the shared coordinate.

**Example 3 — A Go module.** You release `github.com/acme/toolkit v0.5.0` by pushing a Git tag. A user runs `go get github.com/acme/toolkit@v0.5.0`; the Go proxy fetches it from your repo, caches it, and serves it to everyone after that. You never ran a "publish" command.

## Common Mistakes

- **Depending on `latest`.** `latest` is just a tag that someone moves. Your build today and tomorrow can silently get different bytes. Pin a real version (and ideally a digest).
- **Committing tokens.** A registry token in Git is a published credential. Use CI secrets and revoke leaked ones immediately.
- **Forgetting to bump the version.** Most registries refuse to overwrite an existing version. If your publish fails with "version already exists", you forgot to increment.
- **Using your password to log in from CI.** Use a scoped automation token instead so you can revoke it cleanly.
- **Pushing to the wrong namespace.** `docker push nginx` (no namespace) targets Docker Hub's official library — which you can't write to. Always prefix `ghcr.io/myorg/...` or your registry host.

---

## Apply it

1. Choose one small, known input for **Registries & Distribution**.
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

- What problem does Registries & Distribution solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
