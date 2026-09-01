# Python Error Handling — Junior

Use exceptions for exceptional outcomes and make the failure useful.

- Catch the narrowest exception you can handle.
- Add context when re-raising.
- Use `finally` or `with` for cleanup.
- Never use a bare `except:`; it also catches interrupts and system exits.

```python
try:
    user = load_user(user_id)
except FileNotFoundError as exc:
    raise UserNotFound(user_id) from exc
```

Test both the successful result and the expected failure.
