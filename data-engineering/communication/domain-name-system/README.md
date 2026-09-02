# Domain Name System

> Resolve a name deliberately, predict cache behavior, and roll out record changes without guessing.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [DNS Resolution Flow](dns-resolution-flow/junior.md) | Trace stub, recursive, and authoritative resolution. |
| 02 | [Record Types](record-types/junior.md) | Choose records that match the routing requirement. |
| 03 | [DNS Load Balancing](dns-load-balancing/junior.md) | Understand what DNS can and cannot balance. |
| 04 | [DNS Caching and TTL](dns-caching-and-ttl/junior.md) | Predict propagation and stale-answer windows. |
| 05 | [GeoDNS and Anycast](geodns-and-anycast/junior.md) | Compare location-based answers with routed anycast. |

## Practice loop

Query from at least two resolvers, inspect the authoritative answer and TTL, then write the expected old/new answer window before changing a record.
