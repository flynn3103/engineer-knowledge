# Event Replay - Senior
| Failure or mistake | Control |
|---|---|
| handler has external effects | replay-safe mode |
| duplicate application | offset/version guard |
| incompatible old schema | upcaster or versioned handler |
| replay never catches live | capacity margin and throttling |
| bad cutover | atomic alias and rollback |
Monitor replay rate, live arrival rate, convergence ETA, rejects, checksums, and storage growth. Preserve the old projection until the new one survives production validation.
## Test yourself
1. When can replay never converge?
2. How do upcasters preserve old events?
3. What makes cutover reversible?
Continue to [`professional.md`](professional.md).
