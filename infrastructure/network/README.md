# Network

> Trace how an application message becomes packets, crosses networks and cloud boundaries, and returns as a trusted response.

Start with models and transport trade-offs. Then study secure sessions, modern HTTP, server-to-client delivery, proxies, congestion, container and cloud network topology, and Internet routing. Real-time, bidirectional application protocols (WebSockets, long polling) now live in [Data Engineering → Communication](../../data-engineering/communication/README.md) alongside the other client/service communication patterns — this section keeps the transport and infrastructure layer underneath them.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [OSI and TCP/IP](osi-and-tcp-ip/junior.md) | Locate a symptom at the right layer. |
| 02 | [TCP vs UDP](tcp-vs-udp/junior.md) | Choose transport from delivery and latency needs. |
| 03 | [TLS and HTTPS](tls-and-https/junior.md) | Inspect trust, identity, and negotiation failures. |
| 04 | [HTTP/1.1, HTTP/2, HTTP/3, and QUIC](http-evolution-1-2-3-quic/junior.md) | Explain protocol behavior from a request trace. |
| 05 | [Server-Sent Events](server-sent-events/junior.md) | Deliver resumable server-to-client events. |
| 06 | [Proxies and NAT](network-proxies-and-nat/junior.md) | Trace address translation and forwarded identity. |
| 07 | [Congestion Control and TCP Tuning](congestion-control-and-tcp-tuning/junior.md) | Measure before tuning throughput or latency. |
| 08 | [Container and Overlay Networking](container-and-overlay-networking/junior.md) | Follow packets across namespaces and overlays. |
| 09 | [Cloud Network Architecture (VPC)](vpc/junior.md) | Design isolated, routable network boundaries in the cloud. |
| 10 | [BGP and Internet Routing](bgp-and-internet-routing/junior.md) | Reason about path selection and blast radius. |

## Practice loop

Capture one request with command-line tools or packet inspection, label each boundary it crosses, predict the next observable event, and compare the prediction with evidence.
