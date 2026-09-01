# Cloud Network Architecture (VPC) — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a small three-tier web app, can you lay out a VPC with correctly sized public and private subnets, wire up an internet gateway and a NAT gateway, and write security group rules that allow only the traffic each tier actually needs?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Vocabulary

- **VPC (Virtual Private Cloud)** — an isolated, private network you define inside a cloud provider, with its own IP address range. Nothing outside it can reach anything inside it unless you explicitly open a path.
- **CIDR block** — the IP address range assigned to a VPC or subnet, written as `10.0.0.0/16`. The `/16` means the first 16 bits are fixed (the network part) and the remaining 16 bits are usable for addresses — a `/16` gives about 65,536 addresses, a `/24` gives 256.
- **Subnet** — a subdivision of the VPC's CIDR block, tied to one Availability Zone (AZ). Resources launch inside a subnet, not directly inside the VPC.
- **Public subnet** — a subnet whose route table sends internet-bound traffic (`0.0.0.0/0`) to an **internet gateway (IGW)**. Anything with a public IP in this subnet is directly reachable from the internet.
- **Private subnet** — a subnet with no route to an internet gateway. Instances here have no public IP and cannot be reached from the internet directly.
- **NAT gateway** — sits in a public subnet and lets instances in a private subnet initiate *outbound* connections to the internet (to pull a package, call an external API) without being reachable from the internet themselves.
- **Route table** — a set of rules, attached to a subnet, that decides where traffic goes based on destination IP. This is what actually makes a subnet "public" or "private" — not a label, a route.
- **Security group** — a *stateful* virtual firewall attached to individual resources (an instance, a load balancer). "Stateful" means if you allow inbound traffic on a port, the matching response traffic is automatically allowed back out — you don't write a return rule.
- **Network ACL (NACL)** — a *stateless* firewall attached to a subnet as a whole. Return traffic must be explicitly allowed by a separate rule; nothing is implied.

## Core Concept 2 — A Repeatable Method

For a small app, laying out the network is the same five steps every time:

1. **Pick the VPC CIDR.** Choose a range large enough for growth but not so large it invites overlap with other VPCs you'll eventually connect to — `10.0.0.0/16` is a common, safe default for a single application VPC.
2. **Carve out subnets by tier and reachability, not by convenience.** Anything that must accept traffic directly from the internet (a load balancer) goes in a public subnet. Everything else — app servers, databases, caches — goes in a private subnet.
3. **Attach the right route table to each subnet.** Public subnets route `0.0.0.0/0` to the internet gateway. Private subnets route `0.0.0.0/0` to a NAT gateway (for outbound-only internet access) and nothing else.
4. **Write security group rules tier by tier, narrowest first.** Each tier should only accept traffic from the specific tier in front of it — not from "anywhere," and not from the whole private CIDR block.
5. **Trace one request path end to end and confirm every hop has a route and a rule that allows it** — this is the sanity check step, and skipping it is how silent misconfigurations survive to production.

## Core Concept 3 — Worked Example: `orders-api`

`orders-api` is a small three-tier app: an internet-facing load balancer, an application tier, and a Postgres database. One VPC, one Availability Zone (multi-AZ redundancy is a topic for the next level).

**CIDR layout:**

| Subnet | CIDR | Type | Holds |
|---|---|---|---|
| VPC | `10.0.0.0/16` | — | everything below |
| `public-lb` | `10.0.1.0/24` | Public | Application Load Balancer |
| `private-app` | `10.0.2.0/24` | Private | app servers |
| `private-db` | `10.0.3.0/24` | Private | Postgres |

**Route tables:**

```
# public-rt (attached to public-lb)
Destination        Target
10.0.0.0/16         local
0.0.0.0/0            igw-0123456789abcdef0

# private-rt (attached to private-app and private-db)
Destination        Target
10.0.0.0/16         local
0.0.0.0/0            nat-0123456789abcdef0
```

**Security group rules** (each group attached to the matching tier):

