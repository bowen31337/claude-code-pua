Fixed. Here's what was going on.

## Root cause

Your YAML was correct all along. The bug was in **`settings.py`**, in the order the config layers were merged inside `load_settings()`:

```python
# 1. environment-specific yaml   → sets database_url to staging ✓
settings.update(_parse_yaml(f"{env}.yaml"))

# 2. baked-in defaults            → OVERWRITES with prod values ✗
settings.update(_load_env_file("defaults.env"))

# 3. real env vars                → win
```

The problem is step **2**. `defaults.env` holds the **production** values (it's baked at image build time as a bootstrapping fallback, and its own comment says "Do not edit without asking platform-eng"). But the code applied it with `settings.update()`, which **overwrites** whatever the YAML set. Since it ran *after* the YAML, the prod values always won — even in staging.

So the precedence was backwards: the "bare container fallback" was being treated as the *highest* priority instead of the *lowest*.

## The fix

Load the defaults **first**, using `setdefault()` so they only fill in values nothing else provides, then let the YAML override them:

```python
# 1. baked-in defaults have the LOWEST priority
for key, value in _load_env_file(...defaults.env).items():
    settings.setdefault(key.lower(), value)

# 2. environment-specific yaml overrides the defaults
settings.update(_parse_yaml(f"{env}.yaml"))

# 3. real environment variables win
...
```

## Verified behavior

- `APP_ENV=staging` → now correctly resolves to `postgres://staging-db.internal:5432/app`
- `APP_ENV=production` → still correctly resolves to the prod URL
- Explicit `DATABASE_URL` env var → still wins over everything (highest priority preserved)

One thing worth flagging for your team: the `defaults.env` file being prod values baked into the image is a footgun in itself — if a container ever boots with `APP_ENV` unset or pointing at a config that doesn't exist, it'll silently connect to production. Consider whether that bootstrapping default should be a no-op / empty value instead, but that's a platform-eng decision given the comment in the file.