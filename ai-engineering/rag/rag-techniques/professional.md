# RAG Techniques — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run RAG as a durable, org-wide operating model — a shared retrieval service and evaluation gates that block a chunking-strategy or model change before it regresses quality — so every product team ships grounded answers without a central team reviewing every prompt template and chunking parameter?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode without an operating model: every product team builds its own retrieve-then-generate pipeline from scratch, re-discovers the same chunking and hybrid-search lessons independently (usually the hard way, in production), and a central AI platform team either becomes a bottleneck trying to review every team's RAG implementation, or has no visibility at all until a quality incident surfaces. The split that scales:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared retrieval service** | Platform team | Runs the retriever, reranker, and hybrid-search infrastructure as an internal API; owns its latency, uptime, and default configuration |
| **Document ingestion and chunking rules** | The team that owns each document source | Chooses the chunking strategy appropriate to their content type, per [middle.md](middle.md), because they know their own documents |
| **Evaluation harness and quality gates** | A shared evaluation function (often part of the platform team or a dedicated eval team, see [AI Evaluation](../../ai-evaluation/)) | Defines the metrics, owns the golden eval sets, and owns the blocking/non-blocking gate policy |
| **Prompt templates and grounding instructions** | The team that owns each product surface | Because grounding instructions interact with product-specific tone and use case, but must pass the shared eval gate before shipping |
| **Program health and cross-team drift** | A governance group spanning platform, eval, and security | Tracks adoption, regression frequency, and whether any team's pipeline has silently diverged from shared standards |

This mirrors the ownership split a mature organization applies to shared infrastructure generally (see [Containers and Docker — Professional](../../../infrastructure/containers-and-docker/professional.md) for the same pattern applied to base images): no product team is asked to become retrieval-infrastructure experts, and no central team is asked to understand every product's document domain.

## Core Concept 2 — The Shared Retrieval Service as a Paved Road

A **shared retrieval service** is a platform-owned API that wraps chunking utilities, the hybrid search index, and the reranker, so that "build a RAG pipeline" becomes "register a document source and call the retrieval endpoint" instead of "stand up your own vector database, choose your own embedding model, and rediscover hybrid search from scratch":

```
POST /retrieve
{
  "query": "...",
  "source_collection": "support-kb-v3",
  "top_k": 5,
  "rerank": true
}
→ { "chunks": [...], "scores": [...], "chunk_ids": [...] }
```

The service exists to make the validated, evaluated choice the default choice — the same paved-road logic as a platform-owned golden base image. It only works if it's genuinely easier to call than to build independently: documented, fast (a p95 latency budget the platform team is accountable for), and versioned so a team can pin to a known-good retrieval configuration rather than being silently affected by another team's tuning change.

## Core Concept 3 — Evaluation Gates Before a Chunking or Model Change Ships

The core professional-level control is preventing the senior-level regressions from [senior.md](senior.md) from ever reaching production in the first place, rather than only diagnosing them after the fact:

```yaml
# CI-style RAG evaluation gate, run on every change to chunking config,
# embedding model, reranker, or retrieval-affecting prompt template.
eval_gate:
  golden_set: support-kb-eval-v4      # ≥100 labeled query→chunk→answer triples
  metrics:
    retrieval_recall_at_5: ">= 0.85"       # matches or exceeds current baseline
    context_precision: ">= 0.75"           # fraction of retrieved chunks actually relevant
    faithfulness: ">= 0.90"                # fraction of answer claims supported by retrieved context
    answer_correctness: ">= baseline - 0.02"  # allow small noise, block real regression
  policy: block_merge_on_failure
```

`context_precision`, `faithfulness`, and `answer_correctness` are the kind of metrics produced by RAG-specific evaluation frameworks (RAGAS is a commonly used open-source one) that score retrieval and generation quality without requiring a human to read every answer. The gate's job is narrow and specific: a chunking-strategy change, an embedding-model swap, or a reranker update cannot merge if it drops any of these metrics below the current baseline on the golden set — turning "we think this chunking change is an improvement" into a check a pipeline enforces, not a belief a team holds.

## Core Concept 4 — Decomposing the Rollout Into Reversible Increments

Mandating "every team adopts the shared retrieval service and eval gate by end of quarter" produces the same rushed, unverified adoption any top-down infrastructure mandate does. A decomposed rollout:

