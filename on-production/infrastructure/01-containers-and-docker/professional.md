# Containers and Docker — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run container image standards — base images, build patterns, vulnerability scanning, registries — as a durable, org-wide operating model, so every team ships small, reproducible, patched images without a central team reviewing every Dockerfile?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable organizational failure mode: a central platform or security team tries to personally review and approve every team's Dockerfile, becomes a bottleneck the moment more than a handful of teams are shipping containers, and the review queue grows faster than the team can clear it. The split that actually scales distributes ownership by who has the context to make each decision correctly and sustain it over time:

| Layer | Owner | Responsibility |
|---|---|---|
| **Golden base images** | Platform team | Build, patch, and version a small set of approved base images (per language/runtime) that other teams build on top of, so patching a CVE happens once centrally instead of once per team |
| **Application-specific Dockerfile layers** | The team that owns the service | Everything above the golden base — dependency installs, application source, the multi-stage split appropriate to their build — because they know their own build and runtime needs |
| **Scanning policy and severity gates** | Security engineering | Define what counts as a blocking vulnerability, own the scanning tool and its ruleset, and evolve the policy as the threat landscape changes |
| **Registry infrastructure and image distribution** | Platform team | Run the internal registry mirror, its retention policy, and its availability, so no individual team depends on an external registry's rate limits or uptime for their own deploys |
| **Program health and enforcement** | A governance working group spanning platform and security | Track adoption, drift, and scan-finding trends across the org; escalate when a team's images fall behind or a shared base image has no active owner |

This split keeps each layer within what its owner can actually sustain: no product team is asked to track CVE disclosures across every language ecosystem, and no central team is asked to understand every service's specific build requirements.

## Core Concept 2 — Golden Base Images as a Paved Road

A **golden base image** is a platform-owned, versioned, pre-scanned image that other teams build `FROM` instead of pulling directly from a public registry. It exists to make the secure, small, patched choice the *default* choice rather than something every team has to independently discover and re-derive:

```dockerfile
# Instead of every team independently choosing (and re-justifying) a base:
FROM node:20-slim

# Teams build from a platform-maintained, pre-scanned, versioned image:
FROM registry.internal/golden/node:20-slim-v3
```

The golden image itself is built and patched centrally — when a CVE is disclosed in a package it contains, the platform team patches it once, publishes a new version, and every consuming team's next build picks it up (or is notified to rebuild against it), instead of a dozen teams each independently discovering and separately patching the same underlying issue. This is the same leverage as a shared library: fix it once, upstream of everyone who depends on it.

A paved road only works if teams actually prefer it to the alternative, which means it has to be genuinely easier than pulling directly from a public registry — published with clear version support windows, fast to build from (cached in the internal registry mirror, not refetched externally), and documented well enough that adopting it doesn't require asking the platform team a question every time.

## Core Concept 3 — Decomposing the Rollout Into Reversible Increments

Mandating "every team switches to the golden base image by end of quarter" produces exactly the theater that any top-down infrastructure mandate produces: rushed, unverified switches made to hit a deadline rather than because the image was actually validated. Decompose the rollout instead:

1. **Pilot with one team, on one service** — ideally one whose current base image is already flagged by a vulnerability scan, so the motivation is concrete and the win is measurable and specific.
2. **Extract the golden image's structure from what the pilot needed**, rather than designing it by committee beforehand — the pilot reveals which language versions, which OS packages, and which build-time tools are actually required, and which speculative options nobody uses.
3. **Wire vulnerability scanning into CI as a non-blocking report first**, before it blocks any merge — this surfaces how much of the existing fleet would fail the gate, without breaking anyone's build on day one of the policy existing.
4. **Turn the scanning gate blocking only for new builds**, not retroactively for already-running images, so the backlog of existing non-compliant images doesn't halt current work; existing images get a scheduled remediation window instead of an overnight break.
5. **Expand team by team**, reusing the golden image and the same scanning ruleset, and track adoption as a fraction (services built from a golden base / total services) rather than a binary "migrated or not."

Each step stays independently reversible: if the golden image needs a new variant after the third team adopts it, that's a version bump, not a program failure, because no later step assumed the first version was final.

## Core Concept 4 — Migration, Governance, and Supply-Chain Risk

Rolling this out across an organization with years of existing images surfaces risk a single pilot doesn't:

- **Legacy images on end-of-life bases.** Services built years ago on a base OS or language runtime version that has stopped receiving security patches are common, and their owners are often unaware the base is unsupported — discovery starts with an inventory scan across the fleet, not with asking teams to self-report.
- **Registry sprawl and rate limits.** Teams pulling directly from a public registry at scale can hit that registry's rate limits during a busy deploy period, an outage caused entirely by infrastructure choice rather than application bugs. An internal registry mirror removes this dependency and gives the platform team control over caching and availability.
- **Provenance and supply-chain integrity.** For compliance and for genuine security assurance, an organization increasingly needs to answer "was this image built from the source we think it was, by the pipeline we think built it, and has it been tampered with since?" — the standard tools here are image **signing** (cosign is the common tool for signing and verifying OCI images) and a **Software Bill of Materials (SBOM)** enumerating every package and version an image contains, both of which only have value if generated automatically as part of the build pipeline, not produced retroactively when an auditor asks.
- **Scanning-gate rollout causing a broad, sudden break.** Turning a vulnerability-severity gate from advisory to blocking for the *entire* existing fleet at once, rather than only for new builds (Core Concept 3, step 4), can break dozens of teams' deploys simultaneously over vulnerabilities that predate the policy and were never the deploying engineer's decision to fix in that moment.

## Core Concept 5 — Outcome Measures and Exit Conditions

A durable program needs measures that show it is producing real security and reliability improvement, not just a compliance checkbox:

```yaml
# Program health dashboard, reviewed quarterly.
metrics:
  golden_base_adoption: "services built from a golden base image / total services"
  fleet_scan_pass_rate: "images passing the current severity gate / total images scanned"
  patch_latency: "median time from CVE disclosure in a base image to a patched image reaching production"
  image_size_trend: "median final-stage image size across the fleet, tracked over time"
  registry_availability: "internal registry mirror uptime and pull success rate"
exit_conditions:
  pilot_to_expansion: "pilot service passes the scanning gate, image size drops measurably versus its prior base, and the platform team can patch and republish the golden base without the pilot team's involvement"
  program_maturity: "golden_base_adoption > 80% of active services, and patch_latency trending down for two consecutive quarters"
```

The number that matters most is `patch_latency`: an org can have high adoption of the golden base on paper while still taking weeks to actually roll a critical CVE patch to production, if the "notify teams to rebuild" step is manual and unenforced. Adoption and pass-rate are leading indicators of whether the paved road exists and is being used; patch latency is the outcome measure that proves the paved road actually delivers what it exists for — faster, more reliable patching than each team doing it independently. Set "the program is working" on that trend, not on adoption percentage alone.

## Core Concept 6 — Cross-Team Contracts

Once many teams build on shared golden images, the image is only as trustworthy as the platform team's discipline in maintaining and communicating about it. Formalize this the way an internal API is formalized:

- Every golden base image publishes a **support contract**: which major version is current, which are still patched but deprecated, and the date a version stops receiving security patches entirely.
- Consuming teams build against a specific major version (`golden/node:20-slim`, not an unpinned floating alias) and are expected to plan their own upgrade to the next major version ahead of its deprecation date, rather than being surprised by it.
- A breaking change to a golden image — dropping a package a consuming team depended on, changing a default that affects runtime behavior — goes through the same change-review process as a breaking API change, with advance notice to known consumers, because for a team that built on the old behavior, it functionally is a breaking change.
- Accountability follows the contract: if a CVE reaches production because the platform team was slow to patch the golden base, that is the platform team's action item; if it reaches production because a team ignored a deprecation notice and never upgraded, that is the consuming team's.

## Core Concept 7 — Sustained Delivery, Not a Static Migration

Getting every team onto golden base images once is not the end state — new CVEs, new language runtime releases, and new teams being onboarded keep happening indefinitely. A sustainable cadence:

