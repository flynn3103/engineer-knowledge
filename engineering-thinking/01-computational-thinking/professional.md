# Computational Thinking — Professional

**Your question:** How do I decompose a system so the organization can scale—adding teams, features, and operational changes without coordinated rollouts?

Professional decomposition aligns **architecture, ownership, and operational reality**. A boundary that’s technically sound but has no clear owner becomes a coordination bottleneck. A system optimized for elegant code but owned by five teams becomes expensive to change.

## Align architecture and ownership (Conway’s law)

The structure of your system reflects the structure of your organization.

**Principle:** Communication paths should match data flow and ownership.

### Bad alignment
```
Architecture: OrderService → PaymentService → BillingService
Ownership: OneTeam owns all three services

Cost: OnTeam is a bottleneck; can’t deploy independently; on-call for everything
```

### Good alignment
```
Architecture: OrderService (Checkout team) → PaymentGateway (Payment team)
              OrderService (Checkout team) → InvoiceService (Finance team)

Ownership: Checkout team owns OrderService; Payment team owns PaymentGateway
Cost: Each team owns their domain; can deploy independently; clear on-call responsibility
```

### How to evaluate proposed boundaries

For each proposed service or capability:

1. **Who owns it?** (Must be one team; shared ownership = coordination debt)
2. **Who calls it?** (Identify all consumers; more consumers = higher change cost)
3. **Can one team deploy it?** (If PaymentTeam deploys, does CheckoutTeam need to deploy first? If yes: bad boundary)
4. **Who has on-call responsibility?** (If unclear, the boundary is too ambiguous)
5. **What data does it own?** (Other services can read this data but not write it; if multiple services write, merge them)

**Example:** Should we extract an “Discount Engine” as a separate service?

| Question | Answer | Implication |
|---|---|---|
| Who owns it? | Finance team (discount rules, compliance) | ✓ Clear owner |
| Who calls it? | Checkout, Subscriptions, Orders | Many consumers; higher coordination cost |
| Can Checkout deploy alone? | No; Discount changes are managed by Finance | Checkout depends on Finance team’s deployment schedule |
| On-call responsibility? | Finance team owns correctness; Checkout owns integration | ✓ Clear boundaries |
| Data ownership? | Finance writes discount rules; Checkout reads them | ✓ Single source of truth |

**Decision:** Extract only if Finance team will actively evolve discount logic independently. Otherwise, keep embedded in Checkout for now.

## Manage cognitive load per team

A team’s cognitive load is how much they need to understand and remember.

**High cognitive load:**
- Team owns OrderService, PaymentIntegration, BillingEngine, ShippingService (unrelated domains)
- Team must coordinate with Payment, Finance, Logistics teams on every change
- Team on-call for 6 different failure scenarios
- Result: slow deployments, more bugs, team burnout

**Low cognitive load:**
- Team owns OrderService (clear domain boundary)
- OrderService has well-defined interfaces to Payment, Finance, Shipping services
- Team is on-call only for OrderService failures
- Team can deploy independently; other teams evolve their services
- Result: fast deployments, higher quality, sustainable pace

### Design platform capabilities to reduce repeated work

Platform teams (infrastructure, tooling, shared services) reduce cognitive load by providing “paved roads”:

**Platform provides:**
- Deployment pipeline (teams use it, don’t build it)
- Observability stack (teams write logs/metrics, don’t build dashboards)
- Authentication (teams use it, don’t build identity systems)
- Database access patterns (teams use prepared templates, not raw SQL)

**Escape hatches:** Teams can build custom solutions for justified reasons, but default is the paved road.

**Bad approach:** Platform builds “one size fits all” → no escape hatches → teams blocked when they need exceptions  
**Good approach:** Platform provides standard 80% solution + clear process for the other 20%

## Design evolutionary seams for staged migration

When replacing a system, use **staged migrations** to reduce risk and maintain optionality.

### Five migration patterns

