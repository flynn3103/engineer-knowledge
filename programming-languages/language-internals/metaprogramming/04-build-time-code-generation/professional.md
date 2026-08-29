# Build-Time Code Generation — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Build-Time Code Generation** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Schema Registry — Contracts as Governed Artifacts

At scale, schemas cannot live as loose files in dozens of repos. A **schema registry** makes the IDL a first-class, versioned, governed artifact:

- **Single source of truth, centrally hosted.** The `payments.proto` everyone depends on has one canonical, versioned home.
- **Compatibility enforced at push time.** The registry rejects a schema change that breaks wire compatibility (reused field number, type change) *before* it can affect any consumer — the gate the generator itself never provides.
- **Access control and ownership.** Who may change the payments contract is governed, not implicit.
- **Generation as a service.** Consumers fetch generated code for a pinned schema version (and a pinned generator version) from the registry, rather than each running `protoc` with bespoke plugins.

The registry turns "every team runs their own generator on copied `.proto` files" (chaos, skew, incompatibility) into "one governed contract, compatibility-gated, with reproducible generation." This is the single highest-leverage structural change for generation at scale.

### 2. Hermetic, Reproducible Generation

Reproducibility means: the *same* schema + the *same* pinned generator produces *byte-identical* output, anywhere, any time. Two requirements:

1. **A pinned, hermetic generator.** The generator (and every plugin) is version-locked and supplied as a declared build input — via Bazel's build graph, a pinned container image, or a tool like `buf` that bundles the toolchain. No reliance on whatever `protoc` happens to be on the developer's `PATH`.
2. **A deterministic generator.** The generator must emit identical bytes for identical input — no embedded timestamps, no nondeterministic map iteration ordering the output, no absolute paths. A nondeterministic generator makes reproducibility and drift checks impossible (every run "differs"). Mature generators document and guarantee determinism.

Bazel is the archetype: `proto_library` + language rules make the schema a declared input, the generated code a declared output, and the generator a pinned tool in the build graph — generation is incremental, cached, and hermetic by construction. Outside Bazel, the common pattern is **containerized generation**: a pinned image with the exact generator+plugins, run identically in CI and locally.

### 3. Generator Version Management Across a Fleet

A generator upgrade (e.g. a new `protoc-gen-go` major) can change generated output — new APIs, renamed symbols, different defaults. Across hundreds of consumers this is a coordinated migration, not a `bump-and-pray`:

- **Pin centrally, roll deliberately.** The registry/platform owns the blessed generator version; consumers do not each pick their own.
- **Canary the upgrade.** Regenerate a few representative services with vN+1, build and test them, before rolling fleet-wide.
- **Decouple generator upgrades from schema changes.** Never change the schema *and* bump the generator in the same step — you cannot tell which caused a difference.
- **Diff the generated output across generator versions** as part of the upgrade review, not just the schema diff.

Version skew (`senior.md`) at fleet scale is not a churning diff — it is *incompatible generated code across services*, which is a production incident waiting to happen.

### 4. CI/CD Topologies for Generation

Three common topologies, each with trade-offs:

```text
  A. GENERATE-IN-EACH-BUILD (gitignored)
     schema ──▶ each CI build runs the pinned generator ──▶ compile
     + DRY, no committed artifacts   − every build needs the toolchain; slower

  B. COMMIT-AND-DRIFT-CHECK
     schema ──▶ author regenerates + commits ──▶ CI drift-check gates staleness
     + zero-setup clones, fast builds, auditable   − two-step authoring, diff noise

  C. PUBLISH-AS-PACKAGES (registry/poly-repo)
     schema ──▶ registry generates + publishes versioned SDKs ──▶ consumers depend on a version
     + clean consumers, explicit versioning, decoupled rollout   − registry infra, lag between schema and SDK
```

At scale, **C (publish generated SDKs as versioned packages)** is the mature pattern for cross-team contracts: a service depends on `payments-client@2.3.0`, upgrades on its own schedule, and the schema/generator infrastructure is owned by a platform team. **B** remains common within a repo; **A** suits hermetic mono-repos (Bazel).

### 5. Supply-Chain Integrity of Generated Code

Generated code is *executable code in your supply chain*, produced by a tool — so it inherits supply-chain risk:

- **Provenance.** Record which generator (name, version, hash) produced which artifact, so an SBOM/SLSA attestation covers generated code, not just hand-written code.
- **Integrity of the generator itself.** A compromised generator (or a malicious plugin) can inject code into *every* artifact it produces — a high-value supply-chain target. Pin by content hash, fetch from trusted registries, verify signatures.
- **Reproducibility as a security control.** If generation is reproducible, an auditor can independently re-run it and confirm the committed/published generated code matches the schema — detecting tampering.
- **Committed generated code aids audit.** Reviewers and scanners see exactly what ships; gitignored generated code is invisible until build time, which complicates audit.

The mental shift: the generator is a privileged build component with write access to your binary, and must be governed like one.

### 6. Mono-Repo vs Poly-Repo Distribution

Where generated code lives shapes how cross-cutting schema changes propagate:

- **Mono-repo:** schema, generated code, and all consumers in one repo. A schema change and its consumer updates land in *one atomic commit* — no version negotiation, no flag day, instant fleet-wide consistency. Cost: requires a mono-repo and (usually) a hermetic build (Bazel) to scale.
- **Poly-repo + published SDKs:** schema in one repo; generated SDKs published as versioned packages; consumers upgrade independently. Cost: version negotiation, lag, the **expand-migrate-contract** dance for breaking changes — but teams deploy on their own schedule and ownership is clean.

Most large organizations run **poly-repo with a schema registry and published SDKs**, because independent deployment outweighs atomic consistency; the very largest (Google-style) run mono-repos where atomic schema migrations are the norm.

