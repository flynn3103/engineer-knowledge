# Tools and MCP — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run tool and MCP infrastructure as a durable, org-wide operating model — a shared tool registry, a real security review process for new tools, and versioning/deprecation for schemas agents depend on — so every team gets vetted, discoverable capabilities without a central team reviewing every tool by hand?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The same organizational failure pattern shows up here as with container base images and agent scaffolding: a central platform or security team trying to personally review every tool every team wants to build or connect to becomes a bottleneck the moment tool count grows past what a handful of people can track. The split that scales:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared tool/MCP registry infrastructure** | Platform team | Runs the catalog, its discovery mechanism, and its versioning tooling, so teams find and depend on tools through one system instead of ad hoc lists |
| **Security review process and checklist** | Security engineering | Owns what counts as a passing review for a new tool, and evolves the checklist as new attack patterns (like prompt injection via tool output) are understood |
| **Individual tool implementations and schemas** | The product team that owns the underlying capability | Builds and maintains their own tools within the reviewed security boundary, because they understand their own domain's specific needs |
| **Program health and enforcement** | A governance group spanning platform and security | Tracks registry adoption, review backlog, and incident trends; escalates when a tool has no active owner or a review has gone stale |

## Core Concept 2 — A Shared Tool Registry as a Paved Road

A **tool registry** is a central, searchable catalog of every tool and MCP server approved for use across the org, each entry carrying: its owner, its declared scope (what it can actually do, per the least-privilege design from the senior guide), its current security-review status and date, and its version. The registry exists so a team building a new agent chooses from a vetted set instead of independently deciding, team by team, whether to trust some third-party MCP server they found — the same leverage a golden base image gives a container fleet, or a shared agent scaffold gives loop safety: solve the vetting problem once, centrally, instead of once per team.

```yaml
# Example registry entry
tool: get_order_status
owner: billing-platform-team
scope: "read-only, single order lookup by ID, scoped to requesting customer's own orders"
security_review: passed, 2026-06-02
version: 2.1.0
transport: mcp (stdio, internal)
```

A registry only functions as a paved road if using it is genuinely easier than not — fast to search, with a working connection example, and current enough that teams trust its review status rather than re-verifying independently every time.

## Core Concept 3 — The Security Review Process

Every new tool entering the registry passes a defined, risk-scaled review before it's listed as approved — not a uniform months-long process for every tool regardless of risk:

```yaml
review_checklist:
  scope_declared_and_minimized: "Does the tool's credential match the narrowest scope that does its job, per least-privilege design?"
  input_validation_present: "Are authorization checks separate from shape checks, and actually enforced in code?"
  output_handling_verified: "Is the tool's result treated strictly as data when re-injected into agent context, with no elevated trust?"
  blast_radius_capped: "Is there an enforced maximum (amount, rate, record count) per call, independent of any prompt instruction?"
  audit_logging_wired: "Does every call produce a log entry sufficient to reconstruct what happened later?"
fast_track: "read-only tools with no write capability and no sensitive data exposure"
full_review: "any tool that writes, deletes, sends externally, or moves money"
```

This ties directly to the risk tiers from the [professional agentic-techniques guide](../agentic-techniques/professional.md) — a Tier 1 read-only tool gets the fast track; a Tier 3/4 tool gets full review, and its registry entry should record which tier it's classified at so downstream teams building agents around it know what technique (gating, audit depth) is mandatory when they use it.

## Core Concept 4 — Versioning and Deprecation as a Contract

A tool's schema is a contract other teams' agents depend on, exactly the way a golden container base image or a shared library is — and it needs the same discipline. A breaking change to a tool's parameters (renaming a field, changing what a return value means, tightening validation in a way that now rejects previously-valid calls) is a breaking change for every agent built against the old schema, even though nothing "crashes" the way a compiler error would — an agent calling the old schema against the new tool can produce malformed calls or subtly wrong behavior that goes unnoticed far longer than a build failure would.

