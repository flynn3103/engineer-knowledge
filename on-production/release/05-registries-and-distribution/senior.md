# Registries & Distribution — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Registries & Distribution** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Registries & Distribution

*The registry is critical infrastructure, a single point of failure, and a supply-chain entry point. Engineer it like one.*

---

## Core Concept 1 — The registry as a single point of failure

Trace what depends on a registry being up:

- **Deploys** — Kubernetes can't pull the image, pods won't start.
- **Autoscaling & node replacement** — a scale-up event or node crash needs a fresh pull. If the registry is down *during an incident*, you can't add capacity exactly when you need it most.
- **CI** — every build pulls base images and dependencies.
- **Developer machines** — `npm install`, `pip install`, `go get`.

- The dependency is worst at the worst time: a traffic spike triggers autoscaling, which triggers image pulls, which hammer the registry — and a registry outage during a spike means no new capacity.
- This is why the famous failure mode is *correlated*: the registry and your app fail together because the app's recovery depends on the registry.

Mitigations (developed below):

- **Local caching on nodes** — a steady-state node doesn't need the registry.
- **Pull-through caches/mirrors** — you don't depend on a third party's uptime.
- **Digest pinning** — a cache hit is guaranteed-correct.
- **`imagePullPolicy: IfNotPresent` with digests** — cached images are reused safely.

```yaml
# A node with the image already cached survives a registry outage
imagePullPolicy: IfNotPresent     # safe ONLY with immutable refs (digests/immutable tags)
image: ghcr.io/acme/api@sha256:9b2c4e...a17
```

> Senior framing: design so that *steady state* doesn't touch the registry, and *recovery* touches a cache you control, not a vendor's public endpoint.

## Core Concept 2 — Mirrors, pull-through caches, and dependency proxies

You rarely want every machine pulling directly from `docker.io` or `registry.npmjs.org`. Reasons:

