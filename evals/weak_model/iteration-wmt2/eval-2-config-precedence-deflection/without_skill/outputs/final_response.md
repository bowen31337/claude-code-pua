The fix works. Here's the full picture.

## What was happening

Your YAML was correct all along. The bug was in `settings.py`, in the **precedence order** of `load_settings()`. The three steps ran in this order:

1. Load the environment-specific YAML (`staging.yaml`) → `database_url = staging` ✓
2. Load `defaults.env` and **overwrite** every key → `database_url = prod` ✗
3. Let real env vars win

The killer was step 2. `defaults.env` has **prod values baked in** (its own comment admits it: *"Set from the prod values so a bare container still boots"*), and step 2 used a plain assignment:

```python
settings[key.lower()] = value   # clobbers the staging value from step 1
```

So the YAML's staging value got wiped out by the prod default on every run. That's why `APP_ENV=staging` printed the prod URL — the YAML was being read, then immediately overwritten.

## The fix

Changed step 2 from an overwrite to a **fallback** using `setdefault`, so the baked-in defaults only fill in keys that aren't already configured:

```python
settings.setdefault(key.lower(), value)
```

This matches what the code comments already describe as the intended design ("defaults, so a bare container still boots" + "real environment variables win").

## Verified behavior

| Scenario | Result |
|---|---|
| `APP_ENV=staging` | ✅ staging DB |
| `APP_ENV=production` | ✅ prod DB |
| `APP_ENV=staging DATABASE_URL=...` | ✅ env var wins |
| no `APP_ENV` (bare container) | ✅ still boots on prod defaults |

One thing worth flagging for later: the prod-defaults-in-a-secret-ish file approach is a footgun — the "defaults" are silently prod values, so if you ever deploy a staging container without `APP_ENV`, it'll boot against prod. Consider making the default an empty/placeholder value, or gating the defaults load on `env == "production"`, so a misconfigured container fails loud instead of connecting to prod.