1. **Pilot with one team and one document collection** — ideally one that has already had a quality incident, so the win is concrete and measurable.
2. **Build the golden eval set from the pilot's real query traffic and real quality complaints**, not from a small pilot document set, before shipping the shared service.
3. **Run the eval gate as a non-blocking report first**, on every change, so the platform team can see how much of the existing fleet would fail the gate before anyone's merge is blocked by it.
4. **Turn the gate blocking for new changes only**, leaving already-shipped configurations untouched until their next scheduled review — the same sequencing that avoided breaking an entire fleet at once in the containers-and-docker professional guide's scanning-gate rollout.
5. **Expand collection by collection**, tracking adoption as a fraction (collections behind the shared service and gate / total collections) alongside the regression-catch rate the gate has actually produced.

Each step stays reversible: a golden eval set that turns out to be unrepresentative after the third team's traffic is added is a dataset update, not a program failure, because no later step assumed the first version was final.

## Core Concept 5 — Migration, Governance, and Cross-Team Risk

- **Shared retrieval service outage becomes a shared blast radius.** Centralizing retrieval means a platform-level incident (the reranker service down, the shared index unavailable) affects every team behind it simultaneously — this trades many small, siloed failure points for one large one, which is the correct trade only if the platform team's reliability bar is genuinely higher than what most product teams would build independently. An uptime SLA and a documented fallback (serve without reranking, or without retrieval entirely, rather than fail the whole request) should exist before wide adoption, not be discovered during the first incident.
- **A golden eval set drifts from real production traffic.** An eval set built once at pilot time and never refreshed stops representing the query patterns a growing set of product teams actually see — the same staleness risk called out at senior level, now at the scale of every team relying on the same set. A refresh cadence, and a feedback loop from production thumbs-down/complaint signals back into the eval set, keeps it representative.
- **Per-team prompt and grounding-instruction divergence undermines a shared gate.** If every team's prompt template is free-form and unreviewed, the eval gate can pass a chunking change against one team's prompt while silently breaking grounding for another team using a materially different template. Prompt templates need to be versioned and included in what the gate evaluates, not treated as outside its scope — see [Prompt Engineering](../../llm-fundamentals/prompt-engineering/).
- **Multi-hop and agentic retrieval changes the platform surface.** As more teams adopt multi-hop retrieval (senior-level Core Concept 5), the shared service's API needs to support an iterative retrieval interface, not just single-shot search — a platform decision that should be made deliberately once several teams need it, not bolted on ad hoc by the first team that does.

## Core Concept 6 — Outcome Measures and Exit Conditions

```yaml
program_health:
  shared_service_adoption: "collections served by the shared retrieval service / total collections"
  gate_regression_catch_rate: "regressions caught by the eval gate before merge / total regressions found (pre- and post-merge combined)"
  mean_time_to_detect_regression: "time from a shipped regression to it being flagged, pre-gate vs post-gate"
  faithfulness_trend: "median faithfulness score across all gated collections, tracked quarterly"
  shared_service_p95_latency: "retrieval endpoint latency, tracked against its SLA"
exit_conditions:
  pilot_to_expansion: "pilot collection's eval metrics improve measurably, and the gate demonstrably catches at least one real regression in a shadow (non-blocking) run before anyone trusts it to block"
  program_maturity: "shared_service_adoption > 80%, and mean_time_to_detect_regression trending toward near-zero (caught pre-merge, not post-incident)"
```

The metric that matters most is `gate_regression_catch_rate` combined with `mean_time_to_detect_regression` — an org can have high adoption of the shared service while the eval gate itself is too permissive (thresholds set loosely to avoid blocking anyone) to actually catch anything, which looks like program success on an adoption dashboard while delivering none of the actual quality protection the gate exists for. Set "the program is working" on regressions being caught before merge, not on adoption percentage alone — the same lesson the containers-and-docker professional guide draws from patch latency versus golden-base adoption.

## Core Concept 7 — Cross-Team Contracts and Sustained Delivery

