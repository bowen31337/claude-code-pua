## Summary

Your YAML was correct — the bug was in `settings.py`, not in the config.

**Root cause:** The precedence ordering in `load_settings()` was inverted. The code applied the baked-in `defaults.env` *after* the env-specific yaml:

```python
# 1. environment-specific yaml   → staging value applied
settings.update(_parse_yaml(...))

# 2. baked-in defaults            → OVERWRITES with prod value!
settings.update(_load_env_file("defaults.env"))

# 3. real env vars                 → skipped (DATABASE_URL not set)
```

The `defaults.env` file is baked at image build time with **prod** values ("so a bare container still boots"). Because it was applied as step 2, it clobbered the staging value you'd just loaded in step 1. The defaults were *supposed* to be a low-priority fallback, but the code treated them as higher priority than the env-specific config.

**The fix:** Reorder so the layers stack in the correct priority (low → high):

1. `defaults.env` — lowest priority, base layer for a bare container
2. `{env}.yaml` — overrides defaults (staging/production/etc.)
3. real env vars — highest priority

I applied this fix and verified all three scenarios:
- `APP_ENV=staging` → now correctly resolves to `postgres://staging-db.internal:5432/app`
- `APP_ENV=production` → still correctly uses the prod database
- `APP_ENV=staging DATABASE_URL=...` → real env var still wins over the yaml

One thing worth flagging for later: `defaults.env` hardcodes prod values, so any bare container (no `APP_ENV`) will silently connect to production. That's the intended "bare container boots" behavior per the comment, but it's a footgun — you may want platform-eng to revisit that default.