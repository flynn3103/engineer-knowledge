# Python Code Organization — Middle

Organize by capability: `users`, `billing`, or `notifications`, rather than `models`, `helpers`, and `services` shared by everything.

- Keep framework handlers thin.
- Put business rules in capability packages.
- Keep database and HTTP clients behind focused boundaries.
- Avoid circular imports; they reveal confused ownership.

Use a `src/` layout to prevent tests from importing the working directory instead of the installed package.
