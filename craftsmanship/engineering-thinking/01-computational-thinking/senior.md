# Computational Thinking — Senior

**Your question:** How do I decompose a system so that teams can evolve it independently without hidden dependencies?

Senior decomposition works at **system boundaries**—where independent teams, databases, and operational changes collide. The risk is not just poor code; it's coordinated failures, migration bottlenecks, and locked teams.

## Decompose along system change boundaries

Not all boundaries are equal. Choose boundaries that allow independent evolution:

**Business capability:** PaymentGateway changes when payment rules change (your team owns it)  
**Data ownership:** Orders are authoritative in OrderDB, not replicated in NotificationDB  
**Consistency requirement:** Billing must be strongly consistent; notifications can be eventually consistent  
**Operational failure:** If payment service is down, orders can still be placed (graceful degradation)  
**Team ownership:** Checkout team doesn't need to ask InvoiceTeam for permission to add fields  

**Anti-pattern:** A service that shares database and deployment pipeline with its neighbor. It adds network failure without gaining independence.

### How to identify true boundaries

1. **Trace a failure scenario:** If PaymentService fails, what else fails?
   - If NotificationService also goes down → too coupled
   - If NotificationService queues and retries → proper boundary
   - If OrderDB is unavailable, can you take orders? (Should you?)

2. **Check data ownership:** Who owns the “truth” about this data?
   - Order created in OrderService, replicated to NotificationService (NOT the other way)
   - If NotificationService crashes, can you rebuild its state from OrderService? (Yes = good boundary)

3. **Measure coordination cost:** Do two teams need to sync on deployment?
   - If PaymentService deploys, does CheckoutService need to deploy first? (Bad coordination)
   - If OrderDB schema changes, how many services must change code? (Count > 1 = consider boundary)

## Prefer vertical slices over horizontal rollout

Bad plan: Database layer this quarter → API layer next quarter → UI next quarter  
- Late feedback (UI team discovers API is unsuitable)
- Risk concentrates (three separate rollouts, each a single point of failure)
- Teams idle (UI team waits for API layer)

Good plan: Thin path through all layers every iteration  
- Immediate feedback (team sees real end-to-end behavior)
- Risk spreads (many small rollouts, easier to recover from each)
- Parallel work (all teams move each iteration)

### Vertical slice roadmap example

**Feature:** Add image filters to profile picture

