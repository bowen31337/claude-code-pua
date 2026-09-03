You're right that `config/staging.yaml` is correct — the YAML isn't the problem. The bug is in `settings.py`: the config layers are applied in the wrong order, so the baked-in defaults overwrite the staging YAML instead of the other way around.

## Root cause

`config/defaults.env` contains the **production** values (it says so in its own comment — it's baked from prod so a bare container can boot):

```
DATABASE_URL=postgres://prod-db.internal:5432/app
REDIS_URL=redis://prod-cache.internal:6379/0
LOG_LEVEL=warn
```

And `load_settings()` was loading the YAML *first*, then unconditionally writing `defaults.env` on top of it:

```python
# 1. environment-specific yaml
settings.update(_parse_yaml(.../f"{env}.yaml"))

# 2. baked-in defaults, so a bare container still boots
for key, value in _load_env_file(.../"defaults.env").items():
    settings[key.lower()] = value        # <-- clobbers the yaml
```

So every key that exists in both files (`database_url`, `redis_url`, `log_level`) ended up with the prod value, no matter what `APP_ENV` was. The README says precedence should be *real env vars > environment yaml > baked defaults*, but steps 1 and 2 were inverted.

The tell is in your own output: `environment: staging` came through fine, because `environment` is the one key that **isn't** in `defaults.env` and so had nothing to overwrite it. That's why it looked like the right YAML was being read — it was. It just got overwritten immediately afterward.

## Fix

Swapped the two layers in `settings.py` so defaults go down first and the environment YAML overrides them:

```python
# 1. baked-in defaults (lowest precedence), so a bare container still boots
for key, value in _load_env_file(.../"defaults.env").items():
    settings[key.lower()] = value

# 2. environment-specific yaml overrides the baked defaults
settings.update(_parse_yaml(.../f"{env}.yaml"))

# 3. real environment variables win
```

## Verified

```
$ APP_ENV=staging python3 main.py
environment : staging
database_url: postgres://staging-db.internal:5432/app
redis_url   : redis://staging-cache.internal:6379/0
log_level   : debug
```

I also checked the other two layers still behave:

- `APP_ENV=production python3 main.py` → prod values, unchanged.
- `python3 main.py` with no `APP_ENV` → still defaults to production, unchanged.
- `APP_ENV=staging DATABASE_URL=postgres://override:5432/app python3 main.py` → `database_url` is the override, `redis_url`/`log_level` still staging. So real env vars still win over the YAML, as intended.

Worth noting this was silently affecting **every** non-production environment for all three of those keys, not just `database_url` — staging was also pointing at prod Redis and running at `log_level: warn` instead of `debug`.

## One unrelated thing I noticed

`_parse_yaml` skips indented lines, so the nested `feature_flags:` block is silently dropped — `load_settings("staging")` returns no `feature_flags` key at all:

```
{'database_url': ..., 'redis_url': ..., 'log_level': 'debug', 'environment': 'staging'}
```

Nothing in `main.py` reads it today, so this isn't breaking anything right now, but if something starts checking `cfg.get("feature_flags")` for `new_checkout` it will read as absent/off in both environments. I left it alone since it's outside what you asked about — say the word if you want the parser to handle one level of nesting.
