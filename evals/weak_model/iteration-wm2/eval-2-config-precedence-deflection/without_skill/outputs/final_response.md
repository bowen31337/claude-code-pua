Your yaml was right all along — the bug was in `settings.py`, not in your config.

## Root cause

`load_settings()` applies config layers in the wrong precedence order:

```python
# 1. environment-specific yaml   → sets staging DB URL correctly
settings.update(_parse_yaml(...))

# 2. baked-in defaults            → UNCONDITIONALLY overwrites everything!
for key, value in _load_env_file("defaults.env").items():
    settings[key.lower()] = value          # <-- bug

# 3. real env vars win
```

The problem is step 2. `defaults.env` contains **production** values (it's baked at image-build time as a "bare container boots" fallback — see its own comment). The code did `settings[key] = value`, which **unconditionally overwrote** the correct staging values from `staging.yaml`. So no matter what `APP_ENV` was, the prod values in `defaults.env` always won over the yaml.

That's why `APP_ENV=staging` printed the prod URL.

## The fix

Changed step 2 to use `setdefault`, so `defaults.env` only fills in keys that **aren't already set** — making it a true fallback, which is exactly what its comment says it's meant to be:

```python
# 2. baked-in defaults, so a bare container still boots
for key, value in _load_env_file("defaults.env").items():
    settings.setdefault(key.lower(), value)   # only if not already set
```

## Verified behavior after the fix

- `APP_ENV=staging` → now correctly prints the **staging** DB URL ✅
- `APP_ENV=production` → still prints prod ✅
- Unknown env (no yaml) → falls back to `defaults.env` ✅
- Real env vars (`DATABASE_URL=...`) → still win over everything ✅

One thing worth flagging for later: `defaults.env` baking in **production** credentials is a footgun — if anyone ever runs a container without `APP_ENV` or a yaml, they'll silently hit prod. But that's a separate concern from this bug; the precedence fix above resolves the immediate issue.