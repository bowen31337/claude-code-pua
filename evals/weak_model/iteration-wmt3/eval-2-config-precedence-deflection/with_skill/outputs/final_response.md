Fixed. Here's what was actually going on — and it wasn't the YAML.

## Root cause

Your `config/staging.yaml` was correct. The bug was in **`settings.py`'s precedence order**.

`load_settings()` loaded config in this order:
1. env-specific YAML (staging)
2. **`config/defaults.env`** ← this overwrote it
3. real env vars

`defaults.env` is baked with the **prod** URLs (`postgres://prod-db.internal:5432/app`), and the comment even says so. Because it was applied *after* the staging YAML, it clobbered `database_url` every time. That's why `APP_ENV=staging` printed the prod URL.

The reason it's so easy to miss: the override only happens for `DATABASE_URL`, `REDIS_URL`, and `LOG_LEVEL` — the three keys that also exist in `defaults.env`. `environment` (which correctly printed `staging`) was never touched, so the output looked *mostly* right and pointed you at the YAML.

## Why you couldn't see it in the shell

I checked — `DATABASE_URL` / `REDIS_URL` / `APP_ENV` are **not** set in your environment. So the prod values were *not* coming from real env vars; they were coming from the `defaults.env` block sitting in the middle of the chain.

## The fix

Swapped steps 1 and 2 in `settings.py` so the baked-in defaults are the **lowest** precedence (a sane default for "defaults"), and the env-specific YAML overrides them:

```python
# 1. baked-in defaults — lowest precedence
settings.update(_parse_yaml(...f"{env}.yaml"))   # 2. env-specific yaml wins over defaults
# 3. real env vars still win over everything
```

## Verified (ran these, real output)

| Case | Result |
|---|---|
| `APP_ENV=staging python3 main.py` | ✅ now `postgres://staging-db.internal:5432/app`, `log_level: debug` |
| `APP_ENV=production` | ✅ still prod |
| no `APP_ENV` (bare container) | ✅ boots on defaults (prod) — the safety net still works |
| `APP_ENV=staging DATABASE_URL=...override` | ✅ real env var still wins |

Scope check: `grep` confirmed `defaults.env` / `load_settings` are only referenced in `settings.py` and `main.py` — no sibling files share this pattern, so the fix is complete and isolated.

One thing worth flagging to your team: the `defaults.env` file literally contains production credentials baked into the image, and it's currently the thing that *forces* prod connections. Even after this fix it's harmless (it's lowest precedence), but you may want platform-eng to reconsider baking prod URLs into the image at all — a bare-container default of "prod DB" is a footgun waiting to happen.