# Kubernetes Orchestration — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which invariant — replica count, available capacity, or scheduling correctness — breaks first when a node fails or is drained, and what actually restores it?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

## The invariant Kubernetes is actually protecting

Every core object exists to protect one invariant: **the number of healthy, schedulable replicas matches the declared desired count, continuously, without a human in the loop.** Probes, scheduling constraints, and disruption budgets are all mechanisms serving that one invariant. The senior-level questions are about what happens to it under conditions the happy path never exercises: a node dies, a node is drained for maintenance, or the scheduler simply cannot place a Pod.

## Two very different kinds of disruption

Kubernetes explicitly distinguishes these because the guarantees available differ:

| | Voluntary disruption | Involuntary disruption |
|---|---|---|
| Cause | Node drain for maintenance/upgrade, manual node removal, cluster-autoscaler scale-down | Node crash, kernel panic, network partition, node-level out-of-memory |
| Can Kubernetes ask permission first? | Yes — via `PodDisruptionBudget` | No — the node is simply gone |
| What protects the invariant | `PodDisruptionBudget` blocks the drain until enough replicas are elsewhere | The ReplicaSet controller notices missing Pods (via node heartbeat timeout) and creates replacements on other nodes |
| Typical recovery bound | Bounded by the maintenance process itself | Bounded by the node-monitor grace period plus scheduling and image-pull time |

A `PodDisruptionBudget` is what makes voluntary disruption *safe*:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: pricing-api-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: pricing-api
```

With `pricing-api` running 3 replicas and `minAvailable: 2`, a node drain that would take down 2 of the 3 replicas at once is *blocked* by the API server until enough Pods are healthy elsewhere. This is a mechanism, not a policy suggestion — `kubectl drain` on a node running the last-affordable replica will hang rather than proceed.

## Failure mode: the scheduler can't place the Pod at all

The invariant also breaks silently when a replacement Pod is created but never scheduled. `kubectl get pods` shows `Pending` indefinitely. This happens when:

- **Resource pressure** — no node has enough allocatable CPU/memory left to satisfy the Pod's `requests`.
- **Affinity/anti-affinity conflicts** — a `podAntiAffinity` rule spreading replicas across nodes has no remaining eligible node.
- **Taints without matching tolerations** — nodes reserved for another workload class reject the Pod outright.

```text
$ kubectl get pods
pricing-api-7f9c6-znk2q   0/1   Pending   0   4m

$ kubectl describe pod pricing-api-7f9c6-znk2q
...
Events:
  Warning  FailedScheduling  0/6 nodes are available: 4 Insufficient cpu,
                              2 node(s) had taint {dedicated: batch}, that
                              the pod didn't tolerate.
```

The invariant ("3 healthy replicas") is violated for as long as this Pod sits `Pending`, and nothing self-heals it — a human or an autoscaler has to add capacity or relax the constraint. This is the gap junior/middle-level mental models miss: reconciliation guarantees Kubernetes will keep *trying*, not that it will *succeed*.

## Spreading replicas so one failure doesn't take the invariant with it

Anti-affinity is the mechanism that keeps "3 replicas" from silently becoming "3 replicas on one node" — a configuration that satisfies the letter of the invariant while leaving it one node failure away from zero.

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: pricing-api
        topologyKey: kubernetes.io/hostname
```

`requiredDuringSchedulingIgnoredDuringExecution` is a hard constraint: the scheduler leaves a Pod `Pending` rather than violate it. That's a deliberate trade-off — it trades "always spread" for "sometimes can't schedule at all" on a small or unbalanced cluster. The `preferred` variant trades the opposite way: it always schedules something, but silently allows replicas to bunch up under pressure. Choosing between them is choosing which failure mode you would rather have.

## Evidence, not preference: validating the design

A senior claim about resilience needs to be demonstrated, not asserted. Two forms of evidence are cheap to gather and directly test the invariant:

1. **Node failure injection.** Cordon and drain a node running one replica (or, in a test cluster, forcibly delete the node object) and measure how long until `kubectl get pods` shows the replacement `Running` again, and whether the Service's Endpoints count ever dropped below what the `PodDisruptionBudget` should have guaranteed for a voluntary case.
2. **Scheduling pressure test.** Deliberately fill a test cluster's allocatable capacity close to the workload's total requests, then scale up and observe whether Pods go `Pending` and why (`kubectl describe` reveals the exact scheduling predicate that failed) — this validates that requests are sized honestly and that anti-affinity rules do not leave the workload unschedulable in the actual node topology.

Neither of these requires guessing. Both produce a timestamp, a `kubectl describe` event, or an Endpoints count — observable evidence a design review can check.

## Recovery paths and where responsibility actually lives

