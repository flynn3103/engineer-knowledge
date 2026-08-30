# Encryption Key Lifecycle — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run key lifecycle management as a durable, org-wide practice with clear ownership across security, platform, and product teams, so every classified data store can prove rotation compliance and meet a crypto-shred SLA without a project-by-project scramble?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

> **Roadmap:** [Data Privacy](../README.md) → Encryption Key Lifecycle

*A senior engineer can make one system's key lifecycle correct. An organization with dozens of services, several clouds, and a legal deadline on every erasure request needs that correctness to be a property of how teams work together, not a property of one team's diligence.*

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable organizational failure: a central security team tries to own every service's key usage decisions, burns out reviewing services they don't operate, and rotation compliance quietly drifts the moment their attention moves elsewhere. The split that holds:

| Layer | Owner | Responsibility |
|---|---|---|
| **KMS/HSM infrastructure, root and regional KEKs** | Central security/platform team | Operate the KMS, define rotation policy defaults, manage regional key residency, own the `destroy` and `rotate` primitives that every service calls |
| **DEK granularity and usage within a service** | The team that owns that service's data | Decide per-user vs per-tenant DEKs for their own data model, wire their erasure workflow to the shared `destroy` API, keep their own derived copies (caches, exports) honest about re-deriving plaintext from the key |
| **Shared key-service interface** | Platform team | Maintain the thin wrapper library/API every service uses instead of calling the KMS directly, so rotation, destroy, and audit logging stay consistent across languages and teams |
| **Compliance reconciliation and audit evidence** | Security/compliance function | Reconcile which classified data stores actually use the shared key-service, track rotation-compliance and crypto-shred-SLA metrics org-wide, escalate services still on static or legacy keys |

This mirrors how a mature organization splits any shared-infrastructure practice: correctness at the point of use stays with the team that best understands their own data, while a small central function keeps the underlying primitive consistent and keeps a real accounting of who's actually using it correctly.

## Core Concept 2 — Decomposing the Rollout Into Reversible Increments

Mandating org-wide per-user DEKs and a shared key-service by a fixed deadline produces rushed migrations, unreviewed key hierarchies, and services that technically comply while quietly caching plaintext downstream. Decompose it instead:

1. **Pilot on one service with active, legally-deadlined erasure requests** — the motivation already exists, and success (a real erasure completed within SLA, provably) is easy to point to.
2. **Extract the shared key-service interface from the pilot**, not from a committee's first-principles design — the pilot reveals which operations (`wrap`, `unwrap`, `destroy`, `rotate`) are actually needed and how services realistically call them.
3. **Migrate services by data-classification tier, restricted first** (see [PII and Data Classification](../01-pii-and-data-classification/README.md)) — the highest-risk, highest-legal-exposure data gets the correct key granularity before lower tiers do, because that's where an erasure-SLA miss is most costly.
4. **Run legacy and migrated key paths side by side during transition**, with the shared key-service supporting both a static legacy key (read-only, being phased out) and the new per-unit DEK path, so no service needs a risky flag-day cutover.
5. **Only then set an org-wide expectation** — every service above a defined data-sensitivity threshold must use the shared key-service — once the interface and migration pattern have survived several real services and at least one real erasure deadline.

Every step stays reversible: if the shared interface needs a new operation after the third service adopts it, that's an interface revision, not a program failure, because nothing downstream assumed the first version was final.

## Core Concept 3 — Migration, Governance, and Compliance Risk

Rolling this out across an existing organization surfaces risks a single pilot doesn't:

