# Systems Thinking — Senior

Senior systems thinking selects interventions by leverage and side effects.

## Find leverage points

Changing a parameter—more threads or memory—is low leverage when the governing rule is wrong. Higher leverage may come from admission control, ownership, incentives, information visibility, or the goal itself.

## Model resilience

Ask how the system behaves during partial failure, recovery, and operator intervention. Include retry budgets, queue limits, circuit breaking, degraded modes, and restoration sequence. A system that recovers components in the wrong order can immediately fail again.

## Avoid policy resistance

Teams adapt to metrics and constraints. A target for ticket closure can reduce ticket quality; a utilization target can destroy headroom. Predict how people and automation respond to the intervention.

## Test yourself

1. Which intervention changes a rule rather than a parameter?
2. How can a reliability metric create unsafe behavior?
3. What sequence dependencies matter during recovery?
4. Where would you place admission control and why?

Continue to [`professional.md`](professional.md).
