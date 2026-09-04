**Root cause: it's a config-load ordering bug in `settings.py`, not your YAML.**

`load_settings()` applies the three layers in this order:

1. `config/staging.yaml` → correctly sets `database_url` to the staging URL
2. `config/defaults.env` → **unconditionally overwrites** it with the prod URL
3. real env vars → no-op, because none are set

The culprit is step 2 in `settings.py`:

```python
for key, value in _load_env_file(os.path.join(CONFIG_DIR, "defaults.env")).items():
    settings[key.lower()] = value          # <-- always overwrites
```

`defaults.env` is deliberately baked with the **production** values ("Set from the prod values so a bare container still boots"). Because that loop has no guard, it clobbers the staging values the yaml just loaded. Since no real `DATABASE_URL`/`REDIS_URL`/`LOG_LEVEL` env vars are set in your shell, nothing fixes it afterward — so staging ends up pointing at prod.

**The fix** — make the baked-in defaults a true *fallback* (only fill keys that aren't already set):

```python
# 2. baked-in defaults, so a bare container still boots
for key, value in _load_env_file(os.path.join(CONFIG_DIR, "defaults.env")).items():
    settings.setdefault(key.lower(), value)
```

`setdefault` preserves the yaml value when present and only fills in when the key is missing — which is exactly what "bare container still boots" is supposed to mean.

After this change, `APP_ENV=staging python3 main.py` will print the staging `database_url`. (Equally valid: reorder so the defaults load *first* and the yaml overrides them, but `setdefault` is the minimal, clearest fix and keeps the documented precedence: env vars > yaml > baked defaults.)