# Over-Engineering Anti-Patterns — Junior

> Over-engineering adds moving parts before the problem proves they are needed.

## Goal

Build the simplest solution that satisfies the current requirement, and capture future ideas without quietly adding them to the work.

## The shapes

| Anti-pattern | Signal | Better move |
|---|---|---|
| Premature optimization | Tuning without a measured bottleneck. | Write clear code; measure first. |
| Speculative generality | An abstraction has one use. | Keep a concrete implementation. |
| Gold plating | Extra features are not requested. | Finish acceptance criteria first. |
| Yo-yo problem | Behavior is spread through deep inheritance. | Prefer simple composition. |
| Lasagna code | Layers only forward calls. | Remove the layer or give it a job. |
| Accidental complexity | Tools outweigh the problem. | Choose the smallest dependable mechanism. |
| Soft coding | Rules hide in vague configuration. | Keep stable rules in typed code. |
| Bikeshedding | Minor choices consume major time. | Decide by impact and time-box debate. |

## Start concrete

```python
def apply_discount(total, is_member):
    if is_member:
        return total * 0.9
    return total
```

Do not create a plugin system or strategy hierarchy until real variation requires it. A small concrete function is easier to read, test, and replace.

## Keep scope visible

- Read the acceptance criteria before coding.
- Put useful but unrequested ideas in a backlog item or note.
- Ask before expanding a public API, schema, or dependency.
- Prefer one obvious path over options that no caller uses.

## Avoid fake flexibility

```python
def load_rules():
    return {"member_discount": 0.10}

def apply_discount(total, rules):
    return total * (1 - rules["member_discount"])
```

This is appropriate only when a trusted owner must change the rule without a deploy and the input is validated, audited, and tested. Otherwise, the configuration merely hides ordinary code.

## Before you commit

- Which requirement needs every new layer, option, or dependency?
- What evidence says this is a performance bottleneck?
- Can one function or object solve the problem clearly?
- Did you spend review time on the highest-risk question?

## Check your understanding

1. When does an abstraction earn its existence?
2. Why can configuration create more complexity than code?
3. Which part of your current work is outside the requested scope?