**Pattern 1: Branch by abstraction**
- New code path hidden behind feature flag
- Both old and new paths run in production
- Switch traffic gradually: 1% → 10% → 100%
- Exit criteria: No errors for 7 days, feature flag removal scheduled

**Pattern 2: Strangler fig pattern**
- New service intercepts requests at the boundary
- Old service still handles request if new service fails
- Gradually increase traffic to new service
- Old service gracefully deprecated
- Exit criteria: No traffic to old service for 30 days

**Pattern 3: Dual writes with verification**
- Write to both old and new systems
- Read from old system only
- Compare results to ensure new system is correct
- Only after verification: switch reads to new system
- Exit criteria: New system data matches old system for 14 days

**Pattern 4: Schema expand and contract**
- Add new columns; don’t remove old ones
- Update application to read from new columns (with fallback to old)
- After verification period: remove old columns
- Exit criteria: No code reading old columns for 30 days

**Pattern 5: Canary deployment**
- Deploy to 1 instance serving real traffic
- Monitor metrics: errors, latency, resource usage
- If healthy after 1 hour: deploy to 10% of instances
- If healthy after 4 hours: deploy to 100%
- Rollback: instant revert to previous version
- Exit criteria: All instances running new version with zero rollbacks

### Establish measurable exit criteria

Every migration stage needs:
- **What we’re watching:** Error rate, latency, data consistency, traffic percentage
- **When we’re done:** “Zero errors for 7 days” or “100% traffic routed”
- **If we fail:** Automatic rollback or escalation rule
- **Who decides:** Explicit owner for go/no-go decision

**Example migration stage:**
```
Stage: Canary deployment to 5% traffic

Watch:
  - Error rate (target: ≤ 0.1% — same as old system)
  - P99 latency (target: ≤ 200ms — same as old system)
  - Memory usage (target: ≤ 2GB per instance)

Done when:
  - Metrics stable for 4 hours
  - No alerts triggered
  - New system processed ≥ 100k requests

Fail if:
  - Error rate > 1%
  - P99 latency > 500ms
  - Memory leak detected
  - → Automatic rollback

Owner: Payment service team
```

## Operability framework: Ask before building

Before committing to a decomposition, answer these questions:

1. **Ownership clarity**
   - Who owns the invariant when two services disagree? (e.g., Order says “paid”, Payment says “failed”)
   - Who can make fast decisions without waiting for other teams?

2. **Deployment independence**
   - Can the OrderService team deploy without PaymentService team deploying first?
   - If no: the boundary doesn’t provide independence

3. **Failure isolation**
   - If PaymentService is down for 2 hours, what else fails?
   - Is that acceptable? (e.g., orders queue up = acceptable; cannot show order confirmation = bad)

4. **Observability**
   - What metric shows if this boundary is causing problems? (latency, queue depth, coordination cost)
   - How would we know it’s time to merge these services back?

5. **Scalability at the boundary**
   - At 10× current load, what fails first?
   - (e.g., rate limits, timeouts, queue overflow → is this acceptable or do we need redesign?)

6. **Temporary work removal**
   - Which migration tools (feature flags, compatibility layers) are temporary?
   - When will they be removed? Who owns removal?
   - If not removed in 6 months, escalate as technical debt

## Delivery method: Reversible increments

**Antipattern:** Big bang decomposition—redesign everything, then deploy
- Risk: One wrong assumption breaks the entire system
- Recovery: Revert everything (days of work, lots of data to reconcile)

**Pattern:** Reversible increments—each change can be undone independently
- Slice 1: Deploy new service; route 1% traffic; keep old service as fallback
  - Revert: Delete new service, resume 100% traffic to old service (1 minute)
- Slice 2: Route 10% traffic; monitor
  - Revert: Same as Slice 1
- Slice 3: Route 100% traffic; old service still running
  - Revert: Same as Slice 1
- Slice 4: Delete old service code (only after weeks of zero errors)
  - No revert needed; if something breaks weeks later, it’s not related to this deletion