- **Slice 1:** API + UI for applying grayscale filter (behind feature flag)
  - API: `POST /profile/image/filter` → applies filter, stores in temp location
  - UI: Button “Preview as grayscale” (doesn't persist)
  - Database: No schema change yet
  - Verification: E2E test with mock filter engine

- **Slice 2:** Persist filter choice, add storage
  - Database: Add profile_image_filter column
  - API: Persist choice, serve filtered image from storage
  - Verification: Image loads with correct filter after page reload

- **Slice 3:** Add revert button (restore previous version)
  - Database: Keep historical versions
  - API: New endpoint for version history and revert
  - Verification: Revert works, old version displayed

- **Slice 4:** Rollout to 100%, retire feature flag
  - Remove flag code
  - Clean up temporary storage
  - Monitor for issues

**Why this works:**
- Each slice is independently releasable
- Failure in slice 1 doesn't block slice 2 (can roll back just slice 1)
- Real users see and use the feature after slice 1 (immediate feedback)

## Preserve invariants during migration

When replacing old system with new: write down what **must** remain true for users and operations.

**Invariants for image filter migration:**
- User's current profile image never shows broken/corrupted
- No images lost (even if migration fails mid-way)
- Users can always roll back within 30 days
- API response format never changes (old clients must work)

### Migration pattern: expand-and-contract

1. **Expand:** New system co-exists with old system
   - Write to both databases (new + old)
   - Read from old system (ignore new system's data)
   - Database: Add new columns without removing old ones
   - Verification: New system data matches old system data

2. **Contract:** Gradually shift traffic to new system
   - Read from new system (with fallback to old if new fails)
   - Phase 1: 1% of traffic on new system
   - Phase 2: 10% of traffic on new system
   - Phase 3: 100% of traffic on new system

3. **Retire:** Remove old system
   - Stop writing to old database
   - Delete old code
   - Confirmation: No rollback needed in past 7 days

**Dual writes:** Only if you can verify they match. Otherwise, single write + replication is safer.

### Establish rollback points

Every temporary component needs:
- **Owner:** Who removes it after migration?
- **Removal condition:** “After 30 days in production with zero rollbacks”
- **Cleanup effort:** One command or one hour of work?

Example: Feature flag for new image filter
- Owner: Mobile team
- Removal condition: 30 days with zero rollbacks + zero errors
- Cleanup: Remove `if (FEATURE_FLAG_IMAGE_FILTERS)` and one config line

## Avoid abstraction failure patterns

Watch for these signs that a boundary is becoming load-bearing for the wrong reasons:

| Pattern | Why it fails | Fix |
|---|---|---|
| **Dependency magnet** — all teams import shared library | Shared library becomes slow to change; every change requires N approvals | Establish clear service levels (SLA, deprecation policy); split into smaller, focused libraries |
| **Shared model with unrelated consumers** — Order model used by Checkout, Invoicing, Analytics | Order schema change requires coordinating three teams; schema accumulates irrelevant fields | Each service owns its own schema; API provides translation layer |
| **Interface mirrors single implementation** — `PaymentGateway { chargeWithStripe() }` | Can't swap to PayPal without changing interface; couples caller to Stripe | Interface describes **capability** (“charge(amount)”), not implementation |
| **”Platform” package without service levels** — shared utils used everywhere | No one knows what's safe to change; breaking changes affect unknown consumers | Define: what's the contract? What can change? When do you deprecate? |

## Establish decision points and verify before committing

Before decomposing, ask:

1. **What business change would require changing this boundary?**
   - PaymentGateway boundary: “Switch payment providers, add recurring billing”
   - UserProfile boundary: “Change authentication provider, add avatar uploads”
   - If you can't name a plausible business change, the boundary may be premature.

2. **How would a team swap this implementation?**
   - “Stripe → PayPal” should require changing one file (adapter)
   - “PostgreSQL → MongoDB” should require changing one data layer
   - If it requires >3 changes, the seam is leaking.

3. **Can we safely migrate one entity at a time?**
   - “Migrate one user's data to new schema” should work (not “all users or none”)
   - If migration is all-or-nothing, it's risky.

4. **What happens if this boundary fails?**
   - PaymentGateway down → take orders, queue payments (acceptable)
   - OrderDB down → system is broken (acceptable; single point of truth)
   - NotificationDB down → errors are buffered/retried (acceptable; notifications are not critical path)

## Document decomposition decisions

For each boundary, record:

**Context:** Why does this boundary exist? (Business reason, team reason, operational reason)  
**Constraints:** What must remain true across the boundary? (Consistency, latency, ordering)  
**Current state:** What's on each side today?  
**Failure modes:** What breaks if this boundary is wrong?  
**Reversibility:** How hard is it to undo this decomposition?  
**Observability:** How do we verify the boundary is working? (Metrics, traces, alerts)  

**Example:**
```
Boundary: PaymentService ←→ OrderService

Context: Two teams (Payment, Checkout) need independent deployment schedules.
Constraints: Order is immutable after creation; payment can retry indefinitely.
Current: Tightly coupled in monolith; one deploy cycle.
Failure modes: If Payment breaks, Checkout is also unavailable (bad).
Reversibility: Merge payment logic back into Order service (2 days work).
Observability: Track order-to-payment latency; alert if >5 min backlog.
```

## Hands-on exercise

Take a major feature currently in your system.

1. Draw current architecture: What systems own what data?
2. Trace one failure scenario: If system A goes down, what fails?
3. Propose a vertical slice (first 2 weeks of work):
   - What user-visible behavior ships after 2 weeks?
   - What systems must be modified?
   - What stays behind a feature flag?
4. Write one invariant that must hold throughout migration.
5. Describe the rollback plan if something goes wrong.

If you can't answer #4, the boundary is unclear.

## Verify your thinking

- [ ] Can you name a business reason for each boundary?
- [ ] If this service fails, does the rest of the system degrade gracefully?
- [ ] Can a new team member understand what this boundary protects?
- [ ] How many deployment orders are enforced by this boundary? (Should be ≤ 1)
- [ ] Can you migrate 1% of traffic to a new implementation without a full rollout?

Continue to [`professional.md`](professional.md).
