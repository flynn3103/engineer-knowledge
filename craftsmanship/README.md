# Craftsmanship

> Craftsmanship is the discipline of making software safe to understand, change, review, operate, and improve.

This roadmap integrates thinking skills and practical disciplines, presenting each through junior, middle, senior, and professional responsibility levels.

## Part 1: Engineering Thinking

The foundational thinking skills that surround implementation. Start with framing and solving a single problem, expand into systems and uncertainty, and finish with techniques for generating better options, modeling responsibilities, testing beliefs, and improving how you learn.

| # | Topic | What you'll learn |
|---|---|---|
| 01 | [Computational Thinking](engineering-thinking/01-computational-thinking/) | Decompose problems, recognize recurring structures, choose useful abstractions, design algorithms, and map domain concepts into code. |
| 02 | [Problem-Solving](engineering-thinking/02-problem-solving/) | Understand the real problem, devise and execute a plan, debug from evidence, reflect, and recover when you are stuck. |
| 03 | [Systems Thinking](engineering-thinking/03-systems-thinking/) | Reason about emergence, feedback loops, second-order effects, trade-offs, leverage points, and bottlenecks. |
| 04 | [Critical Thinking](engineering-thinking/04-critical-thinking/) | Separate claims from evidence, catch fallacies and cognitive biases, and compare engineering trade-offs objectively. |
| 05 | [First-Principles Thinking](engineering-thinking/05-first-principles-thinking/) | Reduce a problem to genuine constraints, challenge inherited assumptions, and rebuild possible solutions from fundamentals. |
| 06 | [Probabilistic Thinking](engineering-thinking/06-probabilistic-thinking/) | Make calibrated decisions with base rates, expected value, failure probabilities, risk, and uncertain estimates. |
| 07 | [Creative and Lateral Thinking](engineering-thinking/07-creative-and-lateral-thinking/) | Generate and evaluate non-obvious options through divergence, inversion, analogy, and productive constraints. |
| 08 | [Object Thinking](engineering-thinking/object-oriented-design/) | Model behavior and responsibility, use tell-don't-ask and CRC techniques, and recognize when object thinking is the wrong fit. |
| 09 | [Scientific and Hypothesis-Driven Thinking](engineering-thinking/09-scientific-and-hypothesis-driven/) | Form falsifiable hypotheses, design experiments, measure before optimizing, and use spikes to retire uncertainty. |
| 10 | [Metacognition and Learning](engineering-thinking/10-metacognition-and-learning/) | Inspect your own reasoning, practice deliberately, learn efficiently, and map the limits of your knowledge. |

## Part 2: Practical Disciplines

Seven essential practices for making code safe, understandable, and maintainable.

| Discipline | Main outcome |
|---|---|
| [Code Review](code-review/README.md) | Improve correctness, design, security, learning, and team flow. |
| [Diagnostics](diagnostics/README.md) | Turn production symptoms into evidence, mitigation, and durable learning. |
| [Documentation](documentation/README.md) | Keep decisions, interfaces, and operations understandable and current. |
| [Legacy Code](legacy-code/README.md) | Create safety before changing code you do not fully understand. |
| [Object-Oriented Design](object-oriented-design/README.md) | Assign behavior and responsibility while controlling coupling. |
| [Professionalism](professionalism/README.md) | Make honest commitments, protect quality under pressure, and collaborate responsibly. |
| [Technical Debt](technical-debt/README.md) | Manage future change cost as an explicit engineering investment. |

## Level progression

```mermaid
flowchart LR
    Junior[Junior: make one safe change] --> Middle[Middle: improve a module]
    Middle --> Senior[Senior: protect a system]
    Senior --> Professional[Professional: shape engineering capability]
```

Use the lowest level that matches your current responsibility, apply its method to real work, and move up when you can explain the trade-offs and verify the result independently.

## How to use this guide

**Step 1:** Pick a topic from Part 1 (thinking) or Part 2 (practice) that matches your current challenge.

**Step 2:** Start at the level that fits your responsibility: Junior for assigned tasks, Middle for module ownership, Senior for system-level decisions, Professional for organization-scale impact.

**Step 3:** Apply one concrete practice from that level to real work. Verify it works. Move to the next level when you can explain the trade-offs.