**Recovery time for reversible increments:** ≤ 5 minutes  
**Recovery time for big bang:** 4+ hours + data reconciliation

## Staff-level decomposition checklist

### Phase 1: Frame the problem
- [ ] Write the business problem in one sentence
- [ ] List non-negotiable invariants (what must never break)
- [ ] Identify constraints (team size, deployment frequency, compliance)
- [ ] Identify current pain points (slow deployments, frequent conflicts, high on-call load)

### Phase 2: Map the boundaries
- [ ] Draw current architecture: What owns what data?
- [ ] Identify failure scenarios: If X goes down, what fails?
- [ ] Identify ownership: Who makes decisions about each component?
- [ ] Measure coordination cost: How many deployments require coordination?

### Phase 3: Evaluate options
- [ ] Option A: Keep monolith, improve internal separation
  - Cost: Coordination remains high; but no network failure
  - Benefit: Simpler operational model
- [ ] Option B: Extract one service
  - Cost: Network failure, eventual consistency
  - Benefit: One team can move faster; other teams blocked
- [ ] Option C: Extract two services + clear contracts
  - Cost: Higher complexity; two teams move independently
  - Benefit: Both teams unblocked; clearer ownership

### Phase 4: Plan reversible delivery
- [ ] Define vertical slices (each 2-4 weeks of work)
- [ ] For each slice: what’s the exit criteria? What’s the rollback plan?
- [ ] Assign owner for each slice’s go/no-go decision
- [ ] Plan temporary infrastructure (feature flags, compatibility layers) with removal date

### Phase 5: Instrument and measure
- [ ] Operational metrics: error rate, latency, resource usage
- [ ] Correctness metrics: data consistency, invariant violations
- [ ] Coordination metrics: number of teams involved in deployments
- [ ] Team metrics: deployment frequency, on-call page count

### Phase 6: Expand based on evidence
- [ ] Continue only if metrics are healthy (errors ≤ SLA, no invariant violations)
- [ ] If metrics are bad: pause, investigate, fix (do not proceed to higher traffic)
- [ ] Track temporary components: when does removal happen?

## Anti-patterns to avoid

| Anti-pattern | Consequence | Prevention |
|---|---|---|
| **Shared ownership** — Two teams own same service | Slow decisions; conflict on deployments | One team owns; others use well-defined interface |
| **Tight coupling** — Service A changes require Service B code change | High coordination cost; deployments must sync | Use versioned APIs; backward-compatible contracts |
| **No exit criteria** — Experimental feature lives forever | Technical debt accumulates; confusion about “permanent” vs “temporary” | Explicit owner and removal date for every experiment |
| **Over-instrumentation** — Metrics everywhere but no one knows what to do with them | Alert fatigue; false positives ignored | Keep 5 critical metrics; define action for each alert |
| **Premature optimization** — Extract service before problem is clear | Unnecessary complexity; coordination cost without benefit | Wait for evidence (deployment conflicts, on-call load) |

## Hands-on exercise

Take one significant technical initiative planned for your team.

1. **Frame:** What business problem does this solve? What invariants must hold?
2. **Map:** Draw current state and proposed new state. Who owns each piece?
3. **Evaluate:** For the proposed design, answer operability questions:
   - Can one team deploy independently?
   - If one service fails, what fails? Is that acceptable?
   - What metric shows if this boundary is causing coordination cost?
4. **Design reversibility:** Sketch a 3-slice migration plan with exit criteria for each slice.
5. **Measure:** Name 5 metrics you’d watch during rollout. What’s the threshold for rollback?

If you can’t clearly answer #3 and #4, the design is incomplete.

## Verify your thinking

- [ ] Is there exactly one team accountable for this boundary?
- [ ] Can the owner deploy and recover without asking other teams?
- [ ] If this service fails, is the rest of the system acceptable?
- [ ] Have we named and scheduled removal for temporary migration components?
- [ ] Can we roll back this change in under 5 minutes?
- [ ] Did we identify the evidence that justified this decomposition?
