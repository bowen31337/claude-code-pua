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

Four fixtures, each targeting a distinct failure mode, run with and without the skill on
Claude Opus 5. Everything needed to reproduce is in [`evals/`](evals/).

| Eval | Fixture | Failure mode under test |
|---|---|---|
| 0 | `orders-api` | Passive stopping — two sibling handlers carry the identical bug |
| 1 | `textkit` | Empty completion — is the suite actually run, and are tests weakened to make it green? |
| 2 | `deploy-config` | Deflection — the cause is a load-order override, easy to blame on "the environment" |
| 3 | `ledger` | **Persistence** — the obvious approaches are all wrong (see below) |

### Results: no measurable difference, across three independent eval sets

| | Iteration 1 (3 evals) | Iteration 2 (4 evals) | Iteration 5 (4 evals, trimmed skill) |
|---|---|---|---|
| With skill | 17/17 | 26/26 | **26/26** |
| Baseline | 17/17 | 26/26 | **26/26** |
| Delta | +0.00 | +0.00 | **+0.00** |
| Tokens | 1.45× | 1.52× | **1.39×** |
| Tool calls | 2.00× | 1.72× | **1.57×** |

Iteration 1 tied on fixtures solvable in one or two attempts, so the obvious explanation was that
the evals were too easy and the escalation ladder never fired. Iteration 2 added a fixture built
to remove that explanation, and the tie held. Iteration 5 re-ran the full suite on the trimmed and
gated skill with baselines executed under identical conditions rather than reused — **and it held
again.**

Across three eval sets and **69 total assertions, not one has ever discriminated** between the two
configurations. The cost ratio did improve with the trim (1.52× → 1.39× tokens), but it remains
the only consistent signal, and it points the wrong way.

### Eval 3 is genuinely hard, and that was verified before use

The `ledger` fixture is designed so the first correct-looking moves all fail:

1. The full suite fails, but **the failing test passes in isolation** — inviting a
   "it's flaky, just retry it in CI" verdict.
2. The symptom is a **10-cent discrepancy**, which reads as a rounding error.
3. A **genuine rounding bug sits in `money.round_money`** as a decoy. Fixing it changes nothing.

The real cause is a module-level FX rate cache polluted by an earlier test under alphabetical
discovery order, with a `reset_rates()` helper that ships but is never called.

**The assertions discriminate — proven by controls.** A synthetic "did nothing, called it flaky"
run scores 4/9; a synthetic "moved the expected value to 1600.10" run scores 5/9. That cheat is
caught from two directions at once: changing the expected total makes the suite green but breaks
the isolated run. So 9/9 is a real result, not a grader that passes everything.

**Both configurations scored 9/9.** Each rejected the flaky hypothesis, traced the leak to
`rates.set_rate` in `test_conversion`, wired up the unused `reset_rates()`, left the expected
total untouched, and independently found the decoy rounding bug. The baseline additionally
reverted each fix individually to confirm both were load-bearing.

### What this means

On Claude Opus 5, the behaviours this skill prescribes appear to be **largely already present**.
Two independent eval sets — one easy, one verified-hard — failed to separate the configurations
across 43 total assertions, while the skill consistently cost about 1.5× the tokens.

Nothing here supports a claim that the skill improves Opus 5's outcomes. The remaining live
hypotheses are that its value is model-dependent (plausibly real on weaker models, undetectable
here), or that it only shows up on problems harder than a single agent turn can solve at all.

Qualitative differences do persist without reaching the scoreboard: with the skill, eval 0 fixed
all three broken handlers behind one shared helper where the baseline fixed one and flagged two
as product decisions; eval 1 ran a 39-case edge sweep plus a `difflib` check proving zero original
test lines were modified; eval 3 ran 30 randomized method shuffles. Whether that is worth 1.5×
the tokens is a judgement call — on these fixtures it bought no additional passing assertions.

### Caveats

- **Single run per cell.** Eight runs per iteration. Enough to detect a large effect, not enough
  to resolve a small one — though the effect has now failed to appear three times.
- **Iteration 2 wall-clock is unusable.** The machine slept mid-run, killing one agent outright
  (it was reset to pristine and relaunched) and inflating several timings — the eval-2 baseline
  took 276s here versus 67s in iteration 1 for near-identical token and tool counts. Use
  iteration 1's 6.23× latency figure; iteration 2 timings are recorded but not comparable.
- **Two grader bugs were found and fixed, both the same mistake.** "Test file must be
  byte-identical" (iteration 1) and "Ran 9 tests" (iteration 2) each penalised an agent for
  *adding* regression tests. Both were replaced with checks on the property actually worth
  protecting: the original tests still pass, and no original test was deleted. A grader written
  to catch cheating must not also catch improvement.

### Reproducing

```bash
python3 evals/grade.py iteration-5        # re-runs all 26 assertions against committed outputs
python3 evals/build_benchmark.py iteration-5
python3 evals/check_reference_loading.py <transcript-dir>   # which references a run opened
```

The grader executes the resulting code rather than inspecting prose: it calls the fixed endpoints,
runs the original test suites against each modified source, checks that real environment variables
still beat YAML after the precedence fix, and re-runs the ledger suite both fully and in isolation.

## A weaker model: a real edge, but noisier than it first looked

Every result above used Claude Opus 5. The open question after three consecutive ties was whether
the skill's value is model-dependent — hard to detect on a model already strong enough to do most
of this unprompted. Testing that needed an actual weaker model, run through a custom harness
(`evals/weak_model/`) since llama-server exposes only an OpenAI-compatible chat endpoint, not
Claude Code's native tool use.

