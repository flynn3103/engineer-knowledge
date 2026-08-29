# Code Organization

> Make dependencies, ownership, release boundaries, and executable wiring obvious from the repository structure.

## Path

| Step | Topic | Decision you learn to make |
|---|---|---|
| 1 | [Modules and Dependencies](01-modules-and-dependencies/README.md) | What belongs in the module graph, and how is it verified? |
| 2 | [Packages](02-packages/README.md) | Which code changes together behind one package API? |
| 3 | [Project Layout](03-project-layout/README.md) | Which top-level structure fits the actual program? |
| 4 | [Internal Packages](04-internal-packages/README.md) | Which APIs must not become external contracts? |
| 5 | [Workspaces](05-workspaces/README.md) | When should several modules be developed together locally? |
| 6 | [Dependency Injection](06-dependency-injection/README.md) | Where should construction and side effects meet? |
| 7 | [Architecture Patterns](07-architecture-patterns/README.md) | Which boundaries earn their complexity? |
| 8 | [Module Versioning](08-module-versioning/README.md) | How do consumers upgrade without surprise breakage? |
| 9 | [Private Modules](09-private-modules/README.md) | How are authentication and module paths configured safely? |

## Apply it

Draw the import direction for one executable, identify the composition root, and run `go list -deps ./...` plus `go test ./...` to compare the intended boundaries with the actual module graph.
