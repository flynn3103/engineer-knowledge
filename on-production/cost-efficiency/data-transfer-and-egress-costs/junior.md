# Data Transfer and Egress Costs — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a small service's traffic broken down by same-AZ, cross-AZ, cross-region, and internet-egress paths, can you identify which path is driving the transfer bill and apply the cheapest fix without changing what the service does?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Vocabulary

- **Ingress** — data coming *into* a cloud provider's network. Almost universally free across major providers.
- **Egress** — data leaving a network boundary (an Availability Zone, a region, or the provider entirely, out to the public internet). This is the side that gets billed, and it is the whole subject of this topic.
- **Availability Zone (AZ)** — an isolated data-center facility within a region. Traffic between two resources in the *same* AZ is the cheapest tier, often free.
- **Region** — a geographic grouping of AZs (for example, several AZs make up one region). Traffic between AZs *within* the same region ("cross-AZ") is billed, but at a much lower rate than traffic leaving the region.
- **Cross-region transfer** — data moving between two different regions (say, a US region and a European region). Priced higher than cross-AZ because it usually rides a longer, more expensive backbone path.
- **Internet egress** — data leaving the cloud provider's network entirely, bound for an end user's browser, another company's data center, or another cloud provider. This is typically the most expensive tier, and it is the tier every end-user request eventually touches.
- **CDN (Content Delivery Network)** — a network of edge locations that cache content close to end users, so repeat requests are served from the edge instead of traveling all the way back to your **origin** (the actual server or storage bucket that holds the real data).

A useful mental model: think of data transfer cost as a set of **tiers**, cheapest to most expensive, and every hop your request path takes lives in one of them.

| Tier | Typical relative cost | Why |
|---|---|---|
| Same-AZ | Lowest (often free) | Stays inside one physical facility |
| Cross-AZ (same region) | Low-to-moderate | Still inside the provider's regional backbone |
| Cross-region | Moderate-to-high | Longer path, sometimes crosses continents |
| Internet egress | Highest | Leaves the provider's network entirely |

These are *relative* orderings, not fixed prices — actual rates vary by provider, region pair, and change over time. Never treat a specific number you read somewhere as still accurate; treat the ordering (same-AZ cheaper than cross-AZ cheaper than cross-region cheaper than internet egress) as the stable fact worth remembering.

## Core Concept 2 — A Repeatable Method

Given any small service, finding and fixing an expensive data-transfer path follows the same five steps:

1. **Map the request path.** Draw every hop from client to response: load balancer, app server, cache, database, object storage. Note the AZ and region each resource actually lives in — not where you assume it lives.
2. **Pull the real transfer numbers.** Use the cloud billing console or cost-allocation tags to get actual gigabytes transferred per hop for one period (a week or a month).
3. **Classify each hop into a tier** using the table above: same-AZ, cross-AZ, cross-region, or internet egress.
4. **Find the largest-volume hop sitting in an expensive tier.** Volume times tier price is what matters — a huge same-AZ transfer can cost less than a small internet-egress transfer.
5. **Apply the cheapest available fix without changing behavior**: move two chatty resources into the same AZ, add an edge cache/CDN in front of a public-facing path, or use a private connectivity option instead of a public one. Then re-measure.

## Core Concept 3 — Worked Example: `ThumbAPI`

`ThumbAPI` is a small service that resizes and serves thumbnail images to a mobile app used worldwide. Its request path today: client → app servers (one region) → object storage bucket (same region as the app servers). There is no CDN — every request goes all the way back to the app servers and the bucket.

One month of transfer volume, pulled from the billing console (illustrative figures, not current pricing):

| Hop | Tier | Volume/month | Illustrative relative $/GB | Illustrative monthly cost |
|---|---|---|---|---|
| App servers ↔ storage bucket | Same-region | 2 TB | 1x (baseline unit) | $20 |
| App servers → client (worldwide) | Internet egress | 40 TB | 9x baseline | $3,600 |
| **Total** | | | | **$3,620** |

The internet-egress hop is 20x the volume of the same-region hop, at a much higher per-gigabyte rate — it dominates the bill by a wide margin. That is the hop worth fixing.

