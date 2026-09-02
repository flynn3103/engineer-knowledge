# Systems Thinking — Middle

Use causal loops to explain change over time.

- A reinforcing loop amplifies change: more retries create more load, which creates more failures and retries.
- A balancing loop resists change: autoscaling adds capacity when utilization rises.
- Delays cause overshoot: new capacity arrives after queues have already exploded.

Map signs between variables, but validate the model with time-series evidence. Correlation without mechanism is not a loop.

## Bottlenecks and trade-offs

System throughput is limited by the active constraint. Speeding non-bottlenecks increases inventory or queues, not output. When the constraint moves, measure again.

Use scenario tables for second-order effects: immediate benefit, downstream response, delayed consequence, and new equilibrium.

## Test yourself

1. Is autoscaling always a balancing loop? When can it reinforce failure?
2. How does delay create oscillation?
3. Why does optimizing a non-bottleneck fail to improve throughput?
4. What observation would falsify your loop diagram?

Continue to [`senior.md`](senior.md).
