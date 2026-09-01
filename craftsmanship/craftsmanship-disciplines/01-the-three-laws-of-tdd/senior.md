# The Three Laws of TDD — Senior

## Goal

Use TDD as design feedback while knowing when its rules need a wider safety net.

## System-level use

- Work outside-in: express an outcome, then drive the next inner unit.
- Prefer real, in-memory collaborators for stable domain behavior.
- Mock at volatile boundaries when interaction itself is the contract.
- Treat difficulty writing a test as evidence of coupling or unclear responsibility.

## Guardrails

- Do not let mocks dictate a brittle call sequence.
- Use characterization tests before changing unknown legacy behavior.
- Time-box spikes; replace exploratory code with tests before relying on it.
- Pair TDD with observability, security review, and production feedback.
