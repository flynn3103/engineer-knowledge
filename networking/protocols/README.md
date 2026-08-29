# Protocols

> Trace how an application message becomes packets, crosses networks, and returns as a trusted response.

Start with models and transport trade-offs. Then study secure sessions, modern HTTP, long-lived connections, proxies, congestion, container paths, and Internet routing.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [OSI and TCP/IP](01-osi-and-tcp-ip/junior.md) | Locate a symptom at the right layer. |
| 02 | [TCP vs UDP](02-tcp-vs-udp/junior.md) | Choose transport from delivery and latency needs. |
| 03 | [TLS and HTTPS](03-tls-and-https/junior.md) | Inspect trust, identity, and negotiation failures. |
| 04 | [HTTP/1.1, HTTP/2, HTTP/3, and QUIC](04-http-evolution-1-2-3-quic/junior.md) | Explain protocol behavior from a request trace. |
| 05 | [WebSockets](05-websockets/junior.md) | Operate a bidirectional connection safely. |
| 06 | [Server-Sent Events](06-server-sent-events/junior.md) | Deliver resumable server-to-client events. |
| 07 | [Long Polling and Streaming](07-long-polling-and-streaming/junior.md) | Match delivery style to update behavior. |
| 08 | [Proxies and NAT](08-network-proxies-and-nat/junior.md) | Trace address translation and forwarded identity. |
| 09 | [Congestion Control and TCP Tuning](09-congestion-control-and-tcp-tuning/junior.md) | Measure before tuning throughput or latency. |
| 10 | [Container and Overlay Networking](10-container-and-overlay-networking/junior.md) | Follow packets across namespaces and overlays. |
| 11 | [BGP and Internet Routing](11-bgp-and-internet-routing/junior.md) | Reason about path selection and blast radius. |

## Practice loop

Capture one request with command-line tools or packet inspection, label each boundary it crosses, predict the next observable event, and compare the prediction with evidence.
