# Infrastructure as Code — Middle

<!-- level-focus -->
At middle level, focus on this question:

> How do you structure Terraform state and modules so that a mistake in staging cannot destroy production?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

## 1. From "One Config" to "Many Environments"

At junior level, one configuration managing one bucket is enough. In a real system you have at least staging and production, usually more (dev, staging, prod, maybe per-region copies), and the moment a second environment exists you face a boundary decision: **does staging and production share one state file, or do they each get their own?**

Sharing one state file means one `terraform apply` can touch both environments in a single run — convenient until a variable is wrong and a "small" change to staging's instance size accidentally resizes production's. Separate state files mean an engineer can only ever affect the environment they're pointed at, at the cost of some duplicated configuration. This is the central trade-off of this level: **isolate blast radius, but don't duplicate so much that the environments drift apart from each other by accident.**

## 2. Remote State and Locking

A local `terraform.tfstate` file works for one person on one laptop. It fails the moment a second person needs to run `apply` — there's no shared source of truth, and no protection against two people applying at the same time. The fix is a **remote backend** with **locking**:

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "acme-terraform-state"
    key            = "networking/vpc/staging/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

- The **S3 bucket** stores the actual state file (with versioning enabled, so a corrupted or bad write can be rolled back).
- The **DynamoDB table** provides a distributed lock: when someone runs `apply`, Terraform writes a lock record before touching anything, and a second `apply` against the same `key` fails immediately with "Error acquiring the state lock" instead of racing.
- The `key` is the address of *this specific* state file. Staging and production point at different keys (`.../staging/terraform.tfstate` vs `.../prod/terraform.tfstate`), which is what actually separates their blast radius — not the code, the **backend configuration**.

## 3. Isolating Blast Radius: Three Options

| Approach | How it separates environments | Blast radius if a mistake happens | Change cost |
|---|---|---|---|
| **One state, `count`/`for_each` over environments** | Same state file holds both | Total — a bad `apply` can touch every environment at once | Lowest to write, highest to operate |
| **Terraform workspaces** (`terraform workspace new prod`) | Same backend key prefix, separate internal state per workspace | Contained per workspace, but easy to `apply` in the wrong workspace by mistake (no visual cue in the terminal) | Low — same code, switch context with one command |
| **Directory-per-environment** (`environments/staging/`, `environments/prod/`) | Fully separate backend `key`, separate `.tfvars`, often separate provider credentials | Contained — you can only run `apply` from inside the directory you're in, and the directory name is visible | Higher — some duplication across directories, resolved by pulling shared logic into modules |

The middle-level judgment: **workspaces are fine for many near-identical short-lived environments (e.g., per-feature preview environments); directory-per-environment is the safer default for staging vs. production**, because the separation is visible in the file path, not hidden in an easy-to-forget `terraform workspace select` command.

## 4. Module Composition

Once you have more than one environment, copy-pasting the same VPC/database HCL into each one guarantees they drift apart over time — someone fixes a bug in staging and forgets prod exists. The fix is a **module**: a directory of `.tf` files with input variables and outputs, called once per environment with different values.

```text
modules/
  network/
    main.tf        # resource blocks: VPC, subnets, route tables
    variables.tf   # environment, cidr_block, az_count
    outputs.tf     # vpc_id, subnet_ids
environments/
  staging/
    main.tf
    staging.tfvars
  prod/
    main.tf
    prod.tfvars
```

```hcl
# environments/staging/main.tf
module "network" {
  source      = "../../modules/network"
  environment = "staging"
  cidr_block  = "10.20.0.0/16"
  az_count    = 2
}
```

```hcl
# environments/prod/main.tf
module "network" {
  source      = "../../modules/network"
  environment = "prod"
  cidr_block  = "10.30.0.0/16"
  az_count    = 3
}
```

The module is the single place the VPC's actual logic lives; each environment only supplies the values that legitimately differ (address space, availability zone count). A bug fix in `modules/network/main.tf` benefits every environment the next time each one runs `plan` — but each environment still applies independently, on its own schedule, against its own state.

## 5. Verification: Unit and Integrated-Flow Levels

| Level | Command / action | What it catches |
|---|---|---|
| **Unit** | `terraform validate` | Syntax errors, type mismatches, missing required arguments — before any network call |
| **Unit** | `terraform plan` in CI on every pull request | Unexpected diffs, accidental destroys, a variable that resolves to the wrong environment |
| **Unit** | `terraform plan -refresh-only` | Drift — where reality has moved away from state, without proposing to "fix" it destructively |
| **Integrated** | `terraform apply` against a real sandbox/staging environment | Whether the module's resources actually come up healthy together, not just individually |
| **Integrated** | A smoke test hitting the deployed endpoint (e.g., `curl` against the new load balancer, or a query against the new database) after apply | Whether the infrastructure is not just *created* but *usable* |