- **A patch cadence for golden images tied to CVE disclosure severity**, not a fixed calendar — a critical CVE in a widely-used base package triggers an out-of-band patch and republish; routine dependency updates follow a regular, lower-urgency schedule.
- **A mandatory rebuild trigger on golden image patch**, automated where possible (a bot opening a PR bumping the base image tag in each consuming team's Dockerfile), so a patched base actually reaches production quickly rather than sitting available-but-unused until someone happens to rebuild.
- **New teams onboard onto the golden base by default**, not as an opt-in step someone has to remember — the paved road should be the path of least resistance for a brand-new service, not a retrofit applied only after an incident.
- **A program-level retrospective every couple of quarters** against the outcome measures from Core Concept 5, asking explicitly: is patch latency actually falling, and if not, is the bottleneck the platform team's patch speed, the notification mechanism, or consuming teams deprioritizing the rebuild?

---

## Real-World Examples

- **A pilot's concrete win funds expansion.** A service flagged by a vulnerability scan for an outdated base image becomes the pilot for the golden-image program; switching it drops both its open CVE count and its image size measurably, giving the platform team a specific, demonstrated result to justify expanding rather than a mandate imposed with no proof it helps.
- **An automated rebuild bot closes the patch-latency gap.** After a critical CVE in a base package, the platform team patches and republishes the golden image within hours, but manual adoption across forty consuming teams would have taken weeks; an automated bot opening a version-bump PR against every consumer's Dockerfile closes most of that gap within a day.
- **A blocking gate rolled out to the whole fleet at once breaks unrelated teams' deploys.** A security team turns a scanning severity gate from advisory to blocking for every image simultaneously; a dozen teams' deploys fail overnight on pre-existing vulnerabilities they had no chance to remediate in advance, and the gate is rolled back to advisory-only for existing images while remaining blocking for new builds — exactly the sequencing Core Concept 3 describes avoiding.
- **Adoption looks strong, patch latency doesn't move.** An org reaches 85% golden-base adoption, but patch latency for a recent CVE still took three weeks to reach most of the fleet, because the rebuild-notification step was a wiki-page instruction rather than an automated PR; the next quarter's investment shifts from adoption outreach to automating the rebuild trigger.

## Common Mistakes

- **Centralizing Dockerfile review in one platform team.** That team cannot sustain reviewing every service's application-specific build logic, and the review queue becomes the actual bottleneck to shipping.
- **Mandating full migration before piloting.** Skipping the pilot means the golden image's structure is guessed at rather than derived from a real service's actual needs, and gets painfully revised after wide adoption instead of cheaply after one team's experience.
- **Turning a scanning gate blocking for the entire existing fleet at once.** Breaks many teams' deploys simultaneously over vulnerabilities that predate the policy; gate new builds first, remediate the existing fleet on a scheduled window.
- **Measuring only adoption percentage, never patch latency.** High adoption with slow patch rollout looks like program success on a dashboard while delivering little of the actual security benefit the program exists for.
- **Publishing golden images with no support-window contract.** Consuming teams build on an image version with no idea when it stops being patched, and are surprised by a deprecation instead of planning for it.
- **Leaving the patch-to-production step manual.** Without an automated rebuild trigger, a patched golden image sits available but unused while the vulnerable version keeps running in production.

---

## Apply it

1. Inventory the base images currently in use across a set of services you have visibility into, and identify which are on an end-of-life or otherwise unsupported version.
2. Design a golden base image for the runtime most commonly used across those services, and pilot it on the one service whose current base image scored worst in the inventory.
3. Define the outcome measures you'd track for this program, starting with `patch_latency` scoped to this one golden image and its known consumers, and write the concrete exit condition that would justify expanding beyond the pilot.
4. Draft a one-page support contract for the golden image: current version, deprecation timeline for the version it replaces, and who consuming teams contact about a breaking change.
5. Design the automated rebuild-notification mechanism (a bot-opened PR, a CI check, or equivalent) that would close the gap between "the platform team patched the golden image" and "the fix is actually running in production," rather than relying on teams remembering to rebuild.

## Verify your work

- The inventory names specific services on end-of-life bases, not a general impression that "some services are probably outdated."
- The pilot's golden image measurably improves at least one concrete metric (image size, open CVE count) for the pilot service, with a before/after number, not just adoption.
- The outcome measure is specific and falsifiable (a rate or duration with a clear numerator and denominator), not a vague statement like "more secure images."
- The support contract states an actual deprecation date or trigger for the previous version, not an open-ended "eventually."
- The rebuild-notification mechanism is automated enough that a patched golden image reaching production does not depend on every consuming team independently remembering to act.

## Review questions

- Why does centralizing every team's Dockerfile review in one platform team tend to fail as the number of teams grows?
- What does a slow patch latency reveal about a golden-image program that high adoption alone does not?
- Why can turning a vulnerability-scanning gate blocking for the entire existing fleet at once cause more harm than gating only new builds first?
- What turns a golden base image's support window into something a consuming team can actually plan against, rather than a surprise deprecation?
