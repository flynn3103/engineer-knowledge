# Embeddings and Vector Databases — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you govern embedding and vector infrastructure across an organization — a shared embedding service, cost allocation across teams, index rebuild SLAs, and multi-tenant isolation — so every team gets fast, correct, isolated vector search without each one operating its own vector database?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

Without a deliberate operating model, every team that needs semantic search independently picks an embedding model, stands up its own vector database instance, and re-derives the migration and filtering lessons from the middle and senior guides the hard way. The split that scales:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared embedding service** | Platform team | Wraps the chosen embedding model(s) behind an internal API; owns model version, rate limiting, and cost per call |
| **Vector database infrastructure** | Platform team | Runs and scales the vector database (or manages the relationship with a managed provider); owns index rebuild SLAs and uptime |
| **Collection/namespace ownership and metadata schema** | Individual product teams | Own what gets embedded, what metadata is attached, and their own filtering requirements — because they know their own data and access rules |
| **Multi-tenant isolation policy** | Security engineering, enforced jointly with platform | Defines whether tenant isolation is namespace-level or filter-level, and audits that the enforcement actually holds |
| **Program health, cost, and drift** | A governance group spanning platform, security, and finance | Tracks adoption, cost trends, and whether any team has silently forked off the shared infrastructure |

This is the same ownership logic as [RAG Techniques — Professional](../rag-techniques/professional.md) and [Containers and Docker — Professional](../../../infrastructure/containers-and-docker/professional.md): each layer sits with whoever can actually sustain the decision — no product team is asked to become vector-database operators, and no central team is asked to understand every team's document domain or access rules.

## Core Concept 2 — The Shared Embedding Service as a Paved Road

A **shared embedding service** is a platform-owned internal API that every team calls instead of each independently integrating with an external embedding provider:

```
POST /embed
{ "text": "...", "model_version": "v3" }
→ { "vector": [...], "dimensions": 1536, "model_version": "v3" }
```

Centralizing this buys three things no individual team can get on its own: a single place to enforce rate limits against the external provider (so one team's traffic spike doesn't exhaust a shared quota), a single place to track and control cost, and — most importantly for the senior-level migration pattern — a single place to manage model versioning, so "which embedding model produced this vector" is a fact the platform tracks centrally rather than something each team's code has to remember correctly on its own.

The paved road only works if it's genuinely easier than calling an external API directly: low added latency, clear versioning semantics, and a migration path (Core Concept 5) that individual teams don't have to design themselves.

## Core Concept 3 — Cost Allocation

Embedding and vector-storage cost is real and scales with usage — attributing it per team is both a FinOps necessity and a forcing function that surfaces inefficient usage:

```yaml
# Per-team usage metering, aggregated monthly
team_usage:
  support-kb-team:
    embedding_calls: 2_400_000
    tokens_processed: 1_100_000_000
    vectors_stored: 3_200_000
    storage_gb: 18.4
    estimated_cost_usd: 890
  legal-docs-team:
    embedding_calls: 340_000
    tokens_processed: 410_000_000
    vectors_stored: 1_100_000
    storage_gb: 6.1
    estimated_cost_usd: 310
```

This kind of per-team metering (whether charged back directly or only shown as "showback" for awareness) makes cost a visible, attributable signal instead of a single line item on the platform team's cloud bill that nobody can explain. It also surfaces real inefficiency: a team re-embedding the same unchanged documents on every deploy because their ingestion pipeline lacks the change-detection discipline covered in [Knowledge Base Design — Middle](../knowledge-base-design/middle.md) shows up directly as an unusually high `embedding_calls`-to-`vectors_stored` ratio, a pattern that's invisible without per-team metering and obvious with it.

## Core Concept 4 — Index Rebuild SLAs

A **rebuild** — re-indexing a collection after a chunking change, an embedding-model migration (senior level), or a bulk metadata schema change — needs a committed service level, not an ad hoc "whenever the platform team gets to it":

```yaml
rebuild_sla:
  full_corpus_reembed: "completes within 48h of an approved migration start, for corpora under 20M vectors"
  shadow_index_validation: "eval-set comparison (recall, completeness) available within 4h of reembed completion"
  cutover: "reversible alias flip, rollback executable within 15 minutes of a detected regression"
  availability_during_rebuild: "99.9% search availability on the active index throughout"
```

