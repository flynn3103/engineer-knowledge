# Python Error Handling — Middle

Translate failures at boundaries. A database error should not leak directly into an HTTP response or a domain use case.

- Define a small domain exception hierarchy when callers need distinct recovery.
- Preserve the original cause with `raise ... from exc`.
- Validate untrusted input at the boundary.
- Log a failure once, where enough context exists to act.

Use retries only for known transient failures, with timeout, backoff, and idempotency.
