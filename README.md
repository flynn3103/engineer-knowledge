# 🎓 Engineer Knowledge

> A personal project for organizing, consolidating, and strengthening the essential knowledge needed to grow as an engineer.

### 🌐 Live site: **[flynn3103.github.io/engineer-knowledge](https://flynn3103.github.io/engineer-knowledge/)**

## Purpose

The knowledge required for modern engineering work is scattered across countless blogs, courses, and documentation. This project brings it all together in **one place**, in a **structured way**, organized around six domains:

- **Craftsmanship** — engineering thinking (computational, systems, critical, first-principles, probabilistic, creative, debug-thinking, scientific reasoning), code review, object-oriented design, documentation, legacy code, professionalism, and on-production practice (estimation, testing, performance, release, SRE & reliability, security, privacy, cost)
- **Programming Languages** — Go, Python, plus shared language/runtime internals
- **Infrastructure** — containers, Kubernetes, deployment strategies, CI/CD, IaC, GitOps, multi-region, disaster recovery, autoscaling, VPC, virtual machines, and network protocols
- **Data Engineering** — service communication and APIs, databases, distributed systems, event streaming, orchestration, storage, and concurrent processing
- **AI Engineering** — LLM fundamentals (including model selection/fine-tuning), RAG, agent architecture, evaluation, and MLOps
- **Blog** — *coming soon*

## Project Structure

```
📁 engineer-knowledge
├── 📂 craftsmanship/                     # Thinking skills + practical disciplines + on-production practice
│   ├── engineering-thinking/             # 11 sections: computational → object thinking (incl. debug-thinking)
│   ├── code-review/                      # Review practices across levels
│   ├── documentation/                    # Decisions, interfaces, operations
│   ├── legacy-code/                      # Working with unfamiliar code safely
│   ├── object-oriented-design/           # Behavior, responsibility, coupling
│   ├── professionalism/                  # Reliability, growth, integrity
│   └── on-production/                    # Estimation, testing, performance, release, SRE & reliability, security, privacy, cost
├── 📂 programming-languages/
│   ├── golang/                           # Go roadmap — concurrency through production debugging
│   ├── python/                           # Python roadmap
│   └── language-internals/               # Runtime, memory, types, compilers, and interoperability
├── 📂 infrastructure/                    # Containers, orchestration, deployment, CI/CD, IaC, GitOps, VPC, VMs, and protocols
├── 📂 data-engineering/                  # Communication/APIs, databases, distributed systems, streaming, scheduling, storage, and concurrency
├── 📂 ai-engineering/                    # LLM fundamentals (incl. model selection/fine-tuning), RAG, agents, evaluation, MLOps
└── 📂 blog/                              # Coming soon
```

## How to use

Each topic follows a consistent multi-level file structure:

| File | Purpose |
|------|---------|
| `README.md` | Topic overview and navigation |
| `junior.md` | Foundations a junior developer needs |
| `middle.md` | Mid-level depth and patterns |
| `senior.md` | Senior-level mastery |
| `professional.md` | Expert-level production knowledge |

Every level guide ends with unanswered comprehension questions for active recall.

## Who is this for?

This project was primarily created for personal use, but anyone looking to grow as an engineer is welcome to use it.

## License

[MIT](LICENSE) — flynn3103, 2026