The SLA exists to make a real operational promise concrete: a team requesting a migration knows what to expect and can plan around it, and the platform team has an explicit target to be held accountable to rather than an implicit expectation nobody agreed to. `availability_during_rebuild` at 99.9% is what forces the shadow-index pattern from [senior.md](senior.md) to be the platform's *only* supported migration path — an in-place rebuild that takes the active index offline cannot meet that number, so the SLA itself is what prevents a team from taking a shortcut that risks downtime.

## Core Concept 5 — Multi-Tenant Isolation

When multiple teams — or, in a customer-facing product, multiple *customers* — share vector infrastructure, isolation has two viable designs with a real trade-off:

| Approach | How it works | Trade-off |
|---|---|---|
| **Namespace/collection-per-tenant** | Each tenant gets a physically separate collection or index | Strongest isolation guarantee — a filter bug literally cannot leak across tenants, because there's no shared index to leak across; higher operational overhead at very large tenant counts (thousands of small collections) |
| **Shared collection with a tenant-ID metadata filter** | All tenants' vectors live in one collection; every query includes a mandatory `tenant_id` filter | Lower operational overhead, better resource utilization at high tenant counts; isolation is only as strong as the code path that guarantees the filter is *always* applied — a missing filter on one query path is a cross-tenant data leak, not a degraded-quality bug |

The decision rule: **namespace-per-tenant is the correct default whenever tenant counts are moderate and isolation is a hard security requirement** (a customer-facing SaaS product where one customer's data leaking to another is a severe incident); **shared-collection-with-filter is justifiable when tenant counts are very high** (tens of thousands of small internal team collections where per-tenant infrastructure overhead becomes the binding cost) **and the platform can prove, not just assert, that the filter is always applied** — the pre-filtering mechanism from [middle.md](middle.md) Core Concept 5 is precisely the enforcement point, and it needs to be enforced at the platform/query-gateway layer, not left to each calling team's application code to remember correctly every time.

This is the same access-control-correctness problem covered from the document-permissions angle in [Knowledge Base Design — Senior](../knowledge-base-design/senior.md); here it's the infrastructure-level version of the same guarantee.

## Core Concept 6 — Decomposing the Rollout

1. **Pilot the shared embedding service and one shared vector database instance with two or three teams**, chosen to include at least one with a real multi-tenant isolation requirement, so that constraint is validated early rather than discovered later.
2. **Extract the service's API contract and the cost-metering schema from what the pilot teams actually need**, not a speculative design.
3. **Publish cost metering as visibility-only first** (showback, not chargeback), so teams see their usage and adjust behavior before any billing consequence exists.
4. **Turn on rebuild SLA enforcement and isolation auditing before onboarding teams broadly**, so the guarantees the platform is asking teams to trust are actually being tested, not assumed.
5. **Expand team by team**, tracking adoption alongside the outcome measures below — not adoption alone.

## Core Concept 7 — Outcome Measures and Exit Conditions

```yaml
program_health:
  shared_infra_adoption: "teams using shared embedding service + vector DB / total teams needing vector search"
  cost_per_1k_queries: "tracked per team and org-wide, trended quarterly"
  rebuild_sla_compliance: "rebuilds completing within the committed SLA window / total rebuilds"
  isolation_audit_pass_rate: "scheduled cross-tenant leak tests passing / total run"
exit_conditions:
  pilot_to_expansion: "pilot teams' migrations complete within the target rebuild SLA, and a deliberate isolation audit (attempting to retrieve another tenant's data) finds zero leaks"
  program_maturity: "shared_infra_adoption > 80%, rebuild_sla_compliance trending toward 100%, and isolation_audit_pass_rate at 100% sustained across at least two consecutive audit cycles"
```

`isolation_audit_pass_rate` is the measure that matters most and the one most likely to be skipped under delivery pressure — a shared vector infrastructure program can look fully successful on adoption and cost metrics while nobody has actually tried, on a schedule, to retrieve one tenant's data as another tenant to confirm the isolation boundary holds. Treat an isolation audit the way a security team treats a penetration test: scheduled, adversarial, and something the program's maturity claim depends on passing, not something inferred from "we designed it to be isolated."

## Core Concept 8 — Cross-Team Contracts and Sustained Delivery

- The shared embedding service publishes a support contract per model version — current, deprecated-but-served, and end-of-life date — exactly mirroring the golden-base-image contract pattern; a deprecation triggers the shadow-index migration path from [senior.md](senior.md) for every consuming team, coordinated rather than left to each team's own initiative.
- A breaking change to the vector database's default indexing configuration (switching the platform-managed default from HNSW to an IVF-PQ variant at very large scale, for example) goes through advance notice and a validated migration plan for affected teams, the same as any other breaking infrastructure change.
- Accountability follows ownership: a missed rebuild SLA is the platform team's action item; a cross-tenant isolation failure traced to a team bypassing the shared query gateway (calling the vector database directly instead of through the platform's enforced-filter layer) is that team's action item, and is also a signal the paved road wasn't easy enough to use as intended.
- The program is never static: new teams onboard continuously, embedding models improve and warrant evaluation for migration, and the isolation audit runs on a fixed recurring cadence indefinitely, not once at launch.

