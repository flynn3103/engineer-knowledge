# Knowledge Base Design — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run knowledge-base freshness, ownership, and access control as a durable, org-wide program — so a hundred document collections across a dozen teams stay current and correctly scoped without a central team manually reviewing every source?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode without an operating model: every team stands up its own ingestion pipeline, invents its own metadata schema, and nobody owns the question "is this collection still accurate?" once the person who built it moves to a different project. A collection with no clear owner degrades silently — nobody notices staleness because nobody is accountable for noticing. The split that scales:

| Layer | Owner | Responsibility |
|---|---|---|
| **Ingestion platform** (parsing, chunking utilities, the metadata schema standard) | Platform team | Runs shared ingestion tooling per [middle.md](middle.md); owns the schema contract every collection must populate |
| **Each document collection's content and freshness** | The team that owns the source system (HR wiki, support tickets, product docs) | Registers the collection, sets its freshness SLA, and is the escalation point when staleness or an access-control gap surfaces |
| **Access-control policy and enforcement** | Security/platform, jointly with each collection owner | Platform enforces pre-filtering per [senior.md](senior.md) as a structural guarantee; collection owner is accountable for keeping `acl` metadata accurate |
| **Cross-collection registry and health** | A governance function (often part of the platform or AI-evaluation team, see [AI Evaluation](../../ai-evaluation/)) | Tracks every registered collection's owner, SLA, and staleness/access-audit status in one place |

This mirrors the ownership split a mature organization applies to any shared data infrastructure (see [Feature Store — Professional](../../mlops/feature-store/professional.md) for the same pattern applied to model-input data instead of documents): no product team is asked to become ingestion-pipeline experts, and no central team is asked to know whether a specific HR policy is current — that judgment belongs to the team that owns HR content.

## Core Concept 2 — A Collection Registry, Not Tribal Knowledge

The professional-level control that prevents "nobody knows this collection exists anymore" is a **registry** — a single source of truth for every knowledge-base collection in the org:

```yaml
# registry entry — one per collection
collection_id: support-kb-v3
owner_team: support-eng
source_system: zendesk-articles
freshness_sla: "detected change reflected in index within 4 hours"
change_detection: event-driven + 15min poll backstop   # per middle.md Core Concept 2
access_levels: [public, internal, restricted-legal]     # per senior.md Core Concept 4
last_audited: 2025-11-02
deprecation_status: active
```

A registry entry is not documentation nobody reads — it's the row a staleness dashboard and an access-control audit both query against. Without it, "which team owns the collection that just leaked restricted content" is a Slack-archaeology exercise during an incident instead of a one-line lookup.

## Core Concept 3 — Freshness SLA Tiers, Not One Global Number

Not every collection needs the same freshness guarantee, and treating "4-hour freshness" as a blanket policy either wastes engineering effort on a slow-changing archive or under-protects a collection where staleness has real cost:

| Tier | Example collection | Freshness SLA | Justification |
|---|---|---|---|
| **Critical** | Pricing, active legal holds, security policies | Minutes (event-driven, no polling backstop delay tolerated) | Stale content here causes financial or legal exposure |
| **Standard** | HR policies, product documentation, support macros | Hours (matches the [middle.md](middle.md) event-driven-plus-poll default) | Staleness causes user-visible wrong answers, not acute harm |
| **Archival** | Historical release notes, closed-ticket knowledge | Days to weekly | Content rarely changes after creation; tight freshness buys little |

Assigning every collection to a tier at registration time (Core Concept 2) turns "how fresh should this be?" from a one-off engineering decision made once per pipeline into a governed classification every new collection goes through, consistent with how the org already treats data sensitivity or service-tier classification elsewhere.

## Core Concept 4 — Staleness and Access-Drift Alerting

A freshness SLA that's never checked is a documentation exercise, not a guarantee. The program needs two distinct, automated alerts, because they catch different failure classes:

