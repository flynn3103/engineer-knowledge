# Tidy First — When and How — Senior

Senior practice uses tidying to reduce change risk, not to maximize local elegance. The key decision is how much structural work buys a safer, faster next change.

## Sequence by reversibility

Start with moves that are easy to reason about, verify, and revert. Examples: rename, extract a pure decision, isolate an adapter, then alter behavior. Defer moves that redefine ownership, data flow, or public contracts until their risks are explicit.

## Keep the system shippable

- Each tidy should compile and pass its relevant tests.
- Separate structural and behavioral commits so review and rollback are clear.
- Use characterization tests when preservation is uncertain.
- Watch for seams, transaction boundaries, and observability disappearing during extraction.

## Decide when not to tidy

Do not tidy first when an incident needs the shortest safe fix, the intended behavior is unclear, the cleanup has a large blast radius, or the code will not be touched again soon. In those cases, contain the change and create a bounded follow-up if the economics support it.

## Review prompts

- What exact future step becomes cheaper after this tidy?
- What evidence proves behavior preservation?
- Could another team’s concurrent work make this tidy costly?
- Is this still small enough to abandon without regret?
