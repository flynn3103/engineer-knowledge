# Cloud Network Architecture (VPC) — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you design a network operating model — shared transit infrastructure, IP address governance, and ownership boundaries — so that dozens of teams can provision and evolve their own subnets and security groups without a central network team becoming a bottleneck or an unnoticed security gap?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership and Cognitive Load

A senior-level design gets the topology right for a handful of VPCs. At organization scale, the harder problem is *who is allowed to change what*, because the number of teams touching the network grows faster than any one team's ability to review every change. Getting this wrong produces one of two failure patterns:

- **Central bottleneck.** A network platform team reviews every subnet, every security group rule, and every peering request for every product team. This scales linearly with the number of requests and eventually becomes the slowest step in shipping anything that touches the network — teams start routing around it with workarounds that are worse for security than the review process was trying to prevent.
- **Ungoverned sprawl.** Every team gets full ownership of their own VPC with no shared constraints, no CIDR coordination, and no consistent baseline (logging, mandatory NACLs, tagging). This scales in the other direction: nobody can answer "what can reach our payments database" org-wide, because the answer is scattered across dozens of independently-designed VPCs.

The professional-level answer is a split of ownership that keeps each team's cognitive load bounded to what they can actually reason about:

| Owned centrally (network platform team) | Owned by product teams |
|---|---|
| Transit gateway / hub topology and its route tables | Their own VPC's subnet layout within an allocated CIDR block |
| IP address allocation (IPAM) — which team gets which CIDR range | Their own security group rules within the tier boundaries they're responsible for |
| Baseline guardrails: mandatory flow logs, mandatory deny-by-default NACLs, disallowed rules (e.g., no `0.0.0.0/0` on ports 22/3389) enforced by policy-as-code | Which of their own resources sit in which of their subnets |
| Cross-VPC connectivity requests (attaching to the hub, or approving a rare direct peering exception) | Day-to-day changes within their own boundary that don't touch shared infrastructure |

This is the same principle as a well-drawn service boundary applied to network infrastructure: a team should be able to make the changes that only affect them without asking anyone, and changes that affect shared infrastructure or other teams should go through a defined, fast contract rather than an open-ended review queue.

## Core Concept 2 — IP Address Governance as a Contract

The single most common organization-scale network failure is CIDR collision discovered late — two teams independently choose `10.0.0.0/16` for their VPC, and the collision surfaces only when someone tries to connect them, often under deadline pressure. At professional scale this cannot be handled by convention or tribal memory; it needs a real allocation contract:

- **A reserved address space, subdivided by policy**, for example a `10.0.0.0/8` block split into `/16` allocations, with a documented, self-service process for a team to request the next available `/16` from an IP address management (IPAM) tool or equivalent registry — not a Slack message to whoever remembers the spreadsheet.
- **An allocation SLA**, so "we need a CIDR block" doesn't become a multi-week blocker for a new team's project. A same-day or same-hour automated allocation (an IPAM pool with policy-based assignment) is achievable and removes the incentive for teams to just pick something and hope.
- **A single source of truth that's queryable**, so "does this CIDR range collide with anything?" is a lookup, not an email thread across every team that might own a VPC.

This is infrastructure the whole organization depends on but that no single product team should own informally — it belongs with the network platform team specifically because a collision's cost is paid by whichever two teams later need to connect, not by the team that made the original choice.

## Core Concept 3 — Decomposing a Migration Into Reversible Increments

Consider a realistic initiative: an organization with 30 product teams currently runs a flat, single-VPC-per-environment model with an ad hoc peering mesh that's become unmanageable (the failure mode from the senior level, at real scale). The goal is to migrate to a hub-and-spoke model with a transit gateway, per-team VPCs, and centralized IPAM — without a "big bang" cutover that risks an outage across every team at once.

A durable delivery plan breaks this into increments that are each independently reversible and independently observable:

1. **Stand up the hub (transit gateway) and IPAM pool with zero production traffic depending on them yet.** This increment can be fully validated (attachment works, route propagation behaves as expected, IPAM allocates without collision) with no risk to any live team, and rolled back trivially if it doesn't.
2. **Onboard one low-criticality, low-traffic team as a pilot**, keeping their existing peering connections live in parallel (dual-path) rather than cutting over instantly. Success is measured by comparable latency and zero dropped connections through the new path over an observation window, not by "it deployed without erroring."
3. **Define and publish the migration contract for the remaining teams**: what changes on their end (attaching to the hub, adopting the new CIDR allocation if they need to re-address), what stays the same (their own security groups, their internal subnet layout), and what the rollback path is if their traffic through the hub misbehaves.
4. **Migrate teams in waves, each wave's exit condition being observable and pre-agreed**, for example: flow logs show zero traffic still traversing the old peering connection for that team, for a full week, before that peering connection is deleted. This is a reversible, evidence-gated increment, not a scheduled cutover date treated as the source of truth.
5. **Decommission the old peering mesh only after every team's exit condition has been independently confirmed**, not on a single global "migration complete" declaration — because the risk being managed is exactly that one team's traffic pattern was missed by the general assumption that everyone had moved.

