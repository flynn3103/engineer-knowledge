# Python Code Organization — Junior

Organize a project so a reader can find the entry point, feature code, and tests quickly.

```text
my_app/
├── src/my_app/
│   ├── __init__.py
│   ├── users.py
│   └── main.py
└── tests/test_users.py
```

- Group related behavior in a module.
- Keep tests next to the feature in the test tree.
- Avoid `utils.py` as a dumping ground.
- Keep executable startup code in `main.py` or a CLI module.

Move code only when its responsibility becomes clearer, not merely because a file grows.
