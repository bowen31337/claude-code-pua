# Your YAML is fine — the loader applies it in the wrong order

`config/staging.yaml` is correct and it *is* being read. The problem is in `settings.py`: the baked-in defaults are loaded **after** the environment YAML, so they overwrite it.

The original `load_settings()` did this:

```python
# 1. environment-specific yaml
settings.update(_parse_yaml(.../f"{env}.yaml"))

# 2. baked-in defaults, so a bare container still boots
for key, value in _load_env_file(.../"defaults.env").items():
    settings[key.lower()] = value      # <-- clobbers the yaml values
```

`config/defaults.env` is populated from the prod values, so step 2 stamped `DATABASE_URL`, `REDIS_URL`, and `LOG_LEVEL` back to prod on every run, regardless of `APP_ENV`.

The giveaway: before the fix, `APP_ENV=staging` printed `environment: staging` (that key only exists in the YAML, so nothing overwrote it) but prod values for everything else — exactly the three keys `defaults.env` defines. It also meant staging and production produced byte-identical output.

## The fix

Swapped the two steps so the ordering matches what the README specifies (real env vars > environment yaml > baked defaults):

```python
# 1. baked-in defaults, so a bare container still boots (lowest precedence)
for key, value in _load_env_file(.../"defaults.env").items():
    settings[key.lower()] = value

# 2. environment-specific yaml overrides the baked defaults
settings.update(_parse_yaml(.../f"{env}.yaml"))

# 3. real environment variables win
```

Only `settings.py` changed; no config files were touched.

## Verified

```
APP_ENV=staging     -> staging-db.internal, staging-cache.internal, log_level debug
APP_ENV=production  -> prod-db.internal,    prod-cache.internal,    log_level warn
APP_ENV=staging DATABASE_URL=postgres://override/db LOG_LEVEL=trace
                    -> database_url=postgres://override/db, log_level=trace,
                       redis_url still staging  (real env vars beat yaml, per-key)
no APP_ENV          -> production values (unchanged default behaviour)
```

All three precedence layers now behave as documented, and the bare-container case still works since `defaults.env` remains the base layer.

## One unrelated thing I noticed (not fixed)

`_parse_yaml` skips any line that is indented or has an empty value, so `feature_flags:` and its nested `new_checkout` are silently dropped from the returned settings in both environments. Nothing currently reads `feature_flags`, so it isn't causing a problem today — but if something starts depending on it, it will read as missing rather than as `false`. Worth a look separately if you plan to use those flags.
