# Go Code Organization — Junior

Your first job is to make a small program easy to read. A reader should find the entry point, the feature code, and the tests without guessing.

## Start with one module

Create a module once, then run commands from its root:

```bash
go mod init github.com/acme/todo
go mod tidy
go test ./...
```

Commit both `go.mod` and `go.sum`. Do not edit `go.sum` by hand; Go maintains it.

## Use packages to group related behavior

All files in a folder normally belong to one package. Put code together when it changes for the same reason.

```text
todo/
├── cmd/todo/main.go
├── task/task.go
├── task/service.go
└── task/service_test.go
```

```go
// task/service.go
package task

type Service struct{ store Store }

func (s Service) Complete(id string) error {
	return s.store.MarkComplete(id)
}
```

Keep tests beside the code they test. A test in `task/service_test.go` documents how callers are expected to use `task`.

## Export only the small public surface

An uppercase name is visible to other packages; a lowercase name is private to its package.

```go
package task

type Task struct { // exported: callers can use it
	ID string
}

func validateID(id string) error { // private implementation detail
	return nil
}
```

Make a name exported only when another package truly needs it. Fewer exported names make refactoring safer.

## Keep `main` boring

`main.go` should configure and connect the program, then call application code. Do not put business rules, SQL, and HTTP handlers together in `main`.

```go
func main() {
	store := postgres.NewStore(os.Getenv("DATABASE_URL"))
	service := task.NewService(store)
	server := httpapi.NewServer(service)
	log.Fatal(server.ListenAndServe())
}
```

## Before you add a folder

Ask these questions:

- Does this code have one clear job?
- Will another package import it?
- Would a new teammate know why it exists from its name?

If the answer is no, keep the code in its current package for now.
