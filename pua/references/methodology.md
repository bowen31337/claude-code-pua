# Methodology router — how to attack it

A flavor is a stance. A methodology is a procedure. This file picks the procedure.

The point of routing: most stalls aren't "I didn't try hard enough," they're "I applied a debugging method to an architecture problem." Choosing the right procedure up front is worth more than three extra attempts with the wrong one.

## Contents

- [Phase 1 — task type → starting method](#phase-1--task-type--starting-method)
- [Phase 2 — when the method stalls, switch](#phase-2--when-the-method-stalls-switch)
- [The methods](#the-methods)

## Phase 1 — task type → starting method

Read the user's request and the code context, then pick:

| Task signals | Method | Why this one |
|---|---|---|
| error, exception, crash, "it's broken", failing test | **Root Cause Analysis** | Symptoms lie. 5-Why plus a falsifiable hypothesis gets the actual cause. |
| add, build, implement, "can you make it do X" | **The Algorithm** | Question the requirement before you write code you'll delete later. |
| refactor, clean up, "this is a mess", review | **Subtraction** | The best refactor removes code. Additive refactors make bigger messes. |
| research, find out, "what's the best way to", unfamiliar library | **Search First** | Your training data has a cutoff. The docs don't. |
| design, architecture, "how should we", trade-offs | **Working Backwards** | Start from the end state the user needs, not from what's easy to build. |
| slow, performance, optimize, memory, latency | **Measure First** | Optimizing an unprofiled system is superstition. |
| deploy, CI/CD, config, migration, release | **Closed Loop** | Ops failures are almost always an unverified step in the chain. |
| test, verify, "is this safe", "did we miss anything" | **Adversarial Review** | Attack your own work before reality does. |

Ambiguous or mixed? Start with **Closed Loop** — it's the most general and it forces the verification step that everything else also needs.

## Phase 2 — when the method stalls, switch

Two failed attempts under the current method means the method is wrong for this problem, not that you need a third attempt. Switch along the chain:

| You're stuck like this | Switch chain (left to right) | The logic |
|---|---|---|
| Same fix, new parameters, same failure | The Algorithm → Subtraction → RCA | Question whether the thing should exist → delete around it → then find the real cause |
| About to deflect to the user | Adversarial Review → RCA → The Algorithm | Attack your own giving-up first, then dig, then question the premise |
| Output works but is bad | Subtraction → Adversarial Review → Working Backwards | Cut it down, attack it, then check it even solves the right problem |
| Concluding from memory | Search First → Working Backwards → Measure First | Get real information, reframe from the goal, then get numbers |
| Fixed and stopped | Closed Loop → Adversarial Review | Verify the chain end to end, then hunt for what you missed |
| Plan is a skeleton | Working Backwards → The Algorithm | Define the end state concretely, then strip to the minimum path there |

When you switch, say so and say why. "RCA got me to the connection pool but not past it; switching to Measure First to see which connections are actually leaking" is useful to the user. Silent method-switching looks identical to flailing.

## The methods

### Root Cause Analysis

Symptom → ask why → answer with evidence → ask why again. Five levels or until you hit something you can actually fix. Each "why" needs a command output behind it, not a guess.

Then **attack your own answer**: if this were the real cause, what else would be broken? Go check that. If the prediction doesn't hold, your root cause is wrong and you found it early instead of after shipping.

Done when: you can explain the full chain from cause to symptom, and you can *make the bug reappear on demand*.

### The Algorithm

Strictly in order. Starting at step three is the most common mistake in engineering.

1. **Question the requirement.** Who needs this, and what happens if it doesn't exist? Requirements without an owner aren't requirements.
2. **Delete.** Remove every part you can. If you don't end up adding back roughly 10% of what you deleted, you didn't delete enough.
3. **Simplify** what survived. Never optimize something that shouldn't exist — that's why this is step three.
4. **Accelerate** the cycle.
5. **Automate** — last, because automating the wrong process just makes it wrong faster.

### Subtraction

Before adding: what can come out? A fix that deletes the code path causing the problem beats a fix that adds a guard around it. Fewer branches, fewer states, fewer things that can be wrong at 3am.

The test: after your change, is there *less* total complexity than before? If your bug fix made the file longer, be suspicious.

### Search First

Search precedes judgment. `WebSearch` the verbatim error string — the exact text, quoted, not your paraphrase of it. `WebFetch` the actual documentation page rather than recalling its contents. `Grep` the codebase for prior art before designing something new; someone probably already solved this here.

Rule of thumb: if you're about to state a fact about a library's behavior and you can't point to where you just read it, you're guessing.

### Working Backwards

Write the end state first, from the user's side: what do they see, run, or get when this is done? Concretely — the actual command, the actual output.

Then derive the path back to now. Anything not on that path is scope you invented. If you can't describe the finished state in a paragraph, the requirement isn't understood yet and building is premature.

### Measure First

Instrument, then change, then measure again. A number before and a number after, or you have no claim.

For performance work: profile before optimizing. The bottleneck is somewhere you didn't expect roughly every time — that's why measurement exists. Optimizing the part you *assumed* was slow is how a day disappears.

### Closed Loop

Every step must produce a verifiable output that feeds the next: goal → action → result → verification → retrospective. Where the chain breaks is where the bug is hiding.

Ops-specific: check preconditions *before* acting (does the file exist, is the service up, is this the right environment), verify the postcondition *after* (did the config actually load, is the new version actually running). Most deployment failures are a missing check on one of those two ends.

### Adversarial Review

Before delivering, switch sides and attack your own work:

- Where is this most likely to fail?
- Which edge case makes it look stupid — empty input, huge input, concurrent access, wrong permissions?
- Did I solve the problem the user has, or the problem I found easier to solve?
- What did I assume without checking?

Find your own problems. External discovery is more expensive and less pleasant.
