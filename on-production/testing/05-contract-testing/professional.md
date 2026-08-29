# Contract Testing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Contract Testing** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Contract Testing
>
> *Adopting contract testing across an org: governance, ownership, versioning at scale, and CD integration.*

---

## Core Concept 1 — The adoption sequence

Roll out in an order that produces value early and avoids a big-bang stall:

```
1. Stand up the broker as platform infra (PactFlow hosted, or self-host).
   - SSO, RBAC, backups, retention policy. Treat it like a prod service.
2. Pick ONE high-value, painful consumer/provider pair as the pilot.
   - Ideally one that currently relies on a flaky shared E2E env.
3. Wire the consumer pipeline: pact test → publish (version=SHA, branch).
4. Wire the provider pipeline: verify → publishVerificationResult.
5. Turn on PENDING pacts on the provider (Concept 6) so new contracts
   never break the provider build before first verification.
6. Add can-i-deploy as a gate in BOTH pipelines (--to-environment).
7. Add record-deployment to both deploy steps.
8. Measure: contract coverage, gate catches, E2E flakiness drop.
9. Templatize the pipeline steps; onboard the next teams from the template.
```

The two non-negotiables that make or break adoption: **pending pacts on** (so providers aren't punished for consumers' new contracts) and **record-deployment everywhere** (so the gate is accurate). Skip either and teams lose trust in the gate, which is fatal.

---

## Core Concept 2 — Ownership: who owns the contract

In consumer-driven testing the *content* of the contract is determined by the consumer, but **ownership is a social contract** that must be explicit:

- **The consumer owns what's in the contract** — only the fields and interactions it actually uses. Bloated contracts (declaring fields the consumer ignores) over-constrain the provider and are the consumer's bug to fix.
- **The provider owns honoring it** — implementing state handlers and keeping responses compatible.
- **Both own the conversation when verification fails.** A failed verification is a *negotiation*, not a unilateral blocker: either the provider preserves the field, or the consumer agrees it can stop reading it and updates its contract.

Make ownership legible:

```
Convention (documented in the platform runbook):
  - Pacticipant names = service names, kebab-case, globally unique.
  - Each pacticipant maps to exactly one team (broker "team" field / labels).
  - A failed verification opens an auto-filed ticket tagged to BOTH teams.
  - The consumer team is the approver for changes to its own contract.
```

Without explicit ownership, a failed verification becomes a hot potato and the gate gets disabled "to unblock the release" — the beginning of the end.

---

## Core Concept 3 — CDC vs provider-driven as an org decision

At one service this is a tooling choice; at org scale it's a *policy* with real trade-offs:

| Factor | Consumer-driven (Pact) | Provider-driven (SCC / schema) |
|--------|------------------------|--------------------------------|
| No-silent-break guarantee | Strong — provider verifies every consumer's needs | Weaker — provider may drop unmentioned fields |
| Who must participate | Every consumer publishes a contract | Provider only |
| Works for unknown consumers | No | Yes |
| Coordination cost | Higher (consumers maintain contracts) | Lower |
| Best fit | Internal, enumerable consumers; high blast-radius seams | Public APIs; many/anonymous consumers; provider-owned platforms |

The pragmatic org policy is **hybrid, by boundary class**:

- **Internal service-to-service** → consumer-driven (Pact). The strong guarantee is worth the ceremony where blast radius is high and consumers are knowable.
- **Public/partner edge** → provider-driven / schema-based (OpenAPI), with formal versioning and deprecation windows (the `api-versioning` skill).
- **gRPC internal platform** → `buf` breaking-change detection as a schema gate; add message/Pact only where richer semantics matter.

Write this down as an architecture standard so teams don't relitigate it per service.

---

## Core Concept 4 — Versioning and branch/environment strategy at scale

At scale, the broker's value depends entirely on disciplined version metadata. Standardize three things:

