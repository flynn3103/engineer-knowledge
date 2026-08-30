# Test Data Management — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Test Data Management** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Data Management
>
> *Running test data as an organisational program — ownership, GDPR governance, synthetic-data pipelines, and lifecycle economics.*

---

## Core Concept 1 — Test Data as a Platform Program

A program differs from a project: it has a permanent owner, a charter, and success metrics. A test-data platform program typically owns:

- The **builder/factory library** consumed by every suite.
- The **masking and synthetic-generation pipelines** that produce safe realistic data.
- The **provisioning tooling** that gives engineers data-on-demand.
- The **policy and enforcement** that keeps PII out of lower environments.

Useful program metrics: median time to provision a usable dataset; percentage of suites on the shared builder library vs hand-rolled; data-freshness age (how old is the masked sample?); and PII-exposure incidents (target: zero). These turn "we have good test data" from a vibe into a measurable capability with owners and trends.

The framing that wins funding: test data is on the critical path of every release. Slow, unrealistic, or non-compliant test data taxes every team continuously and risks a breach. A small central investment removes a distributed, recurring cost — the classic platform argument.

---

## Core Concept 2 — Owning the Builder Library Across an Org

A single team's builder library is easy. An org-wide one faces a tension: central teams want consistency; product teams want to extend builders for their own domains. The pattern that resolves it is **a core library plus a contribution model**:

- The platform team owns the **core** (base builders, the clock, persistence helpers, the masking primitives) and the **contracts** (every builder must be composable, clock-injected, and backward-compatible).
- Product teams **contribute** domain builders via review, following those contracts. The platform team gates merges on the contracts, not on domain knowledge it doesn't have.
- **Versioning and deprecation** are run like any library: semantic versions, a deprecation window, and a migration guide when a contract changes. Breaking 900 downstream test files without a migration path is how platform teams lose trust.

```python
# Contract enforced in CI for every contributed builder:
#   1. build() returns a valid object with zero required args
#   2. all dates come from inject_clock(), never datetime.now()
#   3. adding a field uses a default — never a new required arg
def test_builder_contract(builder_cls):
    obj = builder_cls().build()            # must work with no overrides
    assert obj is not None
    assert_no_wall_clock_calls(builder_cls)  # static/AST check for now()
```

The decisive cultural rule: **a broken core builder is a P1**, because it breaks every team at once. The owning team must treat the library with the same operational seriousness as a production service — on-call, SLAs, and a changelog.

---

## Core Concept 3 — The Compliance Dimension: GDPR and Data Residency

Test data is where engineering practice meets data-protection law, and the law is not optional.

**The core prohibition.** Personal data in test environments is still personal data. GDPR's **purpose limitation** means data collected to provide a service generally may not be repurposed for testing without a lawful basis. **Data minimisation** means you shouldn't hold PII you don't need — and for testing, you almost never *need* real identities. The practical conclusion is the senior-level rule, now with legal teeth: **raw production PII must not enter lower environments.**

**Data residency.** Some jurisdictions require personal data to stay within their borders. If your test infrastructure or a developer's laptop sits in another region, even masked-but-reversible (pseudonymised) data can violate residency. Fully synthetic or irreversibly anonymised data sidesteps residency because it isn't personal data — another argument for synthesis over copying.

**DPIA and the right to erasure.** Risky processing (e.g. building a re-identifiable test set from prod) can require a **Data Protection Impact Assessment**. And GDPR's **right to erasure** is a trap for sloppy test data: if a user requests deletion but their data was copied — unmasked — into ten test databases and three laptops, you cannot honestly say you deleted it. Keeping PII out of test environments is the only sane way to stay erasable.

**Lineage.** Auditors ask "where did this dataset come from and what was done to it?" Maintain **lineage**: every test dataset records its source, its masking pipeline version, and its generation date. Without lineage, you cannot prove compliance even if you are compliant.

This is a domain where engineering must partner with legal/DPO early; the cost of retrofitting compliance after an incident dwarfs the cost of designing it in.

---

## Core Concept 4 — Building a Synthetic-Data Generation Program

A one-off faker script is a tool; a synthetic-data *program* is sustained capability. Its components:

- **Schema-aware generators** that emit referentially-intact graphs across all entities, so a generated customer comes with consistent orders, payments, and addresses.
- **Distribution fidelity.** The program learns or encodes production's statistical shape — value distributions, skew, cardinality, null rates — without copying any row, so synthetic data exercises the same query plans and edge cases prod does.
- **Determinism.** A seed makes any generated dataset reproducible, so a bug found against "synthetic dataset v7 / seed 42" can be regenerated exactly.
- **Validation.** The program checks its own output: referential integrity holds, distributions match targets within tolerance, and — critically — **no real record leaked through** (a privacy check, since some model-based generators can memorise and reproduce real rows).

```python
# A program emits versioned, validated, reproducible datasets:
ds = synth.generate(
    profile="ecommerce-prod-2024Q2",   # encodes prod distributions, no real rows
    seed=42,                            # reproducible
    scale=10_000_000,                   # production volume for perf suites
)
synth.validate(ds, checks=[referential_integrity, distribution_match,
                           no_memorised_records])
synth.publish(ds, version="ds-2024Q2.7", lineage=ds.lineage)
```

The strategic payoff: synthetic data has **no PII**, so it crosses environment and residency boundaries freely, scales to any volume for [performance and load testing](../09-performance-and-load-testing/README.md), and is reproducible for debugging — while the validation step guards the one residual risk, memorisation. A blend of synthetic bulk plus carefully masked production long-tail is still common, but a strong synthetic program shrinks the masked-prod surface and thus the compliance surface.

