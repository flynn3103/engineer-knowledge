# Characterization Tests — Professional

Organizations use characterization tests to make high-risk modernization and ownership transfer possible. The goal is a maintained contract, not maximum test count.

## Establish a contract-discovery practice

For important systems, keep a lightweight inventory of public behavior, owners, consumers, and evidence. Combine executable tests with versioned API schemas, recorded integration cases, and operational dashboards.

## Run a safe change program

1. Identify the boundary and its consumers.
2. Capture representative behavior and publish the findings.
3. Separate compatibility tests from desired-future behavior tests.
4. Introduce a version, adapter, or feature flag when the contract must change.
5. Monitor production use, errors, and fallback paths.
6. Retire compatibility behavior on an explicit date with an owner.

## Guardrails

- Treat generated golden files as reviewed code; make differences readable.
- Keep test data lawful, minimized, and reproducible.
- Allocate time to remove flaky or opaque tests; an untrusted gate is no gate.
- Track coverage of critical contracts, not only line coverage.

Success means teams can change an old boundary with evidence, clear consumer communication, and a reversible rollout.