- **Legacy services with a single static key baked into configuration.** Some older services encrypt everything with one long-lived key stored in a secrets manager, with no per-user granularity at all — migrating these requires a dual-read period (decrypt with the old static key, re-encrypt with a new per-user DEK on next write) rather than a one-shot cutover, and a plan for what happens to data that's never rewritten.
- **Multi-cloud KMS reconciliation.** A service on one cloud's KMS, another on a second cloud's equivalent, and a third talking to an on-prem HSM each expose slightly different rotation semantics and deletion grace periods — the shared key-service has to normalize these differences so a `destroy` call means the same thing everywhere, or the org-wide SLA metric in Concept 4 is comparing incompatible guarantees.
- **Auditor evidence requirements that outlive the data itself.** An auditor may require proof that a specific key was destroyed on a specific date, retained for years — even though the data it protected is, by design, now unreadable and effectively gone. The audit trail (see [Audit Logging](../04-audit-logging/README.md)) has to survive independently of the data it describes.
- **Cross-region key residency intersecting with disaster recovery.** A regional KEK that must stay within a jurisdiction's boundary for residency reasons complicates the org's standard multi-region DR replication policy — an undocumented exception here quietly reintroduces a residency violation the first time DR fails over (see [Data Residency](../03-data-residency/README.md)).
- **Coordination cost getting every consumer of a data store to honor the shared destroy path.** The team that owns the primary database can migrate quickly; the team that built a downstream analytics export years ago and has since moved on to other priorities is the one most likely to still be caching plaintext, and is the hardest to find and hold accountable.

## Core Concept 4 — Outcome Measures and Evidence-Based Exit Conditions

```yaml
# Program health dashboard, reviewed each security/compliance cycle.
metrics:
  rotation_compliance_rate: "KEKs rotated within policy window / total KEKs under management"
  crypto_shred_sla: "p95 time from erasure request received to key destruction confirmed"
  legacy_static_key_services_remaining: "count of services still using a single static, non-per-unit key"
  derived_copy_coverage: "known derived copies (caches, exports, indexes) verified to re-derive plaintext from the key / total known derived copies"
  audit_evidence_completeness: "destroy events with a retrievable, timestamped audit record / total destroy events issued"
exit_conditions:
  pilot_to_expansion: "pilot service completes at least one real erasure request within the target SLA, with a fully retrievable audit trail"
  program_maturity: "legacy_static_key_services_remaining trending toward zero for restricted-tier data, and derived_copy_coverage above an agreed threshold org-wide"
```

`derived_copy_coverage` is the metric most programs skip and most need: a high rotation-compliance rate and a fast crypto-shred SLA both look great on a dashboard while an unaccounted-for analytics export somewhere still holds erased users' plaintext. Track it explicitly, the same way a resilience program tracks whether its failure-mode catalog reflects the system as built rather than as imagined.

## Core Concept 5 — Cross-Team Contracts

Once an erasure SLA is a real commitment — to users, to legal, to an auditor — formalize what each team owes the others the same way an API contract gets formalized:

- Every team owning a classified data store publishes a **key lifecycle contract**: which key granularity they use, which shared key-service operations they call, and which of their own derived copies, if any, are still pending migration to re-deriving plaintext from the key rather than caching it.
- The compliance function designs its audit reporting against the *published* contract, not against whatever a service's key usage happens to look like today — this is what lets an owning team refine their internal key handling without silently breaking the org's compliance picture.
- A contract change — a new derived copy being added, a move to a different KMS provider, a change in DEK granularity — goes through the same review as any other data-model change with compliance impact, because for the compliance function relying on that contract's guarantees, it functionally is one.
- Accountability follows the contract: if an erasure SLA is missed because a team's own derived copy wasn't migrated, that team owns the fix; if it's missed because the shared key-service's `destroy` operation itself failed or was slow, the platform/security team owns it.

## Core Concept 6 — Sustained Delivery, Not a Static Deliverable

The practice is never "finished" — new services launch, new regions open, new KMS providers get adopted, and the key lifecycle program has to keep up:

