# Kubernetes Orchestration — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you let dozens of independent teams deploy safely onto shared Kubernetes clusters without the platform team becoming the bottleneck for every rollout?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

## The organizational problem behind the objects

By the time a company runs Kubernetes at scale, the technical objects — Pod, Deployment, Service — are not the hard part. The hard part is that dozens of teams share a small number of clusters, and the platform team that owns those clusters cannot review every Deployment manifest before it ships without becoming a queue that stalls every other team's delivery. The professional-level design question is: what guardrails let teams operate independently on shared infrastructure, using Kubernetes's own primitives, without a human gate on every change?

## Namespaces as the unit of ownership

A Namespace is the natural boundary for team ownership on a shared cluster — not because it isolates network traffic by default (it does not, without a NetworkPolicy) but because it is the scope for RBAC, ResourceQuota, and LimitRange. The operating model: **one namespace, or a small named set, per team, with quotas and role bindings scoped to it**, so a team's mistakes are contained to their own capacity allocation and cannot silently consume a neighbor's.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-checkout-quota
  namespace: checkout
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    pods: "60"
```

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: checkout-defaults
  namespace: checkout
spec:
  limits:
    - default:
        cpu: "250m"
        memory: "256Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
      type: Container
```

The `ResourceQuota` is the capacity contract: the checkout team can request whatever mix of Deployments they want, as long as the namespace total stays under the quota — no cluster-wide capacity conversation needed for routine changes. The `LimitRange` is the safety net for manifests that forget to declare resources at all, so an omission does not turn into unbounded consumption.

## RBAC as the delegation boundary

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: checkout-team-deploy
  namespace: checkout
subjects:
  - kind: Group
    name: team-checkout
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: edit
  apiGroup: rbac.authorization.k8s.io
