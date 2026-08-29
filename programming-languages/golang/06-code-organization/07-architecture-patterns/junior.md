# Architecture Patterns — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Architecture Patterns** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## What an "Architecture Pattern" Means at the Folder Level

A Go module is a tree of directories. Each directory is a package. Each package can `import` any other package — *unless* the rules of the chosen pattern forbid it.

That is the entire game. An architecture pattern, expressed as Go folders, is:

```
<some directory tree>
+ a rule that says "package X may not import package Y"
```

When the rule is followed, the import graph has the shape the pattern prescribes. When it is broken, the picture stops looking like the pattern's diagram, and you slowly drift back toward "everything imports everything."

Concretely, every pattern below shares three properties:

1. **Business logic gets the cleanest part of the tree.** It does not import frameworks, drivers, or HTTP types.
2. **Infrastructure is replaceable.** You can swap Postgres for SQLite, or HTTP for gRPC, by adding a folder, not by editing the domain.
3. **Tests run without the network.** Because the domain does not depend on the database, you can unit-test it with no Docker container in sight.

The patterns differ in *how* they enforce these properties. Layered does it with horizontal slices. Hexagonal does it with a "core + ports + adapters" picture. Clean does it with concentric rings. Onion is essentially a re-naming of clean. The day-to-day Go folder layouts are surprisingly similar — what differs is the vocabulary and the precise rules.

---

## The Pattern Tour: Four Shapes You Will See

```
LAYERED                 HEXAGONAL                CLEAN                ONION
------------            ---------------          --------------       --------------
| handler  |            +-+--------+-+           +-------------+      +-------------+
+----------+            |A|        |A|           |  Frameworks |      |  Infra/UI   |
| service  |            |D|  CORE  |D|           +-------------+      +-------------+
+----------+            |A|        |A|           |  Adapters   |      | App Services|
| storage  |            +-+--------+-+           +-------------+      +-------------+
+----------+              ^   ^   ^              | Use Cases   |      |   Domain    |
| db       |              |   |   |              +-------------+      |  Services   |
------------            adapter adapter           |  Entities  |      +-------------+
                                                  +-------------+      | Domain Model|
                                                                       +-------------+
```

The four pictures look different. The reality, in a Go module, is that they often produce **very similar folder trees**. The names change; the import rules remain "outside depends on inside, never the reverse."

A short way of holding all four in your head:

- **Layered**: a stack. Each layer talks only to the one directly below.
- **Hexagonal**: a core surrounded by adapters. The core defines interfaces (ports); adapters implement them.
- **Clean**: concentric rings — entities, use cases, interface adapters, frameworks. Dependencies point inward.
- **Onion**: same picture as clean but the rings are named differently (domain model, domain services, application services, infrastructure).

If that sounds repetitive — it is. The teams who picked these names cared about emphasis, not novelty. We will look at each in turn with concrete folders.

---

## Layered Architecture in Go

The oldest pattern in software, and still the right answer for most small services.

### The picture

```
+---------------------+
|    Presentation     |   HTTP handlers, CLI commands, gRPC servers
+---------------------+
|     Application     |   Use cases: "CreateOrder", "ListOrders"
+---------------------+
|       Domain        |   Order, Money, business rules
+---------------------+
|   Infrastructure    |   Postgres driver, S3 client, email sender
+---------------------+
```

The strict rule of "classic" layering: **a layer may only call the layer directly below it.** Some teams relax this to "any layer below," which is more practical and equally common in Go.

### A minimal Go folder tree

```
myshop/
├── cmd/
│   └── shop-api/
│       └── main.go
├── internal/
│   ├── handler/         ← presentation
│   │   └── order.go
│   ├── service/         ← application
│   │   └── order.go
│   ├── domain/          ← business rules
│   │   └── order.go
│   └── repo/            ← infrastructure (DB)
│       └── order.go
├── go.mod
└── go.sum
```

### How the imports look

```
cmd/shop-api  →  internal/handler  →  internal/service  →  internal/domain
                                                     ↘
                                                       internal/repo  →  internal/domain
```

The `domain` package imports nothing from this module. It is the bottom of the tree — a pure island of types and rules. Everything else can import it; it imports nothing back. That is what makes it testable.

### A peek at each layer

**`internal/domain/order.go`**

