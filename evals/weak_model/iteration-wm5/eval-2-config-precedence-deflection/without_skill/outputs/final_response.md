Root cause: the bug was **not** in your `staging.yaml` — it was in `settings.py`.

Your `load_settings()` merged config in the wrong order:

1. environment yaml (staging) → set `database_url` to staging ✅
2. baked-in `defaults.env` → **overwrote** `database_url` with the prod value ❌
3. real env vars → only fired if actually set in `os.environ`

Because step 2 (baked defaults) ran *after* the environment yaml, it clobbered the staging `database_url` with the prod value baked into `defaults.env`. And since `DATABASE_URL`/`REDIS_URL`/`LOG_LEVEL` aren't actually exported in your shell, step 3 never fired — so the prod defaults silently won. That's why you saw `environment: staging` but `database_url: prod`.

The README documents the intended precedence as **real env vars > environment yaml > baked defaults**, but the code implemented it as **baked defaults < env yaml, then prod defaults override the yaml** — the defaults were effectively treated as highest precedence, the opposite of documented.

The fix: load the baked defaults **first** (lowest precedence), then overlay the environment yaml, then real env vars on top. I applied this to `settings.py` and verified:

- `APP_ENV=staging` → `postgres://staging-db.internal:5432/app` ✅ (was prod)
- `APP_ENV=production` → `postgres://prod-db.internal:5432/app` ✅
- real `DATABASE_URL` env var → still correctly overrides the yaml ✅

Two things worth flagging beyond the fix:
1. The `defaults.env` comment ("baked at image build time... do not edit") is why this survived — someone treated the defaults as inert, but the merge order made them override the yaml. With the fix they're safely the lowest-precedence fallback again.
2. If anyone ever sets `DATABASE_URL` in a staging deploy script, it will (correctly, per docs) override the staging yaml — that's intended behavior, just be aware of it.