```

Binding the built-in `edit` ClusterRole to a team's identity group, scoped to their namespace via a `RoleBinding` (not a `ClusterRoleBinding`), is what turns "the platform team must apply every change" into "the checkout team applies their own changes, and cannot touch anyone else's namespace." This is the mechanism that removes the platform team from the deploy path while keeping the blast radius of a mistake contained.

## Decomposing platform rollout into reversible increments

Rolling this operating model out to an existing 30-team, single-shared-namespace cluster is itself a delivery problem, not a one-shot migration. A sequence that keeps every step observable and reversible:

1. **Add quotas and limit ranges to existing namespaces without changing anything else.** Set the quota generously above current observed usage first, so nothing breaks; this step's only purpose is to make consumption visible (`kubectl describe quota` in every namespace) before it becomes a hard boundary.
2. **Tighten quotas to a realistic ceiling per team**, informed by a few weeks of the visibility gained in step 1 — reversible by loosening again if a team's legitimate need was mis-measured.
3. **Introduce team-scoped RBAC alongside, not instead of, existing platform-team access**, so a misconfigured RoleBinding does not lock a team out — remove the platform team's blanket edit access only after the team confirms they can deploy through their own binding.
4. **Publish a golden-path Deployment/Service/PodDisruptionBudget template** so teams onboarding after this point start with correct probes, requests, and a PDB by default rather than re-deriving those decisions team by team.
5. **Track and retire exceptions.** Some teams need quota exceptions or extra RBAC scope during the transition — track these explicitly with an owner and a review date rather than letting them become permanent silent bypasses.

Each step is independently observable (a quota event, an RBAC audit-log entry, a template adoption count) and independently reversible, which is what makes it safe to run this migration incrementally across 30 teams over multiple quarters instead of as a single cutover weekend.

## Exit conditions, not calendar deadlines

"Team onboarded to the shared-cluster operating model" should be a checkable state, not a date on a plan:

| Condition | How it's checked |
|---|---|
| Namespace has an enforced `ResourceQuota` and `LimitRange` | `kubectl get resourcequota,limitrange -n <team-ns>` returns non-empty |
| Team has a working `RoleBinding` scoped to their namespace, platform-team blanket access removed | RBAC audit shows only the scoped binding is used for the team's applies over a trial window |
| Every Deployment in the namespace declares resource requests and a readiness probe | An admission-time check or periodic audit reports zero manifests missing either |
| A `PodDisruptionBudget` exists for every Deployment with more than one replica | Same audit, extended to PDB presence |
| Team has drained a node in a non-production namespace at least once and observed the PDB behave as expected | A recorded exercise, not an assumption |

Gating "done" on these observable conditions, rather than "we sent the migration email," is what prevents a platform initiative from being reported complete while half the fleet is still running unquota'd, probe-less Deployments that happen to work until the first real incident.

## Cross-team contracts and accountability

The professional-level design has to be explicit about who owns what when something breaks at the boundary between teams:

- **The platform team owns:** node capacity planning, cluster upgrades, the default `LimitRange`/quota mechanism, the golden-path template, and the admission-time checks that enforce probes and requests exist.
- **Each product team owns:** their namespace's Deployments, their own probe correctness (a readiness check that lies about health is not the platform team's bug to fix), their PDB's `minAvailable` value, and staying inside their quota.
- **The shared, negotiated boundary:** what happens when a team's legitimate quota need exceeds what the cluster's total capacity can currently support — this needs a named process (a capacity request reviewed against actual node headroom), not an implicit assumption that quotas can always be raised on request.

Without this split written down, an incident caused by, say, a missing readiness probe on one team's Deployment turns into a platform-team fire drill instead of the owning team's fix — which defeats the point of the delegation model.

## A sustained-delivery scenario

Six months into the rollout above, a new team joins the org and needs a namespace. Success is not "they got a namespace" — it is that the whole path from "new team requests onboarding" to "team is shipping their own Deployments safely" runs without the platform team touching the checkout, payments, or search namespaces at all:

1. The new team's namespace is created from the golden-path template — quota, limit range, RBAC, default PDB pattern — a repeatable action, not a bespoke conversation.
2. The team ships their first Deployment using the template's probe and resource defaults; the admission check confirms compliance automatically.
3. Three months later the team's traffic grows and they hit their quota ceiling; they file a capacity request against the documented process, get an answer within the agreed SLA, and continue shipping without a platform-team engineer writing YAML on their behalf.
4. A cluster-wide node upgrade happens; every team's PDB, set at onboarding, gates the drain per namespace exactly as designed — the platform team drains 40 nodes without needing to individually coordinate with 30 teams about whether it is safe to touch their Pods.

Measuring this as ongoing — deploys per week without platform-team involvement, time-to-capacity-answer, drains completed without a manually paused rollout — rather than as a single "migration complete" milestone is what keeps the operating model honest as the org keeps growing. It has to keep working for team 31 and team 50, not just the first cohort.

## Common mistakes at this level

- **Quotas set once at rollout and never revisited.** Team usage grows; the quota becomes either a constant source of friction (too tight) or a rubber stamp nobody enforces (raised so high it is meaningless).
- **RBAC delegation without an admission-time backstop.** Teams get edit access to their namespace but nothing checks that their manifests actually declare requests, probes, and PDBs — the delegation removes the platform team's gate without replacing it with an automated one.
- **Treating "onboarded" as a one-time event.** No periodic audit means a team's namespace can silently drift out of compliance (a new Deployment ships without a PDB) with nobody noticing until an incident.
- **No named capacity-escalation process.** Every quota-increase request becomes an ad hoc negotiation, which is exactly the bottleneck the operating model was meant to remove.
- **Governance imposed as a single big-bang cutover** instead of the staged, reversible rollout above — a failed big-bang migration erodes trust in every future platform initiative.

## Apply it

1. Define a golden-path namespace template that bundles a `ResourceQuota`, a `LimitRange`, a scoped `RoleBinding`, and a default `PodDisruptionBudget` pattern.
2. Apply the template to one real team's namespace alongside their existing platform-team access, without removing anything yet.
3. Run an audit script that reports, per namespace, which Deployments are missing resource requests, a readiness probe, or a PDB.
4. Remove the platform team's blanket access for that one namespace only after the audit shows full compliance and the team has completed one self-service deploy.
5. Define and document the capacity-escalation process for when a team's quota need exceeds current cluster headroom, including a response SLA.

## Verify your work

- The audit script run against the onboarded namespace reports zero Deployments missing requests, probes, or a PDB.
- The team completes at least one full deploy cycle using only their scoped RBAC, with no platform-team `kubectl apply` in the audit log.
- A simulated node drain against the onboarded namespace is gated correctly by its PDB, observed the same way as in the senior-level exercise.
- A capacity-escalation request submitted through the documented process receives a decision within the stated SLA, with the decision and rationale recorded.

## Review questions

- What observable conditions, not calendar dates, mark a team as successfully onboarded to a shared-cluster operating model?
- Why does delegating RBAC to teams require an admission-time backstop instead of trusting the golden-path template alone?
- Who owns the fix when an incident traces back to a missing readiness probe in a team's own namespace?
- How would you detect a namespace that has silently drifted out of compliance months after onboarding, before it causes an incident?
