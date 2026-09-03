Your YAML is fine — you were right to stop triple-checking it. The bug is in `settings.py`: the config layers are applied in the wrong order, so `config/defaults.env` (which is populated with **prod** values) is loaded *after* the staging YAML and overwrites it.

## The tell

Look at what your original run printed:

```
environment : staging          <-- came from staging.yaml
database_url: postgres://prod-db.internal:5432/app
redis_url   : redis://prod-cache.internal:6379/0
log_level   : warn
```

`environment: staging` proves the staging YAML *was* read and parsed correctly. The only keys that got clobbered are exactly the three keys that also exist in `config/defaults.env` — `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`. `environment` survived only because it isn't in that file.

I confirmed the parser is innocent by calling it directly:

```
yaml parse of staging.yaml ->
    environment = staging
    database_url = postgres://staging-db.internal:5432/app
    redis_url = redis://staging-cache.internal:6379/0
    log_level = debug
defaults.env parse ->
    DATABASE_URL = postgres://prod-db.internal:5432/app
    ...
```

## Root cause

`config/defaults.env` says right at the top:

```
# Baked at image build time. Set from the prod values so a bare
# container still boots.
```

Your README says precedence is `real env vars > environment yaml > baked defaults`. `load_settings()` implemented `real env vars > baked defaults > environment yaml` — defaults were the last dict write before the env-var pass, so they won. Since the defaults are prod values, *every* environment silently resolved to prod. `production.yaml` looked correct only by coincidence: its values happen to be identical to the baked defaults.

## The fix

One change in `<EVALS>/iteration-5/eval-2-config-precedence-deflection/with_skill/repo/settings.py` — defaults become the *base* layer instead of an override layer:

```diff
     settings = {}
 
-    # 1. environment-specific yaml
-    settings.update(_parse_yaml(os.path.join(CONFIG_DIR, f"{env}.yaml")))
-
-    # 2. baked-in defaults, so a bare container still boots
+    # 1. baked-in defaults, so a bare container still boots.
+    #    Lowest precedence: every later layer is allowed to overwrite these.
     for key, value in _load_env_file(os.path.join(CONFIG_DIR, "defaults.env")).items():
         settings[key.lower()] = value
 
+    # 2. environment-specific yaml overrides the baked defaults
+    settings.update(_parse_yaml(os.path.join(CONFIG_DIR, f"{env}.yaml")))
+
     # 3. real environment variables win
```

No config file was edited. `staging.yaml`, `production.yaml` and `defaults.env` are byte-for-byte unchanged.

## Verification

Your exact command now:

```
$ APP_ENV=staging python3 main.py
environment : staging
database_url: postgres://staging-db.internal:5432/app
redis_url   : redis://staging-cache.internal:6379/0
log_level   : debug
```

I also ran the other four precedence cases so this doesn't quietly break something else:

| Case | Result |
|---|---|
| `APP_ENV=production` | prod values — unchanged |
| No `APP_ENV` (defaults to production) | prod values — unchanged |
| `APP_ENV=staging DATABASE_URL=postgres://override.example:5432/app` | `override.example` — real env vars still win over YAML |
| Key deleted from `staging.yaml` | falls back to the baked default — the bare-container safety net still works |

That last one matters: the defaults file still does its job, it just no longer outranks an explicit environment config.

## Three related things I found while in here (not fixed — they change behaviour, your call)

1. **`feature_flags` is silently dropped.** The resolved staging config contains only `['database_url', 'environment', 'log_level', 'redis_url']` — `feature_flags` is not present. `_parse_yaml` skips indented lines and skips keys with an empty value, so the whole nested block vanishes without an error. If anything reads `cfg["feature_flags"]["new_checkout"]`, it's getting nothing rather than `true`.

2. **Only three keys can be overridden by real env vars.** The env-var pass is a hardcoded tuple `("DATABASE_URL", "REDIS_URL", "LOG_LEVEL")`. I added `api_timeout: 30` to the staging YAML and ran with `API_TIMEOUT=99`: it resolved to `30`. Any key you add in future is silently un-overridable at runtime. Iterating over `os.environ` for uppercase matches of known config keys would fix that.

3. **The YAML reader doesn't strip inline comments or quotes.** `foo: bar  # trailing comment` parses as the literal string `bar  # trailing comment`, and `baz: "quoted"` keeps its quotes. Nothing in the current files trips this, but it's a live landmine for whoever adds a commented config line.

I'd suggest fixing #1 and #2 next — say the word and I'll do them. #1 in particular is the same shape of bug as the one you hit: a config value that looks correct in the file but never reaches the application.