- **Staleness alert** — for each collection, compare the time since the last detected-and-ingested change against its tier's SLA (Core Concept 3); alert the owning team when a collection's actual freshness lag exceeds its committed SLA, not just when ingestion errors outright. A pipeline that's technically running but silently falling behind (a webhook provider degrading, a poll job's schedule drifting) is a more dangerous failure than one that's visibly down, because nothing else signals it.
- **Access-drift alert** — periodically (per Core Concept 3's tiering, more frequently for restricted collections) reconcile each collection's `acl` metadata against its source system's current permissions, flagging any chunk whose stored access level no longer matches the source of truth. This is the org-scale version of the ACL-sync discipline from [senior.md](senior.md) Core Concept 3, run as a scheduled audit across every collection rather than trusted to have worked correctly once per collection at build time.

Both alerts route to the collection's registered owner (Core Concept 2), not to the platform team — the platform team owns whether the alerting mechanism itself works; the collection owner owns responding to what it reports.

## Core Concept 5 — Source Deprecation as a Managed Lifecycle

Knowledge bases accumulate collections that outlive their usefulness — a product that's been sunset, a policy wiki replaced by a new one, a support-ticket archive for a discontinued feature. Leaving a deprecated collection live and searchable isn't neutral: it actively risks surfacing outdated, contradicted information in a generated answer, the same "two conflicting chunks retrieved together" failure from [senior.md](senior.md), except here the conflict is with the org's *current* source of truth rather than another chunk in the same corpus.

A managed deprecation lifecycle, not an ad hoc deletion:

1. **Flag** — the collection owner (or the registry itself, via an inactivity signal — no source updates detected for N months) marks a collection `deprecation_status: flagged`.
2. **Exclude from default retrieval, keep queryable on demand** — the same tombstone principle as an individual superseded chunk in [middle.md](middle.md) Core Concept 5, applied at the whole-collection level: stop surfacing it in normal search, but don't hard-delete immediately, in case a historical query legitimately needs it.
3. **Notify known consumers** — any product surface configured to query this collection gets an advance-notice window before removal, the same contract discipline a shared retrieval service publishes for a model or config change (see [RAG Techniques — Professional](../rag-techniques/professional.md) Core Concept 7).
4. **Archive or delete** — after the notice window, either move the collection to a separate archival tier (Core Concept 3) if there's a plausible future need, or delete it and remove its registry entry.

Skipping straight from "nobody uses this anymore" to hard deletion is the mistake this lifecycle prevents: a collection someone forgot they still queried resurfaces as a broken integration, not a deliberate, communicated decision.

## Core Concept 6 — Decomposing the Rollout Into Reversible Increments

Mandating "every team registers their collection and adopts the shared schema by end of quarter" produces the same rushed, unverified adoption any top-down data-governance mandate does. A decomposed rollout:

1. **Pilot with one collection that's already had an incident** — a stale-content complaint or an access-control near-miss makes the win concrete and gives the registry schema a real test before it's asked to fit every future case.
2. **Build the registry schema from the pilot's actual fields**, not a speculative superset — add fields other collections turn out to need as they onboard, rather than guessing every field up front.
3. **Run staleness and access-drift alerting in report-only mode first**, so the platform team can see how many existing collections would already be out of SLA before anyone is paged for it.
4. **Turn alerting active for newly registered collections first**, remediating the pre-existing fleet on a scheduled review rather than paging every owner simultaneously for gaps that predate the program.
5. **Expand collection by collection**, tracking registry coverage as a fraction (registered collections / total known collections) alongside the incident-catch rate alerting has actually produced.

Each step stays reversible: a registry field that turns out to be the wrong shape after the third team onboards is a schema migration, not a program failure, because no later step assumed the pilot's schema was final.

## Core Concept 7 — Outcome Measures, Exit Conditions, and Accountability

```yaml
program_health:
  registry_coverage: "registered collections / total known collections"
  sla_compliance_rate: "collections currently within their freshness SLA / total registered"
  access_drift_incidents: "chunks found with stale ACL metadata per audit cycle, trend over time"
  mean_time_to_remediate_staleness: "time from staleness alert to collection back in SLA"
  deprecation_lifecycle_adherence: "flagged collections that completed the full lifecycle vs skipped straight to deletion"
exit_conditions:
  pilot_to_expansion: "the pilot collection's staleness or access-drift alerting catches at least one real gap in report-only mode before anyone trusts it to page"
  program_maturity: "registry_coverage > 90%, and access_drift_incidents trending down release over release, not flat or rising"
```

The metric that matters most is `access_drift_incidents` trending down, not `registry_coverage` alone — an org can register every collection and still have the access-control audit itself be too infrequent or too shallow to catch real drift, which looks like program success on a coverage dashboard while delivering none of the actual security guarantee the registry exists to support. Set "the program is working" on drift being caught and remediated, not on how many collections have a row in the registry.

Accountability follows the same split as Core Concept 1: an access-control leak that reaches production because the platform's pre-filtering enforcement had a bug is a platform incident; a leak that reaches production because a collection owner's `acl` metadata went stale and nobody responded to the access-drift alert is that team's incident, escalated per the standard on-call ownership model the org already uses for production services.

---

## Real-World Examples

- **A report-only staleness alert surfaces a forgotten pipeline before a user complaint does.** During pilot rollout, the alerting system (running in report-only mode) flags a support-KB collection that's been silently 3 weeks stale because its source webhook provider changed its payload format months earlier — nobody noticed because the poll-interval reconciliation backstop had also quietly stopped running. The platform team fixes both before alerting is ever turned active, giving the program a concrete, demonstrated catch instead of a theoretical one.
- **Registry coverage looks strong while access-drift audits are too infrequent to matter.** An org reaches 92% registry coverage, but restricted-tier collections are only access-audited quarterly — a permission revocation that should have propagated within hours per Core Concept 4 sits unreconciled for two months before the next scheduled audit catches it. The following quarter's investment shifts from chasing coverage to tightening audit frequency for the highest-sensitivity tier specifically.
- **A deprecated collection resurfaces as a broken integration instead of a managed transition.** A collection nobody remembered was still wired into one internal tool gets hard-deleted the day after being flagged, with no notice window — the tool starts failing silently, and the incident becomes the concrete case that gets the notify-before-delete step added to the required lifecycle going forward.

## Common Mistakes

- **Treating registry coverage as the program's success metric instead of drift/incident-catch rate.** A fully registered fleet with infrequent or shallow audits still leaks stale content and stale permissions — coverage alone doesn't prove the guarantees behind it are enforced.
- **Applying one global freshness SLA to every collection.** Wastes engineering effort tightening freshness on a slow-changing archive while under-protecting a collection where staleness has real financial or legal cost.
- **Routing staleness and access-drift alerts to the platform team instead of the collection owner.** The platform team can't judge whether a specific policy document is actually still accurate; only the team that owns the source content can.
- **Skipping the deprecation lifecycle and hard-deleting a collection the moment it looks unused.** Breaks any integration nobody remembered still depended on it, turning a manageable transition into an incident.
- **Mandating registry adoption org-wide before piloting the schema on one real collection.** The schema gets guessed at rather than derived from a real collection's actual fields and failure modes.

---

## Apply it

1. Inventory the knowledge-base collections currently running (or planned) across teams you have visibility into, and identify which ones have no clear, current owner.
2. Design a registry schema (Core Concept 2) covering owner, source system, freshness SLA tier, change-detection strategy, and access levels — pilot it against one real collection's actual fields.
3. Assign a freshness tier (Core Concept 3) to that pilot collection and define its concrete SLA, justified by the real cost of staleness for that specific content.
4. Design the staleness and access-drift alerts (Core Concept 4) for the pilot collection and run them in report-only mode for at least one full cycle; record whether either would have caught a real gap.
5. Write the deprecation lifecycle steps (Core Concept 5) you'd apply to a collection you already know is a candidate for retirement, and the notice window you'd give known consumers before removal.

## Verify your work

- The registry schema is derived from a real pilot collection's fields, not designed speculatively before any collection used it.
- You can name a specific staleness or access-drift gap the report-only alerting caught, with evidence, not a general belief that "it should help."
- Every collection you inventoried has an assigned freshness tier with a stated justification, not a single default applied uniformly.
- You can state who — which specific team — is accountable for responding to a staleness or access-drift alert on a given collection, not "the platform team" as a default answer.
- The deprecation plan you wrote includes a notice window to known consumers before removal, not an immediate delete.

## Review questions

- Why does registry coverage alone fail to prove that freshness and access-control guarantees are actually being enforced?
- What's the risk of applying a single global freshness SLA to every knowledge-base collection in an org, regardless of content type?
- Why should a staleness or access-drift alert route to a collection's content owner rather than the platform team that built the ingestion pipeline?
- What specifically goes wrong when a collection is hard-deleted the moment it's flagged as unused, instead of going through a notice-and-archive lifecycle?
- Why does piloting a registry schema on one real collection produce a better result than designing it speculatively for every collection at once?
