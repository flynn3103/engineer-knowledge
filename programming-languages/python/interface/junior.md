# Python Interfaces — Junior

An interface is the small promise your code makes to its caller.

- Name functions after actions and return values consistently.
- Use type hints for inputs and outputs.
- Prefer a small class or function over a large dictionary with undocumented keys.
- Keep public functions easy to call and test.

```python
def format_name(first: str, last: str) -> str:
    return f"{first.strip()} {last.strip()}"
```

Write one example test for every public behavior.
