# Go Code Organization — Professional

At organization scale, the aim is not one universal Go layout. It is a system of conventions that lets many teams change software safely and independently.

## Establish a small, enforceable standard

Document a few rules that teams can apply without architecture meetings:

- Every executable starts in `cmd/<name>` and has one composition root.
- Packages have a named capability and a clear owner.
- Application implementation stays under `internal/` by default.
- Shared libraries are created only with consumers, an owner, tests, documentation, and a compatibility policy.
- `go.mod` and `go.sum` are committed; dependency changes are reviewed and automated.

Make the rules easy to verify with repository templates, CI checks, and code review prompts—not a large diagram that becomes stale.

## Design reuse as a product decision

The cost of a shared package is long-term compatibility, support, security updates, and coordination. Copying a small amount of stable code can be cheaper than coupling two teams through a premature library.

Promote code into a shared module only after repeated, compatible use cases appear. Give it semantic versions, release notes, an owner, and a migration path.

## Govern modules and supply chain

For each repository, decide explicitly:

- which modules are public or private;
- where dependencies are fetched from (`GOPROXY`, `GOPRIVATE`);
- how versions, licenses, vulnerabilities, and licenses are reviewed;
- how reproducible builds and emergency upgrades are handled.

Keep this policy proportional. A small internal service needs a simpler process than a widely distributed SDK, but both need clear accountability.

## Measure whether the structure works

Use evidence rather than folder aesthetics:

- Lead time for a cross-cutting change.
- Number of packages touched by a feature.
- Frequency of dependency upgrades and security fixes.
- Ownership ambiguity and review bottlenecks.
- The effort required to test a use case without infrastructure.

When these worsen, simplify boundaries first. The best Go organization makes the common change local, obvious, and low-risk.
