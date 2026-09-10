# Functional Requirements — Professional

Align requirements with delivery. Requirements are not a static specification; they are a contract between product, engineering, and business. Decompose requirements into reversible, observable increments. Track progress and adjust based on evidence.

## Design and operations checklist

1. **Classify requirements by stability and risk.** Stable requirements can be implemented fully; uncertain requirements need experimentation.
2. **Define MVP scope explicitly.** What is the minimum set of requirements that delivers value?
3. **Map dependencies across teams.** Which requirements require coordination? Which can be owned independently?
4. **Set acceptance criteria at multiple levels.** Unit, feature, and integration criteria should be observable and measurable.
5. **Plan for reversibility.** Which requirements can be undone or changed without breaking the system?
6. **Track requirement coverage.** Which requirements are implemented, tested, and deployed?

## Decomposition into increments

Break requirements into increments that:
- Deliver observable value (users can test it)
- Are reversible (can be rolled back without breaking the system)
- Can be owned by one team
- Have clear acceptance criteria
- Can be completed in one sprint or release cycle

Example: Payment processing feature

```
Increment 1: Accept payment method (card details)
Increment 2: Validate payment with gateway
Increment 3: Create order on successful payment
Increment 4: Handle payment failures and retries
Increment 5: Send confirmation email
Increment 6: Support multiple payment methods
```

Each increment is independently testable and deployable.

## Governance and coordination

- **Requirement ownership:** Who is responsible for each requirement? (Product, engineering, business)
- **Escalation:** What happens when requirements conflict or change?
- **Communication:** How do teams stay aligned as requirements evolve?
- **Metrics:** How do we measure if a requirement is working in production?

## Sustained delivery

Requirements are not a one-time specification. They evolve as:
- Users discover new needs
- Business priorities shift
- Technical constraints change
- Competitive pressure increases

Establish a feedback loop:
1. Deploy requirement to production
2. Measure user behavior and business impact
3. Gather feedback from support and analytics
4. Adjust requirement or implementation
5. Plan next increment

## Realistic scenario: Global e-commerce platform

**Initial requirements:** Users can browse products and place orders.

**Evolving requirements (by region and business need):**
- EU: GDPR compliance (data deletion, consent)
- Asia: Multiple payment methods (local wallets, bank transfers)
- US: Subscription orders (recurring billing)
- All: Fraud detection and prevention

**Decomposition:**
- **Phase 1:** Core checkout (US, single payment method)
- **Phase 2:** Regional payment methods (Asia)
- **Phase 3:** Subscription orders (recurring billing)
- **Phase 4:** GDPR compliance (data deletion, consent)
- **Phase 5:** Fraud detection (machine learning model)

**Ownership:**
- Phase 1: Checkout team
- Phase 2: Payments team (coordinate with regional partners)
- Phase 3: Billing team
- Phase 4: Legal + Engineering (compliance)
- Phase 5: Data science + Engineering (fraud prevention)

**Metrics:**
- Checkout completion rate
- Payment success rate by method
- Subscription retention rate
- GDPR data deletion requests processed
- Fraud detection accuracy

## Test yourself

1. How do you decompose a complex requirement into reversible increments?
2. What makes a requirement "done" in production?
3. How do you handle requirements that conflict across teams?
4. What metrics indicate a requirement is working as intended?

## Further reading

- Marty Cagan, *Inspired: How to Create Products Customers Love*
- Lean Product Playbook: How to Innovate Successfully
- Continuous Discovery Habits: Discover Products that Create Customer Value
