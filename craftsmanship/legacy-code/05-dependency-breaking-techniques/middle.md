# Dependency-Breaking Techniques — Middle

Choose a technique based on the dependency you must control and the amount of code you can safely move.

## Useful techniques

| Problem | Smallest practical technique |
|---|---|
| Hidden pure logic | Extract function or method |
| Direct SDK or I/O call | Wrap it in an adapter |
| Object creates collaborator | Constructor or parameter injection |
| Global time/configuration | Pass a clock or settings object |
| Large method mixes decisions and effects | Separate decision from effect |

```python
def discount_for(total: float) -> float:
    return 0.10 if total >= 100 else 0.0

def checkout(total: float, charge) -> float:
    final = total * (1 - discount_for(total))
    charge(final)
    return final
```

`discount_for` is now easy to characterize; `charge` can be faked. Keep the behavior and call order intact while extracting.

## Decision rules

- Prefer extraction before introducing a new type.
- Prefer an adapter at an external boundary over leaking a vendor API throughout the domain.
- Preserve the public API during migration with a delegating default.
- Use inheritance or patching only when an interface cannot be introduced safely yet.

After each step, run the characterization tests. If they fail, revert the small step and understand the hidden coupling before proceeding.
