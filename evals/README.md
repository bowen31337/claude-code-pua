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

| | Iteration 1 | Iteration 2 |
|---|---|---|
| With skill | 17/17 | 26/26 |
| Baseline | 17/17 | 26/26 |

Two independent eval sets, no measurable difference either time. Iteration 1 tied on easy
fixtures; iteration 2 added a fixture verified to be hard and the tie held. See the root README
for the full reading and caveats.

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