1. **Version = immutable build identity.** Use the full git SHA (optionally `1.4.2+sha`). Never reuse a version number for different code.
2. **Branch metadata mirrors VCS.** Publish with `--branch $GIT_BRANCH` so the broker can reason about mainline vs feature work and auto-select WIP pacts.
3. **Environments are first-class.** Record deployments to named environments (`production`, `staging`) so `can-i-deploy --to-environment` is meaningful.

```bash
# Consumer publish — full identity + branch
pact-broker publish ./pacts \
  --consumer-app-version "$(git rev-parse HEAD)" \
  --branch "$GIT_BRANCH" \
  --tag-with-git-branch \
  --broker-base-url "$PACT_BROKER_URL" --broker-token "$PACT_BROKER_TOKEN"

# After a successful deploy — make the gate accurate
pact-broker record-deployment \
  --pacticipant OrdersService \
  --version "$(git rev-parse HEAD)" \
  --environment production
```

Add a **retention/cleanup policy** so the broker doesn't accumulate millions of stale feature-branch versions: keep all `production`/`staging` versions and the latest N per branch, prune the rest. Stale data slows queries and muddies the matrix.

---

## Core Concept 5 — The can-i-deploy gate across many pipelines

With dozens of services, the gate must be *templated, fast, and trustworthy*. A reusable pipeline fragment every team includes:

```yaml
# shared CI template: contract-gate (parameterized by PACTICIPANT)
deploy-gate:
  script:
    - pact-broker can-i-deploy
        --pacticipant "$PACTICIPANT"
        --version "$(git rev-parse HEAD)"
        --to-environment "$TARGET_ENV"
        --retry-while-unknown 60 --retry-interval 10
  rules:
    - if: '$DEPLOYING == "true"'
```

Operational rules that keep it healthy at scale:

- **The gate queries recorded results — it runs no tests — so it's fast and deterministic.** Slowness means broker/network, not test flakiness; treat broker latency as a platform SLO.
- **`--retry-while-unknown`** absorbs the race where a consumer just published and the provider hasn't verified yet.
- **Never let teams bypass the gate ad hoc.** A bypass is a policy exception that should require sign-off and leave an audit trail — otherwise the gate's guarantee silently evaporates. (See the broader quality-gates section for break-glass design.)

---

## Core Concept 6 — Pending pacts and WIP pacts: adopting without blocking

The single biggest adoption blocker is this failure mode: a consumer publishes a *new* contract requiring a field the provider doesn't yet have; the provider's *next, unrelated* build runs verification and goes red — punishing the provider for the consumer's in-progress work.

**Pending pacts** solve this. When enabled, a pact that has *never been successfully verified* on the provider's mainline is included in verification *for information* but does **not fail** the build:

```javascript
new Verifier({
  provider: 'PaymentsService',
  providerBaseUrl: 'http://localhost:8080',
  pactBrokerUrl: process.env.PACT_BROKER_URL,
  enablePending: true,                    // new contracts won't fail the build
  includeWipPactsSince: '2026-01-01',     // auto-include WIP pacts from feature branches
  providerVersionBranch: process.env.GIT_BRANCH,
  consumerVersionSelectors: [
    { mainBranch: true },                 // verify mainline consumers
    { deployedOrReleased: true },         // and whatever is live
  ],
}).verifyProvider();
```

How the lifecycle works:

```
Consumer publishes new contract requiring `currency`.
  → Provider build verifies it as PENDING → reports "would fail" but build stays GREEN.
Provider team adds `currency`, verifies → contract becomes VERIFIED on mainline.
  → From now on it is NO LONGER pending → future regressions FAIL the build.
```

**WIP pacts** extend this to feature branches: contracts in flight are auto-pulled into verification without the provider explicitly configuring each one. Together these let you turn on contract testing everywhere *immediately* without a coordination freeze — new work flows in safely, and the gate hardens automatically once a contract is first satisfied.

---

## Core Concept 7 — Governance, conventions, and metrics

Treat the contract program like any platform capability — with standards and signals:

