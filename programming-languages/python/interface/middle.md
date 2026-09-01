# Python Interfaces — Middle

Design boundaries around what callers need, not around implementation classes.

- Use `Protocol` for behavior-based dependencies.
- Use dataclasses or validated models for stable data shapes.
- Keep optional parameters rare; a growing parameter list signals a new object or use case.
- Make invalid states difficult to construct.

```python
from typing import Protocol

class UserStore(Protocol):
    def get(self, user_id: str) -> "User": ...
```

Type-check in CI and keep runtime validation at system boundaries.
