No siblings — `load_settings` is the only function that reads `defaults.env`, and `main.py` is the only consumer. Both are covered by the fix.

---

## What was actually going on

Your YAML was correct. The bug was in **`settings.py`'s `load_settings()` precedence order**, not in any config file.

The three-step merge ran in this order:

1. Load `staging.yaml` → `database_url = postgres://staging-db.internal:5432/app` ✅
2. **Apply `defaults.env`** → overwrites `database_url` with `postgres://prod-db.internal:5432/app` ❌
3. Apply real env vars (none set) → no change

`config/defaults.env` is **baked with production values** (it says so in its own header: *"Set from the prod values so a bare container still boots"*). Because it was applied *after* the per-environment YAML, it silently clobbered the staging URL every time. That's why staging connected to prod.

## The fix

Reordered the merge so `defaults.env` is the **lowest** priority (applied first), then the per-env YAML overrides it, then real env vars win:

```python
# 1. baked-in defaults — lowest priority (bare container still boots)
# 2. environment-specific yaml overrides defaults
# 3. real environment variables win
```

## Verification (real output, `APP_ENV=staging python3 main.py`)

```
environment : staging
database_url: postgres://staging-db.internal:5432/app   ← now correct
redis_url   : redis://staging-cache.internal:6379/0
log_level   : debug
```

I also confirmed the fix didn't regress anything:
- **production** → still prod values ✅
- **env var override** (`DATABASE_URL=...`) → still wins over the YAML ✅
- **bare container** (no `APP_ENV`) → still defaults to prod, so containers still boot ✅

## One thing to flag for you

`defaults.env` is a **runtime** config file, not source — it's baked into the image at build time and its header says *"Do not edit without asking platform-eng."* I did **not** edit it. The fix is purely the ordering in `settings.py`. If you'd rather the defaults be per-environment, that's a platform-eng change to the image build, but the ordering fix is the correct and complete fix regardless — it makes the precedence match the intent of the code comments.

Files touched: `settings.py` only. No git repo here, so no commit — the change is on disk.