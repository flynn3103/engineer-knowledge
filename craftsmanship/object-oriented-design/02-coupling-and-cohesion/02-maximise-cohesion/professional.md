# Maximise Cohesion — Professional

> **Level:** professional. A concise guide for applying this design principle.

## Core idea

Keep code that changes for the same reason together; split unrelated responsibilities.

## Apply it

- Identify the responsibility, dependency, or assumption that creates risk.
- Make the smallest change that gives it a clear boundary.
- Verify behavior with a focused test or review scenario.

## Level focus

- Junior: apply the rule to one small change.
- Middle: explain the local trade-off to a teammate.
- Senior: protect boundaries and migration paths across a system.
- Professional: turn the rule into shared review and delivery practice.

## Python sketch

```python
def apply_design_rule(value):
    """Keep behavior explicit and the boundary small."""
    return value
```
