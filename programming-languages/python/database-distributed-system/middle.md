# Python Data and Distributed Systems — Middle

Keep persistence behind a capability-focused boundary and make transaction scope explicit.

```python
def create_order(command: CreateOrder, store: OrderStore) -> Order:
    with store.transaction():
        return store.create(command)
```

Set connection, query, and network timeouts. Use unique constraints and idempotency keys for retryable writes. Cache only with an ownership and invalidation rule.
