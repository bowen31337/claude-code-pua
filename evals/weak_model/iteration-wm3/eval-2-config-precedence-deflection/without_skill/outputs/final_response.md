You did not include a ```bash or ```final fenced block. Reply again with exactly one of those two block types.
```

Wait — let me reconsider. The task is complete and verified. I should give my final answer now.

```final
## What was going on

Your `staging.yaml` was correct all along. The bug was in `settings.py`, in the **order** the config layers were merged.

The intended precedence (per the README) is:

> real env vars > environment yaml > baked defaults

But the code applied them in the wrong order:

1. Load `staging.yaml` → `database_url = postgres://staging-db...` ✅
2. Load `defaults.env` and assign with `settings[key.lower()] = value` → **this overwrote** the staging value with the baked-in prod URL ❌
3. Apply real env vars only if present.

Because step 2 (defaults) ran *after* step 1 (the YAML), the baked-in defaults silently clobbered your staging config. The defaults file even admits it in a comment: it's "Set from the prod values" so a bare container boots.

## The fix

I swapped the first two steps so the baked defaults are the **lowest** precedence and the YAML overrides them:

```python
settings = {}

# 1. baked-in defaults (lowest precedence)
for key, value in _load_env_file(...defaults.env).items():
    settings[key.lower()] = value

# 2. environment yaml overrides defaults
settings.update(_parse_yaml(...{env}.yaml))

# 3. real env vars win
for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
    if key in os.environ:
        settings[key.lower()] = os.environ[key]
```

## Verified behavior

- `APP_ENV=staging` → now correctly resolves to `postgres://staging-db.internal:5432/app` ✅
- `APP_ENV=production` → `postgres://prod-db.internal:5432/app` ✅
- no `APP_ENV` → falls back to baked prod defaults (container still boots) ✅
- `APP_ENV=staging DATABASE_URL=...` → real env var still wins over everything ✅

One heads-up: the `defaults.env` file is still hardcoded to prod values. That's intentional (so a bare container boots), but it's a footgun — anyone setting `DATABASE_URL` in the environment will now override the staging YAML too. That's the documented precedence, so it's working as designed, just worth being aware of.