The problem was never your YAML — it was correct. The bug was in `settings.py`, in the **precedence ordering** inside `load_settings()`.

What was happening on `APP_ENV=staging python3 main.py`:
1. Load `staging.yaml` → `database_url = postgres://staging-db.internal:5432/app` ✓
2. Apply `defaults.env` → **overwrites** `database_url` with the prod URL ✗
3. Apply real env vars → none set, no change

Because the baked-in `defaults.env` was applied *after* the environment-specific yaml, it clobbered your staging value every time. (The `defaults.env` comment telling you not to edit it is a red herring — the fix belongs in `settings.py`, not in that file.)

The fix: reorder so `defaults.env` is applied **first** (lowest priority, as a boot fallback), then the yaml overrides it, then real env vars win. This preserves the documented intent of `defaults.env` ("so a bare container still boots") — a fallback should have the *lowest* priority, not override real config.

Verified after the change:
- `APP_ENV=staging` → staging DB ✅
- `APP_ENV=production` → prod DB ✅
- no `APP_ENV` → still boots from `defaults.env` ✅
- real `DATABASE_URL` env var → still wins ✅

The one-line change was swapping the order of steps 1 and 2 in `load_settings()`.