Fixed. Here's the rundown.

## What was actually going on

Your YAML was fine — the bug was in **`settings.py`**, in the order the config layers were merged.

`config/defaults.env` is **baked with the production URLs** (its own comment says so: *"Set from the prod values so a bare container still boots"*). In `load_settings()`, that defaults file was being applied in **step 2 — after** the environment-specific YAML. So every run, the staging config got loaded and then immediately overwritten by the prod defaults:

```
1. staging.yaml  → database_url = staging   ✅ loaded correctly
2. defaults.env  → database_url = prod      ❌ clobbers it
3. env vars      → (none set)               → prod wins
```

You triple-checked the YAML because the YAML was never the problem. The prod values were hiding in `defaults.env`, applied at the wrong precedence.

## The fix

Reordered the merge so `defaults.env` is the **lowest-priority fallback** (what it was intended to be), applied *before* the env-specific YAML:

1. `defaults.env` — lowest, just keeps a bare container alive (uses `setdefault` so it only fills gaps)
2. `{env}.yaml` — overrides the defaults
3. real env vars — highest priority

## Verified behavior

| Scenario | database_url |
|---|---|
| `APP_ENV=staging` (was broken) | `postgres://staging-db.internal:5432/app` ✅ |
| `APP_ENV=production` | `postgres://prod-db.internal:5432/app` ✅ |
| no `APP_ENV` (bare container) | `postgres://prod-db.internal:5432/app` ✅ |
| `APP_ENV=staging` + `DATABASE_URL=...` | override wins ✅ |

Staging now hits the staging DB, production still works, a bare container still boots on prod, and explicit env vars still take top priority. The change is in `settings.py` (I removed the `.bak` after confirming).

One thing worth flagging to your team: `defaults.env` being seeded with prod credentials is a footgun in its own right — if someone ever runs a bare container in a staging context, it'll connect to prod. You may want platform-eng to reconsider how that file is baked, but that's a separate concern from this bug.