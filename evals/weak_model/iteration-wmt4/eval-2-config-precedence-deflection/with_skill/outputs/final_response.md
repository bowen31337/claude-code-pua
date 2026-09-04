No siblings — `load_settings` is only invoked from `main.py`, and the precedence logic lives in exactly one place. The fix is complete and isolated.

---

## Root cause: it was never the YAML

You triple-checked the yaml, and you were right — `config/staging.yaml` is correct. The bug was in **`settings.py`'s config precedence order**, which contradicted the documented contract in `README.md`.

### What the code was actually doing

`README.md` documents the intended precedence:

> real env vars > environment yaml > baked defaults

But `load_settings()` applied them in the wrong order:

1. load `{env}.yaml`
2. `settings.update(defaults.env)` ← **this overwrote the yaml**
3. real env vars

So the *effective* order was `env vars > defaults > yaml`. Since `config/defaults.env` is baked with **production** values (intentionally, so a bare container boots), the prod `database_url` clobbered the staging yaml on every staging run. The yaml was correct but always lost.

### Proof

Before fix:
```
APP_ENV=staging python3 main.py
database_url: postgres://prod-db.internal:5432/app   ← prod, from defaults.env
```

After fix (reordered so defaults are the base, yaml overrides them, env vars win — matching the README):
```
APP_ENV=staging python3 main.py
database_url: postgres://staging-db.internal:5432/app   ← correct
```

I also verified the three sibling scenarios still hold: production still resolves to prod, a bare container (no `APP_ENV`) still boots to prod, and a real `DATABASE_URL` env var still wins over everything.

### The fix

One file, `settings.py` — reordered the three steps so the baked defaults are loaded *first* as the base, then the env yaml overrides them, then real env vars win. No changes to any config file.

### Siblings checked
- `load_settings` is called only from `main.py` — no other callers.
- The precedence logic exists in exactly one place — no duplicated copy elsewhere.

### One thing worth flagging (not something I changed)
`defaults.env` is intentionally prod-baked ("Do not edit without asking platform-eng"). The real fix was the ordering; the prod defaults are now correctly *overridden* by the staging yaml rather than clobbering it. If you'd rather not rely on that ordering, the alternative is to make the defaults empty/neutral — but that's a platform-eng decision, so I left it alone.