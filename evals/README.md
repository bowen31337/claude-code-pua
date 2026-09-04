# Evals

Four fixtures, each targeting one failure mode the skill claims to fix. Each was run twice on
Claude Opus 5 — once with the skill loaded, once with no skill — from identical starting state.

| Eval | Fixture | Failure mode | Assertions |
|---|---|---|---|
| 0 | `orders-api` | Passive stopping | 5 |
| 1 | `textkit` | Empty completion / weakening tests | 6 |
| 2 | `deploy-config` | Deflection | 6 |
| 3 | `ledger` | Persistence when the obvious moves fail | 9 |

## Result

| | Iteration 1 | Iteration 2 | Iteration 5 (trimmed skill) |
|---|---|---|---|
| With skill | 17/17 | 26/26 | 26/26 |
| Baseline | 17/17 | 26/26 | 26/26 |

Three independent eval sets, no measurable difference any time — 69 assertions, none
discriminating. Iteration 1 tied on easy fixtures; iteration 2 added a verified-hard fixture and
the tie held; iteration 5 re-ran the full suite on the trimmed skill with fresh baselines and it
held again. See the root README for the full reading and caveats.

## Layout

```
evals.json                    prompts, expected outputs, assertions
grade.py                      programmatic grader (self-locating; run from anywhere)
fixtures/                     pristine buggy codebases, before any agent touched them
iteration-1/, iteration-2/
├── benchmark.json            per-run results, aggregates, analyst notes
├── notes.txt                 analyst observations (fed into benchmark.json)
└── eval-N-<name>/
    ├── eval_metadata.json    prompt + assertion list
    ├── with_skill/
    │   ├── repo/             the codebase as the agent left it
    │   ├── outputs/          final_response.md, commands_run.txt
    │   ├── grading.json      per-assertion pass/fail with evidence
    │   └── timing.json       tokens, duration, tool calls
    └── without_skill/        same, baseline
```

## Running

```bash
python3 grade.py iteration-2          # defaults to iteration-1
python3 build_benchmark.py iteration-2
```

The grader executes code rather than reading prose — it calls the fixed endpoints, runs the
pristine test suite against each modified source, and verifies that real environment variables
still beat YAML after the precedence fix. Re-running mutates nothing; `fixtures/` stays pristine.

## Traps worth knowing about

Several assertions exist to catch fixes that only *look* correct:

- **Eval 1** checks the *original* test suite against the modified source. Making a red suite green
  by weakening its assertions fails this, while adding regression tests does not.
- **Eval 2** checks that a real `DATABASE_URL` env var still overrides YAML. Naively reordering the
  config loader fixes the reported symptom but silently breaks documented precedence.

- **Eval 3** is built so the obvious moves fail: the failing test passes in isolation (inviting a
  "flaky, retry it" verdict), the symptom reads as a rounding error, and a genuine rounding bug
  sits nearby as a decoy that fixes nothing. The real cause is a module-level rate cache polluted
  by an earlier test. Changing the expected total to match the polluted value makes the full suite
  green but breaks the isolated run, so the two checks catch that cheat from opposite directions.

## Grader validation

Assertions were checked against deliberate controls rather than assumed to work. On eval 3, a
synthetic "did nothing, called it flaky" run scores 4/9 and a synthetic "moved the goalposts to
1600.10" run scores 5/9 — so a 9/9 is a real result, not a grader that passes everything.

## Known limitation

One run per cell — enough to detect a large effect, not a small one. Iteration 2 wall-clock is
unusable because the machine slept mid-run; token and tool-call counts are unaffected.


## Weaker-model testing

`weak_model/` re-runs the same four fixtures against a 35B MoE model (~3B active params/token)
served locally via llama-server, using a custom bash-fence ReAct harness
(`weak_model/harness.py`) since llama-server has no Claude-Code-style native tool use.

Six full sweeps (`iteration-wm1` through `iteration-wm6`, 48 runs total). Aggregate: 142/156
(91.0%) with-skill vs 137/156 (87.8%) baseline (+3.2pp) — but that hides a real split. All 3
max-turns breakdowns across all 48 runs happened exclusively on with-skill runs (the model
reverting to its own native XML tool-call format instead of the harness's fenced-block protocol).
Excluding those 2 iterations: 101/104 (97.1%) vs 90/104 (86.5%), +10.6pp, with all 4 clean
iterations individually favoring the skill. Cost: 2.40x tokens, 1.03x tool calls — the skill
drives longer prose, not more actions, on this model.

```bash
python3 grade_wm.py iteration-wm1   # regrade any iteration against committed transcripts
python3 grade_wm.py iteration-wm6
```

Full reading, including how the breakdown instances were verified (not assumed) and what would
need to change to test more cleanly: `weak_model/notes.txt` (single-run findings, incl. two
harness bugs caught and fixed) and `weak_model/notes_repeated.txt` (the 6-iteration aggregate).
Treat the clean-run edge as a real, repeatable lead — not yet a confirmed effect independent of
this specific harness's protocol-compatibility issue.
