# Cloud Network Architecture (VPC) — Middle

<!-- level-focus -->
At middle level, focus on this question:

> When a multi-service application spans two Availability Zones and several tiers, how do you decide which resources get their own subnet, which security-group boundaries are worth drawing, and how do you verify that a boundary actually holds after someone changes a rule?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — From "Does It Work" to "Is It the Right Boundary"

A junior-level layout gets one instance of each tier working in one Availability Zone. Middle-level work is about the boundary decisions that don't show up until the system has to survive a zone failure, scale past one instance per tier, or let a second team add a component without asking the first team's permission for every change.

Three boundary questions recur on every real VPC design:

1. **How many subnets, really?** One subnet per tier per AZ is the standard pattern — not one subnet per microservice. A subnet is a routing and failure-domain boundary, not a service boundary; security groups already separate services within a subnet. Over-splitting subnets multiplies route tables and NACLs to maintain for no additional isolation, since security groups do the fine-grained work.
2. **Shared or dedicated NAT gateway per AZ?** A single NAT gateway serving both AZs is cheaper but makes that NAT gateway's AZ a single point of failure for all outbound traffic — if that AZ has an outage, private subnets in the *other* AZ lose internet egress too, because their route table points at a NAT gateway that's now unreachable. One NAT gateway per AZ costs more but keeps outbound traffic entirely within the healthy AZ during a partial outage.
3. **CIDR-based or security-group-based rules, and how many groups?** Referencing a security group in a rule (as in the junior worked example) is more maintainable as membership changes, but every additional group is one more thing to audit. The middle-level judgment call is where to stop splitting — typically one group per tier, not per instance role, unless two roles in the same tier genuinely need different inbound rules.

## Core Concept 2 — Evaluating Competing Layouts

| Dimension | Fewer, larger subnets/groups | More, smaller subnets/groups |
|---|---|---|
| Blast radius of a route-table mistake | Larger — affects everything sharing that subnet | Smaller — isolated to one subnet's tenants |
| Operational overhead (things to keep in sync) | Lower | Higher |
| Ability to apply per-tier NACLs | Coarser | Finer |
| Cost (NAT gateways, VPC endpoints, peering attachments) | Lower | Higher |
| Onboarding a new component | Fast — fits into existing tier subnet | Slower — needs its own subnet/route table review |

Neither side wins outright. The signal for **under-application** (too coarse) is a security incident or outage post-mortem that says "we couldn't tell what else was affected because everything shared one subnet's blast radius." The signal for **over-application** (too fine) is a change request that takes a full day of route-table and NACL edits to add one more resource that any reasonable engineer would expect to be a five-minute security-group change.

## Core Concept 3 — Worked Scenario: `checkout-platform`

`checkout-platform` spans two AZs and four components: a public load balancer, an app tier (`checkout-api`), a background worker tier (`checkout-worker`) that processes queued payment retries, and a shared RDS Postgres instance. It also calls out to S3 for receipt storage.

**Subnet layout (one subnet per tier per AZ):**

| Subnet | CIDR | AZ | Type |
|---|---|---|---|
| `public-a` | `10.0.0.0/20` | us-east-1a | Public |
| `public-b` | `10.0.16.0/20` | us-east-1b | Public |
| `app-a` | `10.0.32.0/20` | us-east-1a | Private |
| `app-b` | `10.0.48.0/20` | us-east-1b | Private |
| `data-a` | `10.0.64.0/20` | us-east-1a | Private |
| `data-b` | `10.0.80.0/20` | us-east-1b | Private |

`/20` subnets (4,096 addresses each) leave headroom for autoscaling the app and worker tiers without re-carving the VPC later — a common middle-level correction to the junior-level habit of defaulting every subnet to `/24`.

**The boundary decision that matters here:** should `checkout-api` and `checkout-worker` share the `app-*` subnets, or get their own? They share the subnets — both are "the app tier" from a routing and blast-radius standpoint — but they get **separate security groups**, because the worker has no reason to accept inbound traffic from the load balancer at all, only from an internal queue. Collapsing them into one security group would mean a misconfigured rule change for one silently changes exposure for the other.

**Security group design:**

| Security group | Inbound allowed from | Purpose |
|---|---|---|
| `sg-lb` | `0.0.0.0/0` on 443 | Public entry |
| `sg-checkout-api` | `sg-lb` on 8080 | Handles live requests |
| `sg-checkout-worker` | (no inbound from `sg-lb`; internal queue only) | Processes retries, never faces the load balancer |
| `sg-data` | `sg-checkout-api`, `sg-checkout-worker` on 5432 | Both app-tier roles read/write Postgres |

