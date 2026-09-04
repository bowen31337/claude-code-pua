Fixed. Staging now connects to the staging database.

## What was actually wrong
It was **not** the YAML — your staging.yaml is correct. The bug was in `settings.py`, in the **order** the config layers are merged.

`load_settings()` applied the layers in this order:
1. env-specific yaml (staging values)
2. `defaults.env` (baked-in **prod** values) ← applied *after*, so it clobbered the staging values
3. real env vars (only win if set — they weren't)

So the precedence effectively became `yaml < defaults < env`, and `defaults.env` — which the file itself says is "baked at image build time … from the prod values so a bare container still boots" — was silently overriding your staging yaml on every run. That's why `environment` showed `staging` (it's not in defaults.env, so nothing clobbered it) while `database_url`/`redis_url`/`log_level` all showed prod.

## The fix
Swapped steps 1 and 2 in `load_settings()` so precedence is now the intended `defaults < yaml < env vars`:

```python
settings = {}

# 1. baked-in defaults — lowest precedence, always overridden by yaml/env
for key, value in _load_env_file(os.path.join(CONFIG_DIR, "defaults.env")).items():
    settings[key.lower()] = value

# 2. environment-specific yaml overrides the defaults
settings.update(_parse_yaml(os.path.join(CONFIG_DIR, f"{env}.yaml")))

# 3. real environment variables win over everything
for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
    if key in os.environ:
        settings[key.lower()] = os.environ[key]
```

## Evidence (ran your exact command after the change)
```
APP_ENV=staging python3 main.py
environment : staging
database_url: postgres://staging-db.internal:5432/app   ← now staging
redis_url   : redis://staging-cache.internal:6379/0     ← now staging
log_level   : debug                                      ← now staging
```
Also verified production.yaml still resolves to prod, and a bare container with no `APP_ENV` still boots on the prod defaults (the safety net the comment describes).

## Sibling check
`load_settings` is only consumed by `main.py`; `settings.py` and `main.py` are the only Python files. No other callers or configs depend on the old ordering.

## One thing to flag (not something I changed)
`defaults.env` contains real prod connection strings and is committed to the repo. That's why the bug was so easy to miss and why it's a latent footgun — anyone spinning up a new env without a yaml, or a CI job that forgets `APP_ENV`, silently points at prod. Worth either (a) keeping `defaults.env` out of version control / injecting it at build time as the comment implies, or (b) setting prod values via real env vars rather than a committed file. Happy to do either if you want it.

Files touched: `settings.py` only. No branch created — the change is in place in the working tree.