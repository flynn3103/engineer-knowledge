# Computational Thinking — Middle

**Your question:** How do I design clean boundaries so changes stay local and teams can work independently?

Junior level teaches you to break features into outcomes. At middle level, you're grouping outcomes into **capabilities**—cohesive modules that hide implementation and expose stable interfaces.

## Move from technical layers to business capabilities

Junior: Separate concerns (validation, storage, database)  
Middle: Group concerns that **change together** for business reasons

**Wrong approach (layered):**
```
UserController → UserService → UserRepository
ImageStore → ImageService → ImageRepository
```
Change in image upload logic touches 3 files in 3 layers. Change in billing logic touches different files in the same layers. Each layer mixes unrelated concerns.

**Better approach (capability-based):**
```
UserProfile capability: handles avatar upload, resize, validation, storage location decision
BillingEngine capability: handles invoice generation, payment retry logic, receipt storage
```
Each capability owns decisions end-to-end. One business change = one capability change.

### How to identify capability boundaries

1. **Trace a business rule.** “Users can upload only within first 7 days” appears in validation, UI, and API checks. These belong together.
2. **List what changes together.** If image resizing rules change, do billing rules change? No → separate capabilities.
3. **Name after business role, not technology.** “User avatar service” ✓ vs. “file storage layer” ✗
4. **Check coupling direction.** Billing shouldn't import from UserProfile; UserProfile shouldn't import from Billing.

### Define seams: where behavior can vary

A **seam** is a boundary where you can swap behavior without changing surrounding code. Good seams make testing easier and allow independent evolution.

**Seam examples:**
- Interface: `PaymentGateway { charge(amount) -> TransactionID }`
- Function signature: `resizeImage(bytes, targetWidth) -> bytes`
- Database contract: “images table has columns: id, user_id, url, created_at”
- API contract: “GET /user/profile returns { avatar_url, display_name, ... }”

**Not a seam:** coupling that can't be swapped
- “UserProfile imports Stripe SDK directly” (tightly coupled to Stripe)
- “Checkout stores orders in a global static variable” (untestable)

### How to apply it: design a capability

**Scenario:** Add a feature where users can set image filters (grayscale, blur, etc.). Images need reprocessing without re-uploading.

**Steps:**

1. **Write the invariant:** “A user's profile image has one current filter setting; historical versions are retained for 30 days.”

2. **List what changes together:**
   - Filter selection (grayscale, blur, sepia)
   - Image reprocessing logic
   - Storage location for variants
   - UI for filter preview
   - Database schema (add filter column)

3. **Define the smallest stable interface:**
   ```
   ProfileImageProcessor:
     - apply_filter(image_id, filter_name) -> result
     - list_filters() -> [names]
     - revert_to_version(image_id, version_date) -> result
   ```

4. **Mark boundaries where external systems attach:**
   - API endpoint: `POST /profile/image/filter` (external input)
   - Image storage port: `ImageStore { save(), delete(), fetch() }` (interchangeable: local disk or S3)
   - Background job: trigger reprocessing (can use queue or cron)

5. **Test the abstraction:**
   - Mock ImageStore → verify filter logic is tested without S3 calls
   - Mock background job → verify API responds immediately
   - Integration test: end-to-end with real storage

## Generalize from evidence, not intuition

You see duplicate code in two places. Resist the urge to create a generic helper immediately.

**Rule of three:** Wait until you've seen the pattern three times **and** understand what's truly invariant.

**Examine each occurrence:**
- Occurrence 1: Validate user email before sending confirmation
- Occurrence 2: Validate recipient email before forwarding message
- Occurrence 3: Validate support contact email before creating ticket

**Analyze:**
- Invariant: SMTP RFC 5321 syntax check
- Variation: where the email is used (confirmation, forwarding, support ticket)

**Generalize:** Extract `Email.is_valid(string) -> bool`, keep in shared utility  
**Don't generalize:** Combine into `NotificationHelper.validate_and_send()` (mixes validation and side effects)

If two paths **look** similar but obey different business rules, duplication is safer:
- Path A: “Resellers get 20% discount, applied after tax”
- Path B: “Premium users get 15% discount, applied before tax”
- Temptation: Create `applyDiscount(amount, rate, timing)`
- Reality: When rules diverge (next quarter: corporate accounts get stacked discounts), the generic helper becomes a maze of conditionals.

## Reason about performance at multiple scales

Junior: “Does it work?” Middle: “Does it work at our scale?”

For a given algorithm, name:
- Input size: “1,000 users” or “1M transactions”
- Dominant operation: “database query per request” or “loop through all items”
- Performance requirements: “<100ms response” or “<1GB memory”

**Example:** Checkout loads all orders to compute “frequently bought together”
- At 1,000 orders: scan-all-orders = 5ms ✓
- At 1,000,000 orders: scan-all-orders = 5s ✗
- Solution: pre-computed cache or limited window (last 10k orders)

**Consider beyond Big-O:**
- Time: how long the operation takes
- Memory: peak allocation during operation
- I/O: database queries, disk reads, network round-trips
- Concurrency: can two requests run simultaneously? Do they lock the same resource?
- Failure: if a slow operation times out, can it retry? Does retry make it worse?

## Verification: end-to-end test + unit test

- **Unit test:** Capability works with mocked dependencies (fast, isolated)
- **Integration test:** Capability works with real collaborators (slow, reveals real failure modes)
- **Verification questions:**
  - Can I test the capability in isolation?
  - What inputs cause this capability to fail? (Try to write one failing test; if you can't think of one, you haven't explored boundaries)
  - If a dependent system is slow/unavailable, does this capability degrade gracefully?

## Common mistakes at middle level

| Mistake | Fix |
|---|---|
| Create a capability too early (saw two uses, not three) | Accept duplication; refactor once the pattern stabilizes |
| Make an interface too generic (“process(data) -> data”) | Add specificity: is it validation, transformation, or persistence? Name accordingly |
| Expose implementation details (return list of internal objects) | Wrap in a domain type; only return what the caller should know |
| Create a shared capability that multiple teams depend on without agreement | Establish explicit contracts; add versioning and deprecation plan |

## Hands-on exercise

Pick a feature you recently shipped. Draw it:
1. What capability contains the core logic? (name it)
2. What external systems does it depend on? (draw the seams)
3. Could you test the capability without touching those external systems?
4. If you needed to swap storage from PostgreSQL to MongoDB, how many files would change?

If the answer to #4 is >3 files, your seams are leaking abstraction.

## Verify your thinking

- [ ] Can you name the invariant that justifies this capability boundary?
- [ ] Does this capability have exactly one reason to change?
- [ ] Could you test this capability with a fake database?
- [ ] If an external system fails, does this capability degrade gracefully or crash?
- [ ] Is the interface small enough that someone could implement a second version?

Continue to [`senior.md`](senior.md).
