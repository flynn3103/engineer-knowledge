# Infrastructure

> Ship a running instance safely across environments — containers, orchestration, deployment strategies, pipelines, infrastructure as code, and the network/scaling mechanics that keep it running.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Containers and Docker](containers-and-docker/junior.md) | Package an application into a container image and run it. |
| 02 | [Kubernetes Orchestration](kubernetes-orchestration/junior.md) | Run many containers together with Pods, Deployments, and Services. |
| 03 | [Deployment Strategies](deployment-strategies/junior.md) | Replace a running version safely — rolling, blue-green, canary. |
| 04 | [CI/CD Pipelines](ci-cd-pipelines/junior.md) | Get code from commit to a deployable artifact and trigger a deploy. |
| 05 | [Infrastructure as Code](infrastructure-as-code/junior.md) | Declare and provision infrastructure as version-controlled code. |
| 06 | [Multi-Region Deployment](multi-region-deployment/junior.md) | Run a service across regions — active-active vs. active-passive. |
| 07 | [Autoscaling](autoscaling/junior.md) | Adjust running capacity automatically as load changes. |
| 08 | [GitOps (Argo CD, Flux)](gitops-argocd-flux/junior.md) | Drive delivery from a git repo as the pull-based source of truth. |
| 09 | [Virtual Machine](virtual-machine/junior.md) | Use VMs as a deployment unit and know when to choose them over containers. |
| 10 | [Network](network/README.md) | Understand the wire-level mechanics (TCP/UDP, TLS, HTTP evolution) and cloud network architecture (VPC) infrastructure runs on. |

## How to use this section

Each topic has four depth levels — **junior → middle → senior → professional**. Start at your level and climb. Containers and Docker is the foundation everything else packages and runs; Kubernetes Orchestration and Deployment Strategies build on it; CI/CD Pipelines and Infrastructure as Code are how changes get there in the first place, with GitOps as a pull-based alternative to pipeline-driven delivery. Multi-Region Deployment and Autoscaling are the operational mechanics that keep a running system available under load, and Network (including cloud network architecture / VPC) is the substrate all of it runs on. Virtual Machine is the alternative deployment unit to containers, useful when isolation or compliance needs outweigh container density.

> Recovering from a large-scale disaster (RPO/RTO, failover drills) now lives in [Craftsmanship → On Production → Disaster Recovery](../craftsmanship/on-production/disaster-recovery/README.md), alongside the rest of the post-launch reliability practice.

---

> Part of the [Engineer Knowledge](../README.md) roadmap. See also [On Production](../craftsmanship/on-production/README.md) for what happens to a system once it's running on this infrastructure.
