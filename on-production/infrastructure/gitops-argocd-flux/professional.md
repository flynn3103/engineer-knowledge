# GitOps (Argo CD, Flux) — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you migrate an organization of many teams and services onto GitOps in reversible, evidence-backed increments, with ownership and governance that don't route every ordinary release through one platform team?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

*Senior level contains the blast radius of one bad commit across a fleet of clusters. Professional level is a different problem: dozens of teams need to keep shipping, on their own schedule, for years, through a model that neither collapses into a platform-team bottleneck nor quietly regresses back into ad-hoc `kubectl apply`. This is about the operating model, not the controller configuration.*

---

## Core Concept 1 — Split Ownership Before Scaling Adoption

A GitOps rollout that survives contact with 40 services needs two clearly separated owners, or the platform team becomes the approver of every team's every release — recreating the exact bottleneck GitOps was supposed to remove.

| | Platform team owns | Application team owns |
|---|---|---|
| Control plane | Argo CD/Flux install, upgrades, controller RBAC, cluster onboarding | Nothing here — they consume it |
| Shared conventions | Base Kustomize layers, ApplicationSet/Kustomization templates, sync-wave conventions | Their own overlays built from the shared templates |
| Scoping | Argo CD `AppProject` (or Flux tenant RBAC) restricting which repos/clusters/namespaces a team's apps may touch | Their manifests and promotion PRs within that scope |
| Day-to-day releases | Not involved | Approves and merges their own promotion PRs |
| Boundary changes | Reviews requests for a new cluster, namespace, or shared-base version bump | Requests boundary changes; doesn't need approval for ordinary releases |

The `AppProject` (or its Flux equivalent) is the mechanism that makes this safe to decentralize: it is what stops team A's Application from ever being pointed at team B's namespace, even though team A can merge to their own repo without platform review.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: checkout-team
  namespace: argocd
spec:
  sourceRepos:
    - https://github.com/example-org/checkout-gitops.git
  destinations:
    - namespace: checkout-*
      server: https://prod-cluster.example.internal
  clusterResourceWhitelist: []   # no cluster-scoped resources without platform review
```

## Core Concept 2 — Decompose the Migration Into Reversible Increments

A big-bang cutover from push-based pipelines to GitOps across every team is not reversible if it goes wrong. A staged sequence keeps every step undo-able:

1. **Pilot.** One low-risk service, one environment (staging). Prove reconciliation, the rollback story, and the on-call runbook. Turn what worked into a scaffold — a repo template, a starter `AppProject`, a starter base — that the next team copies instead of inventing their own.
2. **Cohort.** Onboard 3–5 more teams onto the same paved road, **in parallel with the legacy push-based path still live**. Nothing forces a team off the old path before the new one has been proven under their own workload.
3. **Default flip.** New services are GitOps-only from day one. Existing services migrate opportunistically, each tracked against the exit condition below rather than a calendar deadline.
4. **Decommission per service.** Only after a service meets its exit condition does the platform team revoke that service's legacy CI deploy credentials. This is what keeps the whole migration reversible at every step — the old path isn't removed until the new one has evidence behind it, not just an announcement.

## Core Concept 3 — Migration, Governance, Operational, and Compliance Risks

- **Migration risk — silent regression.** A team nominally "on GitOps" that still runs `kubectl apply` or a legacy pipeline "just for this one hotfix" has quietly kept the old trust model alive underneath the new one. The only reliable mitigation is removing standing prod-write credentials from the old CI path once the exit condition is met — discouraging the shortcut isn't enough; make it unavailable.
- **Governance — a second, independent layer.** Git review can lapse (a rushed approval, a stale required-check). Cluster-side admission control (Kyverno or OPA Gatekeeper) enforcing policy independently of what got merged — no `:latest` tags, mandatory resource limits, no cluster-admin ClusterRoleBindings — means a review gap doesn't equal an unguarded cluster.
- **Compliance — Git history as the audit trail.** "Who changed what, when, with whose approval" becomes answerable directly from Git log, which is valuable for change-management and audit regimes — but only holds if merges are actually reviewed (not rubber-stamped), force-push is disabled on tracked branches, and commit authorship isn't shared/generic.
- **Operational — a distinct on-call class.** "The GitOps controller is unhealthy" is a different failure than "a workload is unhealthy," with a different responder and a different runbook (see Core Concept 4 in the senior guide: reconciliation can be silently stalled while the controller pod looks fine). Professional-level rollout needs this runbook to exist *before* the first cohort goes live, not after the first missed incident.
- **Coordination — the shared base is a contract.** Once ten teams' overlays depend on one shared `base/`, changing it is equivalent to changing a shared library's public API: it needs versioning, a deprecation window, and notice to consuming teams — not a silent edit that reaches everyone's next sync at once.

## Core Concept 4 — Outcome Measures and Evidence-Based Exit Conditions

Track categories of measure, not a single vanity number:

| Measure | What it captures | Who acts on it |
|---|---|---|
| Deployment lead time (merge → running in target env) | Whether GitOps actually shortened the path from commit to production | Application team, per service |
| Fraction of services with zero standing human/CI write-credentials to the cluster | Whether the GitOps path is exclusive, not just available | Platform team, tracked per service |
| Mean time to rollback (`git revert` → Healthy) vs. the prior manual process | Whether rollback genuinely got faster and more predictable | Application team, validated during incident drills |
| Drift incidents auto-reverted vs. requiring manual intervention | Whether self-heal is doing real work or drift is slipping through | Platform team, via reconciliation alerting |
| Sync failure rate per service | Early signal of a team's overlays degrading in quality over time | Application team, reviewed periodically |

A per-service **exit condition** for decommissioning the legacy path should be concrete and checkable, for example: *N consecutive production releases delivered exclusively through the GitOps path, zero manual `kubectl` writes in the audit log for that namespace, and on-call has exercised the rollback runbook for this service at least once.* Retiring legacy credentials before this evidence exists turns "we migrated" into an assumption instead of a verified fact.

## Core Concept 5 — Cross-Team Contracts and Accountability

Write down, briefly, what each side guarantees:

- **Platform guarantees:** a reconciliation SLO for the control plane (e.g., "no Application should go more than N minutes without a successful reconciliation attempt before alerting fires"), an upgrade cadence for Argo CD/Flux itself, availability of the secrets backend, and stable, versioned base/ApplicationSet templates.
- **Application team guarantees:** their own manifests pass the shared CI validation, their promotion policy stays inside the environments their `AppProject` scopes them to, and they respond to their own service's sync failures rather than escalating every failure to the platform team.

This contract is what lets teams deliver with limited coordination: an ordinary release never needs the platform team's sign-off. Only a boundary change — a new cluster, a new namespace, a bump to a shared base version — crosses the line back into a conversation between the two teams.

## Scenario: Sustained Delivery, Not a Static Cutover

This is not a one-time migration; new teams keep onboarding, the shared base keeps evolving, and clusters keep getting added over years. When the shared base needs a breaking change — say, a new required NetworkPolicy label — the platform team publishes it as a new version (a new base path or tag) rather than editing the existing one in place. Each consuming team migrates on their own schedule, each bump reviewed as their own PR. The old base version is deprecated only after a measured adoption threshold is reached (e.g., "no Application still references the old base path"), not on a hard calendar date alone that ignores whether teams actually moved.

```mermaid
flowchart LR
    Team["App team PR: bump own overlay"] --> CI["Shared CI validation"]
    CI --> Merge["Merge inside team's AppProject scope"]
    Merge --> Controller["Platform-owned GitOps controller"]
    Controller --> Cluster["Team's namespace only"]
    Platform["Platform team: base v2 release"] -.notify, no forced cutover.-> Team
