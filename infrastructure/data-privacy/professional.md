# Data Privacy — Professional

GDPR defines purpose limitation and data-subject rights; envelope encryption systems separate data and key control; Apache Iceberg and Delta Lake snapshots show why logical deletion does not immediately remove physical files. At scale, lineage, backups, derived data, and vendor propagation dominate.

## Design and operations checklist

1. Maintain data inventory, purpose, owner, and residency.
2. Minimize and segregate sensitive data.
3. Control access and key lifecycle.
4. Implement retention, deletion, and legal hold.
5. Audit vendors and recovery paths.
6. Test rights requests and breach response.

```text
PURPOSE -> COLLECT -> USE -> SHARE -> RETAIN -> DELETE -> PROVE
```

## Test yourself

1. Design verified deletion across backups and a lakehouse.
2. How can derived features retain personal information?
3. Which key design supports regional isolation?
4. What evidence supports a regulator audit?

## Further reading

- GDPR principles and data-subject rights.
- NIST Privacy Framework.
- Cloud KMS envelope-encryption guidance.
