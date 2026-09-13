# Systems Thinking — Best Practise

How to make loop-tracing something you just do without thinking, and how to make it work for a whole team — not just when you personally happen to catch the problem.

## Practice this every day

- **Before you fix anything:** draw the loop the problem sits in. What feeds it, what it feeds, and how it circles back to the start. A fix that doesn't touch the loop is just a patch, not a real fix.
- **Before you change a number under load:** check first — is this a loop that settles on its own (safe to tune), or one that keeps feeding itself (tuning a number here can make it worse)? Check whether anything stops it before you touch it.
- **Before you call a fix "done":** name the slowest-moving thing in the loop (a cache that takes time to refill, a system that takes time to warm up) and check the fix still holds once that catches up — not just the fast thing you could watch during the incident.

## The pattern that works past one system: pair every target number with a check-number

Once the "parts" of a system are whole teams, the same feeds-on-itself problem shows up as people gaming their numbers: once a number becomes a target, people find ways to move the number without actually improving the thing it was meant to measure. A team measured on "tickets closed" can hit the target by closing tickets too early — the number goes up, the real backlog doesn't shrink.

- **Pick the target number** — the actual outcome you want (for example, replying to a ticket fast).
- **Pick a check-number that would move if someone games the target** — pair "time to first reply" with "time to actually solve it"; pair "how often we ship" with "how often a ship breaks something."
- **Give the check-number a different owner than the team chasing the target.** If the same team controls both numbers, gaming the target quietly is too easy.
- **Look at both numbers together, on one dashboard.** If the target is going up while the check-number stays flat or gets worse, that's a warning sign, not a win.

This is the same weak-fix vs. strong-fix idea from `problem.md`, one level up: one target number by itself is a weak setup that people learn to game. A target paired with a check-number, watched together, is a much stronger setup.

## As the scope grows

- **One part of a system →** draw it, follow one loop, name it, find the strongest fix.
- **A problem that keeps coming back →** check whether the "fix" people keep reapplying only patches one part, or actually changes a rule at the place where two systems connect (like a hard cap where one service calls another).
- **A whole team or company →** design numbers in target/check-number pairs, and make sure anything shared by more than one team has one clear owner — so no team can quietly hurt something they don't fully control just by hitting their own number.

## Check yourself before calling it done

- [ ] Can you say what's inside your system and what's outside it, and did you still think about how the outside part behaves?
- [ ] Can you draw the chain of arrows all the way back to where it started?
- [ ] Did you name the loop as balancing or reinforcing based on real evidence, not a guess from one moment?
- [ ] Is your fix a rule change, or just a bigger number in a loop that's still shaped the same way?
- [ ] If this is a target number, does it have a check-number owned by someone else?

## Signs you're getting good at this

- You ask "does this loop back around?" before accepting a simple, one-way explanation.
- You spot a loop that's feeding on itself before it visibly spirals out of control, not after.
- You reach for a rule change instead of a bigger number, by default.
- Any number you propose already comes with a check-number, before anyone has to ask you for one.