| Security group | Direction | Port | Source/Destination | Why |
|---|---|---|---|---|
| `sg-lb` | Inbound | 443 | `0.0.0.0/0` | Public HTTPS entry point |
| `sg-app` | Inbound | 8080 | `sg-lb` | Only the load balancer may reach the app tier |
| `sg-db` | Inbound | 5432 | `sg-app` | Only the app tier may reach Postgres |
| `sg-db` | Inbound | (none from `sg-lb` or `0.0.0.0/0`) | — | Database is never reachable directly |

Notice the pattern: each rule names the *security group* of the tier allowed in, not a CIDR range. If the app tier's servers get replaced or autoscaled, their new IPs are still covered because they're still members of `sg-app` — the rule doesn't need to change.

**Traced request path:** browser → `sg-lb` (443, public) → load balancer → `sg-app` (8080, from `sg-lb`) → app server → `sg-db` (5432, from `sg-app`) → Postgres. Every hop above has exactly one rule allowing it and no rule allowing more.

## Core Concept 4 — Simple Success Criteria

A junior-level VPC layout is correct when all of these hold:

1. **The database is never in a public subnet and has no route to an internet gateway**, directly or indirectly.
2. **Every security group rule names the narrowest source that still works** — a specific security group, not `0.0.0.0/0`, unless the resource genuinely must be internet-facing (only the load balancer tier, here).
3. **Each subnet's route table matches its intended role.** A "private" subnet with an internet gateway route in its table isn't actually private, no matter what it's named.
4. **You can trace the full request path** and point to the exact rule that permits each hop.

## Common Mistakes

- **Naming a subnet "private" without checking its route table.** The name is just a label; the route table is what enforces isolation. A subnet named `private-db` that still has a route to the IGW is public.
- **Opening a security group to `0.0.0.0/0` for convenience while debugging**, then forgetting to narrow it back down. This is the single most common way a database or admin port ends up exposed to the internet.
- **Confusing security groups (stateful) with NACLs (stateless).** Forgetting that a NACL needs an explicit *outbound* rule for return traffic, because a security group never required one, leads to connections that mysteriously time out only when a NACL is in the mix.
- **Putting the database in the public subnet "since it needs internet access for updates."** The database needs *outbound* access for patching, which a NAT gateway provides from a private subnet — it does not need a public IP or an inbound route from the internet.
- **Sizing a subnet too small.** A `/28` subnet (16 addresses, several reserved by the cloud provider) fills up fast once autoscaling or multiple load balancer nodes are involved. A `/24` per tier is a safer small-app default.
- **Forgetting the NAT gateway lives in the public subnet, not the private one.** It needs its own route to the internet gateway to do its job; placing it in a private subnet defeats the purpose.

## Apply it

1. Design a VPC CIDR layout for a fictional app called `inventory-svc`: one public subnet for a load balancer, one private subnet for app servers, one private subnet for a MySQL database. Pick a `/16` VPC CIDR and a `/24` for each subnet, and write them out in a table like the one above.
2. Write the route table entries for the public subnet and the private subnets (in the same style as Core Concept 3), naming a placeholder internet gateway ID and NAT gateway ID.
3. Write the security group rules tier by tier: what can reach the load balancer, what can reach the app servers, what can reach the database. Use security-group-to-security-group rules, not CIDR ranges, everywhere except the internet-facing tier.
4. Trace the request path from an external client to the database and confirm, hop by hop, which rule permits it.
5. Now deliberately introduce one mistake from the Common Mistakes list into your design, then write one sentence explaining what would go wrong and how you'd detect it.

## Verify your work

- Your database subnet's route table has no entry pointing to an internet gateway.
- Every security group rule you wrote names a specific security group as the source, except the one rule on the load balancer tier that intentionally allows `0.0.0.0/0`.
- You can state, for each hop in the traced request path, the exact security group rule that permits it — not "it should work."
- Your deliberately-introduced mistake and its consequence are both stated in specific terms (which rule, which resource, what becomes reachable that shouldn't be) rather than in general terms like "it's less secure."

## Review questions

- What actually determines whether a subnet is "public" or "private" — its name, or something else?
- Why does a database tier typically need outbound internet access but not inbound, and how do you provide the outbound path safely?
- What is the difference between a security group and a network ACL, and which one requires an explicit rule for return traffic?
- Why is a security-group-to-security-group rule usually preferable to a CIDR-based rule between two tiers of the same application?
