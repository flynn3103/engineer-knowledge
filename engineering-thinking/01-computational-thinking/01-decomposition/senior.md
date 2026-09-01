# Decomposition - Senior

Choose boundaries that contain future change, preserve business rules, and cost less to reconnect than they save.

## Find natural seams

A seam separates responsibilities, language, data, ownership, or change patterns.

1. Propose a seam from evidence.
2. Check cohesion within both resulting pieces.
3. Check coupling across the boundary.
4. Move or remove the seam if it creates unnecessary dependency.

Use repository and team evidence:

- Which files change together?
- Which rules have different owners?
- Where does a business term change meaning?
- Which parts scale, fail, or release independently?
- Which third-party detail changes frequently?

## Hide volatile decisions

Expose a stable capability, not a vendor or implementation detail.

- Checkout should request `quote(items, destination)` from tax calculation.
- Checkout should not know the tax vendor endpoint, cache, or response shape.
- Complete this sentence for each module: "This prevents the rest of the system from knowing ____."

If no decision is hidden, the boundary may not be useful.

## Use domain language and invariants

- Map important terms with stakeholders. Different definitions are candidate context boundaries.
- Keep one meaning of a term inside a boundary; translate explicitly between contexts.
- Write each critical invariant in one sentence before splitting.
- Keep data and state changes needed for that invariant together.
- If distribution is unavoidable, design idempotency and compensation deliberately.

Example: do not confirm an order until payment is authorized and inventory is reserved.

## Design recomposition first

Trace normal and partial-failure flows across every significant seam. Ask:

- How many synchronous calls are required?
- Who owns timeout, retry, and idempotency behavior?
- Which system owns each fact?
- Can contracts evolve independently?
- What happens if one dependency succeeds and the next fails?

Chatty calls and shared writes are evidence that the seam is weak.

## Choose the right lens

| Lens | Best fit | Risk |
|---|---|---|
| Functional | Pipelines | Shared internal representations |
| Data | Parallel scale | Expensive cross-partition work |
| Domain | Business capabilities | Splitting shared invariants |

Combine lenses when needed. A domain module may use an internal pipeline and regional data partitions.

## Do not extract a service by default

Start with an in-process module. Add a network boundary only with evidence:

- Stable independent ownership.
- Different scaling or release needs.
- Valuable failure isolation.
- Clear data ownership and contained invariants.
- Acceptable operational and integration cost.

## Boundary decision record

```markdown
## Candidate boundary and seam evidence
What responsibilities, data, language, and independent changes support it?

## Hidden decision and invariants
What volatility is contained, and which rules must remain inside?

## Recomposition and contract
Trace normal and failure flows; define data, operations, and version ownership.

## Alternatives
Why is a smaller refactor or in-process module insufficient?
```

## Checklist

- [ ] Change, language, ownership, and invariant evidence support the seam.
- [ ] Each boundary hides a concrete volatile decision.
- [ ] Data ownership, contracts, retries, and failure recovery are explicit.
- [ ] Integration cost is lower than the independence gained.
- [ ] Distribution has a concrete benefit.

> Cut where change and invariants naturally separate, then calculate the cost of reconnecting the pieces.

Next: [Professional level](professional.md)

## Check your understanding

1. How are seams, cohesion, and coupling different?
2. Why must invariants shape system boundaries?
3. What evidence justifies service extraction?
