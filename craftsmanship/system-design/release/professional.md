# Release — Professional

SLSA defines provenance levels; Sigstore uses transparency logs and keyless signing; Argo Rollouts and Flagger automate progressive delivery; The Update Framework protects update metadata. At fleet scale, control-plane failure, credential compromise, registry availability, and incompatible automation become systemic risks.

## Design and operations checklist

1. Make artifacts immutable and provenance verifiable.
2. Separate build, deployment, and exposure.
3. Test mixed versions, migrations, and rollback.
4. Bound rollout and automate stop conditions.
5. Protect signing and deployment authority.
6. Audit release outcomes and stale flags.

```text
SOURCE -> BUILD -> ATTEST -> DISTRIBUTE -> EXPOSE -> VERIFY -> PROMOTE/RECOVER
```

## Test yourself

1. Design release recovery after registry compromise.
2. How can automated canaries approve a broken release?
3. Which provenance evidence supports incident response?
4. How do you avoid one global release-control bottleneck?

## Further reading

- SLSA specification.
- Sigstore and The Update Framework documentation.
- Humble and Farley, *Continuous Delivery*.
