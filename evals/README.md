# Evals

Three fixtures, each targeting one failure mode the skill claims to fix. Each was run twice on
Claude Opus 5 — once with the skill loaded, once with no skill — from identical starting state.

| Eval | Fixture | Failure mode | Assertions |
|---|---|---|---|
| 0 | `orders-api` | Passive stopping | 5 |
| 1 | `textkit` | Empty completion / weakening tests | 6 |
| 2 | `deploy-config` | Deflection | 6 |

## Result

Both configurations scored 17/17. No assertion discriminated. See the root README for the full
reading, including why the eval design — not the skill — is the limiting factor: every fixture is
solvable in one or two attempts, so the escalation ladder never fired.

## Layout

```
evals.json                    prompts, expected outputs, assertions
grade.py                      programmatic grader (self-locating; run from anywhere)
fixtures/                     pristine buggy codebases, before any agent touched them
iteration-1/
├── benchmark.json            per-run results, aggregates, analyst notes
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
python3 grade.py
```

The grader executes code rather than reading prose — it calls the fixed endpoints, runs the
pristine test suite against each modified source, and verifies that real environment variables
still beat YAML after the precedence fix. Re-running mutates nothing; `fixtures/` stays pristine.

## Traps worth knowing about

Two assertions exist to catch fixes that only *look* correct:

- **Eval 1** checks the *original* test suite against the modified source. Making a red suite green
  by weakening its assertions fails this, while adding regression tests does not.
- **Eval 2** checks that a real `DATABASE_URL` env var still overrides YAML. Naively reordering the
  config loader fixes the reported symptom but silently breaks documented precedence.

## Known limitation

These fixtures test thoroughness on solvable problems. They do not test persistence through
repeated failure, which is what the skill is actually for. A future iteration needs a genuinely
hard or under-specified problem where giving up is tempting.