---

## Core Concept 5 — Self-Service Test Data and Data-on-Demand

The bottleneck in mature orgs is rarely *building* a dataset — it's *getting one* when you need it. If provisioning a realistic dataset requires a ticket and a two-day wait, engineers will route around it (often by copying prod). The fix is **data-on-demand**: self-service provisioning that delivers a ready, compliant dataset in seconds.

Implementations range from a CLI/API that clones a masked golden dataset into an ephemeral database, to scenario-driven provisioning where an engineer requests a *shape* and the platform generates it:

```bash
# Engineer requests a scenario; platform provisions a compliant dataset.
$ testdata provision --scenario "enterprise-customer-with-overdue-invoice" \
                     --target ephemeral --ttl 2h
provisioned: db=eph-7f3a (synthetic, no PII), expires in 2h, lineage=ds-2024Q2.7
```

Design principles: every provisioned dataset is **compliant by construction** (synthetic or masked, never raw prod), **ephemeral** (a TTL so it doesn't accumulate), **labeled with lineage**, and **fast** (seconds, not tickets). When the compliant self-service path is faster than copying prod, the breach vector disappears on its own — convenience does the enforcement that policy alone never could.

---

## Core Concept 6 — The Lifecycle and Economics of Stale Data

Stale test data is an invisible, compounding tax. Its costs:

- **False confidence.** Tests pass against distributions and schemas that no longer match production, so the suite stops catching real regressions while still looking green — the most dangerous failure mode in testing.
- **Engineer friction.** People burn hours fighting datasets that don't reflect reality, debugging "failures" that are really data drift.
- **Re-introduced risk.** When official data is stale, engineers improvise — and improvisation is where prod copies sneak back in.

A lifecycle program counters this with a **refresh cadence** (scheduled re-subset/re-mask or regeneration), an **owner accountable for freshness** (with a data-age SLA as a metric), **versioned golden datasets** so suites can pin a known baseline and upgrade deliberately, and **retirement** of datasets no one uses (every retained dataset is attack surface).

The TCO argument: the cost of a synthetic/masking program and its refresh cadence is visible and bounded. The cost of stale data — missed regressions shipped to production, engineer-hours lost to drift, and the breach risk of improvised prod copies — is larger but diffuse, which is exactly why it goes unfunded until an incident makes it concrete. The professional's job is to make that diffuse cost visible *before* the incident.

---

## Core Concept 7 — Enforcement: Making the Compliant Path the Only Path

Policy that relies on people remembering will fail under deadline. Enforcement makes compliance structural:

- **Network/access controls.** Lower environments cannot reach production data stores; prod exports require approval and are blocked from writing to non-prod targets.
- **Scanning.** Automated PII scanners run against non-prod databases and CI artifacts, alerting on anything resembling real emails, card numbers, or national IDs. A hit is treated as an incident.
- **Masking-at-export.** If any production export is permitted, it passes through a mandatory masking pipeline at the boundary — there is no path that emits raw PII.
- **Provenance gates in CI.** Test jobs may only attach datasets tagged with valid lineage from the platform; an untagged dataset fails the pipeline.

```yaml
# CI gate: a job may only use datasets with verified, compliant lineage.
test:
  requires:
    dataset.lineage.source: ["synthetic", "masked"]   # never "raw-prod"
    dataset.lineage.masking_version: ">= 3.2"
    dataset.pii_scan: "clean"
```

The goal is that the compliant path is also the *easiest and fastest* path (via data-on-demand), and the non-compliant path is *structurally blocked* (via access controls and scanning). When both hold, compliance stops depending on discipline and becomes a property of the system — which is the only form of compliance that survives a deadline.

---

## Real-World Examples

- **Right-to-erasure failure.** A company received an erasure request and discovered the user's unmasked data in six test databases and several laptops, copied from old prod dumps. They could not certify deletion, triggering a regulator interaction. The remediation banned raw exports and rebuilt test data on a synthetic foundation.
- **The self-service flip.** A platform team measured that 40% of PII-scan hits came from engineers copying prod because the official dataset took two days to provision. Shipping a two-second `testdata provision` command dropped raw-prod copies to near zero within a quarter — convenience enforced the policy.
- **Distribution drift caught late.** A fraud model's tests passed for a year against a frozen 2022 synthetic profile; production traffic had shifted, and the suite missed a regression. A quarterly regeneration cadence with distribution-match validation closed the gap.
- **The contributed-builder rescue.** An org-wide builder library with a contribution model let twenty teams share one `OrderBuilder`. A regulatory schema change (a mandatory consent field) was rolled out as a defaulted field in the core builder; all twenty teams' suites stayed green without per-team edits.

---

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Policy without enforcement | Routed around under deadline | Access controls + scanning + CI gates |
| Slow data provisioning | Drives engineers to copy prod | Two-second data-on-demand |
| No lineage on datasets | Can't prove compliance to auditors | Tag source, masking version, date |
| Builder library with no SLA/owner | Breaks every team; trust erodes | Treat as a production service (on-call) |
| One-off synthetic scripts | No fidelity, no validation, no reuse | A validated, versioned generation program |
| Ignoring data residency | Pseudonymised data crosses borders illegally | Synthetic/anonymised for cross-region |
| Never retiring old datasets | Accumulating attack surface | Lifecycle: refresh and retire |

---

## Apply it

1. Define the user or business outcome that **Test Data Management** should improve.
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

- Which measurable outcome justifies investing in Test Data Management?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
