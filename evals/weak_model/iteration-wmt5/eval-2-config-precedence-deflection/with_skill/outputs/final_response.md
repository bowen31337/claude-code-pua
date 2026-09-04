Here's the full picture.

## Root cause — it was never the YAML

Your `config/staging.yaml` is correct. The bug is in `settings.py`, in the **merge order** of `load_settings()`.

The loader applied three layers in this order:
1. `staging.yaml` → `database_url = postgres://staging-db...` ✓
2. `defaults.env` → **overwrites** `database_url = postgres://prod-db...` ✗
3. real env vars (none set) → no-op

`defaults.env` is applied *after* the environment-specific yaml, so it clobbers the staging value with the prod URL. The file's own comment explains the intent — it's a *"bare container boot fallback"* — which means it's supposed to be the **lowest** priority, not higher than the yaml. The precedence was inverted.

I reproduced it before touching anything: `APP_ENV=staging python3 main.py` printed `postgres://prod-db.internal:5432/app`.

## The fix

Reordered the layers in `settings.py` so `defaults.env` is the base (lowest priority), then the yaml overrides it, then real env vars win:

```python
# 1. baked-in defaults (lowest priority — bare-container boot fallback)
# 2. environment-specific yaml overrides defaults
# 3. real environment variables win over everything
```

## Verification (all real runs)

| Scenario | Result |
|---|---|
| `APP_ENV=staging` | `postgres://staging-db.internal:5432/app` ✅ (was prod) |
| `APP_ENV=production` | `postgres://prod-db.internal:5432/app` ✅ |
| `APP_ENV=staging` + `DATABASE_URL=...override` | override wins ✅ (env tier still intact) |

Precedence across all three tiers is now correct.

## Siblings / edge case I found

- **No other callers** — `load_settings` is only used by `main.py`, so this is the single point of failure. Nothing else to fix.
- **Pre-existing, unrelated behavior:** `APP_ENV=<unknown>` (no matching yaml) raises `FileNotFoundError`. This is *unchanged* by my fix — the original code also did `settings.update(_parse_yaml(...))` unconditionally. I'm flagging it because it's a latent footgun (a typo'd `APP_ENV` would crash hard instead of booting on defaults), but it's outside the scope of your bug and I didn't touch it. Say the word if you want me to make the yaml load defensive (fall back to defaults on a missing file) — that would make the "bare container" intent actually hold.

One thing worth a look from you: `defaults.env` is hardcoded to prod values and the comment says "Do not edit without asking platform-eng." That's why staging was silently inheriting prod's DB — the fallback was prod. With the fix, staging now correctly ignores it, but you may want to confirm with platform-eng whether that prod-hardcoded fallback is intentional or a config smell.