**Reducing NAT dependency with a VPC endpoint:** since `checkout-worker` needs S3 for receipts, routing that traffic through the NAT gateway works but adds NAT data-processing cost and an unnecessary hop through the public subnet's egress path. A **VPC endpoint for S3** (a gateway endpoint, added to the private route tables) lets traffic to S3 stay on the provider's internal network instead of traversing the NAT gateway — cheaper and one fewer thing that breaks if the NAT gateway has a bad day.

```
# data-rt entries after adding the S3 gateway endpoint (app-a / app-b route tables)
Destination           Target
10.0.0.0/16             local
0.0.0.0/0                nat-0a1b2c3d4e5f67890
pl-0abc12de              vpce-0f1e2d3c4b5a69870   # S3 prefix list, via gateway endpoint
```

## Core Concept 4 — Verifying the Boundary, Not Just the Happy Path

A boundary is only real if you can show it holds, at two levels:

**Unit level — one rule, one check.** Before merging a security-group change, confirm the specific claim it makes: "only `sg-checkout-api` can reach port 5432 on `sg-data`." A cloud provider's reachability-analysis tooling (for example AWS VPC Reachability Analyzer, or an equivalent path-tracing tool) can confirm a path is blocked between two specific resources without needing a live deployment — this is the network equivalent of a unit test.

**Integrated-flow level — the whole request path, under a realistic condition.** After deployment, verify the full path end to end and under at least one failure condition:

- A request from the public load balancer reaches `checkout-api` and gets a response.
- `checkout-worker`, which has no inbound rule from `sg-lb`, is confirmed *unreachable* from the load balancer's subnet — attempting the connection should time out, not succeed.
- With one AZ's NAT gateway deliberately marked unhealthy (or its route temporarily removed in a test environment), confirm outbound traffic from the *other* AZ's private subnets is unaffected — this is what the per-AZ NAT gateway decision from Core Concept 1 is actually buying you, and it's worth proving instead of assuming.

## Common Mistakes at This Level

- **Treating "one subnet per microservice" as more secure.** It multiplies subnets and route tables without adding isolation that security groups didn't already provide, and it makes CIDR planning brittle as the number of services grows.
- **Sharing one NAT gateway across AZs to save cost, without writing down that this creates a cross-AZ dependency.** The cost trade-off itself is often reasonable for a non-critical workload; the mistake is not treating it as a documented decision that could bite during an AZ-level incident.
- **Collapsing two tiers with different exposure needs into one security group** because they happen to run in the same subnet, as with `checkout-api` and `checkout-worker` above.
- **Verifying only the happy path.** Confirming the load balancer can reach the app tier is necessary but not sufficient — confirming the *worker* tier cannot be reached the same way is the actual boundary claim being made, and it's the check most often skipped.
- **Adding a NAT gateway route for traffic that a VPC endpoint could carry instead**, paying for and depending on a hop that a same-account, same-region service (S3, DynamoDB) doesn't need.

## Apply it

1. For a fictional `notifications-platform` with an app tier (`notif-api`), a worker tier (`notif-dispatcher`) that has no public-facing role, and a shared Redis cache, design the subnet layout across two AZs using the same per-tier, per-AZ pattern shown above.
2. Decide, and write one sentence justifying, whether `notif-api` and `notif-dispatcher` should share a security group or use separate ones.
3. Write the security group rule set for all three components, including the Redis cache, using security-group references rather than CIDR ranges.
4. Describe (in words, no tooling required) the unit-level check you would run to confirm `notif-dispatcher` cannot be reached from the public load balancer's subnet.
5. Describe the integrated-flow check you would run after deploying a single-NAT-gateway design to confirm what happens to `notif-dispatcher`'s outbound traffic if that NAT gateway's AZ has an outage.

## Verify your work

- Your subnet table has exactly one subnet per tier per AZ — not one per microservice, and not one shared subnet for all private resources.
- Your justification for shared vs. separate security groups names the actual difference in exposure between the two components, not just "to be safe."
- Every security group rule you wrote references another security group as the source, except the load balancer's public-facing rule.
- Your unit-level check names the two specific resources (or security groups) being tested and the expected result (blocked), not a general statement that "security should be tested."
- Your integrated-flow answer correctly identifies that a single shared NAT gateway ties both AZs' outbound traffic to one AZ's health, and states what evidence (a timeout, a reachability-tool result) would show this during an actual outage.

## Review questions

- Why is "one subnet per tier per AZ" usually the right granularity, rather than one subnet per microservice?
- What operational risk does a single shared NAT gateway introduce that one NAT gateway per AZ avoids, and what does it cost to avoid that risk?
- When should two components that share a subnet still get separate security groups?
- What is the difference between verifying a network boundary at the unit level and verifying it at the integrated-flow level, and why do you need both?