```go
package domain

import "errors"

type OrderID string

type Order struct {
    ID    OrderID
    Items []Item
    Total int64 // cents
}

type Item struct {
    SKU      string
    Quantity int
    UnitCost int64
}

func (o *Order) Validate() error {
    if len(o.Items) == 0 {
        return errors.New("order has no items")
    }
    return nil
}
```

No `database/sql`, no `net/http`, no third-party imports. Pure types and rules.

**`internal/repo/order.go`**

```go
package repo

import (
    "database/sql"

    "myshop/internal/domain"
)

type OrderRepo struct{ DB *sql.DB }

func (r *OrderRepo) Save(o *domain.Order) error {
    _, err := r.DB.Exec(`INSERT INTO orders (id, total) VALUES ($1, $2)`, o.ID, o.Total)
    return err
}
```

`repo` knows about both SQL *and* the domain. It is glue.

**`internal/service/order.go`**

```go
package service

import "myshop/internal/domain"

type OrderRepo interface {
    Save(*domain.Order) error
}

type OrderService struct{ Repo OrderRepo }

func (s *OrderService) Create(o *domain.Order) error {
    if err := o.Validate(); err != nil {
        return err
    }
    return s.Repo.Save(o)
}
```

`service` defines what it needs (`OrderRepo`) as an interface. The concrete `repo.OrderRepo` satisfies it implicitly. This already starts to look hexagonal.

**`internal/handler/order.go`**

```go
package handler

import (
    "encoding/json"
    "net/http"

    "myshop/internal/domain"
    "myshop/internal/service"
)

type OrderHandler struct{ Svc *service.OrderService }

func (h *OrderHandler) Create(w http.ResponseWriter, r *http.Request) {
    var o domain.Order
    if err := json.NewDecoder(r.Body).Decode(&o); err != nil {
        http.Error(w, err.Error(), 400)
        return
    }
    if err := h.Svc.Create(&o); err != nil {
        http.Error(w, err.Error(), 500)
        return
    }
    w.WriteHeader(201)
}
```

**`cmd/shop-api/main.go`** wires it all up.

```go
package main

import (
    "database/sql"
    "log"
    "net/http"

    _ "github.com/lib/pq"

    "myshop/internal/handler"
    "myshop/internal/repo"
    "myshop/internal/service"
)

func main() {
    db, err := sql.Open("postgres", "postgres://...")
    if err != nil { log.Fatal(err) }

    or := &repo.OrderRepo{DB: db}
    os := &service.OrderService{Repo: or}
    oh := &handler.OrderHandler{Svc: os}

    http.HandleFunc("/orders", oh.Create)
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

That is a complete layered Go service. Five files, ~80 lines, every layer accounted for.

### When layered is the right call

- The service is small to medium (one team, single bounded context).
- You are not yet sure what your "ports" are. Layered does not force you to invent them.
- Junior or mid-level engineers will be reading this code. Layered is the most familiar shape.

### When to outgrow it

- You have more than one external system playing the role of the same abstraction (Postgres *and* in-memory *and* a remote REST cache, all behind "store orders").
- Use cases need to be reused across delivery mechanisms (HTTP *and* a cron job *and* a message handler).
- You start writing tests like "test the service with a fake repo," and you want the fake to feel as natural as the real one.

That is the moment to consider hexagonal.

---

## Hexagonal Architecture (Ports and Adapters) in Go

Cockburn's pattern. The picture is a hexagon, but the shape is incidental. What matters: **the application core defines interfaces (ports); everything outside is an adapter that implements one.**

### The picture

```
                    +-------------------+
       HTTP  ────► |                   | ◄────  Postgres
       gRPC  ────► |    APPLICATION    | ◄────  Redis
       CLI   ────► |       CORE        | ────►  Email API
       Cron  ────► |                   | ────►  Stripe
                    +-------------------+
                       ▲             ▲
                       |             |
                  driving ports   driven ports
                  (incoming)      (outgoing)
