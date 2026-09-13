# Security at Scale — Professional

SPIFFE/SPIRE issues workload identities; OPA evaluates policy; Sigstore records signing in transparency logs; cloud KMS systems separate key material from envelope-encrypted data keys. At scale, policy distribution, certificate storms, revocation, key quotas, and identity ownership become availability concerns.

## Design and operations checklist

1. Map assets, actors, trust boundaries, and abuse cases.
2. Use short-lived identities and least privilege.
3. Separate key, policy, and deployment authority.
4. Verify provenance and dependency policy.
5. Monitor denial, escalation, and credential misuse.
6. Rehearse compromise and revocation.

```text
IDENTITY -> AUTHENTICATION -> AUTHORIZATION -> ENCRYPTION -> AUDIT -> RESPONSE
```

## Test yourself

1. Design workload identity across regions during control-plane loss.
2. How can centralized policy become a security outage?
3. Which signals reveal token theft?
4. How do you rotate a root of trust?

## Further reading

- NIST Zero Trust Architecture SP 800-207.
- OAuth 2.0 Security Best Current Practice.
- SLSA, Sigstore, SPIFFE, and OPA specifications.
