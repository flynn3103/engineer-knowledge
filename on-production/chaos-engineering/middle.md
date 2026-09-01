# Chaos Engineering — Middle

Test process death, network latency or partition, CPU or memory pressure, disk exhaustion, clock behavior, and dependency errors according to real failure modes. Inject one controlled variable and observe retries, queues, shedding, failover, and alerts.

Automate repeatable experiments in CI or staging where fidelity is sufficient; use production only when unique evidence justifies the risk.

## Test yourself

1. Which real incident motivates the experiment?
2. How can retries amplify the fault?
3. Which environment has enough fidelity?
4. What telemetry proves the hypothesis?

Continue to [`senior.md`](senior.md).
