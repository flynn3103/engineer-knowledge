# Domain Name System

> Resolve a name deliberately, predict cache behavior, and roll out record changes without guessing.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [DNS Resolution Flow](01-dns-resolution-flow/junior.md) | Trace stub, recursive, and authoritative resolution. |
| 02 | [Record Types](02-record-types/junior.md) | Choose records that match the routing requirement. |
| 03 | [DNS Load Balancing](03-dns-load-balancing/junior.md) | Understand what DNS can and cannot balance. |
| 04 | [DNS Caching and TTL](04-dns-caching-and-ttl/junior.md) | Predict propagation and stale-answer windows. |
| 05 | [GeoDNS and Anycast](05-geodns-and-anycast/junior.md) | Compare location-based answers with routed anycast. |

## Practice loop

Query from at least two resolvers, inspect the authoritative answer and TTL, then write the expected old/new answer window before changing a record.
