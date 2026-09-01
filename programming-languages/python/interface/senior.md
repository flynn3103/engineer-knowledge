# Python Interfaces — Senior

Protect interfaces that cross teams, services, or plugin boundaries.

- Separate transport models from domain objects.
- Version external APIs deliberately and preserve compatibility where promised.
- Prefer capability-focused interfaces over a broad `Repository` or `Client`.
- Test consumers against realistic contracts, including failures and timeouts.

An interface is successful when an implementation can change without forcing every caller to change.
