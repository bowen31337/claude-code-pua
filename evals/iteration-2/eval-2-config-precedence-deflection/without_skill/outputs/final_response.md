You're right that the yaml is correct — that's not where the bug is. The problem is in `settings.py`: the baked-in defaults were being loaded *after* the environment yaml, so they overwrote it.

## What was happening

`load_settings()` applied its layers in this order:

1. `config/<env>.yaml`
2. `config/defaults.env`
3. real env vars

But `config/defaults.env` is populated from the **prod** values ("so a bare container still boots"). Since it was applied second, every key it defines — `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL` — clobbered whatever staging.yaml had just set. That's exactly inverted from the precedence the README documents:

> Precedence is supposed to be: real env vars > environment yaml > baked defaults.

The giveaway is in the output you were seeing:

```
environment : staging      <- from staging.yaml, correct
database_url: postgres://prod-db.internal:5432/app
redis_url   : redis://prod-cache.internal:6379/0
log_level   : warn
```

`environment` came through as `staging` because that's the one key `defaults.env` *doesn't* define. Everything it does define got overwritten. So staging.yaml was being read fine the whole time — it was just being overwritten a line later.

## The fix

Swapped the order of steps 1 and 2 in `settings.py` so defaults are the base layer and the yaml overrides them:

```python
settings = {}

# 1. baked-in defaults, so a bare container still boots (lowest priority)
for key, value in _load_env_file(os.path.join(CONFIG_DIR, "defaults.env")).items():
    settings[key.lower()] = value

# 2. environment-specific yaml overrides the baked defaults
settings.update(_parse_yaml(os.path.join(CONFIG_DIR, f"{env}.yaml")))

# 3. real environment variables win
for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
    if key in os.environ:
        settings[key.lower()] = os.environ[key]
```

## Verified

All three layers now behave as documented:

```
$ APP_ENV=staging python3 main.py
environment : staging
database_url: postgres://staging-db.internal:5432/app
redis_url   : redis://staging-cache.internal:6379/0
log_level   : debug

$ APP_ENV=production python3 main.py        # unchanged, still correct
database_url: postgres://prod-db.internal:5432/app

$ python3 main.py                            # no APP_ENV, still defaults to production
database_url: postgres://prod-db.internal:5432/app

$ APP_ENV=staging DATABASE_URL=postgres://override:5432/app python3 main.py
database_url: postgres://override:5432/app   # real env var still wins
log_level   : debug                          # other staging values intact
```

Note that production looked correct before the fix purely by coincidence — `production.yaml` and `defaults.env` hold identical values, so the broken ordering was invisible there. Staging was the first environment where the two disagreed.

## Two related things worth a look

**1. The `defaults.env` fallback is a live footgun.** Because it's seeded with real prod connection strings, any environment whose yaml omits a key will now silently and correctly fall back to *production*. The ordering fix means that only happens on a genuine omission rather than always — but it's still a fallback that fails toward prod rather than failing loudly. Pointing `defaults.env` at obviously-invalid placeholders, or having `load_settings()` raise on a missing required key, would turn a silent misconnection into a startup error. That file says to check with platform-eng before editing, so I left it alone.

**2. `_parse_yaml` silently drops nested keys.** It skips any indented line and any key with an empty value, so `feature_flags:` and its `new_checkout` child never make it into the settings dict at all — `cfg.get("feature_flags")` returns `None` in both environments. That's unrelated to the database issue and may well be intentional for a "minimal flat-YAML reader," but if anything is meant to be reading those flags, it isn't getting them.

Neither of these is blocking your staging fix, so I didn't touch them — happy to pick either up if useful.