```

Two kinds of ports:

- **Driving (input) ports.** The interfaces the *outside* calls *into the core* through. "PlaceOrder."
- **Driven (output) ports.** The interfaces the *core* calls *out to the outside* through. "OrderRepository."

### A minimal Go folder tree

```
myshop/
├── cmd/
│   └── shop-api/
│       └── main.go
├── internal/
│   ├── core/                    ← pure application core
│   │   ├── domain/              ← entities, value objects
│   │   │   └── order.go
│   │   ├── port/                ← interfaces (driving + driven)
│   │   │   ├── input.go         ← OrderService interface
│   │   │   └── output.go        ← OrderRepository interface
│   │   └── service/             ← implementations of the input ports
│   │       └── order.go
│   └── adapter/
│       ├── primary/             ← driving adapters
│       │   └── http/
│       │       └── order.go
│       └── secondary/           ← driven adapters
│           ├── postgres/
│           │   └── order.go
│           └── memory/
│               └── order.go     ← swap-in for tests
├── go.mod
└── go.sum
```

Some teams use `driver/` and `driven/` instead of `primary/` and `secondary/`; both spellings are common.

### How the imports look

```
adapter/primary/http  →  core/port (input)
                     →  core/domain
core/service          →  core/port (output)
                     →  core/domain
adapter/secondary/postgres  →  core/port (output)
                            →  core/domain
```

Critically: **`core/` never imports `adapter/`.** That is the single rule that defines hexagonal.

### Tiny example of the rule

**`internal/core/port/output.go`**

```go
package port

import "myshop/internal/core/domain"

type OrderRepository interface {
    Save(*domain.Order) error
    FindByID(domain.OrderID) (*domain.Order, error)
}
```

**`internal/core/service/order.go`**

```go
package service

import (
    "myshop/internal/core/domain"
    "myshop/internal/core/port"
)

type OrderService struct{ Repo port.OrderRepository }

func (s *OrderService) Place(o *domain.Order) error {
    if err := o.Validate(); err != nil {
        return err
    }
    return s.Repo.Save(o)
}
```

**`internal/adapter/secondary/postgres/order.go`**

```go
package postgres

import (
    "database/sql"

    "myshop/internal/core/domain"
)

type OrderRepo struct{ DB *sql.DB }

func (r *OrderRepo) Save(o *domain.Order) error { /* ... */ return nil }
func (r *OrderRepo) FindByID(id domain.OrderID) (*domain.Order, error) { /* ... */ return nil, nil }
```

Notice `postgres.OrderRepo` does not have to *say* it implements `port.OrderRepository`. Go's structural typing means that as long as the methods match, the assignment in `cmd/main.go` will compile. The port lives in the core; the adapter does not need to know it.

### When hexagonal is the right call

- You have *or expect to have* multiple drivers for the same role (HTTP plus a Kafka consumer plus a CLI, all calling the same use cases).
- You have *or expect to have* multiple secondary adapters (Postgres in prod, SQLite for tests, in-memory for unit tests).
- You want a strong invariant that "domain code is pure Go, no third-party imports" and you are willing to enforce it with tooling.

### When it is overkill

- A 200-line CLI that reads stdin and writes stdout. There is one "adapter" each side. Putting them behind a port is ceremony.
- A throwaway prototype. You will rewrite it.

---

## Clean Architecture in Go

Robert Martin's name for a pattern very close to hexagonal. The picture is the famous concentric circles:

```
       +------------------------------------------+
       |             Frameworks & Drivers         |
       |   +--------------------------------+     |
       |   |       Interface Adapters       |     |
       |   |   +------------------------+   |     |
       |   |   |    Application /       |   |     |
       |   |   |    Use Cases           |   |     |
       |   |   |   +---------------+    |   |     |
       |   |   |   |   Entities    |    |   |     |
       |   |   |   +---------------+    |   |     |
       |   |   +------------------------+   |     |
       |   +--------------------------------+     |
       +------------------------------------------+
```

**The dependency rule.** Source-code dependencies point only inward. An outer ring may know about an inner ring; an inner ring must know nothing about an outer ring.

### A minimal Go folder tree

```
myshop/
├── cmd/
│   └── shop-api/
│       └── main.go
├── internal/
│   ├── entity/                  ← innermost ring
│   │   └── order.go
│   ├── usecase/                 ← application/use-case ring
│   │   ├── place_order.go
│   │   └── ports.go             ← interfaces use cases need
│   ├── adapter/                 ← interface-adapter ring
│   │   ├── http/
│   │   │   └── order.go
│   │   └── repository/
│   │       └── postgres_order.go
│   └── infra/                   ← outermost: drivers, framework setup
│       └── db.go
├── go.mod
└── go.sum
```

Conceptually identical to hexagonal. The terminology shifts: ports become "boundaries," entities have a precise meaning ("enterprise-wide business objects"), and "use cases" is the canonical name for the second ring.

### A use case in Go

**`internal/usecase/ports.go`**

```go
package usecase

