# Schema Evolution - Professional
Confluent Schema Registry assigns subject-scoped versions and global IDs; Avro resolves writer and reader schemas; Protobuf preserves numeric tags and unknown fields.
At scale, registry availability, cache churn, subject explosion, and governance latency dominate. Dashboard registration latency, cache hit ratio, incompatible changes, unknown IDs, and fleet version skew.
## Best practices
- Make compatibility policy part of topic ownership.
- Test semantic invariants beyond registry syntax checks.
- Retain schemas as long as corresponding events.
- Rehearse rollback with mixed versions.
```text
wire compatibility prevents decode failure
semantic compatibility prevents wrong meaning
```
## Test yourself
1. How would you migrate a field's type without flag day?
2. What is the registry's disaster-recovery contract?
3. How do retention and schema deletion interact?
## Further reading
- Avro specification: schema resolution.
- Protocol Buffers language guide: updating message types.
- Confluent Schema Registry compatibility documentation.