---

## Real-World Examples

- **Per-team cost metering surfaces an inefficient ingestion pipeline.** A team's `embedding_calls`-to-`vectors_stored` ratio is far higher than peers'; investigation finds their ingestion job re-embeds the entire corpus on every deploy instead of detecting unchanged documents — visible immediately once cost metering exists, invisible before it.
- **A scheduled isolation audit catches a missing filter before a customer does.** A routine adversarial audit attempting cross-tenant retrieval finds one query path — a newly added bulk-export feature — bypassing the shared query gateway's enforced tenant filter and calling the vector database directly; the gap is closed before any real customer data crosses tenant boundaries, and the incident becomes the argument for making the gateway the *only* supported access path, with direct database access removed.
- **A rebuild SLA forces a genuinely reversible migration design.** A platform team initially plans an in-place index rebuild for a large migration; the committed 99.9% availability-during-rebuild SLA makes that design non-viable, forcing adoption of the shadow-index pattern org-wide rather than as a senior-level best practice teams could individually choose to skip under time pressure.

## Common Mistakes

- **Skipping the isolation audit because the design "should" be isolated.** Only a scheduled, adversarial test proves isolation holds in practice; a correct-looking design is not evidence.
- **Rolling out chargeback before showback.** Billing teams for usage before they've had a visibility period to understand and adjust their own consumption produces friction disproportionate to the actual cost problem.
- **Measuring adoption without measuring SLA compliance or isolation audit results.** High adoption of infrastructure that misses its rebuild SLA or fails isolation audits is not a healthy program, regardless of the adoption number.
- **Allowing any path that bypasses the shared query gateway's enforced filtering.** Even one direct-access path undermines the isolation guarantee the entire shared-collection design depends on.
- **Treating a model-version deprecation as each team's independent responsibility with no coordinated migration support.** Recreates the exact "every team re-derives the migration playbook" problem centralizing the service was meant to solve.

---

## Apply it

1. Inventory the vector search usage (or planned usage) across teams you have visibility into, and estimate current or projected cost per team.
2. Design the shared embedding service's API contract and versioning scheme, and the cost-metering schema you'd report per team.
3. Choose, and justify with the trade-off table in Core Concept 5, whether your scenario calls for namespace-per-tenant or shared-collection-with-filter isolation.
4. Define a rebuild SLA with concrete numbers (completion window, availability during rebuild, rollback time) and identify which architectural pattern (shadow-index) it requires as a consequence.
5. Design the isolation audit: what it actually attempts (retrieve another tenant's data through every supported access path), how often it runs, and what a failure triggers.

## Verify your work

- Your cost-metering design would actually surface an inefficient team's usage pattern, not just report an aggregate total.
- Your isolation choice cites tenant count and the severity of a leak, not a default preference.
- The rebuild SLA has concrete numbers (a duration, a percentage), and you can explain why it forces (or doesn't force) the shadow-index migration pattern.
- The isolation audit is described as a scheduled, adversarial test with a defined failure response, not an assumption that the design is correct.

## Review questions

- Why does centralizing the embedding service make model versioning easier to get right than leaving it to each team independently?
- What does per-team cost metering make visible that an aggregate cloud bill does not?
- Under what condition is shared-collection-with-filter isolation justifiable over namespace-per-tenant, and what does that choice depend on being true?
- Why is an isolation audit result a more trustworthy signal of program health than adoption percentage alone?
- What architectural pattern does a strict "availability during rebuild" SLA effectively force, and why?
