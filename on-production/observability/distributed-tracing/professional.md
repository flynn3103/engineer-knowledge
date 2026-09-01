# Distributed Tracing — Professional

<!-- level-focus -->
At professional level, establish distributed tracing as a cross-team diagnostic contract.

## Govern the shared context

Platform owns propagation libraries and exporters; service teams own semantic span names and incident usage. Roll out a compatibility-tested library, migrate critical paths first, and measure connected-trace coverage and investigation time. Escalate schema breaks as production compatibility defects.

## Apply it

1. Assign library, semantic, and privacy owners.
2. Stage a version migration with rollback.
3. Review incident traces for missing boundaries.

## Verify your work

- Cross-team changes preserve trace continuity.
- Coverage and cost are visible to accountable owners.

## Review questions

- Who owns a broken trace between two teams?
- What exit condition makes a tracing migration complete?
