# Seams and Enabling Points — Senior

At this level, seams are a coupling map. A module that creates clients, reads ambient state, and performs I/O internally is expensive to test and change; a module that receives collaborators and returns observable results is controllable.

## Assess a boundary before editing

For each dependency, ask:

- **Control:** can a test choose its inputs and failure mode?
- **Observation:** can a test see the result or effect?
- **Ownership:** who can change the interface and wiring?
- **Blast radius:** how many callers or deployments does a new seam touch?

Use this map to place seams at stable boundaries: time, persistence, network, queues, identity, and third-party SDKs. Do not inject every internal helper merely for theoretical flexibility.

## Choose the seam by cost

| Choice | Best when | Cost to watch |
|---|---|---|
| Constructor/function injection | Unit owns a clear dependency | API migration |
| Adapter around an external API | Vendor behavior leaks inward | Adapter maintenance |
| Composition-root configuration | Choice is deployment-specific | Misconfiguration |
| Temporary patch/wrapper | Characterizing code you cannot yet reshape | Hidden global state |

Prefer the option that makes production and tests use the same program structure. Build-specific substitutions and global patches can unblock work, but they hide behavior differences.

## Land a seam incrementally

1. Capture behavior around the dependency.
2. Introduce the new injectable path beside the old path.
3. Make the old path delegate to the real default.
4. Migrate callers in small batches.
5. Remove the compatibility path only after usage and ownership are clear.

Measure success in lead time and failure isolation: a new test should control the collaborator, and a change to the adapter should not require changing domain rules.

## Review prompts

- Does this seam reveal a real architectural boundary or conceal a design problem?
- Is the default wired at the application edge?
- Can failures and retries be modeled through the seam?
- What is the rollback plan if migrated callers behave differently?
