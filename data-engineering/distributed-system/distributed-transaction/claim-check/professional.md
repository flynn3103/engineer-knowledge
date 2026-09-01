# Claim-Check Pattern - Professional

Claim-check is a distributed garbage-collection and integrity protocol around immutable blobs.

## Real systems

- Amazon S3 gives strong read-after-write consistency but lifecycle deletion is asynchronous.
- Kafka retains the reference log independently of object retention.
- OCI registries use content-addressed manifests and blobs with digest verification.
- Azure Service Bus documents claim-check for payloads beyond broker limits.

At scale, request rate, object-list operations, tiny-object overhead, and cross-region egress dominate. Dashboard referenced versus unreferenced bytes, GET error rate, digest failures, and minimum consumer position before deletion.

## Design and operations checklist

- Define publish ordering and orphan grace periods.
- Bind immutable digest, schema, encryption, and size to each reference.
- Prove cleanup cannot delete replayable data.
- Test object-store outage and credential rotation.

```text
write blob -> verify durability -> publish claim
delete only after no valid reader can claim it
```

## Test yourself

1. How would you prove a blob is unreachable before deletion?
2. What changes for mutable object keys?
3. How do regional failures affect reference placement?

## Further reading

- Enterprise Integration Patterns, *Claim Check*.
- Amazon S3 consistency and lifecycle documentation.
- OCI Image Specification: content descriptors.
