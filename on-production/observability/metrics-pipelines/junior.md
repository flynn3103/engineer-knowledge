# Metrics Pipelines — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you configure a Prometheus scrape job for one service, confirm the target is actually being collected, and explain what pull-based collection requires that push-based collection does not?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — What a Metrics Pipeline Is

Instrumentation (covered elsewhere in this site's Monitoring material) is about a running process emitting numbers about its own behavior. A **metrics pipeline** is everything that happens *after* that: something has to reach out and collect those numbers, carry them somewhere, and store them so they can be queried later. This topic starts exactly where instrumentation ends — the collector, the transport, and the storage, not the client-library calls inside application code.

The two collection models you'll meet everywhere:

- **Pull (scrape)**: the metrics backend (Prometheus is the canonical, citable example) reaches out to a known target at a fixed interval and reads its current metric values from an HTTP endpoint.
- **Push (remote-write / push gateway)**: the target itself sends its metrics to a receiving endpoint, rather than waiting to be asked.

## Core Concept 2 — Pull vs. Push, the Basic Trade-off

| | Pull (scrape) | Push (remote-write / gateway) |
|---|---|---|
| **Who initiates** | The collector reaches out to the target | The target sends data on its own schedule |
| **Target must be** | Reachable over the network from the collector, with a stable address | Able to reach the collector; doesn't need to be reachable itself |
| **Good fit for** | Long-running services (web servers, APIs, workers) that stay up between scrapes | Short-lived jobs that finish before a scrape would ever catch them (batch jobs, cron jobs) |
| **Liveness signal for free** | Yes — a target that stops responding shows up as `down` immediately | No — the collector has no idea whether the source is alive unless it pushes on a schedule |
| **Common tool** | Prometheus scraping `/metrics` | Prometheus Pushgateway, or a remote-write client |

At junior level, the practical takeaway is simpler than the full trade-off table: **most long-running services should be scraped (pulled), and only genuinely short-lived jobs should push.** Using push for a normal, always-running service is a common anti-pattern covered under Common Mistakes below.

## Core Concept 3 — A Repeatable Method for Adding a Scrape Target

1. **Confirm the target exposes a metrics endpoint** — usually `/metrics` on some port, returning plain-text Prometheus exposition format. Verify with a direct request before touching any collector config.
2. **Add a scrape job** to the collector's configuration, naming the job something descriptive and pointing it at the target's host and port.
3. **Set a scrape interval** appropriate to the metric's use (15s or 30s is a common default for interactive dashboards; slower for things checked rarely).
4. **Reload or restart the collector** so it picks up the new config.
5. **Verify the target shows as healthy** in the collector's own status view, then query one of the target's metrics to confirm real data is arriving.

## Core Concept 4 — Worked Example: Scraping a Small Service

A small order-service exposes metrics on port `8000`:

```
$ curl http://order-service:8000/metrics
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",route="/orders/:id",status="200"} 42
http_requests_total{method="GET",route="/orders/:id",status="404"} 3
```

Add a scrape job to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "order-service"
    scrape_interval: 15s
    static_configs:
      - targets: ["order-service:8000"]
```

After reloading Prometheus (`kill -HUP <pid>` or the `/-/reload` HTTP endpoint if `--web.enable-lifecycle` is set), two things confirm the target is really being collected:

1. Prometheus's own **Targets** page shows `order-service` with state `UP`, and a recent "last scrape" timestamp.
2. Querying the built-in liveness metric confirms it programmatically:

```promql
up{job="order-service"}
```

A result of `1` means the last scrape succeeded; `0` means Prometheus reached the target's network address but the scrape itself failed (wrong path, non-200 response, malformed exposition format); no result at all usually means Prometheus never became network-reachable to the target in the first place. From there, the metric itself is queryable:

```promql
sum(rate(http_requests_total{job="order-service"}[5m])) by (status)
```

## Core Concept 5 — Push Exists Too, for a Different Shape of Workload

A nightly reconciliation job runs for two minutes and exits. It will never be caught by a scrape on any reasonable interval, because it isn't running when the next scrape would fire. The standard answer is the **Pushgateway**: the batch job pushes its final metric values to the Pushgateway just before exiting, and Prometheus scrapes the Pushgateway itself (pull collects from a push-fed intermediary, rather than Prometheus pulling from the job directly):

```
$ echo "reconciliation_records_processed 18432" | \
  curl --data-binary @- http://pushgateway:9091/metrics/job/nightly-reconciliation
```

The key distinction to hold onto at this level: push (via a gateway) is for things that don't live long enough to be scraped, not a general substitute for pull.

## Common Mistakes

- **Pointing the scrape config at the wrong port or path**, so the target shows `down` even though the process is healthy — always confirm with a direct `curl` first.
- **Forgetting the metrics endpoint isn't network-reachable** from the collector (a firewall rule, a different subnet, a container not exposing the port) — pull collection fails silently as `down`, which looks identical to the process being dead unless you check network reachability specifically.
- **Using the Pushgateway for a normal, always-running service** — pushed metrics persist in the gateway until explicitly deleted, so a service that pushes once and then also gets restarted can leave stale, misleading values behind long after the original process is gone. Long-running services should be pulled.
- **Never checking the `up` metric** and assuming a metric's absence from a query means "zero activity" when it actually means "never successfully scraped."
- **Setting scrape interval far shorter than the metric actually changes**, adding load to both the target and the collector for no real benefit.

## Apply it

1. Write or reuse a tiny HTTP service (any language) that exposes a `/metrics` endpoint with at least one counter, in Prometheus exposition format.
2. Run a local Prometheus instance with a `prometheus.yml` scrape config pointing at your service on its correct host and port, using a 15s scrape interval.
3. Confirm the target shows `UP` on Prometheus's Targets page, and that `up{job="<your job name>"}` returns `1`.
4. Stop your service, wait one scrape interval, and confirm `up` flips to `0` — this proves the pipeline actually detects absence, not just presence.
5. Restart the service, then deliberately misconfigure the scrape port to something wrong, reload Prometheus, and confirm the target now shows `down` with a connection-refused error — then fix it and confirm it returns to `UP`.

## Verify your work

- Prometheus's Targets page shows your job as `UP` with a recent scrape timestamp.
- `up{job="<your job>"}` returns `1` while the service runs and `0` once you stop it, without restarting Prometheus itself.
- A query against your actual counter metric (e.g., `rate(...)[5m]`) returns a sane, non-empty result while the service is running and taking traffic.
- You can explain, in one sentence, why the misconfigured-port experiment produced `down` rather than a missing target entirely.
- You can state which of your two experiments (stopping the service vs. misconfiguring the port) simulates a real target outage, and which simulates a config mistake.

## Review questions

- What is the concrete difference between pull and push collection in terms of who initiates the connection?
- Why does pull-based collection give you a liveness signal "for free" that push-based collection does not?
- Why is the Pushgateway the right tool for a two-minute nightly batch job but the wrong tool for a normal long-running API service?
- If a target shows as `down` in Prometheus, what are two different root causes that could produce that exact same symptom?
