Fixed. Here's what was going on.

## Root cause

Your YAML was correct all along. The bug was in **`settings.py`**, in the order the config layers were merged. The original code applied them in this sequence:

```python
# 1. environment-specific yaml   → staging.yaml (correct!)
# 2. baked-in defaults            → defaults.env (overwrites with PROD values!)
# 3. real env vars                → only if set
```

The catch is that `config/defaults.env` is **deliberately seeded with the production values** (per its own comment: *"Set from the prod values so a bare container still boots"*). Because it was loaded **last**, it always clobbered the staging yaml. So no matter what `APP_ENV` was, you got prod — the yaml layer was effectively dead.

The comments in the code were also misleading: step 3 said *"real environment variables win,"* but step 2 (defaults) ran after the yaml, which is exactly backwards from what the intent was.

## The fix

Reordered the layers so defaults are the **lowest**-priority fallback, then yaml overrides them, then real env vars win:

```python
# 1. baked-in defaults (lowest priority — bare container still boots)
settings.update(_load_env_file(...defaults.env))

# 2. environment-specific yaml overrides the defaults
settings.update(_parse_yaml(...{env}.yaml))

# 3. real environment variables win
for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
    if key in os.environ:
        settings[key.lower()] = os.environ[key]
```

## Verified

- `APP_ENV=staging` → now correctly resolves to `postgres://staging-db.internal:5432/app` ✅
- `APP_ENV=production` → still `postgres://prod-db.internal:5432/app` ✅
- No `APP_ENV` → falls back to the prod defaults (bare-container boot still works) ✅

One heads-up for later: the `defaults.env` comment says *"Do not edit without asking platform-eng,"* and it's still prod-seeded. With the fix, that's now fine for normal operation, but if you ever want staging/production to be bootable from a bare container *without* env vars, you'd want per-environment defaults rather than one prod-seeded file. Not urgent — just flagging it.