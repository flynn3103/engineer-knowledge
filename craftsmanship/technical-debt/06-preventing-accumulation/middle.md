# Preventing Accumulation — Middle

## Goal

Use workflow and automation to stop new debt without blocking useful delivery.

## Quality gates

- Run tests, formatting, type checks, and security scans in CI.
- Use a ratchet: new code must not worsen an agreed baseline.
- Keep gates fast, actionable, and owned.

## Team practices

- Review for clarity, tests, and unnecessary complexity.
- Record important architecture choices in short ADRs.
- Prefer small pull requests with a single purpose.
- Improve the paved path so good defaults are easy to use.

## Avoid

Treating a tool warning count as the whole quality system.
