Your YAML is fine. Stop re-checking it — the bug is in `settings.py`, and your file was never going to fix it.

## What's actually happening

`load_settings()` loaded the config layers in the wrong order:

```python
# 1. environment-specific yaml
settings.update(_parse_yaml(.../staging.yaml))      # sets staging URLs

# 2. baked-in defaults, so a bare container still boots
for key, value in _load_env_file(.../defaults.env).items():
    settings[key.lower()] = value                    # ...then stomps them
```

`config/defaults.env` is baked **from the prod values** (its own header says so), and it was applied *after* the environment YAML. So every key present in both files got overwritten with the prod value, every time, in every environment.

The tell was in your own output. `environment: staging` printed correctly — because `environment` is the one key that *isn't* in `defaults.env`. Everything that appears in both files got clobbered:

```
yaml parsed      : environment, database_url, redis_url, log_level  (all correct staging values)
defaults.env keys: database_url, log_level, redis_url
overlap (stomped): database_url, log_level, redis_url
```

That's also why it looked like the YAML was being ignored — it wasn't. It was being read correctly and then overwritten.

## The fix

Swapped steps 1 and 2 in `settings.py` so defaults are the floor, not the ceiling — matching the precedence your README already documents (`real env vars > environment yaml > baked defaults`):

```python
# 1. baked-in defaults, so a bare container still boots. Lowest priority:
#    these are prod values, so anything more specific must overwrite them.
for key, value in _load_env_file(.../defaults.env).items():
    settings[key.lower()] = value

# 2. environment-specific yaml overrides the baked defaults
settings.update(_parse_yaml(.../{env}.yaml))

# 3. real environment variables win
```

## Verified — all three layers, not just your symptom

```
=== 1. staging (the reported bug) ===
environment : staging
database_url: postgres://staging-db.internal:5432/app
redis_url   : redis://staging-cache.internal:6379/0
log_level   : debug

=== 2. production (regression check) ===
database_url: postgres://prod-db.internal:5432/app

=== 3. no APP_ENV -> defaults to production ===
database_url: postgres://prod-db.internal:5432/app

=== 4. real env var must beat staging.yaml ===
database_url: postgres://override.local:5432/app     <- override wins
log_level   : debug                                   <- yaml still wins elsewhere

=== 5. defaults.env still fills keys the yaml omits ===
database_url: postgres://prod-db.internal:5432/app    <- floor still works
```

Note case 5: the defaults layer still does its "bare container still boots" job. The fix changes precedence, not the safety net.

## Regression guard

Added `test_precedence.py` (stdlib `unittest`, no new deps) pinning all four behaviours above:

```
$ python3 -m unittest test_precedence -v
test_default_env_is_production ... ok
test_defaults_fill_keys_the_yaml_omits ... ok
test_real_env_var_beats_yaml ... ok
test_yaml_beats_baked_defaults ... ok
Ran 4 tests in 0.002s
OK
```

I also checked the test actually catches the bug rather than just passing — reverted `settings.py` to the original, re-ran, got `FAILED (failures=2)` with `'postgres://prod-db...' != 'postgres://staging-db...'`, then restored the fix. A test that can't fail isn't a guard.

## Two related things I found next to it — not fixed, your call

Both are latent (nothing consumes them today), and `defaults.env` says not to touch it without platform-eng, so I flagged rather than changed:

1. **`feature_flags` never reaches the app.** `_parse_yaml` is a flat reader: it `continue`s on indented lines and drops keys with empty values. So `feature_flags:` / `  new_checkout: true` is silently discarded in both YAMLs. Confirmed — the app only ever sees `['database_url', 'environment', 'log_level', 'redis_url']`. The moment someone writes `cfg["feature_flags"]`, it's a `KeyError`, and `new_checkout` is currently dead config in staging. If flags are meant to be live, this parser needs real YAML (`pyyaml`) or explicit nesting support.

2. **The env-var override list is hardcoded to three keys.** `for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL")` — add a fourth key to the configs (say `S3_BUCKET`) and the documented "real env vars win" rule silently stops applying to it, with no error. Same failure signature as the bug you just hit: config that looks right and is quietly ignored. I left it alone deliberately — deriving the list from the config keys would make a stray `ENVIRONMENT` in someone's shell start overriding `environment`, which is a semantics decision you should own rather than inherit from me.

## Files touched

- `settings.py` — reordered the two load steps in `load_settings()` (the fix)
- `test_precedence.py` — new, regression guard

No config files were modified. Your `staging.yaml` was correct the whole time.
