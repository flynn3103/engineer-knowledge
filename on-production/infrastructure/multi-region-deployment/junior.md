# Multi-Region Deployment — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How do you deploy the same service into two regions and prove that each user's request reaches the region that's actually closest and healthy?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

## Vocabulary you need first

- **Region**: an independent, geographically separate deployment location (AWS `us-east-1`, GCP `asia-southeast1`) with its own compute, network, and usually its own copy of the data.
- **Active-active**: two or more regions serve live production traffic at the same time.
- **Active-passive**: one region serves all traffic; another holds a standby copy that is not yet taking traffic.
- **Replica**: a copy of the primary database kept up to date in another region — either **synchronously** (the write waits for the copy to confirm) or **asynchronously** (the write does not wait).
- **Replication lag**: how far behind a replica is compared to the primary, usually measured in seconds or milliseconds.
- **Region-aware routing**: directing a client to a specific region based on where the client is and whether that region is healthy — typically DNS-based (geo-DNS, latency-based routing) or via an anycast IP.
- **Health check**: an automated probe that marks a region "down" for routing purposes when it stops answering correctly.

This topic is not about how a service is deployed *inside* one region (that's containers and orchestration), and it is not about the procedure you run *during* a declared disaster (that's disaster recovery — the failover runbook this topology makes possible). It's also not about adding more instances of the same region when load rises (that's autoscaling) or about the subnet/routing details inside one region's network (that's cloud network architecture). Multi-region deployment is the steady-state decision of which regions take live traffic right now, and how a request finds its way to one of them — the thing disaster recovery falls back on, and the thing autoscaling happens *within*, once you're already there.

A useful way to keep these apart: if the question is "how do we handle a whole region going down," that's disaster recovery. If the question is "which regions are serving traffic on an ordinary Tuesday, and how does a request find the right one," that's this topic.

## The two basic topologies

| | Active-active | Active-passive |
|---|---|---|
| Who serves traffic | Both/all regions, simultaneously | One region; the other stands by |
| Failover | Nothing to fail over — the other region is already live | Requires promoting the standby (a routing change, and often promoting a database replica) |
| Data consistency | Harder to reason about — writes can land in either region | Easier — one region is the single source of truth |
| Infrastructure cost | Full capacity paid for in every region | Standby region can run at reduced capacity |
| Typical shape at junior scale | A stateless API tier behind a global load balancer | A single-writer database with one or more read replicas elsewhere |

Most real systems are a mix: a stateless web/API tier that is active-active, sitting in front of a database that is still active-passive (one write region, plus read replicas elsewhere). Treating "multi-region" as one all-or-nothing switch is the first thing to unlearn — different layers of the same system can sit at different points on this table.

## Step-by-step: standing up a two-region deployment

1. **Deploy the same service into two regions** using your existing container/orchestration pipeline — there's no new deployment mechanic here, you're just running the same thing twice.
2. **Give each regional deployment its own regional entry point** (a load balancer or ingress per region) so each region can serve traffic on its own, without routing through the other.
3. **Add a region-aware routing layer in front of both** — DNS-based latency routing or geo-DNS is the simplest starting point, and doesn't require you to run your own anycast network.
4. **Attach a health check to each region's endpoint** so the routing layer stops sending traffic to a region that is failing, without a human having to notice and intervene.
5. **Send test traffic from both sides of the world (or simulate two vantage points) and confirm each request lands on the nearer, healthy region** — don't just trust the configuration, observe the actual routing decision.

## Worked example: latency-based DNS routing for a listings API

A classifieds marketplace runs its listings API in two regions: `ap-southeast-1` (Singapore) and `us-east-1` (N. Virginia). A DNS provider with latency-based routing (Route 53 is a common real example of this feature) holds two record sets for `api.example.com`:

```
Record set: api.example.com

  - Region: ap-southeast-1
    Value: 203.0.113.10   (Singapore ALB)
    Routing policy: latency
    Health check: hc-sg — HTTP GET /healthz every 30s, 3 consecutive
                  failures marks the region unhealthy

  - Region: us-east-1
    Value: 198.51.100.20  (N. Virginia ALB)
    Routing policy: latency
    Health check: hc-us — HTTP GET /healthz every 30s, 3 consecutive
                  failures marks the region unhealthy
```