| Failure | Who/what detects it | Who/what fixes it | Bound on time-to-recovery |
|---|---|---|---|
| Container crashes | kubelet | kubelet restarts the container in place | Restart backoff (exponential, capped) |
| Pod fails readiness | kubelet, reported to API server | Service removes it from Endpoints; ReplicaSet does *not* replace it | As long as the underlying cause persists |
| Node goes unreachable | Node controller (heartbeat timeout) | ReplicaSet controller creates a replacement Pod on a healthy node | Node-monitor grace period plus scheduling and image-pull time |
| Node drained for maintenance | Operator running `kubectl drain` | PodDisruptionBudget gates the drain; new Pods scheduled elsewhere first | Bounded by the drain process, not by Kubernetes itself |
| No node has room | Scheduler (`FailedScheduling` event) | Nothing, automatically — needs capacity added or constraints relaxed | Unbounded without external action |

The last row is the one senior designs must explicitly own: Kubernetes's self-healing story has a hard edge, and a design that assumes "the cluster will just handle it" without checking headroom against real failure scenarios is an unvalidated assumption, not an architecture.

## A cross-component scenario

`pricing-api` runs 3 replicas, a `minAvailable: 2` PDB, and anti-affinity spreading it across 3 of 5 cluster nodes. An operator needs to patch and reboot 2 of those 5 nodes for a kernel CVE.

- Draining node 1 (holding one `pricing-api` replica): the PDB permits it because 2 replicas remain available; the controller schedules a replacement, which lands on node 4 or 5, not on node 2 or 3 where the current replicas live, because of anti-affinity.
- Draining node 2 immediately after, before the replacement is `Ready`: the PDB now blocks the drain — only 2 replicas are currently available and one is still becoming ready, so removing another would temporarily drop below `minAvailable`. The maintenance script must wait for the new Pod's readiness probe to pass before node 2 can drain.

This sequencing — not just the presence of a PDB — is the actual invariant-preserving behavior, and it is exactly the kind of thing that looks fine in a design doc and fails the first time someone drains two nodes back-to-back without checking Pod readiness in between.

## Questions that expose weak assumptions before implementation

- If every replica of this Deployment is unschedulable at once (capacity exhausted cluster-wide), what actually happens to callers — a Service with zero Endpoints, or something outside Kubernetes that catches it?
- Is the anti-affinity rule `required` or `preferred`, and does the team know which failure mode that choice trades for?
- Does the `PodDisruptionBudget`'s `minAvailable` account for the replicas you would lose to an *involuntary* disruption happening at the same time as planned maintenance?
- Has anyone actually drained a node running this workload in a non-production cluster, or is "Kubernetes will reschedule it" an assumption rather than an observation?

## Common mistakes at this level

- **Treating self-healing as unconditional.** Assuming a dead Pod always comes back without checking whether the cluster has spare schedulable capacity for it to come back *into*.
- **PodDisruptionBudget sized without headroom for concurrent involuntary disruption.** `minAvailable` calculated only against the happy-path replica count, not against "what if a real node also died during this maintenance window."
- **`preferred` anti-affinity assumed to behave like `required`.** Under cluster pressure, replicas quietly co-locate and the "spread across nodes" invariant silently stops holding — nothing errors, it just stops being true.
- **No scheduling-pressure test before rollout.** Sizing `requests` from a spreadsheet instead of observing what happens when the cluster is genuinely close to capacity.

## Apply it

1. Deploy a 3-replica Deployment with a `PodDisruptionBudget` (`minAvailable: 2`) and hard anti-affinity spreading replicas across distinct nodes.
2. Drain one node and confirm the PDB permits it while a replacement schedules onto a different node.
3. Immediately attempt to drain a second node before the replacement Pod is `Ready`, and observe the PDB blocking it.
4. Fill the remaining nodes' allocatable capacity close to the workload's total requests, then scale up by one replica and capture the `FailedScheduling` event.
5. Write down, for each failure triggered, what detected it and what — if anything — fixed it, using the recovery-path table as a checklist.

## Verify your work

- The drain of node 1 succeeds only after a replacement Pod reaches `Ready`, visible in `kubectl get pods -w` output.
- The second drain attempt is observably blocked (`kubectl drain` hangs or errors citing the PDB) until availability recovers.
- `kubectl describe pod` on the scaled-up replica shows an explicit `FailedScheduling` event naming the exact predicate that failed (resource, taint, or anti-affinity).
- The Endpoints count for the Service never drops below the PDB's `minAvailable` at any point captured in the exercise.

## Review questions

- What exactly restores the replica-count invariant after a node fails outright, and what is the time bound on that recovery?
- Why does a `PodDisruptionBudget` protect against voluntary disruption but do nothing for a node that simply crashes?
- What does choosing `required` versus `preferred` anti-affinity actually trade off, and how would you know which one a running cluster is using?
- What evidence would convince a reviewer that a Deployment's resource requests are sized honestly rather than guessed?