- Every registry entry publishes a version and a support window — current version, deprecated-but-still-working versions, and the date a version stops being served.
- Consuming teams build against a specific version, not an unpinned "latest," so a schema change doesn't silently change their agent's behavior underneath them.
- A breaking schema change goes through advance notice to known consumers (the registry's ownership metadata is what makes "known consumers" answerable at all) before the old version's support window closes.
- Deprecating a tool version without a migration path for its consumers reproduces the same "surprise breakage" failure the infrastructure domain's golden-base-image contract exists to prevent.

## Core Concept 5 — Rollout Decomposition

Standing up a registry and review process across an org with many existing, independently-built tools follows the same reversible-increments pattern as any infrastructure program:

1. **Pilot with one team's existing tool set**, ideally one that includes at least one write-capable, higher-risk tool, so the review checklist gets tested against a real, non-trivial case immediately.
2. **Extract the registry's actual required fields from what the pilot needed** — don't design the schema by committee before any real tool has gone through it.
3. **Publish the security checklist as advisory first**, surfacing how many existing tools in the fleet would fail it today, without blocking anyone's current work.
4. **Turn the checklist blocking for newly registered tools only**, with existing unreviewed tools getting a scheduled remediation window rather than an overnight deregistration.
5. **Expand team by team**, tracking registry coverage as a fraction of production tools registered and reviewed, not a binary adopted/not-adopted state.

## Core Concept 6 — Outcome Measures and Exit Conditions

```yaml
program_health:
  registry_coverage: "production tools listed in the registry / total production tools"
  review_currency: "tools with a security review less than N months old / total registered tools"
  review_turnaround_time: "median days from submission to a pass/fail review decision"
  schema_breakage_incidents: "incidents caused by an unannounced or unversioned tool schema change, per quarter"
exit_conditions:
  pilot_to_expansion: "pilot team's tools pass review, the registry entry is complete and current, and the platform team can update registry tooling without the pilot team's direct involvement"
  program_maturity: "registry_coverage > 90%, and schema_breakage_incidents trending toward zero for two consecutive quarters"
```

`schema_breakage_incidents` is the number that proves versioning discipline is actually working, not just documented — high registry coverage with breakage incidents still happening means teams are registering tools but not respecting the version-and-notice contract when they change them.

## Core Concept 7 — Cross-Team Contracts and Sustained Delivery

- Every registered tool's owner is accountable for its support window and advance notice on breaking changes, the same accountability model as the infrastructure domain's golden-base-image contract — if a breaking change reaches a consuming agent without notice, that's the owning team's action item; if a consuming team ignored a deprecation notice and never migrated, that's theirs.
- New tools register by default as part of shipping them, not as a retrospective compliance exercise triggered by an incident.
- A recurring program review (quarterly) checks whether review turnaround time and schema-breakage incidents are actually improving, and if not, whether the bottleneck is review capacity, registry tooling, or teams routing around the registry entirely by connecting to unregistered third-party servers directly.
- The registry's own security-review checklist gets revisited whenever a new attack pattern against tools or MCP servers becomes understood — the checklist from Core Concept 3 is a snapshot of current knowledge, not a permanent, complete list.

---

## Real-World Examples

- **A pilot's write-capable tool stress-tests the review checklist for real.** A team's existing refund tool, run through the review process for the first time, surfaces a gap the checklist hadn't caught — an amount cap enforced in the prompt but not in code — giving the security team a concrete fix to require before the tool is listed, rather than a hypothetical concern raised in the abstract.
- **An unversioned schema change breaks a consuming agent silently.** A team renames a field in their tool's response format without a version bump; a consuming agent built against the old field name keeps running but silently stops using the renamed data, producing subtly wrong answers for weeks before anyone traces it back to the schema change. The fix is enforcing version bumps as a registry requirement, not optional practice.
- **Registry coverage looks strong, breakage incidents don't drop.** An org reaches 92% registry coverage, but schema-breakage incidents haven't declined, because teams register tools once and then edit them in place without going through the version-and-notice process the registry was supposed to enforce. The next quarter's investment shifts from coverage outreach to actually gating in-place schema edits at the registry tooling level.

## Common Mistakes

- **Centralizing every tool's review in one team regardless of risk.** A uniform full review for every tool, including trivial read-only ones, makes the review queue the bottleneck and slows down exactly the low-risk work that didn't need deep scrutiny.
- **Treating registry coverage as sufficient evidence the program is working.** High coverage says tools are listed; it says nothing about whether their schemas are being changed safely, which is what `schema_breakage_incidents` actually measures.
- **Publishing tools with no version or support window.** Consuming teams build against a moving target with no way to know when a breaking change is coming.
- **Rolling the checklist out as blocking for the entire existing fleet at once.** Forces a scramble to re-review every existing tool simultaneously; gate new registrations first, review the backlog on a scheduled cadence.
- **Letting teams bypass the registry by connecting directly to unreviewed third-party MCP servers.** A registry with strong coverage numbers doesn't prevent risk if teams route around it for convenience — this needs to be tracked and closed as its own gap, not assumed away.

---

## Apply It

1. Inventory the tools and MCP servers currently in use across a set of agents you have visibility into, and identify which are unregistered, unreviewed, or unversioned.
2. Run the security review checklist from Core Concept 3 against one existing write-capable tool, and identify which items it would fail today.
3. Define the outcome measures from Core Concept 6 for your org specifically, and write the concrete exit condition that would justify expanding the registry beyond a pilot team.
4. Draft a one-page support contract for one tool: current version, deprecation timeline for the version it replaces, and who consuming teams contact about a breaking change.
5. Design a mechanism that would actually detect a team bypassing the registry by connecting directly to an unreviewed external MCP server, rather than assuming registry coverage alone captures real usage.

## Verify Your Work

- The inventory names specific unregistered or unreviewed tools, not a general impression that "some tools are probably not reviewed."
- The retroactive checklist run against a real tool identifies concrete, specific gaps, not a hypothetical exercise.
- The outcome measure is falsifiable — a rate or count with a clear numerator and denominator — not a vague "tools are more secure now."
- The support contract states an actual deprecation date or trigger, not an open-ended "eventually."
- The bypass-detection mechanism would actually catch a deliberately introduced unregistered connection in a test, not just in theory.

## Review Questions

- Why does reviewing every tool with the same full-depth process, regardless of risk, tend to create a bottleneck as tool count grows?
- What does `schema_breakage_incidents` reveal about a registry program that `registry_coverage` alone cannot?
- Why is a tool's schema a contract in the same sense as an internal API, and what breaks when that contract has no version or deprecation window?
- Why can a program with strong registry coverage numbers still have real, uncaptured risk from unregistered tool usage?
- What's the practical difference between a fast-track and a full security review, and what determines which a given tool gets?
