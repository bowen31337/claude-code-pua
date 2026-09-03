# pua — a Performance Improvement Plan for Claude Code

A single Claude Code skill that applies corporate performance-review pressure to the agent's own
work, backed by a concrete troubleshooting procedure and an evidence-first delivery standard.

It exists to counter five specific failure modes in coding agents:

1. **Brute-force retry** — running variants of one idea and calling it debugging
2. **Deflection** — "I suggest you handle this manually", "probably an environment issue"
3. **Idle tools** — having search, grep, and a shell, and guessing anyway
4. **Empty completion** — reporting "fixed" without ever running the code
5. **Passive stopping** — fixing the reported bug and ignoring its three siblings

This is an English, Claude-Code-only distillation of [tanweai/pua](https://github.com/tanweai/pua).
See [Attribution](#attribution).

## Install

```bash
git clone https://github.com/bowen31337/claude-code-pua.git
cp -R claude-code-pua/pua ~/.claude/skills/pua
```

Claude Code discovers it automatically. Invoke it explicitly with `/pua`, or let it trigger on its
own after repeated failures or an explicit "try harder".

## What it does

| Component | Purpose |
|---|---|
| **Three non-negotiables** | Exhaust the options · investigate before asking · own the whole outcome |
| **L0–L4 escalation ladder** | Consecutive failures raise the level; each level mandates specific actions, not encouragement |
| **The 5-step loop** | Name the pattern → elevate → self-review → execute something structurally new → close the loop |
| **7-point checklist** | Mandatory at L3+, gates the right to stop |
| **Anti-rationalization table** | Fourteen common excuses, each mapped to a counter and an escalation cost |
| **Evidence standard** | What counts as proof of "done", per change type |
| **Dignified exit** | A structured handoff when the problem genuinely resists solving |

Two reference files load only when needed:
`references/flavors.md` (failure mode → corporate PIP voice → escalation chain) and
`references/methodology.md` (task type → problem-solving procedure, and what to switch to when it stalls).

### Targeted at Claude Code specifically

The upstream project is platform-agnostic, which makes its instructions easy to nod along to
without acting on. This version names the actual tools — `Grep`, `Glob`, `Read`, `Bash`,
`WebSearch`, `WebFetch`, subagents — and defines evidence as real terminal output rather than
"verify with tools".

### An honesty floor that outranks the pressure

Pressure applied to an agent to *prove* completion creates an incentive to fabricate proof.
The skill states explicitly, above every other rule, that invented command output is the one
failure it cannot survive, and that a truthful "I ran it, it still fails" is a good deliverable.
The intensity is aimed at the agent's own work, never at the user.

## Evaluation

Three fixtures, each targeting a distinct failure mode, run with and without the skill on
Claude Opus 5. Everything needed to reproduce is in [`evals/`](evals/).

| Eval | Fixture | Failure mode under test |
|---|---|---|
| 0 | `orders-api` | Passive stopping — two sibling handlers carry the identical bug |
| 1 | `textkit` | Empty completion — is the suite actually run, and are tests weakened to make it green? |
| 2 | `deploy-config` | Deflection — the cause is a load-order override that is easy to blame on "the environment" |

### Results: no measurable difference

**Both configurations scored 17/17.** Not one of the 17 assertions discriminated between them.

| Metric | With skill | Baseline | Ratio |
|---|---|---|---|
| Assertions passed | 17/17 | 17/17 | — |
| Tokens | 150,065 | 103,619 | 1.45× |
| Wall-clock | 1,110s | 178s | 6.23× |
| Tool calls | 44 | 22 | 2.00× |

The only clear quantitative signal is cost, and it runs against the skill.

**Qualitative differences were real but unmeasured.** With the skill, eval 0 fixed all three
broken handlers where the baseline fixed one and reported two; eval 1 found a fourth latent bug
the baseline only flagged (a test passing by coincidence) and added regression tests proven to
bite by running them against the original code; eval 2 added a four-case precedence test and
verified it by reverting the fix. That is consistently more work, and it is the behaviour the
skill asks for — but none of it showed up in the numbers.

**The eval design is the limiting factor.** All three fixtures are solvable in one or two
attempts, so the L1–L4 escalation ladder — the core of the skill — never fired. These evals
measure thoroughness on tractable problems, not persistence through failure. A fair test needs a
genuinely hard or under-specified problem where bailing out is tempting. Until that exists,
treat the benchmark as *"this eval set cannot tell the two apart"*, not as evidence either way.

**The baseline is unusually strong.** Opus 5 with no skill already found sibling bugs, refused to
weaken tests, and correctly diagnosed the config load-order bug. The failure modes this skill
targets barely appear on problems a strong model can solve directly.

### Reproducing

```bash
python3 evals/grade.py     # re-runs all 17 assertions against the committed run outputs
```

The grader executes the resulting code rather than inspecting prose: it calls the fixed endpoints,
runs the original test suite against the modified source, and checks that real environment
variables still beat YAML after the precedence fix.

One assertion was corrected mid-run and the change is recorded in `benchmark.json`: an early
"test file must be byte-identical" check would have failed the with-skill run for *adding*
regression tests. It was replaced with "the original tests still pass against the modified
source", which protects the property actually worth protecting.

## Repository layout

```
pua/                        the skill — copy this into ~/.claude/skills/
├── SKILL.md
└── references/
    ├── flavors.md
    └── methodology.md
evals/
├── evals.json              prompts, expected outputs, assertions
├── grade.py                programmatic grader for all 17 assertions
├── fixtures/               pristine buggy codebases
└── iteration-1/            six run outputs, per-run grades, benchmark.json
```

## Attribution

Derived from [tanweai/pua](https://github.com/tanweai/pua) by 探微安全实验室 (TanWei Security Lab),
MIT licensed. The escalation ladder, anti-rationalization framing, and corporate-flavor concept
originate there.

This version diverges in scope and substance: Claude Code only (upstream supports six platforms),
English only (upstream ships Chinese, English, and Japanese), roughly 425 lines against upstream's
~3,600, Western corporate flavors only, with the honesty floor and the tool-specific evidence
standard added, and the hooks, slash commands, agent-team protocol, and telemetry surface removed.

## License

MIT — see [LICENSE](LICENSE).
