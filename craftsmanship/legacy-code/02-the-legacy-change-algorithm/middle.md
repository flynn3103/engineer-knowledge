# The Legacy Change Algorithm — Middle

## Apply the algorithm deliberately

The five steps stay the same. At this level, make each one precise enough that another engineer can review your reasoning.

## 1. Identify the change point

- Write the requested behavior in one observable sentence.
- Trace callers, outputs, and side effects until you can name the narrowest responsible unit.
- Separate the requested change from nearby cleanup ideas.

## 2. Find a test point

- **Sensing:** an output, state change, emitted event, or returned error a test can inspect.
- **Interception:** a collaborator a test can replace to control inputs or prevent real I/O.
- Prefer public behavior. Use internal seams only when no useful public observation exists.

## 3. Break only the needed dependency

```python
class InvoiceService:
    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def mark_overdue(self, invoice_id: str) -> bool:
        invoice = self.repository.get(invoice_id)
        if invoice.due_date < self.clock.today():
            invoice.mark_overdue()
            return True
        return False
```

- Pass time, storage, network clients, and randomness into the unit.
- Keep the new seam narrow; do not redesign the whole module to test one decision.

## 4. Characterize behavior

- Use real, representative inputs.
- Assert what the system does today, even when it looks odd.
- Name the test after the observed rule, not after the implementation.
- Add multiple examples when one input cannot define the boundary safely.

## 5. Change and refactor

1. Run the characterization tests.
2. Make the requested behavior change in a small commit.
3. Add or update tests that state the new rule.
4. Refactor only with the safety net green.

## When tests are expensive

- **Sprout method:** add a new, tested helper and call it from the old code.
- **Sprout class:** add a focused collaborator for new behavior.
- **Wrap method/class:** put a tested layer around the existing behavior to add or observe a change.

Use these to route risk around code that cannot yet be opened safely. They are not excuses to leave the boundary unexplained.

## When you are stuck

- Reduce the requested behavior to one example.
- Add logging or a temporary probe to discover current inputs and outputs.
- Ask a domain expert to validate the observed behavior.
- Find a lower-level pure function or a higher-level integration boundary.
- Record assumptions in the PR instead of silently guessing.

## Review checklist

- [ ] The change point is specific and observable.
- [ ] Tests assert behavior, not incidental private structure.
- [ ] Dependency breaking is minimal and justified.
- [ ] Existing behavior is characterized before intentional change.
- [ ] Sprout or wrap is used when direct modification is disproportionately risky.