**Conventions to mandate:**
- Pacticipant naming = canonical service name; one team per pacticipant.
- Always publish version (SHA) + branch; always `record-deployment`.
- `enablePending` + `includeWipPactsSince` on every provider.
- Contracts use matchers, never literal-value assertions on business data.

**Metrics that tell you the program is healthy:**

| Metric | What it signals |
|--------|-----------------|
| Contract coverage | % of service-to-service edges with a contract |
| Gate catch rate | Breaks caught at `can-i-deploy` vs leaked to prod |
| Verification debt | Count/age of unverified or never-verified pacts |
| E2E suite size & flakiness | Should *drop* as contracts absorb interface checks |
| Time-to-green after a break | How fast the consumer/provider negotiation resolves |

**Anti-goal — Goodhart's law:** don't reward "number of contracts." Reward *edges covered* and *breaks caught*. A team can game contract count with trivial pacts; it can't game a real prod break that the gate stopped.

---

## Core Concept 8 — Relationship to API versioning and E2E reduction

Contract testing and API versioning are complementary, not redundant:

- **API versioning** (the `api-versioning` skill) governs *intentional, planned* evolution — `v1` → `v2`, deprecation windows, sunset headers — especially for public/unknown consumers you can't verify against.
- **Contract testing** governs *unintentional* breakage among consumers you *can* enumerate, and gives a per-deploy safety check.

Use them in layers: contract tests catch the accidental break in CI/CD; versioning provides the deliberate migration path when a break is *intended*. For a public API you do both — schema-based contract checks at the edge plus a formal version policy.

**The E2E reduction is the strategic payoff.** Before contracts, teams pile up end-to-end tests to catch interface drift — slow, flaky, combinatorial. As contract coverage rises, you can *deliberately delete* most of those E2E tests, keeping only a thin layer for true multi-service *behavior* of critical journeys. The target shape (see the [test pyramid](../01-test-strategy-and-the-pyramid/professional.md)):

```
Before contracts:        After contracts:
  many flaky E2E           thin E2E (critical journeys only)
  ───────────────         ──────────────────
  few contract             broad contract coverage (every seam)
  many unit                many unit (unchanged)
```

Track E2E count going *down* as a success metric of the contract program — it's the clearest evidence the investment paid off.

---

## Real-World Examples

- **Platform rollout.** A 40-service org stands up PactFlow as platform infra, pilots on the order/payment seam (their flakiest E2E), templatizes the pipeline, and turns on pending pacts. Within a quarter, contract coverage hits 80% of internal edges and the nightly E2E suite shrinks by half.
- **Pending pacts save a build.** A consumer team publishes a contract needing `currency` on Friday. The provider's Monday build reports it as pending (green), the provider adds the field Tuesday, and the contract hardens — no cross-team fire drill.
- **Hybrid policy.** Internal services use Pact; the public API uses OpenAPI-based bi-directional checks plus a `v1`/`v2` version policy with a 6-month deprecation window.
- **Gate audit trail.** A release engineer needs to bypass `can-i-deploy` during an incident; the break-glass path requires a director's approval and files an automatic ticket, preserving the gate's integrity.

---

## Common Mistakes

- **Big-bang rollout with pending pacts off.** Providers get punished for consumers' new work; teams disable the gate.
- **Letting `record-deployment` lapse.** The gate quietly reasons about the wrong production set.
- **Rewarding contract count.** Goodhart kicks in; reward edge coverage and prod breaks caught.
- **No retention policy.** The broker bloats with feature-branch versions; queries slow, the matrix muddies.
- **Ad-hoc gate bypasses.** Each undocumented bypass erodes the guarantee until it's worthless.
- **Keeping the old E2E suite forever.** You pay for contracts *and* the flaky tests they were meant to replace.
- **No ownership model.** Failed verifications become hot potatoes; the gate gets turned off "to ship."

---

## Apply it

1. Define the user or business outcome that **Contract Testing** should improve.
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

- Which measurable outcome justifies investing in Contract Testing?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
