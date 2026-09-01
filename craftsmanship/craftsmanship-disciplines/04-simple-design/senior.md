# Simple Design — Senior

## Goal

Protect system simplicity as teams, integrations, and constraints grow.

## At scale

- Keep domain boundaries explicit and dependencies directional.
- Use fitness functions to detect forbidden dependencies and latency limits.
- Prefer evolutionary architecture: a small current design plus a safe path to change it.
- Standardize the paved path so the simple implementation is also the easy one.

## Trade-offs

Some complexity is essential: authorization, data ownership, failure handling, and compliance. Make it visible, local, tested, and justified rather than pretending it is absent.
