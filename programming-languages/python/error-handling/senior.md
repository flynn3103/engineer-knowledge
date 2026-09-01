# Python Error Handling — Senior

Failure behavior is part of the service contract.

- Classify errors as invalid request, conflict, transient dependency failure, or internal defect.
- Design compensation and idempotency before retries.
- Propagate cancellation; do not convert it into a generic error.
- Include correlation IDs and safe structured context in observability signals.

Review error budgets and recurring failure modes alongside normal feature work.