import "myshop/internal/entity"

type OrderRepository interface {
    Save(*entity.Order) error
}

type EmailSender interface {
    SendOrderConfirmation(*entity.Order) error
}
```

**`internal/usecase/place_order.go`**

```go
package usecase

import "myshop/internal/entity"

type PlaceOrder struct {
    Repo  OrderRepository
    Email EmailSender
}

func (p *PlaceOrder) Execute(o *entity.Order) error {
    if err := o.Validate(); err != nil {
        return err
    }
    if err := p.Repo.Save(o); err != nil {
        return err
    }
    return p.Email.SendOrderConfirmation(o)
}
```

A use case in clean is a small struct with one method (often `Execute` or `Handle`). One use case per file is the conventional rule.

### When clean is the right call

- You have, or want to enforce, a clear "use cases" layer separate from generic application services.
- The team has read Robert Martin's book and the vocabulary is shared.
- You expect the codebase to grow into many use cases and want each to live in its own file.

### Where it goes wrong in Go

- **Per-method DTO types everywhere.** `PlaceOrderInput`, `PlaceOrderOutput`, `PlaceOrderRequestDTO`. In Go, you often do not need them — entities and `error` are enough.
- **Interfaces invented before they have two implementations.** YAGNI applies. If only one struct will ever implement `OrderRepository`, the interface earns nothing today.
- **`controllers/` and `presenters/` packages cargo-culted from Java/C#.** In Go, an HTTP handler often *is* the presenter. Don't multiply packages without a reason.

---

## Onion Architecture in Go

Jeffrey Palermo's pattern. The picture and the rules are nearly identical to clean architecture. The difference is mostly historical: onion came first (2008); Martin's clean (2012) generalised the same idea.

### The picture

```
       +------------------------------------------+
       |          Infrastructure / UI             |
       |   +--------------------------------+     |
       |   |       Application Services     |     |
       |   |   +------------------------+   |     |
       |   |   |     Domain Services    |   |     |
       |   |   |   +---------------+    |   |     |
       |   |   |   | Domain Model  |    |   |     |
       |   |   |   +---------------+    |   |     |
       |   |   +------------------------+   |     |
       |   +--------------------------------+     |
       +------------------------------------------+
```

Same dependency rule: outer depends on inner; inner knows nothing of outer.

### Onion vs clean: a fast comparison

| Concept | Onion | Clean |
|---|---|---|
| Innermost | Domain Model | Entities |
| Next ring | Domain Services | Use Cases |
| Next ring | Application Services | Interface Adapters |
| Outer | Infrastructure / UI | Frameworks & Drivers |

The vocabulary differs; the folder shapes are essentially interchangeable. Some Go teams pick onion specifically because they want a separate "domain services" ring — operations that span multiple entities but are still pure domain logic, not application use cases.

### A minimal Go folder tree

```
myshop/
├── cmd/
│   └── shop-api/main.go
├── internal/
│   ├── domain/
│   │   ├── model/               ← entities, value objects
│   │   │   └── order.go
│   │   └── service/             ← domain services
│   │       └── pricing.go
│   ├── application/             ← application services / use cases
│   │   └── place_order.go
│   └── infrastructure/
│       ├── http/
│       └── repository/
└── go.mod
```

A domain service in Go is just a package-level struct or function that uses entities but does not depend on infrastructure:

```go
// internal/domain/service/pricing.go
package service

import "myshop/internal/domain/model"