Treat the CI-posted `plan` diff as the primary code review artifact for infrastructure changes — reviewing the HCL alone tells you the intent; reviewing the plan diff tells you the actual effect. A one-line variable typo that silently changes `az_count` from `3` to `2` in production is invisible in a code diff but glaring in a plan diff ("1 to destroy").

## 6. Under- and Over-Application Signals

| Signal | What it means | Fix |
|---|---|---|
| The same 40-line HCL block appears in 3+ environment directories with only values changed | Under-applied — should be a module | Extract into `modules/`, parameterize the differences |
| A module has 20 input variables to handle 3 environments that only ever differ in 2 of them | Over-applied — premature generalization for imagined future callers | Collapse back to the 2 real variables; add more only when a second real caller needs them |
| One state file manages network, database, and application for both staging and prod | Under-applied blast-radius isolation | Split into per-environment (and eventually per-layer) state files |
| Every tiny resource (a single security group rule) is its own module with its own README | Over-applied modularization — more indirection than the resource justifies | Inline small, single-use resources directly in the environment's `main.tf` |

## 7. Incremental Adoption: Bringing Existing Resources Under IaC

Real systems are rarely greenfield. A security group created by hand two years ago still needs to be *managed*, not recreated (recreating it would briefly remove the rules and could cause an outage). `terraform import` attaches an existing resource to a resource block without changing it:

```bash
$ terraform import aws_security_group.app_sg sg-0abc123def456
aws_security_group.app_sg: Importing from ID "sg-0abc123def456"...
aws_security_group.app_sg: Import complete!

Resource actually imported: aws_security_group.app_sg
```

Immediately follow with `terraform plan`. If your `.tf` block doesn't yet match the real configuration, the plan will show the *difference* between what you wrote and what actually exists — write the resource block to match reality first, get to "No changes," and only then make deliberate changes going forward.

## 8. A Cross-Component Scenario

A team is asked to add a read-replica database to staging without touching production. The stack has:

- `modules/network` (VPC, subnets) — shared by both environments
- `modules/database` (RDS primary + optional replica) — new `replica_count` variable added
- `environments/staging/main.tf` calling both modules with `replica_count = 1`
- `environments/prod/main.tf` calling both modules, left at `replica_count = 0`

Because staging and production have separate backend keys, running `terraform apply` inside `environments/staging/` can only ever touch staging's state. The `plan` output for staging shows "1 to add" (the new replica); the `plan` output for production — run separately, deliberately, from its own directory — shows "No changes," which is the evidence that the change is actually isolated.

## Apply it

1. Take a single-environment Terraform config that manages one VPC and one database instance, and extract the VPC logic into `modules/network` with `environment`, `cidr_block`, and `az_count` as variables.
2. Create `environments/staging/` and `environments/prod/` directories, each with its own `main.tf` calling `modules/network`, and its own S3 backend `key` plus DynamoDB `dynamodb_table` for locking.
3. From two separate terminals, run `terraform apply` inside `environments/staging/` at the same time and confirm the second run fails with a state-lock error instead of racing.
4. Add a CI job that runs `terraform validate` and `terraform plan` against both environment directories on every pull request, and require the plan diff to be visible in the PR before merge is allowed.
5. Find one resource in either environment that was created manually (or simulate one by creating a security group by hand), and bring it under management with `terraform import` followed by a `plan` that reaches "No changes."

## Verify your work

- `terraform state list` run inside `environments/staging/` and inside `environments/prod/` shows two different, independent resource lists tied to two different state files.
- The concurrent-apply test produces an explicit lock error ("Error acquiring the state lock"), not a corrupted or partially-applied state.
- A change applied only in staging produces "No changes" when `terraform plan` is run in the production directory afterward.
- The CI-posted plan diff for a pull request matches what `terraform apply` actually does after merge — no surprises between review and execution.
- The imported resource's `terraform plan` reaches "No changes" before any further edits are made to it.

## Review questions

- What decides whether staging and production should share a state file or use separate ones?
- What evidence would show that state locking is actually preventing a concurrent-apply race, not just configured?
- When does extracting a module pay off, and when does it just add indirection over a single-use resource?
- How do you verify an infrastructure change at both the unit level (one resource) and the integrated-flow level (the whole stack working together)?