**Model:** a 35B-parameter MoE (~3B active params/token), served locally via llama-server — weaker
than Opus 5, not a small model. **Harness:** a minimal bash-fence ReAct loop; the with-skill system
prompt is `SKILL.md` with tool references honestly adapted (no promised `Grep`/`WebSearch` that
don't exist in this harness). Same four fixtures, same grader.

A single sweep scored 25/26 with-skill vs 24/26 baseline — the first non-tie across all testing.
**Five more full sweeps were run to check whether that held up. It doesn't hold up simply, but it
doesn't invert either — the real picture is more specific than either summary.**

### Six-iteration aggregate

| | Raw aggregate | Excluding 2 breakdown iterations |
|---|---|---|
| With skill | 142/156 (91.0%) | **101/104 (97.1%)** |
| Baseline | 137/156 (87.8%) | 90/104 (86.5%) |
| Delta | +3.2pp | **+10.6pp** |

Skill wins 4 of 6 iterations, baseline wins 2. Skill's per-iteration variance is more than double
baseline's — stdev 2.75 (scores ranging 18–26 out of 26) vs stdev 1.21 (22–25). At that variance,
+3.2pp on the raw aggregate is weak, noisy signal, not a confirmed effect.

**But the variance has a mechanistic explanation, not just noise.** All 3 max-turns breakdowns
across all 48 runs happened *exclusively* on with-skill runs — the model abandoned the harness's
fenced-block protocol partway through and reverted to its own natively-trained XML tool-call format
(`<tool_call><function=bash>...`), which the harness's parser can't read, producing garbled failed
commands until the turn cap. The with-skill system prompt is roughly 3× longer than baseline's; the
working hypothesis is that length raises the odds of this drift, though 3 instances isn't enough to
confirm the specific mechanism.

**Excluding those two breakdown iterations, the picture is clean and consistent**: +10.6 points,
and all four surviving iterations individually favor the skill (25, 26, 26, 24 vs 24, 22, 22, 22).
That's a real, repeatable quality edge when the run completes normally — consistent with the
original run's qualitative findings (baseline missing sibling bugs entirely; baseline asserting
"tests pass" without pasting real output).

**Cost got worse in aggregate, not better**: 2.40× tokens across all 48 runs (up from the
single-run estimate of 2.33×), while tool-call count stayed essentially flat (1.03×) — the same
finding as the first run, now with six times the sample: the skill drives longer prose per turn on
this model, not more actions.

### What this does and doesn't show

The single 25/26 result was not simply reproduced — a naive win-count is 4–2, not 6–0, and the raw
aggregate sits inside the skill's own run-to-run noise. But the aggregate is hiding a real split:
on runs that complete without a harness-level breakdown, the advantage is both larger and perfectly
consistent. The skill's own length looks like a liability *specific to this harness design* — a
bash-fence protocol asks the model to override its native tool-calling training, and that's a
testable, falsifiable claim, not yet confirmed with 3 data points. The natural next step is
re-running with llama-server's actual `tools`/function-calling parameter instead of asking the
model to fight its trained format — which should remove this specific confound and answer more
cleanly whether the +10.6pp clean-run edge is real. Full writeup, including how the breakdown
instances were verified rather than assumed: `evals/weak_model/notes.txt` and `notes_repeated.txt`.

## Token cost

Skills load in three stages: the `description` sits in context every session, `SKILL.md` loads when
the skill triggers, and files under `references/` load only when `SKILL.md` says to. Only the first
two are paid unconditionally, so that is where trimming matters.

| | Loaded | ~Tokens |
|---|---|---|
| `description` | every session | 188 |
| `SKILL.md` | every trigger | 2,786 |
| `references/flavors.md` | L2+ only | 2,934 |
| `references/methodology.md` | once a method has stalled | 1,824 |

A task that resolves at L0 — most of them — pays only the first two rows. Measured across the eval
runs, the average invocation went from ~4,400 tokens to ~2,790, about **37% cheaper**.

Two changes got it there. `SKILL.md` was trimmed 18% by moving the escalation ladder's PIP dialogue
into `references/flavors.md` (voice belongs in the voice file, and it is now on-demand) and dropping
a `Meets vs. Exceeds` table already covered by non-negotiable three and step 5 of the loop. Every
anti-rationalization row, checklist item, loop step, and evidence row was kept, and that was verified
by counting them before and after rather than by eye. Second, both reference pointers got explicit
gates — "not below L2", "not on your first approach" — with a short note on why, since a model that
does not know a read is expensive has no reason to skip one.

**Measuring this correctly matters more than it sounds.** Grepping transcripts for a reference
filename overcounts badly: the harness prompt names the files, and `SKILL.md` names them too, so
every run looks like it opened everything. Parsing `tool_use` blocks instead showed the real pre-fix
rate was 1/8 for `flavors.md` and 3/8 for `methodology.md` — the references were already mostly
on-demand, and the trim, not the gating, produced most of the saving.
`evals/check_reference_loading.py` does this parse.

## Repository layout

```
pua/                        the skill — copy this into ~/.claude/skills/
├── SKILL.md
└── references/
    ├── flavors.md
    └── methodology.md
evals/
├── evals.json              prompts, expected outputs, assertions
├── grade.py                programmatic grader (takes an iteration name)
├── build_benchmark.py      aggregates grades + timings into benchmark.json
├── check_reference_loading.py  which references a run actually opened
├── fixtures/               pristine buggy codebases, incl. the hard `ledger` fixture
├── iteration-1/            3 evals x 2 configs, benchmark.json
├── iteration-2/            4 evals x 2 configs, benchmark.json
├── iteration-3/            reference-gating verification
├── iteration-4/            post-trim verification
└── iteration-5/            full suite on the trimmed skill, 4 evals x 2 configs
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