func ApplyDiscount(o *model.Order, percent int) {
    if percent <= 0 || percent >= 100 { return }
    o.Total = o.Total * int64(100-percent) / 100
}
```

### When onion is the right call

- You explicitly want a "domain services" ring distinct from "application services."
- You have a rich domain model with operations that span several entities.
- The team likes the onion vocabulary and is consistent about it.

### When it is overkill

- The domain is anaemic — entities with no methods, no rules to encode. Then "domain services" is just "services," and the extra ring buys nothing.

---

## How They Compare Side by Side

| Aspect | Layered | Hexagonal | Clean | Onion |
|---|---|---|---|---|
| **Year (roughly)** | 1970s | 2005 | 2012 | 2008 |
| **Picture** | Stack | Hexagon with ports | Concentric rings | Concentric rings |
| **Direction rule** | Top-down (sometimes relaxed) | Outside → in only | Outside → in only | Outside → in only |
| **Separate "use case" idea?** | No (lives in service) | Yes (input port) | Yes (explicit ring) | Yes (application services) |
| **Separate "domain service" idea?** | No | No | No | Yes |
| **Where Go interfaces are defined** | In the consumer | In the core (port) | In the inner ring | In the inner ring |
| **Boilerplate cost** | Low | Medium | Medium-high | Medium-high |
| **Best for** | Small/medium services | Multiple drivers + drivees | Large apps with many use cases | DDD-flavoured apps |

The honest summary for Go:

- **Layered** is the default. Reach for it first.
- **Hexagonal** is the upgrade once you have multiple drivers/drivees.
- **Clean** and **onion** are nearly the same as hexagonal; the differences are mostly vocabulary and the explicit names of the rings.

---

## Pros & Cons at a Glance

### Layered

**Pros.** Familiar, low ceremony, easy to onboard, fits 80% of services.
**Cons.** Strict version makes "skip a layer" awkward; relaxed version drifts toward "everything imports everything."

### Hexagonal

**Pros.** Multiple drivers/drivees feel natural; tests are trivial with in-memory adapters; domain stays pure.
**Cons.** More files; teams over-invent ports for things with one implementation.

### Clean

**Pros.** Use cases are first-class citizens; one use case per file scales to dozens of features.
**Cons.** Easy to over-engineer in Go: per-method DTOs, presenters, controllers — all of which can be one struct in idiomatic Go.

### Onion

**Pros.** Explicit "domain services" ring helps when domain logic spans entities.
**Cons.** Almost the same as clean; choosing between them is mostly a taste decision.

---

## Code Examples

### Example 1 — Same feature, four shapes (skeleton only)

**Layered**

```go
// internal/handler/order.go (presentation)
// internal/service/order.go (application)
// internal/domain/order.go  (domain)
// internal/repo/order.go    (infrastructure)
```

**Hexagonal**

```go
// internal/core/domain/order.go
// internal/core/port/output.go         ← OrderRepository interface
// internal/core/service/order.go       ← uses port
// internal/adapter/primary/http/order.go
// internal/adapter/secondary/postgres/order.go
```

**Clean**

```go
// internal/entity/order.go
// internal/usecase/place_order.go
// internal/usecase/ports.go            ← OrderRepository interface
// internal/adapter/http/order.go
// internal/adapter/repository/postgres_order.go
```

**Onion**

```go
// internal/domain/model/order.go
// internal/domain/service/pricing.go
// internal/application/place_order.go
// internal/infrastructure/http/order.go
// internal/infrastructure/repository/postgres_order.go
```

### Example 2 — One concrete `Place` use case under each pattern

**Layered (`internal/service/order.go`)**

```go
func (s *OrderService) Create(o *domain.Order) error {
    if err := o.Validate(); err != nil { return err }
    return s.Repo.Save(o)
}
```

**Hexagonal (`internal/core/service/order.go`)** — same code, different package name and the interface lives in `core/port`.

**Clean (`internal/usecase/place_order.go`)** — same code, named `PlaceOrder` with a single `Execute` method.

**Onion (`internal/application/place_order.go`)** — same code, named after the domain action; might delegate pricing to `internal/domain/service`.

The body of the function is identical. The pattern decides only *where it lives* and *what it imports*.

### Example 3 — Wiring a hexagonal app in `main`

```go
package main

import (
    "database/sql"
    "log"
    "net/http"

    _ "github.com/lib/pq"

    "myshop/internal/adapter/primary/http"
    pg "myshop/internal/adapter/secondary/postgres"
    "myshop/internal/core/service"
)

func main() {
    db, _ := sql.Open("postgres", "postgres://...")
    repo := &pg.OrderRepo{DB: db}             // satisfies port.OrderRepository
    svc  := &service.OrderService{Repo: repo}
    h    := &http.OrderHandler{Svc: svc}

    log.Fatal(http.ListenAndServe(":8080", h))
}
```

`main` is the only place that *knows everyone*. The core has no idea what kind of repository it received; the adapter has no idea who is calling it.

### Example 4 — Replacing the adapter in tests

```go
// internal/adapter/secondary/memory/order.go
package memory

import (
    "errors"

    "myshop/internal/core/domain"
)

type OrderRepo struct{ data map[domain.OrderID]*domain.Order }

