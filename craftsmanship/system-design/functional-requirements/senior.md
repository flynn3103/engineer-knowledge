# Functional Requirements — Senior

Manage requirement evolution under uncertainty. Requirements change because business priorities shift, users discover new needs, and systems interact in unexpected ways. Set boundaries to contain scope creep and make trade-offs explicit.

## The mental model

Requirements are not static. They evolve as:
- Business strategy changes
- User feedback arrives
- Integration with other systems reveals conflicts
- Technical constraints become apparent

Your role is to:
1. **Anticipate change:** Which requirements are likely to evolve?
2. **Set boundaries:** What is in scope for this release? What is deferred?
3. **Make trade-offs explicit:** If we add this requirement, what do we sacrifice?
4. **Contain scope creep:** How do we say no without blocking progress?

## Requirement stability and risk

Classify requirements by stability:

| Stability | Example | Risk | Strategy |
|---|---|---|---|
| Stable | "User can log in with email/password" | Low | Implement fully |
| Evolving | "User can authenticate with multiple methods" | Medium | Design for extension, defer some methods |
| Uncertain | "User can integrate with third-party services" | High | Build plugin architecture, start with one provider |

## Boundary setting

Define what is in scope:
- **MVP scope:** Minimum viable product requirements only.
- **Phase 1, 2, 3:** Planned evolution.
- **Out of scope:** Explicitly list what will not be done.

Example:
- **MVP:** User login with email/password, basic profile
- **Phase 2:** Social login (Google, GitHub)
- **Phase 3:** Multi-factor authentication
- **Out of scope (for now):** Biometric authentication, passwordless login

## Handling conflicting requirements

When requirements conflict, gather evidence:
- **User research:** Which behavior do users actually need?
- **Business impact:** Which requirement drives revenue or retention?
- **Technical cost:** Which is cheaper to implement and maintain?
- **Operational burden:** Which creates ongoing support load?

Make the trade-off explicit and document the decision.

## Realistic scenario: Multi-tenant SaaS

**Initial requirement:** "Users can create accounts and manage their data."

**Evolving requirements:**
- Users want to invite team members (collaboration)
- Users want to control who sees what (permissions)
- Users want audit logs (compliance)
- Users want to export their data (portability)

**Conflicts:**
- Audit logs increase storage and query cost
- Fine-grained permissions increase complexity
- Data export must work with all features

**Boundary setting:**
- **MVP:** Single-user accounts, basic data management
- **Phase 1:** Team invitations, basic role-based access (admin/member)
- **Phase 2:** Granular permissions, audit logs
- **Phase 3:** Data export, compliance certifications

**Trade-off:** Defer granular permissions to reduce initial complexity. Accept that early users will have limited control.

## Questions that expose weak assumptions

Before committing to a requirement, ask:
1. What happens if this requirement changes in 6 months?
2. Which other systems depend on this behavior?
3. What is the cost of reversing this decision later?
4. How will we know if this requirement is working?
5. What could go wrong if we implement this incorrectly?

## Test yourself

1. How do you decide which requirements are in MVP vs. deferred?
2. What questions reveal hidden dependencies in requirements?
3. How do you handle a requirement that conflicts with existing behavior?
4. Why is requirement stability important for planning?

Continue to [`professional.md`](professional.md).