- **A recurring key-inventory audit** (quarterly is common) reconciling every classified data store against the key-service's registry of managed keys — this is the mechanism that catches a service that quietly started encrypting new data with a local, unmanaged key.
- **A mandatory review trigger on architecture change**: a new data store, a new region, or a new downstream consumer of classified data opens a required key-lifecycle review, the same way a new dependency should trigger a failure-mode catalog update.
- **Postmortem-style updates when the crypto-shred SLA is missed** — treat an SLA miss as a finding to investigate and record (a stale replica, an unmigrated derived copy, a KMS provider's slower-than-assumed deletion grace period), not a rounding error to shrug off.
- **A program-level retrospective each cycle**, checked against the outcome measures from Concept 4, asking explicitly: is `legacy_static_key_services_remaining` actually declining, and if not, is the bottleneck the migration tooling, team prioritization, or unclear ownership of a specific legacy service?

---

## Real-World Examples

- **A pilot's real deadline funds expansion.** A service under an active legal erasure deadline is chosen as the pilot; completing that one erasure within SLA, with a clean audit trail, becomes the concrete evidence that gets three more teams to opt into the shared key-service the following quarter, instead of a hypothetical pitch about "best practice."
- **A derived copy finally gets an owner.** A quarterly key-inventory audit surfaces an analytics export that has been caching decrypted fields for a long time with no owner; assigning it explicitly and migrating it to reference the shared key-service closes a gap that had been invisible on every previous compliance report.
- **A contract prevents a blame spiral.** An erasure SLA is missed for one user; because the owning team's key-lifecycle contract documented that their downstream export was already flagged "pending migration," the miss resolves as a known, tracked risk with a committed fix date rather than a surprise incident review.
- **`derived_copy_coverage` exposes a program that looks healthier than it is.** An org reaches a strong rotation-compliance rate and a fast median crypto-shred SLA, but a review finds `derived_copy_coverage` stuck below half — the headline metrics were passing while a real share of erasure requests were not actually reaching every copy of the data, and the next cycle's priority shifts to that metric specifically.

## Common Mistakes

- **Centralizing key-usage decisions in one security team** that lacks the context to review every service's data model, causing reviews to become a bottleneck or a rubber stamp.
- **Mandating full org-wide migration before piloting**, producing a migration pattern designed by guesswork instead of one refined cheaply against one real service's real erasure deadline.
- **Measuring rotation compliance and SLA speed alone**, missing that `derived_copy_coverage` or `legacy_static_key_services_remaining` reveal whether the guarantee actually reaches every copy of the data.
- **Leaving multi-cloud KMS semantic differences undocumented**, so the org-wide SLA metric silently averages together guarantees that don't actually mean the same thing.
- **Publishing a key-lifecycle contract and never reviewing changes to it**, letting it drift out of sync with what a service's data model actually does.
- **Treating an SLA miss as an isolated incident** rather than a finding, letting the same root cause — an unmigrated export, a slow KMS provider — recur across multiple services.

---

## Apply it

1. Pick one real, above-threshold classified data store in your organization (or a realistic stand-in) and draft its key-lifecycle contract: DEK granularity used, which shared key-service operations it calls, and any known derived copies still pending migration.
2. Assign a named owner for that store's own key usage, and separately name the owner for the shared key-service interface it depends on.
3. Define the five outcome measures from Concept 4 for that one store (or your org's equivalents) and state the specific exit condition that would move it from "pilot" to "expansion-ready."
4. Decompose a rollout plan into at least four reversible increments (pilot, interface extraction, tier-by-tier migration, org-wide expectation) with an explicit exit condition between each step, rather than one mandated deadline.
5. Define the review trigger that would force this store's key-lifecycle contract to be revisited — tied to a real event (a new derived copy, a KMS provider change, an SLA miss) rather than a calendar reminder alone.

## Verify your work

- The key-lifecycle contract is specific enough that the compliance function could build an audit report from it without a follow-up question to the owning team.
- Every derived copy you documented has a named status (migrated, pending, or verified compliant) — none are unaccounted for.
- Your exit condition names a specific, falsifiable threshold for at least two of the five outcome measures, not a vague "the program should be more mature."
- Your rollout plan's steps are each independently valuable — a reader could stop after any one step and still have gained something real, not just partial progress toward a single big-bang goal.
- The review trigger is tied to an event that will actually recur (new consumers, provider changes, SLA reviews), not to goodwill or memory.

## Review questions

- Why does centralizing key-usage decisions in one security team tend to fail as the number of services grows?
- What does `derived_copy_coverage` reveal that rotation compliance and crypto-shred SLA speed alone do not?
- Why should multi-cloud KMS semantic differences be documented and reconciled centrally rather than left to each service team?
- What turns a key-lifecycle contract into something a compliance function can actually build an audit report from, rather than just documentation?
