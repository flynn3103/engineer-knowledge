# Blast Radius and Recovery — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How do you scope a chaos experiment so its blast radius is small and known, and how do you make it stop automatically before it causes real damage?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Chaos Engineering](../README.md) → Blast Radius and Recovery

*A chaos experiment without a bounded blast radius and an abort condition is not an experiment — it's an unplanned outage with extra paperwork. Learn to draw the fence and set the trip-wire before you light the fire.*

---

## Core Concept 1 — What "blast radius" actually means

**Blast radius** is the portion of your system that an injected fault (or a real failure) is allowed to touch: a percentage of traffic, a number of instances, a single tenant, a single region. It answers one question before anything else: *if this goes wrong, how much of production is affected?*

| Term | Plain-English meaning |
|---|---|
| **Blast radius** | How much of the system is exposed to the fault — 1 pod out of 20, 5% of traffic, one region. |
| **Abort condition** | A concrete, measurable rule that automatically stops the experiment ("stop if 5xx rate exceeds 2% for 60 seconds"). |
| **Rollback** | The action that undoes the fault or the bad change once triggered — delete the fault, redeploy, flip a flag. |
| **Recovery time (MTTR)** | How long from "the fault stopped" to "the system's metrics are back to baseline." |
| **Canary** | A small, isolated subset of instances or traffic used to try something risky before it reaches everyone. |

A junior's whole job on this topic is simple to state and easy to skip under pressure: **never inject a fault without first deciding how big it's allowed to get and how it's guaranteed to stop.**

---

## Core Concept 2 — The four questions before you inject anything

Before running any experiment, however small, answer these in writing:

1. **What fraction of real traffic or instances will this touch?** Name a number — "1 pod of 20," not "a little bit."
2. **What automatically stops it?** A metric threshold a machine checks, not a human staring at a dashboard.
3. **How do you undo it if the automatic stop fails?** A concrete command you can run by hand.
4. **How do you know it's actually over?** The metric that proves the system, not just the fault, has returned to normal.

If you can't answer all four, you are not ready to run the experiment yet.

---

## Core Concept 3 — Worked example: scoping a latency-injection experiment

**Scenario:** The `product-page` service calls a `recommendations` service to render a "you might also like" widget. You want to prove that if `recommendations` gets slow, `product-page` falls back gracefully instead of timing out the whole page. `recommendations` runs as 20 pods behind a Kubernetes Service.

**Step 1 — Scope the blast radius.** Target exactly one pod out of 20 (5% of instances), and only pods labeled `canary: "true"` that never receive more than a small slice of real traffic:

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: recs-latency-canary
spec:
  action: delay
  mode: fixed
  value: "1"                     # exactly 1 pod, not a percentage of the fleet
  selector:
    namespaces: [prod]
    labelSelectors:
      app: recommendations
      canary: "true"
  delay:
    latency: "500ms"
  duration: "10m"                # hard stop even if nothing else fires
```

Two details matter here: `value: "1"` pins the blast radius to a single instance regardless of how the fleet scales later, and `duration: "10m"` guarantees the fault ends even if every other safeguard fails.

**Step 2 — Define the abort condition.** Watch a real metric and kill the experiment automatically if it crosses a threshold:

```bash
#!/usr/bin/env bash
# Poll error rate every 15s; abort if it exceeds 2% for two consecutive checks.
BAD_CHECKS=0
while true; do
  ERR_RATE=$(curl -s 'http://prometheus:9090/api/v1/query' \
    --data-urlencode 'query=sum(rate(http_requests_total{job="product-page",code=~"5.."}[1m])) / sum(rate(http_requests_total{job="product-page"}[1m]))' \
    | jq -r '.data.result[0].value[1] // "0"')

  if (( $(echo "$ERR_RATE > 0.02" | bc -l) )); then
    BAD_CHECKS=$((BAD_CHECKS + 1))
  else
    BAD_CHECKS=0
  fi

  if [ "$BAD_CHECKS" -ge 2 ]; then
    echo "ABORT: error rate $ERR_RATE exceeded threshold twice"
    kubectl delete networkchaos recs-latency-canary
    break
  fi
  sleep 15
