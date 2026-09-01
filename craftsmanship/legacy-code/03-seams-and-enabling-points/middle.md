# Seams and Enabling Points — Middle

A **seam** lets you alter a collaborator without editing the code that uses it. The **enabling point** is where that choice is made. Find both before trying to test legacy behavior.

## Prefer explicit object seams

Pass dependencies in at construction or at the call that needs them. The constructor is the enabling point; the protocol is the seam.

```python
from datetime import datetime
from typing import Protocol

class Clock(Protocol):
    def now(self) -> datetime: ...

class SubscriptionService:
    def __init__(self, clock: Clock):
        self._clock = clock

    def expired(self, ends_at: datetime) -> bool:
        return self._clock.now() > ends_at
```

```python
class FixedClock:
    def __init__(self, value: datetime):
        self.value = value

    def now(self) -> datetime:
        return self.value
```

Keep production wiring at the edge: an application factory creates `SubscriptionService(SystemClock())`; the test supplies `FixedClock(...)`.

## Other useful seams

- **Parameter seam:** pass a value or function for one operation.
- **Factory/configuration seam:** choose an implementation in one factory, not throughout the code.
- **Filesystem/process seam:** wrap `open`, environment access, HTTP, and subprocess calls behind a small adapter.
- **Monkey-patching seam:** use only as a short-term characterization tool; it is less visible and easier to misuse.

## Add a seam safely

1. Name the hard dependency and its observable effect.
2. Extract the smallest interface needed by the caller.
3. Add injection while preserving the old public construction path when callers are numerous.
4. Characterize current behavior, then test through the new seam.
5. Move only the dependency decision to the enabling point.

Avoid a broad “service” interface. A narrow `Clock`, `Mailer`, or `OrderRepository` makes a fake easy to understand and keeps the seam honest.

## Check yourself

- Can a test choose the collaborator without changing production code?
- Is the enabling point obvious to a reader?
- Does the seam expose only what the unit actually needs?