A request from a user in Ho Chi Minh City resolves `api.example.com` and gets back `203.0.113.10` (Singapore), because that region measures lowest latency from resolvers near Vietnam. A request from a user in Ohio gets `198.51.100.20` (N. Virginia). If Singapore's `/healthz` fails 3 checks in a row, the Singapore record is withdrawn from DNS answers, and *all* traffic — including requests from Vietnam — starts resolving to N. Virginia, at a real latency cost, until Singapore recovers and passes its health check again.

Prove the routing is real by tracing the request end to end, rather than trusting the config file:

```
dig api.example.com                    # run from a Singapore-based host
→ 203.0.113.10

dig api.example.com                    # run from a US-based host
→ 198.51.100.20

curl -sv https://api.example.com/healthz
→ inspect a response header or body field that identifies which
  region actually answered (e.g. X-Served-By: ap-southeast-1)
```

If both `dig` runs return the same IP regardless of vantage point, region-aware routing isn't actually doing anything — you have two deployed regions, but you're only using one of them.

## Simple success criteria

A junior-level multi-region deployment is working when all of the following are true at once — not just the first one, which is the one people usually stop at:

1. Two independent regional deployments exist and can each serve traffic on their own, with no dependency on the other being up.
2. A resolver query from a vantage point near each region returns that region's IP, not the same IP everywhere.
3. Forcing one region's health check to fail removes that region from routing answers within the configured check interval, without a manual step.
4. Restoring that region's health returns it to rotation within roughly one TTL/health-check cycle.
5. You can point to which region actually served a given response (via a header, a log line, or a body field) rather than assuming from the request alone.

## Common mistakes at this level

- **Confusing multi-AZ with multi-region.** Multiple availability zones inside one region protect against a single data-center failure. They do nothing for a whole-region outage, and nothing for the latency of a user on the other side of the planet.
- **Assuming DNS changes propagate instantly.** DNS records carry a TTL; a short TTL (30–60 seconds) is needed for routing and health-check changes to take effect promptly, and even then some resolvers and clients cache longer than the TTL suggests.
- **Deploying a second region but pointing it at the same single-region database with no replica.** The "second region" then adds a cross-region round trip on every database call, which can make it *slower* than a single region, not faster.
- **Never testing the unhealthy path.** It's easy to confirm the happy path — both regions up, routing looks plausible — and never simulate a health-check failure to see whether traffic actually reroutes.
- **Writing a health check that always returns `200 OK`.** A health check has to exercise something meaningful (can this instance reach its own database, its own cache) or it will report "healthy" right up until the moment it can't serve a real request.

## Apply it

1. Deploy the same small service (or a stub with a `/healthz` endpoint) to two regions, or to two differently tagged environments that simulate two regions.
2. Configure a DNS record with latency-based or weighted routing pointing at both (or simulate this with two resolver configurations if you don't have a real multi-region DNS provider available).
3. Run `dig` (or an equivalent resolver query) from two different vantage points and record which IP each one returns.
4. Make one region's `/healthz` return a failure, wait for the configured health-check interval to elapse, then re-run the same `dig` query and confirm that region no longer appears in the answer.
5. Restore the health check and confirm routing returns to normal within roughly one TTL / health-check cycle, not immediately and not after an arbitrary wait.

## Verify your work

- Two `dig` outputs from step 3 show different IPs for different vantage points — proof that routing is actually region-aware, not returning the same answer everywhere.
- After forcing a health-check failure, the previously-returned IP for that region stops appearing in DNS answers within the expected number of check intervals.
- Restoring health brings the region back into rotation within roughly one TTL cycle — not instantly, and not "eventually, whenever."
- You can state, in one sentence each, the difference between active-active and active-passive, and say which one your test setup demonstrated.

## Review questions

- What's the difference between deploying across multiple availability zones and deploying across multiple regions?
- Why can a health check that always returns `200 OK` give you false confidence in a multi-region setup?
- What two things have to happen, in order, for DNS-based routing to actually move traffic away from an unhealthy region?
- If a service's web tier is active-active but its database is still single-writer active-passive, what part of the system still has one point of regional dependency?
