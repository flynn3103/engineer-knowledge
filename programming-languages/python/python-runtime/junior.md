# Python Runtime — Junior

Python runs your source as objects and function calls. Start with predictable code before chasing internals.

- Use a virtual environment and record dependencies.
- Know mutability: lists and dicts can change; integers and strings cannot.
- Avoid mutable default arguments; use `None` and create the list inside.
- Use `is None`, not `== None`.

```python
def add_tag(tags=None):
    tags = [] if tags is None else tags
    tags.append("new")
    return tags
```

Run `python -m pytest` and reproduce surprising behavior in a tiny script before changing production code.
