## Summary

**The bug was not in the YAML — it was in the loader's precedence order.**

`config/staging.yaml` is correct (it sets `database_url` to the staging host). The problem was in `load_settings()` in `settings.py`. The three-step merge ran in the wrong order:

1. load environment yaml → staging values ✓
2. **apply `defaults.env` with `settings[key.lower()] = value` → overwrote staging with baked prod defaults** ✗
3. apply real env vars

The `defaults.env` file is "baked at image build time from the prod values so a bare container still boots." Because it was applied *after* the environment yaml, it clobbered the staging database URL every time — exactly the symptom you saw. The precedence in the README ("real env vars > environment yaml > baked defaults") was the intended contract, and the code violated it.

**The fix:** reorder so baked defaults load *first* (lowest precedence), then the environment yaml overrides them, then real env vars win.

**Verified** (ran `APP_ENV=staging python3 main.py` before and after):

| Scenario | Before | After |
|---|---|---|
| `APP_ENV=staging` | `prod-db.internal` ❌ | `staging-db.internal` ✅ |
| `APP_ENV=production` | `prod-db.internal` | `prod-db.internal` ✅ |
| no `APP_ENV` (defaults to production) | `prod-db.internal` | `prod-db.internal` ✅ |
| `APP_ENV=staging` + `DATABASE_URL` set | `override` | `override` ✅ (env var still wins) |

All four behave per the documented precedence.

**Files touched:** `settings.py` (reordered the merge steps; the `_parse_yaml`/`_load_env_file` helpers and the config files were left untouched).

**One thing worth flagging for you:** `defaults.env` is baked from prod values, so any environment that *isn't* explicitly loaded (or a bare container) will still connect to prod. That's the intended "bare container boots" behavior, but it's worth confirming that's actually what you want — if a staging/other container ever loads without the right `APP_ENV`, it'll hit prod. That's a config/ops decision, not a code bug, so I left it alone.