func New() *OrderRepo { return &OrderRepo{data: map[domain.OrderID]*domain.Order{}} }

func (r *OrderRepo) Save(o *domain.Order) error {
    r.data[o.ID] = o
    return nil
}

func (r *OrderRepo) FindByID(id domain.OrderID) (*domain.Order, error) {
    o, ok := r.data[id]
    if !ok { return nil, errors.New("not found") }
    return o, nil
}
```

```go
// internal/core/service/order_test.go
func TestPlace(t *testing.T) {
    repo := memory.New()
    svc  := &OrderService{Repo: repo}
    err  := svc.Place(&domain.Order{ID: "1", Items: []domain.Item{{SKU: "x", Quantity: 1}}})
    if err != nil { t.Fatal(err) }
}
```

No database, no Docker, no fixture files. The cost of the in-memory adapter is paid back many times over in test speed and stability.

---

## Coding Patterns

- **One package per ring/layer at the top, sub-packages by feature underneath.** `internal/usecase/order/`, `internal/usecase/billing/` — easier to grow than a flat `internal/usecase/`.
- **Interfaces named after the role, not the implementation.** `OrderRepository`, not `PostgresOrderRepository`. The implementation's package name supplies the qualifier.
- **One file per use case in clean/hexagonal.** Helps you scan features without reading whole packages.
- **`main.go` is the wiring file.** Composition lives there. Treat it like a `compose.yaml` written in Go.

---

## Clean Code

- **No package called `utils`.** It will become a junk drawer regardless of which pattern you picked.
- **No `manager`, `handler`, `processor` without a noun.** Be specific: `OrderService`, `PaymentProcessor`.
- **No imports of `database/sql` outside the infrastructure ring.** That single rule, enforced, accounts for half of what these patterns are trying to give you.
- **Domain types do not have JSON tags.** `json:"..."` is presentation concern. Use a separate DTO or write a custom marshaller in the adapter.

---

## Common Mistakes

- **Treating "clean" as a checklist of folders.** The folders are the *shadow* of the rules; copying the folders without understanding the rules produces the same mess in different drawers.
- **Adding a port for everything.** A function that wraps `time.Now()` does not need a `Clock` interface unless you actually intend to inject a fake.
- **Putting business rules in handlers.** "It's just a quick check" — and now the validation lives in HTTP land and the cron job duplicates it.
- **Defining interfaces in the package that implements them.** The interface should live with the consumer. The implementation should be discovered structurally.
- **Wiring concrete types deep in the call stack.** Every constructor should accept interfaces (where it makes sense) and let `main` decide the concrete types.

---

## Edge Cases & Pitfalls

- **Cross-cutting concerns** (logging, tracing, metrics). They sit *outside* the rings — usually in middleware in primary adapters and in decorators in secondary adapters. Do not pollute the domain with `log.Println`.
- **Transactions.** They do not naturally live in the domain. The application/use case layer typically opens a transaction, hands a transactional `Repository` to the domain operation, and commits or rolls back.
- **Background jobs.** A worker that consumes Kafka is *another primary adapter*, calling the same use cases as HTTP. Put it under `adapter/primary/worker/`.
- **Multiple databases per service.** Each gets its own secondary adapter package: `adapter/secondary/postgres`, `adapter/secondary/redis`. The core sees only ports.

---

## Tricky Points

- **"Pure domain" is a fiction with sharp edges in Go.** `time.Time` is fine. `context.Context` is borderline (some teams allow it in domain methods, others ban it). `errors` is fine. `database/sql` is not fine. Decide your house rules early.
- **Generics push some logic up the rings.** A generic repository interface (`Repository[T any]`) often lives in the use case ring rather than per-entity. That is OK.
- **Go does not enforce package privacy beyond `internal/`.** No `private` keyword on packages. The pattern's rules are *conventions* until you add a tool like `go-arch-lint` (covered in [`professional.md`](professional.md)).
- **`pkg/` is for things you actually want to share across modules.** Inside a single application, prefer `internal/` everywhere. `pkg/` is a public-API promise; do not casually hand it out.
- **Cyclic imports kill any pattern.** Go forbids them at the language level, which is a friend, not an enemy. If you hit a cycle, the design is wrong; do not paper over it with weird interfaces.

---

## Apply it

1. Choose one small, known input for **Architecture Patterns**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Architecture Patterns solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