The throughline: each step has its own rollback and its own observable success signal, so a partial failure at wave 12 of 30 doesn't require re-litigating waves 1 through 11.

## Core Concept 4 — Compliance, Coordination, and Cross-Team Contracts

Network segmentation is frequently the mechanism that satisfies a compliance requirement, not just a performance or reliability concern:

- **Regulatory segmentation** (for example, cardholder-data-environment scoping under PCI DSS, or a similar mandated isolation requirement) typically requires that specific subnets and security groups can be shown, with evidence, to be reachable only from an approved, minimal set of sources. This means the network platform team's baseline guardrails need to include an auditable answer to "show me everything that can reach this subnet" — which is exactly what centralized flow logs and IaC-managed route tables and security groups provide, and what ungoverned per-team sprawl cannot provide.
- **Cross-team contracts** should be explicit about what a product team can change unilaterally versus what requires a request to the network platform team, with a stated turnaround time for the latter — an unstated or informally-enforced boundary is the bottleneck failure pattern from Core Concept 1 waiting to happen.
- **Accountability** for a network incident should be traceable to the layer that owns the thing that failed: a misconfigured security group within a team's own boundary is that team's incident; a transit gateway route table misconfiguration that exposed two unrelated teams to each other is the network platform team's incident. Mixing these up (blaming a product team for a shared-infrastructure failure, or vice versa) erodes the whole ownership model from Core Concept 1.

## Outcome Measures and Exit Conditions

A migration or an operating-model change like this should be judged against measures that are checkable, not against a felt sense that things are "better organized":

| Outcome measure | What it tells you |
|---|---|
| Time from CIDR request to allocation | Whether IPAM governance is a self-service contract or a hidden bottleneck |
| Number of point-to-point peering connections still in service | Progress of the hub migration; this should trend toward the count that's genuinely justified as two-party relationships, not zero |
| Percentage of subnets covered by mandatory flow logs and baseline NACLs | Whether the guardrail layer is actually universal or has gaps that predate the current governance model |
| Number of security-group or NACL changes requiring central review vs. self-served by product teams | Whether the ownership split from Core Concept 1 is holding, or drifting back toward the bottleneck pattern |
| Traffic volume on decommissioned legacy peering connections, pre-deletion | The evidence gate for wave completion in the migration plan above — should be zero, sustained, before deletion |

Exit conditions for the migration as a whole should be defined the same way each wave's exit condition was: not a date, but a state — every team attached to the hub, zero traffic on legacy peering for a sustained window, and IPAM as the sole source of new CIDR allocations org-wide.

## Apply it

1. For an organization with 20 product teams currently on a flat peering mesh, draft the ownership split (central vs. product-team) for: CIDR allocation, transit gateway route tables, per-team security groups, and mandatory flow logging — using the two-column format from Core Concept 1.
2. Write the allocation contract for IP address governance: the reserved block, the subdivision policy, and the maximum acceptable time from request to allocation.
3. Break a migration from flat peering mesh to hub-and-spoke into at least four increments, each with its own rollback path and its own observable exit condition, following the pattern in Core Concept 3.
4. Name one compliance or regulatory driver (real and general, such as PCI DSS scoping) that would require specific subnets to have auditable, minimal reachability, and state what evidence would satisfy that requirement.
5. Pick two outcome measures from the table above that you would track weekly during the migration, and state what a worsening trend in each would mean operationally.

## Verify your work

- Your ownership split assigns transit gateway route tables and IPAM to the central team and per-team security groups to product teams, with a clear, stated reason tied to blast radius or cross-team impact — not an arbitrary split.
- Your IPAM contract specifies both the reserved block and a concrete allocation turnaround time, not just "teams should coordinate."
- Each migration increment you wrote has both a rollback path and an observable, evidence-based exit condition — not a calendar date standing in for a state.
- Your compliance answer names a specific, real, well-known driver (not a fabricated one) and states what auditable evidence (flow logs, IaC state, a reachability report) would satisfy it.
- Your two chosen outcome measures each come with a stated operational meaning for a worsening trend, not just a definition of the metric.

## Review questions

- Why does a purely centralized network review model eventually become the bottleneck for the whole organization's delivery speed?
- What specific failure does a shared, governed IP address allocation contract prevent, and why is that failure expensive to fix after the fact?
- Why should a large-scale VPC migration be broken into independently reversible increments with evidence-based exit conditions, rather than a single scheduled cutover?
- How should accountability for a network incident be assigned between a central network platform team and a product team, and what determines which one owns a given incident?