```

The visible result: an application team ships a routine change without ever talking to the platform team, while a fleet-wide base change reaches every team on a schedule they each control — and the platform team can see, from the same measures above, exactly which teams still depend on the old version and why.

## Common Anti-Patterns at This Scale

- **One shared monorepo requiring platform review for every team's PR** — this recreates the exact ops bottleneck GitOps was meant to remove, just with a Git UI in front of it.
- **Decommissioning legacy deploy access on a calendar date instead of an exit condition** — strands teams who haven't actually finished migrating, or worse, silently leaves standing credentials nobody remembers to revoke.
- **Editing a shared base in place** — a breaking change lands on every consuming team's next sync simultaneously, with no deprecation window and no way for a team to opt in on their own schedule.
- **Treating Git history as an audit trail without enforcing review** — a rubber-stamped approval process gives compliance no real signal, even though the commits exist.
- **No distinct runbook for "the controller is unhealthy"** — on-call treats it as a generic workload incident and misses that reconciliation itself has stalled fleet-wide.

## Apply it

1. Define the outcome this migration should produce (e.g., deployment lead time and rollback time, per the measures above) before writing any Application/Kustomization templates.
2. Split ownership explicitly: platform owns the control plane and shared templates; each team owns their overlays inside a scoped `AppProject` (or tenant).
3. Run one pilot service through the full increment sequence — pilot, cohort, default-flip — keeping the legacy deploy path alive throughout.
4. Define a concrete, checkable exit condition per service for revoking legacy deploy credentials, and track at least three services against it.
5. Publish the platform/team contract (SLOs, escalation paths, base-version deprecation policy) and confirm at least one boundary-change request (new namespace or base bump) goes through it without becoming a per-release bottleneck.

## Verify your work

- At least one service has met its exit condition and had its legacy CI deploy credentials actually revoked — not just marked "migrated."
- Deployment lead time and rollback time were measured before and after migration for the pilot service, with real numbers, not estimates.
- A shared-base version bump reached consuming teams on their own schedule, with visibility into which teams still reference the old version.
- On-call has exercised the "controller unhealthy" runbook at least once, distinct from a normal workload incident runbook.

## Review questions

- Why does a shared monorepo requiring platform-team review on every PR undermine the point of decentralizing GitOps ownership?
- What concrete evidence should be required before revoking a service's legacy deploy credentials, rather than a migration announcement alone?
- Why does editing a shared base layer in place create more risk than publishing a new version and letting teams migrate on their own schedule?
- What distinguishes the "platform team's guarantee" from the "application team's guarantee" in a cross-team GitOps contract?
