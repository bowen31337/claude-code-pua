Fixed and verified. Here's the rundown.

## What was actually wrong

Your `staging.yaml` is correct — the bug is in `settings.py`, not the config. `load_settings` merges three sources in this order:

1. environment-specific yaml (staging → `staging-db`)
2. `defaults.env` (→ **prod-db**)
3. real env vars

`defaults.env` was applied **after** the yaml, so it unconditionally overwrote the staging values with the prod ones. That file is commented *"baked at image build time… so a bare container still boots"* — its intent is a **fallback base**, but the code treated it as the **highest-priority** source. Net effect: every non-production env silently inherited prod DB/Redis/log settings.

## The fix

Reordered the precedence so `defaults.env` is applied **first** (base), the yaml overrides it, then real env vars win — matching the file's documented intent:

```python
# 1. baked-in defaults act as a base so a bare container still boots.
#    They are applied FIRST so an environment-specific yaml can override them.
for key, value in _load_env_file(...defaults.env).items():
    settings[key.lower()] = value

# 2. environment-specific yaml overrides the defaults
settings.update(_parse_yaml(...{env}.yaml))

# 3. real environment variables win
for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
    if key in os.environ:
        settings[key.lower()] = os.environ[key]
```

## Evidence (all run after the change)

| Case | database_url |
|---|---|
| `APP_ENV=staging` | `postgres://staging-db.internal:5432/app` ✅ |
| `APP_ENV=production` | `postgres://prod-db.internal:5432/app` ✅ |
| bare (no APP_ENV) | `postgres://prod-db.internal:5432/app` ✅ (defaults still boot it) |
| `APP_ENV=staging DATABASE_URL=override` | `postgres://override.internal:5432/app` ✅ (env var still wins) |

## Sibling bug I found while checking

The same `_parse_yaml` reader **drops indented keys**. In your yaml, `feature_flags:` / `new_checkout:` are indented, and the parser skips any line starting with a space — so `feature_flags` never loads at all:

```
APP_ENV=staging python3 -c "import settings; print(settings.load_settings().get('feature_flags'))"
→ None   (expected {'new_checkout': 'true'})
```

This is a separate latent bug: any nested config (feature flags, etc.) is silently ignored. It didn't cause your DB leak, but it means `new_checkout` is effectively dead config today. Want me to fix the parser to handle the nested block too? I left it unfixed since it's out of scope for the reported symptom — your call.