### 7. Large-Scale Migration Patterns

Migrating a schema across a fleet without a flag day uses **expand-migrate-contract**, the same staged pattern as a zero-downtime database migration:

1. **Expand:** add the new field/method/version *additively* (new protobuf field number, new API version). Old and new coexist; nothing breaks. Regenerate; all consumers still compile.
2. **Migrate:** move consumers to the new shape, one team/service at a time, on their own schedule.
3. **Contract:** once telemetry confirms no consumer uses the old shape, remove it and `reserve` the field number.

This works precisely *because* generation makes the contract explicit and compatibility-checkable — the registry can gate each step, and the generated code makes "who still uses the old field" answerable.

---

## Code Examples

### Example 1: `buf` registry-based hermetic generation

```yaml
# buf.gen.yaml — pinned plugins, reproducible output, no local protoc-plugin management.
version: v2
plugins:
  - remote: buf.build/protocolbuffers/go:v1.34.2   # version-pinned, hermetic
    out: gen/go
  - remote: buf.build/grpc/go:v1.4.0
    out: gen/go
```

```bash
buf generate            # runs pinned remote plugins reproducibly
buf breaking --against 'buf.build/acme/payments'   # fleet-wide compatibility gate
```

The generator toolchain is pinned by version and run hermetically; compatibility is gated against the registry's canonical version.

### Example 2: Provenance for generated code in CI

```yaml
- name: Generate
  run: buf generate
- name: Record provenance
  run: |
    echo "generator=protocolbuffers/go:v1.34.2" >> gen/PROVENANCE
    echo "schema_commit=$(git rev-parse HEAD)"   >> gen/PROVENANCE
    echo "generated_at=reproducible"             >> gen/PROVENANCE
```

The SBOM/attestation now covers *how* the generated code was produced, not just that it exists.

### Example 3: Bazel hermetic proto generation

```python
# BUILD — schema is a declared input, generated code a declared output,
# the generator a pinned tool in the build graph.
proto_library(name = "payments_proto", srcs = ["payments.proto"])

go_proto_library(
    name = "payments_go_proto",
    proto = ":payments_proto",
    importpath = "acme/payments",
)
```

Generation is incremental, cached, and reproducible by construction; the generator version is part of the workspace, not the developer's `PATH`.

### Example 4: Fleet generator-upgrade canary

```bash
# Regenerate a representative service with the candidate generator,
# build + test it, and DIFF the generated output before fleet rollout.
PROTOC_GEN_GO=v1.35.0 buf generate --path services/canary
git diff --stat gen/                 # inspect generated-output delta
go test ./services/canary/...        # confirm behavior unchanged
```

Generator upgrades are migrations, canaried like any other.

### Example 5: Expand-migrate-contract on a shared schema

```proto
// EXPAND: add the new field additively; old consumers unaffected.
message Payment {
  uint64 amount_cents = 1;          // legacy
  Money  amount       = 2;          // new richer type, NEW number
  // MIGRATE consumers from amount_cents -> amount over time.
  // CONTRACT (later): remove amount_cents and `reserved 1;`
}
```

---

## Coding Patterns

**Pattern: Centralize the contract in a registry; consume pinned versions.** No team forks or copies the canonical schema.

**Pattern: Make generation hermetic and deterministic.** Pinned, containerized/Bazel-driven generator; assert byte-stable output.

**Pattern: Distribute generated code as versioned SDKs across a poly-repo.** Consumers depend on a version and upgrade on their schedule.

**Pattern: Gate every schema change on a breaking-change check at push.** Compatibility is enforced before consumers are affected.

**Pattern: Treat generator upgrades as canaried, staged migrations** decoupled from schema changes.

**Pattern: Attach provenance to generated artifacts** so the SBOM/attestation covers them.

---

## Best Practices

1. **Host shared schemas in a governed registry with push-time compatibility enforcement.**
2. **Make generation hermetic, pinned, and deterministic** — Bazel or containerized toolchains; assert reproducibility.
3. **Distribute generated code as versioned SDKs** for independently-deployed consumers; mono-repo + atomic only where the build supports it.
4. **Roll generator upgrades as canaried migrations**, decoupled from schema changes, diffing generated output.
5. **Use expand-migrate-contract for every breaking schema change**; never a flag day.
6. **Secure the generator supply chain** — pin by hash, verify signatures, record provenance.
7. **Own generation as a platform service**, not a per-repo afterthought.

---

## Edge Cases & Pitfalls

**A nondeterministic generator.** Map-iteration ordering or embedded timestamps make every run differ; drift checks fire constantly and reproducibility is impossible. Fix the generator (or its config) to be deterministic, or pin it and normalize output.

**Coupling a generator upgrade with a schema change.** When output changes, you cannot attribute it. Always separate the two commits.

**Registry compatibility gate bypassed.** A team copies the `.proto` locally and regenerates, skipping the registry's compatibility check, and ships an incompatible change. Enforce that generation flows through the registry.

**Published-SDK version lag.** The schema changed but the generated SDK is not yet published, so consumers are stuck or pin an old version. Automate SDK publication on schema merge.

**Generator supply-chain compromise.** A malicious plugin injects code into every generated artifact — invisible if generated code is gitignored and unaudited. Pin by hash, verify, and prefer committed + reproducible for audit.

**Mono-repo migrations that touch thousands of files.** An additive schema change regenerates a huge swath; review tooling must collapse generated diffs or reviewers drown. Configure generated-file diff suppression.

**Contract phase skipped.** Old fields are never removed because no one confirms they are unused; schemas bloat for years. Use telemetry to drive the contract step.

---

## Apply it

1. Define the user or business outcome that **Build-Time Code Generation** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Build-Time Code Generation?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
