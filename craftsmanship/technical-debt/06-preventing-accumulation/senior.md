# Preventing Accumulation — Senior

## Goal

Prevent architectural erosion that local tests and linters cannot see.

## System guardrails

- Encode important constraints as fitness functions: dependencies, latency, resilience, and data boundaries.
- Check conformance between intended and built architecture.
- Keep dependency versions and supported platforms moving forward.
- Reduce knowledge debt through ownership rotation, runbooks, and deliberate onboarding.

## Limits

Gates detect only what they can express. Use design review, production evidence, and judgment for the rest.

## Ask

- Does the clean path remain the easiest path?
- What structural rule is currently enforced only by memory?
