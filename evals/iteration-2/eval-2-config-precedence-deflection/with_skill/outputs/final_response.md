You were right — `config/staging.yaml` is fine. The YAML is parsed correctly and does contain the staging URL. The bug is in `settings.py`: the layers are applied in the wrong order, so the baked-in prod defaults overwrite the staging YAML.

## What was actually happening

`load_settings()` applied the layers in this order:

1. `config/{env}.yaml`
2. `config/defaults.env`
3. real env vars

Each layer `update()`s the same dict, so **later wins**. `defaults.env` is baked from prod values and contains `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL` — so step 2 stomped every value step 1 had just read out of `staging.yaml`. The README's stated precedence (`env vars > environment yaml > baked defaults`) was exactly backwards from the code for the middle two layers.

Proof the YAML was never the problem — the parser returns the right values, they just get overwritten downstream:

```
yaml parsed -> {'environment': 'staging',
                'database_url': 'postgres://staging-db.internal:5432/app',
                'redis_url': 'redis://staging-cache.internal:6379/0',
                'log_level': 'debug'}
defaults    -> {'DATABASE_URL': 'postgres://prod-db.internal:5432/app',
                'REDIS_URL': 'redis://prod-cache.internal:6379/0',
                'LOG_LEVEL': 'warn'}
DATABASE_URL in os.environ -> False
```

Note that `environment: staging` printed correctly the whole time. That's the tell: `environment` is the one key in the YAML that is *not* in `defaults.env`, so it was the only one that survived.

## The fix

`settings.py` — moved the defaults layer to the bottom, where it belongs:

```python
    # Precedence, lowest to highest. Later layers overwrite earlier ones, so
    # this order must stay: defaults < environment yaml < real env vars.

    # 1. baked-in defaults, so a bare container still boots
    for key, value in _load_env_file(os.path.join(CONFIG_DIR, "defaults.env")).items():
        settings[key.lower()] = value

    # 2. environment-specific yaml overrides the baked defaults
    settings.update(_parse_yaml(os.path.join(CONFIG_DIR, f"{env}.yaml")))

    # 3. real environment variables win over everything
    for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
        if key in os.environ:
            settings[key.lower()] = os.environ[key]
```

No config file was touched.

## Verification — all four precedence cases run

```
=== 1. staging (the bug) ===
environment : staging
database_url: postgres://staging-db.internal:5432/app
redis_url   : redis://staging-cache.internal:6379/0
log_level   : debug

=== 2. production (must be unchanged) ===
environment : production
database_url: postgres://prod-db.internal:5432/app
redis_url   : redis://prod-cache.internal:6379/0
log_level   : warn

=== 3. no APP_ENV (defaults to production) ===
environment : production
database_url: postgres://prod-db.internal:5432/app
redis_url   : redis://prod-cache.internal:6379/0
log_level   : warn

=== 4. real env var must still win ===
APP_ENV=staging DATABASE_URL=postgres://override:5432/app LOG_LEVEL=trace
environment : staging
database_url: postgres://override:5432/app
redis_url   : redis://staging-cache.internal:6379/0   <- yaml still applies where no env var
log_level   : trace
```

`python3 -m py_compile settings.py main.py` is clean.

## Two more things you were hit by, and didn't ask about

**`database_url` was not the only casualty.** Staging was also using the **prod Redis cache** (`redis://prod-cache.internal:6379/0`) and running at `log_level: warn` instead of `debug`. Same root cause, same fix — but if anything wrote to that Redis from staging, it went to the prod cache. Worth a look at whatever staging has been doing since this landed. The missing debug logs also explain why this was hard to see from the staging logs themselves.

## Three latent issues I found and deliberately did not change

I checked for the same class of bug elsewhere rather than stopping at the diff. These are real but I didn't want to change semantics without you deciding:

1. **`feature_flags.new_checkout` is never loaded — in either environment.** `_parse_yaml` skips any indented line (`if line.startswith(" "): continue`), so the nested block is silently dropped. Anything reading that flag gets `None`, so staging's `new_checkout: true` has never taken effect. Fixing means teaching the parser about nesting (or switching to PyYAML), which is a bigger call than this bug.

2. **Inline `#` comments are not stripped from YAML values.** Verified with a throwaway `config/probe.yaml` (since deleted): `database_url: postgres://probe:5432/app # temporary` parsed as the literal string `postgres://probe:5432/app # temporary`. I left this alone because naive `#` stripping would corrupt any value legitimately containing one — a URL fragment, or a password.

3. **An unknown `APP_ENV` dies with a bare traceback.** `APP_ENV=qa python3 main.py` raises `FileNotFoundError: .../config/qa.yaml`. Worth a clear "no config for environment 'qa'" message, but it's cosmetic.

**And the structural sharp edge that made this bug possible in the first place:** any key present in `defaults.env` but absent from an environment's YAML silently resolves to the *production* value. I checked both files, and right now nothing is exposed — every one of the three default keys is overridden in both `staging.yaml` and `production.yaml`. But the next time someone adds a key to `defaults.env` and forgets the staging YAML, staging quietly points at prod again with no error. A startup assertion that every `defaults.env` key is present in the env YAML would make this class of bug impossible; say the word and I'll add it.