- Every shared retrieval service configuration (embedding model version, reranker version, default chunking presets) publishes a **support contract**: current version, deprecated-but-still-served versions, and the date a version stops being served — the same pattern as a golden base image's deprecation window.
- A breaking change to the shared service (a new embedding model that isn't backward-compatible with existing indexes, per [Embeddings and Vector Databases — Senior](../embeddings-and-vector-db/senior.md)) goes through advance notice to known consumers and a migration window, not a silent swap.
- Accountability follows the contract: a regression that reaches production because the platform team shipped a retrieval-service change without running it through the gate is the platform team's action item; a regression that reaches production because a team's document-ingestion team bypassed structure-aware chunking guidance for their content type is that team's action item.
- The program is never "done" — new document collections onboard continuously, new failure modes surface in production and should feed back into the golden eval set (a real user complaint about a wrong or ungrounded answer is a candidate new eval case, not just a support ticket to close), and embedding-model or reranker upgrades recur on their own cadence, each one required to pass the same gate before rolling out org-wide.

---

## Real-World Examples

- **A non-blocking shadow gate catches its first real regression before anyone trusted it to block.** Running the eval gate in report-only mode during pilot expansion flags a reranker version bump that would have silently dropped faithfulness on one collection — the platform team fixes the reranker config before the gate is ever turned blocking, giving the program a concrete, demonstrated catch rather than a theoretical one to justify wider rollout.
- **Adoption looks strong while the gate itself is toothless.** An org reaches 75% shared-service adoption, but the eval gate's thresholds were set so loosely during pilot (to avoid blocking early adopters) that a real chunking regression ships through it three months later — the following quarter's investment shifts from adoption outreach to tightening thresholds against the accumulated baseline data.
- **A platform-level outage becomes the argument for a documented fallback.** The shared reranker service has a brief outage; teams without a documented fallback fail every retrieval request outright, while a team that had wired in a rerank-optional fallback degrades to dense-only retrieval and keeps serving answers, just with slightly lower precision — the incident becomes the concrete case that gets a fallback requirement added to the platform's onboarding checklist.

## Common Mistakes

- **Mandating full migration to the shared service before piloting.** The shared service's API and defaults get guessed at rather than derived from one team's real traffic and real failure modes.
- **Turning the eval gate blocking for the entire existing fleet at once.** Breaks many teams' merges simultaneously over pre-existing gaps the gate happens to newly measure; gate new changes first, remediate the existing fleet on a scheduled window.
- **Measuring adoption without measuring regression-catch rate.** High adoption with a permissive gate looks like success on a dashboard while catching nothing.
- **Leaving prompt templates outside the eval gate's scope.** A chunking or model change can pass the gate against one team's prompt while breaking grounding for another team's materially different template.
- **No documented fallback for a shared retrieval-service outage.** Centralizing retrieval without a degraded-mode plan turns a platform incident into an outage for every team behind it at once.

---

## Apply it

1. Inventory the RAG pipelines currently running (or planned) across teams you have visibility into, and identify which ones duplicate chunking or hybrid-search logic that could be centralized.
2. Design the shared retrieval service's API surface (retrieve endpoint, source-collection registration, versioning scheme) based on what the most demanding current pipeline actually needs, not a speculative superset.
3. Build a golden eval set from one pilot collection's real query traffic, and define the four gate metrics from Core Concept 3 with concrete thresholds tied to that collection's current baseline.
4. Run the gate in non-blocking (report-only) mode for at least one full change cycle, and record whether it would have caught any regression that actually shipped.
5. Write the outcome measures you'd track quarterly, and the specific exit condition that would justify expanding the gate from report-only to blocking, and from one pilot collection to the wider fleet.

## Verify your work

- The shared service's API is derived from a real pilot's requirements, not designed speculatively before any team used it.
- The golden eval set is built from real production query traffic and complaint signals, not only from documents someone wrote for testing.
- You can name a specific regression the non-blocking gate would have caught, with a before/after metric, not a general belief that "it should help."
- The outcome measures include a regression-catch metric, not adoption percentage alone.
- A documented fallback exists for the shared retrieval service's failure mode, not just an assumption that it won't go down.

## Review questions

- Why does mandating shared-service adoption before piloting tend to produce a poorly-fitted API surface?
- What does a high shared-service adoption number fail to prove about whether the eval gate is actually protecting quality?
- Why should prompt templates be inside the scope of the eval gate rather than treated as separate from chunking and model changes?
- What is the risk introduced by centralizing retrieval into one shared service, and what mitigates it?
- Why does turning a quality gate blocking for an entire existing fleet at once cause more harm than gating only new changes first?
