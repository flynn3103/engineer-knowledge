# Documentation — Professional

Docs-as-code systems such as MkDocs and Sphinx make review and versioning familiar; OpenAPI and protobuf generate contract reference from machine-readable schemas; Backstage catalogs connect ownership, systems, and operational resources; ADR repositories preserve decision history.

At scale, search quality, taxonomy, duplicated authority, ownership, and stale content fail before Markdown syntax. Measure task success, failed searches, onboarding time, runbook use during incidents, stale-page age, and broken contracts—not page count.

## Design and operations checklist

1. Define audience, task, and authority for every artifact class.
2. Keep contract docs machine-checkable where possible.
3. Attach ownership and freshness expectations.
4. Test critical instructions and runbooks.
5. Make deprecation and archival visible.
6. Feed search and incident failures back into documentation work.

```text
KNOWLEDGE -> AUTHORITATIVE ARTIFACT -> REVIEW -> DISCOVERY -> USE -> FEEDBACK
             ownership + freshness + executable evidence
```

## Test yourself

1. Design documentation ownership for a platform with hundreds of services.
2. How do you detect two conflicting sources of truth?
3. Which critical documents should be executable?
4. What metric proves documentation improves engineering outcomes?

## Further reading

- Divio documentation system.
- Diátaxis framework.
- Michael Nygard, “Documenting Architecture Decisions.”
- Google technical writing courses.
