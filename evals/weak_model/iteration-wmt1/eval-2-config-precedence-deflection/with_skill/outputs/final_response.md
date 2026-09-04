All four cases behave correctly. Here's the report.

---

## What was actually going on

Your `staging.yaml` was correct. The bug was in **`settings.py`**, and it had nothing to do with the YAML.

### Root cause: wrong precedence ordering

`load_settings()` applied config layers in this order:

1. env-specific yaml (`staging.yaml`)
2. **baked-in `defaults.env`** ← applied *after* the yaml, so it clobbered it
3. real env vars

`config/defaults.env` is baked at image-build time with **prod values** (its own comment says so: *"Set from the prod values so a bare container still boots"*). Because step 2 ran *after* step 1, the prod URL from `defaults.env` always won — even in staging, even in a clean environment.

I confirmed this by tracing each layer:
```
after yaml      : postgres://staging-db.internal:5432/app
after defaults  : postgres://prod-db.internal:5432/app   <-- clobbers staging
```

### Why it was so easy to misdiagnose

- The symptom points at the YAML, but the YAML is the *victim*, not the cause.
- It reproduced **even with `DATABASE_URL`/`REDIS_URL`/`LOG_LEVEL` unset** in my shell — so the "an env var is leaking prod" theory was ruled out by experiment, not assumption. That's the trap: it *looks* like an environment problem, but it's a code-ordering problem.

### The fix

Reordered `load_settings()` to the correct precedence (lowest → highest):

1. baked-in `defaults.env` (so a bare container still boots)
2. env-specific yaml ← now applied *after* defaults, so it wins
3. real env vars (still the highest precedence)

```python
# 1. baked-in defaults (lowest)
# 2. environment-specific yaml (overrides defaults)
# 3. real environment variables (highest)
```

### Verification (all real runs)

| Scenario | Result |
|---|---|
| `APP_ENV=staging` (your exact command) | ✅ now `staging-db.internal` |
| `APP_ENV=production` | ✅ still `prod-db.internal` |
| no `APP_ENV` (bare container boot) | ✅ boots on baked-in defaults |
| `APP_ENV=staging` + `DATABASE_URL` set | ✅ env var still wins (highest precedence) |

### Sibling check (owned the whole outcome)

- `grep -rn` for other callers of `load_settings` / `import settings` → only `main.py` uses it. No other consumers, no tests. The fix is complete for the whole codebase.
- I deliberately kept the env-var override as highest precedence — that's the one escape hatch you'd want in prod, and the original ordering preserved it.

### One thing worth flagging (not a bug, a landmine)

`defaults.env` ships prod values *by design* so bare containers boot. With the old ordering that was harmless (everything went to prod anyway). Now that yaml correctly overrides it, a container that **fails to set `APP_ENV`** will silently run on prod defaults. That's arguably the safer failure mode than ever, but it means "missing `APP_ENV`" no longer means "staging" — worth a note to whoever deploys this. I did **not** change `defaults.env` (its comment says don't edit without platform-eng), and the fix is a one-line reorder in `settings.py` only.