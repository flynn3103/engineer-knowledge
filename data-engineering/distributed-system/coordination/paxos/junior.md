# Paxos — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Why can't a group of nodes just take a simple majority vote to agree on a
> value, when any node can crash or be slow at any moment?

---

## The problem: agreeing on one value, safely, despite failures

Imagine 5 nodes that must agree on a single value (which transaction
commits first, who the leader is, what the next log entry is) — and any
node can crash, restart, or have messages delayed arbitrarily, at any time,
without warning.

```mermaid
flowchart TD
    N1[Node 1: proposes "A"] --> Vote{Naive majority vote}
    N2[Node 2: proposes "B"\nat nearly the same time] --> Vote
    Vote --> Problem["What if the network delays\nmessages so different nodes\nsee different proposals\nas 'first'?"]
```

A naive "first proposal wins" approach breaks immediately under real
network conditions: different nodes can receive proposals in **different
orders**, or a node can crash **after** convincing some nodes to accept its
value but **before** convincing enough of them, leaving the system in an
ambiguous state — did that value get chosen or not? Paxos (Leslie Lamport,
1998 paper, though the ideas predate the paper's publication) is the first
rigorously proven protocol answering: **how do you guarantee that once a
value is chosen, every node eventually learns the *same* chosen value, even
though nodes fail and messages get delayed, reordered, or lost (but not
corrupted)?**

## The three roles

```mermaid
flowchart LR
    Proposer["Proposer:\nsuggests a value"] --> Acceptor["Acceptor:\nvotes on proposals"]
    Acceptor --> Learner["Learner:\nfinds out what was chosen"]
```

- **Proposers** suggest values (candidate leader, candidate log entry).
- **Acceptors** vote on proposals — a value is **chosen** once a **majority**
  of acceptors have accepted it.
- **Learners** find out which value was chosen (often, a proposer is also a
  learner).

> 🎓 **Takeaway:** the hard part isn't "get everyone to agree when
> everything works" — it's "guarantee agreement is never violated, no
> matter what combination of crashes, delays, and message reordering
> happens." Paxos's entire complexity exists to close every one of those
> edge cases with a proof, not a hope.

## Test yourself

1. Why does "the first message to arrive wins" fail as a consensus protocol
   once you allow for network delay and reordering?
2. What does "a value is chosen once a majority of acceptors accept it"
   guarantee about any *other* possible majority, given there are 5 total
   acceptors?
3. Why might a single proposer crashing partway through convincing acceptors
   leave the system in an ambiguous state, requiring some mechanism to
   safely continue or restart the process?

Continue to [`middle.md`](middle.md).
