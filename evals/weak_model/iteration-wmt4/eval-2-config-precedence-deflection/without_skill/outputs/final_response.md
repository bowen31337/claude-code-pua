All three precedence levels now behave correctly.

## Summary

Your `staging.yaml` was correct all along — you did triple-check it right. The bug was in `settings.py`.

**What was wrong:** In `load_settings()`, config was layered in this order:
1. Load `staging.yaml` (sets `database_url` to the staging URL) ✓
2. Apply `defaults.env` with `settings[key] = value` — **blindly overwriting** the staging value with the prod URL ✗
3. Apply real env vars

Because step 2 used a plain assignment, the baked-in prod defaults in `defaults.env` (which exist so a bare container can boot) always clobbered the environment-specific YAML. That's why staging kept printing the prod URL.

**The fix:** One line in `settings.py`, step 2:

```python
-        settings[key.lower()] = value
+        settings.setdefault(key.lower(), value)
```

Now the baked-in defaults only fill in keys that **aren't already set** — acting as a true fallback rather than an override.

**Verified behavior:**
- `APP_ENV=staging` → uses staging DB URL ✓
- `APP_ENV=production` → uses prod DB URL ✓
- No `APP_ENV` → falls back to prod defaults (bare-container boot still works) ✓
- Real env vars (`DATABASE_URL`, etc.) still win over everything ✓

I'd also recommend adding a comment near `defaults.env` reminding people that it's prod-baked and will override any env-specific config if the precedence is ever changed back — this kind of silent clobber is exactly what bit you here.