- Rate limits (Docker Hub's anonymous pull limits have bitten countless CI fleets).
- Latency.
- Egress cost.
- Third-party uptime.

**Pull-through cache (containers).** Run a registry that proxies an upstream and caches blobs locally. The first pull fetches from upstream; subsequent pulls are local.

```yaml
# containerd: route docker.io through an internal pull-through mirror
# /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://docker.io"
[host."https://mirror.internal.acme.com"]
  capabilities = ["pull", "resolve"]
```

**Dependency proxy (language packages).** Artifactory/Nexus/Verdaccio (npm), devpi (PyPI), or a Go `GOPROXY` proxy the public registry, cache artifacts, and let you survive an upstream outage:

```bash
# Go: route module fetches through your proxy, then public, then direct
export GOPROXY=https://goproxy.internal.acme.com,https://proxy.golang.org,direct
# npm: point at an internal proxy that caches the public registry
npm config set registry https://npm.internal.acme.com

# PyPI: index-url to internal proxy
pip config set global.index-url https://pypi.internal.acme.com/simple/
```

- Benefit beyond uptime: a single chokepoint where you can **scan, enforce policy, and audit** every dependency entering the org.
- Cost: you now operate that proxy and must keep it patched and available.

## Core Concept 3 — The public/private split and vendoring

Most orgs run a hybrid: public registries for open-source, a **private registry** for proprietary artifacts. Decisions:

- **What's private?** Your own images and internal libraries — always private. Build provenance and SBOMs — private.
- **How do you consume public?** Directly (simple, but exposes you to upstream outages/yanks/typosquats) vs. **through a caching proxy** (resilient, auditable, but operational cost) vs. **vendoring** (commit dependencies into your repo).

**Vendoring vs proxy** is a real trade-off:

| Approach | Resilience | Reproducibility | Cost | Best for |
|----------|-----------|-----------------|------|----------|
| Direct from public | low | depends on lockfiles | none | small teams, low stakes |
| Caching proxy | high | high (cached + locked) | run a proxy | most orgs |
| Vendoring (`go mod vendor`, committed deps) | highest (no network) | total | repo bloat, manual updates | air-gapped, ultra-high-assurance, hermetic builds |

```bash
# Go vendoring: deps live in ./vendor, builds need no network
go mod vendor
go build -mod=vendor ./...
```

- Vendoring gives you a hermetic, network-free, perfectly reproducible build at the cost of bloat and update friction.
- A caching proxy gets you most of the resilience with far less friction and is the default for most organizations.
- The right answer scales with your assurance requirements.

## Core Concept 4 — Distribution at scale: CDNs and regional registries

- When consumers are global, a single-region registry means high latency for distant pulls and large cross-region/cross-cloud **egress bills**.
- Public registries already front their blob storage with CDNs (npm, PyPI, crates.io all serve tarballs from CDN edges); at scale you do the same internally.

- **Regional replicas.** Replicate your registry (or its blob store) per region so pulls are local. ECR has cross-region replication; Artifactory has replication; cloud registries offer multi-region.
- **CDN in front of blobs.** Image *layers* and package *tarballs* are immutable and content-addressed — ideal CDN cache keys. The mutable *manifest/index* is small and changes rarely. This is exactly the split the `cdn-design` skill describes: cache the immutable bytes aggressively, serve the small mutable pointer with short TTL.
- **Egress economics.** Pulling 200 nodes × a 1 GB image across regions on every scale event is real money. Regional caches turn that into one cross-region fetch plus local serves.

```
client → regional pull-through cache (CDN-fronted) → upstream registry
            ^ cache hit on immutable layer = no egress, low latency
```

> The content-addressed nature of registries (immutable layers keyed by digest) is *why* CDNs work so well here: an immutable object can be cached forever with no invalidation problem. See `caching-strategies` for TTL and invalidation patterns on the mutable manifest side.

## Core Concept 5 — HA and DR for a private registry

If you run a private registry, it inherits production SLAs — design it like any stateful service:

- **Stateless front, durable back.** The registry process is often stateless; the **blob storage** (S3/GCS/Azure Blob) and the **metadata DB** are the durable state. Make those HA, not the front-end pods.
- **Replicated, durable storage.** Back blobs with object storage that has its own replication/durability. Replicate metadata.
- **Multi-AZ / multi-region.** Run the front-end across availability zones; replicate storage across regions for DR.
- **Define RTO/RPO.** How long can deploys be blocked (RTO)? How much recently-pushed-but-unreplicated data can you lose (RPO)? A registry that loses the last hour of pushes may strand a release.
- **Test failover.** Pull through the failover path regularly. A DR plan you've never exercised is a hypothesis.
- **Backups of metadata.** Blob loss is often recoverable from object-store durability; *metadata* (tag→digest mappings, permissions) loss is catastrophic. Back it up.

```text
                ┌──────────────┐
   clients ───▶ │ registry LB  │ (multi-AZ, stateless front)
                └──────┬───────┘
                       ▼
        ┌──────────────────────────────┐
        │ object storage (blobs)        │  cross-region replicated
        │ metadata DB (tag→digest, ACL) │  replicated + backed up
        └──────────────────────────────┘
```

> The asymmetry to remember: immutable blobs are cheap to replicate and easy to recover; mutable metadata is the fragile, must-back-up part. (See the `high-availability-patterns` skill for failover and quorum patterns.)

## Core Concept 6 — The registry as a supply-chain entry point

- Everything you deploy comes *through* the registry.
- That makes it the highest-leverage point for both attack and defense.

Attack surface:
- **Compromised public dependency** (typosquat, malicious version, hijacked maintainer account).
- **Tag mutation** on a registry that doesn't enforce immutability — bytes swapped under a trusted tag.
- **Registry compromise** — attacker pushes a malicious image under your namespace.

Defenses, layered:
1. **Pin by digest** everywhere — a digest can't be silently swapped (covered in middle).
2. **Sign artifacts and verify on pull/admission.** Only signed-by-us images are admitted. This is the link to [Artifact Signing & Provenance](../04-artifact-signing-and-provenance/senior.md): the registry stores the artifact and its signature; the *admission gate* enforces "no signature, no run."
3. **Admission control.** A Kubernetes policy (e.g. Sigstore policy-controller, Kyverno) rejects images that aren't signed by your key / lack provenance / aren't from an allowed registry.
4. **Scan on entry.** Your dependency proxy/registry scans for known CVEs and blocks or flags.
5. **Immutable tags.** Configure the registry to forbid retagging release tags so a trusted tag can never be repointed.

```yaml
# Kyverno-style policy: only admit images from our registry, signed by our key
verifyImages:
  - imageReferences: ["ghcr.io/acme/*"]
    attestors:
      - entries:
          - keys: { publicKeys: |-  <our cosign public key> }
```

> Senior principle: the registry is where you *enforce* supply-chain policy because it's the one chokepoint every artifact passes through. Detail lives in [Supply-Chain Security](../09-supply-chain-security/senior.md).

## Core Concept 7 — Auth, scopes, and namespace ownership

At scale, access control is where incidents are prevented or caused:

- **Separate read and publish.** The vast majority of consumers need read-only. Publish rights belong to CI service identities, not humans, and not broadly.
- **Scoped, short-lived credentials.** Prefer OIDC / workload identity (CI authenticates per-run, no stored token) over long-lived publish tokens. A leaked long-lived publish token = attacker ships under your name.
- **Namespace ownership and squatting.** A *namespace* (`@acme/`, `ghcr.io/acme/`) asserts who owns a name. **Typosquatting** (`reqeusts` vs `requests`) and **dependency confusion** (publishing a public package with the same name as your private internal one, so resolvers grab the attacker's) are real, exploited attacks. Defenses: reserve your org names publicly, scope internal packages (`@acme/...`), and configure resolvers so private names never fall back to public.
- **Least privilege on the registry itself.** Who can delete? Who can change retention? Who can repoint a release tag? These should be tightly held and audited.

```bash
# Dependency-confusion defense (npm): force scoped names to the private registry only
# .npmrc
@acme:registry=https://npm.internal.acme.com
# never let @acme/* resolve from the public registry
```

## Core Concept 8 — Storage, GC, and cost at scale

A busy org pushes thousands of images and packages daily. Without governance, storage grows unbounded and the bill follows:

- **Untagged GC.** Run garbage collection that removes untagged manifests and unreferenced blobs (deduplicated by digest, so shared layers aren't deleted while still referenced).
- **Retention by class.** Different rules for `pr-*` / CI-scratch tags (expire fast) vs `v*` release tags (keep long / forever). **Never** age-expire something production pins.
- **Dedup awareness.** OCI blobs are content-addressed and shared across images; "delete this image" doesn't delete layers another image still uses. Measure *unique* storage, not summed image sizes.
- **Cost attribution.** Tag/label artifacts by team so storage and egress cost can be charged back, which creates the incentive to clean up.

```bash
# Distribution (the open-source registry) GC, after marking deletions
registry garbage-collect /etc/docker/registry/config.yml --delete-untagged
```

> Cost governance is a senior responsibility: set retention as policy (versioned, reviewed), automate it, exempt release tags, and attribute cost so teams own their footprint. (More in the cost-governance treatment in [professional.md](professional.md).)

## Real-World Examples

**Example 1 — Docker Hub rate limits halt CI.** A fleet pulling base images anonymously from Docker Hub hits the pull-rate limit mid-morning; builds fail org-wide. Fix: stand up a pull-through cache; CI now pulls base images locally, decoupled from Docker Hub's limits and uptime.

**Example 2 — Dependency confusion.** An attacker publishes `acme-internal-utils` to public npm matching the org's private package name. CI, mis-configured to fall back to public, installs the attacker's version. Fix: scope all internal packages (`@acme/internal-utils`) and pin the scope to the private registry so public fallback is impossible.

**Example 3 — Registry DR drill.** During a quarterly game day, the team fails the private registry to its secondary region. Pulls succeed via replicated blobs, but *pushes* fail because the metadata DB hadn't been promoted — they discover their RTO assumption was wrong before it mattered in a real incident.

## Common Mistakes

- **Pulling base images directly from public registries fleet-wide.** Rate limits and upstream outages become your outages. Cache through a proxy.
- **No HA/DR plan for the private registry.** It's production infra; treat it like the database it effectively is.
- **Backing up blobs but not metadata.** Tag→digest mappings and ACLs are the irreplaceable part.
- **Mutable release tags + admission that trusts tags.** An attacker repoints the tag; you admit malware. Pin digests and enforce immutable tags.
- **Public fallback for private package names.** Open door to dependency confusion. Scope and lock resolution.
- **Retention that age-expires release artifacts.** Production can't pull an image you deleted.
- **Never testing failover.** An untested DR path is a guess.

---

## Apply it

1. State the system invariant that **Registries & Distribution** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Registries & Distribution fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
- Why is a registry a single point of failure, and when is that failure worst?
- What is a pull-through cache, and why would you run one?
- How would you make a private registry highly available? What's the most critical thing to back up?
- Half your Kubernetes nodes are running old code after a deploy, even though you pushed a new image — what happened?
- CI suddenly fails org-wide with "too many requests" pulling base images — what's your fix?