done
```

**Step 3 — Run it, then verify recovery.** After the fault ends (by timeout or abort), confirm the system actually came back, not just that the fault stopped:

| Time | Event | `product-page` 5xx rate | p99 latency |
|---|---|---|---|
| T+0:00 | Latency fault applied to 1 pod | 0.1% | 220ms |
| T+2:00 | Error rate rises (fallback path partially misfiring) | 2.4% | 410ms |
| T+2:15 | Abort script triggers, deletes the fault | 2.4% | 410ms |
| T+2:45 | Fault removed, metrics start recovering | 0.9% | 260ms |
| T+3:30 | Metrics back to baseline | 0.1% | 225ms |

The **recovery time** here is measured from the abort trigger (T+2:15) to metrics returning to baseline (T+3:30): **75 seconds.** That number — not "it stopped erroring" — is the deliverable of the experiment.

---

## Core Concept 4 — Simple success criteria

Before you run the experiment, decide what "success" and "failure" mean in plain terms — otherwise you'll rationalize whatever happens after the fact. Two checklists cover most junior-level experiments:

**The experiment succeeded if:**

- The fault stayed inside the blast radius you declared (only the canary pod was affected, not the whole fleet).
- The abort condition fired on its own, or the fault ended at its hard-coded duration — you did not have to manually intervene.
- The system's metrics returned to baseline within a time you can state as a number.
- Nothing outside the scope you declared (other services, other teams' dashboards) showed an unexplained spike.

**The experiment failed — as a control, not as a system test — if any of the following happened:**

- You had to manually delete or kill the fault because the automatic abort didn't fire.
- The blast radius spread beyond what you scoped (e.g., more than the one canary pod was affected).
- You can't say, with a number, how long recovery took.
- Someone else was paged or alarmed because they didn't know an experiment was running.

Notice that these are about the *control mechanism*, not about whether the system handled the fault gracefully. A chaos experiment can "fail" as a system test (the fallback didn't work, the page broke) while still succeeding as an *experiment* — because the point of blast-radius scoping and abort conditions is to make it safe to learn that the fallback is broken, in a way that only affects 5% of instances for a few minutes, instead of finding out from a full outage.

---

## Common Mistakes

1. **Running the first-ever experiment at 100% of traffic.** Always start with the smallest blast radius that still teaches you something — one pod, one tenant, one route.
2. **No automatic abort condition.** "I was watching the dashboard" is not a control; a person can get distracted, get paged elsewhere, or simply be too slow. The abort must be a script or a platform feature, not a promise.
3. **Confusing "the fault stopped" with "the system recovered."** A fault that ends at T+2:15 does not mean the system is healthy at T+2:15 — connection pools, caches, and retry queues can stay unhealthy for minutes afterward. Always watch the recovery metric until it returns to baseline.
4. **No hard duration on the fault.** If your abort script crashes or loses its connection to Prometheus, a fault with no `duration` set can run indefinitely. Always set a timeout as a second line of defense.
5. **Not telling anyone.** If on-call sees a real-looking error-rate spike with no context, they'll page people and start an incident for what was actually your planned experiment. Post in the team channel before you start.

---

## Apply it

1. Pick one low-traffic, non-critical internal service you have access to in a staging environment.
2. Scope a single-instance fault injection (e.g., add 500ms of latency, or kill one pod) using a tool like Chaos Mesh, Gremlin, or a simple `tc`/`iptables` command inside one container.
3. Define one abort condition tied to a real metric (error rate or latency) and a hard-coded maximum duration.
4. Run the experiment, let the abort condition or the duration end it, and watch the dashboard until the metric returns to its pre-experiment baseline.
5. Write down the exact recovery time — the interval between the fault ending and the metric returning to baseline.

## Verify your work

- You can name the exact blast radius you used (e.g., "1 pod of 6," "one staging tenant") before you started.
- The experiment stopped on its own, without you manually intervening, when the abort condition or duration was reached.
- You have a timestamped before/during/after set of metric values, not just a verbal impression that "it recovered."
- The recovery time you recorded is a number, derived from the metrics, not a guess.

## Review questions

- What two numbers must you be able to state before you inject any fault?
- Why is "I was watching the dashboard" not an acceptable abort condition?
- How is recovery time different from the moment the fault itself ends?
- What could happen if an experiment has no hard-coded maximum duration?
