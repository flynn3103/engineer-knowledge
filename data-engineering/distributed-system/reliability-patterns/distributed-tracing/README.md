# Distributed Tracing

> A single user request can fan out across dozens of services — distributed
> tracing stitches every hop back together into one coherent timeline, by
> propagating a shared trace ID and recording a "span" for each unit of
> work, so you can actually answer "where did the time go?"

```mermaid
flowchart LR
    Junior["Junior: why per-service logs aren't enough"] --> Middle["Middle: trace ID, span ID, and context propagation"]
    Middle --> Senior["Senior: sampling - you can't trace every request"]
    Senior --> Professional["Professional: tracing internals at scale - OpenTelemetry and the collector pipeline"]
```

```mermaid
flowchart LR
    Request["Incoming request\n(trace_id=abc123)"] --> ServiceA["Service A\n(span 1)"]
    ServiceA --> ServiceB["Service B\n(span 2, child of span 1)"]
    ServiceB --> ServiceC["Service C\n(span 3, child of span 2)"]
    ServiceA & ServiceB & ServiceC -.all tagged\ntrace_id=abc123.-> Reassembled["Reassembled into ONE\ntimeline for the whole request"]
```

## Choose a level

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Why per-service logs aren't enough](junior.md) | You can explain why correlating logs across services manually doesn't scale. |
| Middle | [Trace ID, span ID, propagation](middle.md) | You can trace how a trace ID propagates across an HTTP call boundary. |
| Senior | [Sampling](senior.md) | You can explain why you can't trace every request at scale, and how sampling decisions are made. |
| Professional | [OpenTelemetry and the collector pipeline](professional.md) | You can design a production tracing pipeline using OpenTelemetry's collector architecture. |

## Practice rule

For any request spanning more than 2 services, ask: "if this request is
slow, can I currently find out exactly which of the N services (and which
specific operation within that service) is responsible?" If the answer
requires manually correlating timestamps across separate log files, you
need distributed tracing, not just better logging.

## Related

- [Service Mesh](../service-mesh/README.md)
- [Consumer Autoscaling on Lag](../../event-streaming/events/consumer-autoscaling-on-lag/README.md)
