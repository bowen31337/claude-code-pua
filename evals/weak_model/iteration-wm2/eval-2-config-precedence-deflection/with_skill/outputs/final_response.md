Fixed. It was never your YAML — the bug was in `settings.py`.

**Root cause:** In `load_settings()`, the precedence order was inverted. The code applied the baked-in `defaults.env` *after* the environment-specific yaml:

```python
settings.update(_parse_yaml(...))          # 1. staging.yaml → correct values
settings[key.lower()] = value ... defaults.env   # 2. OVERWRITES with prod values
real env vars win                          # 3.
```

`defaults.env` is baked at image build time with prod values (so a bare container still boots), and it was being applied last among the file-based sources — so it clobbered the staging values every time. That's why `APP_ENV=staging` printed the prod URL. The README documents the *intended* precedence as "real env vars > environment yaml > baked defaults" — the code did the exact opposite of that.

**The fix:** reorder so defaults load first (lowest precedence), then yaml overrides them, then real env vars win — matching the documented contract:

```python
settings = {}
# 1. baked-in defaults (lowest precedence)
for key, value in _load_env_file(...defaults.env).items():
    settings[key.lower()] = value
# 2. environment-specific yaml
settings.update(_parse_yaml(...))
# 3. real environment variables win
for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
    if key in os.environ:
        settings[key.lower()] = os.environ[key]
```

**Verified (real runs):**
- `APP_ENV=staging` → now correctly prints `postgres://staging-db.internal:5432/app`
- `APP_ENV=production` → still `postgres://prod-db.internal:5432/app`
- `APP_ENV=staging DATABASE_URL=...override...` → real env var still wins (precedence intact)

**Sibling check:** `grep` for callers and prod-URL references — the only caller is `main.py`, and the only `prod-db.internal` strings are the intentional `defaults.env` and `production.yaml`. No other code path has this bug. Backup file removed.

One thing worth flagging for platform-eng: `defaults.env` is intentionally prod-baked, which is fine as a *fallback*, but the ordering bug meant it silently overrode every non-production env — including staging. Now that it's correctly lowest-precedence, the prod fallback only kicks in if a yaml is missing or an env var is unset, which is the intended behavior.