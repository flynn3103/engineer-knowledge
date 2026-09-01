# Model Context Protocol (MCP) - Professional

MCP is a stateful capability-negotiation protocol layered on JSON-RPC 2.0.
Production design therefore combines protocol correctness, RPC operations,
identity propagation, and untrusted extension isolation.

## Protocol internals and named systems

**JSON-RPC 2.0** distinguishes requests, responses, and notifications through
IDs and method names. Implementations must correlate concurrent requests,
avoid replying to notifications, and preserve errors without confusing
application failure with transport failure.

**MCP Streamable HTTP** supports request/response operation and optional
server-to-client streaming. Deployments must handle reconnection, event
ordering, session expiration, and load balancers that may route successive
requests to different instances. Keep durable state external or use explicit
affinity with bounded lifetime.

**OAuth 2.1 / RFC 8707 resource indicators** provide the model for scoped,
audience-bound access tokens. Resource servers validate issuer, audience,
scope, expiry, and subject; forwarding arbitrary upstream tokens is a
credential-confusion vulnerability.

**MCP Inspector** is useful for protocol exploration and capability testing,
but conformance needs automated fixtures for initialization, malformed
messages, cancellation, pagination, and negotiated feature combinations.

## Scale and failure behavior

At 10x, repeated `tools/list` and resource enumeration can dominate remote
servers; cache by server identity and capability version while honoring
change notifications. At 100x, long-lived streams consume file descriptors,
load-balancer capacity, and per-connection memory. Enforce idle deadlines,
connection budgets, and graceful reconnect with jitter.

A slow server creates head-of-line blocking if one client serializes all
requests. Use independent request IDs and bounded concurrency, but preserve
ordering where stateful methods require it. Backpressure notifications and
large resource payloads before they exhaust host memory.

## Operations

Measure initialize failures by negotiated version, request latency/error by
method and server, active sessions, reconnects, capability-change frequency,
authorization denials, response bytes, and protocol violations. Never label
high-cardinality server URLs or user IDs directly in metrics.

Runbooks should distinguish DNS/TLS, authorization, negotiation, framing,
handler, and downstream failures. Capture sanitized JSON-RPC envelopes with
correlation IDs so operators can identify the failed layer.

## Design and operations checklist

- [ ] Protocol and SDK versions are pinned and compatibility-tested.
- [ ] Credentials are scoped, audience-bound, and never passed through blindly.
- [ ] Remote sessions survive instance changes or declare bounded affinity.
- [ ] Local servers run with minimal filesystem, environment, and network access.
- [ ] Calls, streams, payloads, and capability enumeration are bounded.
- [ ] Protocol traces are useful without storing secrets or private resources.

## Cheat sheet

```text
host   = user-facing AI application
client = one host-side server connection
server = provider of tools/resources/prompts
stdio  = local child-process transport
HTTP   = remote transport requiring identity and fleet operations
MCP    = interoperability, not trust or sandboxing
```

## Test yourself

1. How would you operate Streamable HTTP behind a non-sticky load balancer?
2. Which token claims prevent one MCP server from reusing a token at another service?
3. Design conformance tests for cancellation during a long-running tool call.

## Further reading

- Model Context Protocol specification and authorization specification
- Model Context Protocol SDKs and Inspector source repositories
- JSON-RPC 2.0 specification
- OAuth 2.1 draft and RFC 8707, "Resource Indicators for OAuth 2.0"
- RFC 9728, "OAuth 2.0 Protected Resource Metadata"