**The fix:** put a CDN in front of the app servers. Popular thumbnails get cached at edge locations close to users; only cache-misses and first-time requests travel all the way back to the origin.

After adding a CDN with an 90% cache-hit rate (illustrative):

| Hop | Volume/month | Note |
|---|---|---|
| Origin (app servers) → CDN edges | ~4 TB | Only cache misses reach the origin now |
| CDN edges → clients | ~36 TB | Served from edge locations, typically cheaper per GB than origin internet egress, and closer to users |

The functionality did not change — users still get the same thumbnails, at the same URLs. What changed is *where* the bytes travel from on repeat requests, which moves most of the volume out of the most expensive tier.

## Core Concept 4 — Simple Success Criteria

A junior-level fix is trustworthy when all four of these hold:

1. **Every hop in the request path was classified**, not just the one you assumed was expensive.
2. **The numbers came from real billing/traffic data** for a defined period, not a guess.
3. **The fix targets the actual largest cost driver** (volume × tier price), not the hop that was easiest to change.
4. **The fix didn't change what the service does** — same responses, same correctness, only a cheaper path for the bytes.

## Common Mistakes

- **Treating all "data transfer" as one flat cost.** Same-AZ, cross-AZ, cross-region, and internet egress are priced differently; lumping them together hides which hop actually matters.
- **Confusing ingress with egress.** Ingress (data coming in) is typically free; egress (data going out) is the side that's billed. Assuming both are free, or both are billed, leads to wrong conclusions.
- **Environments quietly pointing cross-region.** A staging or backup job copy-pasted from a template can end up reading from one region and writing to another, generating real cross-region transfer cost for no functional reason — this is a very common beginner mistake because it produces no visible bug, just a bigger bill.
- **Skipping a CDN because it "seems like overkill."** For any service serving the same static or semi-static content repeatedly to many users, an edge cache is one of the highest-leverage, lowest-risk fixes available — dismissing it without checking the repeat-request rate is a mistake.
- **Downloading logs or backups across regions out of habit.** Pulling a full log export or backup from a different region for local debugging, routinely, when a same-region copy or a sampled export would answer the same question.
- **Fixing the wrong hop.** Optimizing a same-AZ database call that costs a few dollars a month while a 40 TB internet-egress path costs thousands — always check volume × tier price before deciding where to spend effort.

## Apply it

1. For a fictional service `MediaAPI`, given this hop table — app servers to storage bucket (same region): 1.5 TB/month; app servers to clients worldwide: 25 TB/month, no CDN — classify each hop into a tier (same-AZ, cross-AZ, cross-region, or internet egress).
2. Using the relative cost ordering from Core Concept 1 (same-AZ cheapest, internet egress most expensive), state which hop is the larger cost driver and explain why, referencing both volume and tier.
3. Propose one specific, concrete fix (for example, adding a CDN with edge caching) and describe exactly what would change about the request path — not just "make it cheaper."
4. Estimate, using an illustrative cache-hit rate of your choosing (state the number), roughly how much of the 25 TB would now be served from cache versus still reaching the origin.
5. Write one sentence on how you would confirm, next month, that the fix actually worked — name the specific dashboard or report you'd check.

## Verify your work

- You classified every hop in the request path into the correct tier, not just the one that looked suspicious.
- Your answer correctly identifies the internet-egress hop as the dominant cost, and explains that using both volume and tier, not just "it sounds big."
- Your proposed fix is a specific, named technical change (CDN, moving a resource, a private connectivity option) — not a vague "reduce data transfer."
- Your cache-hit estimate is stated as a number and labeled as an estimate, with a rough resulting split between origin traffic and edge traffic.
- Your verification answer names a specific dashboard or billing report, not "check if it's cheaper."

## Review questions

- What is the difference between ingress and egress, and which one is typically billed?
- Why does the same amount of data cost different amounts depending on whether it stays in one AZ, crosses regions, or reaches the public internet?
- Why can a CDN reduce the origin's egress bill without changing what content users receive?
- Given two hops with different volumes and different cost tiers, how do you decide which one is actually the bigger cost driver?
