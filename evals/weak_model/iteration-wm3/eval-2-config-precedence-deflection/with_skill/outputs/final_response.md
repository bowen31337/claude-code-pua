Fixed. The bug was in `settings.py`, not your YAML — `config/staging.yaml` was correct the whole time.

**Root cause:** `load_settings()` merged config in three steps: (1) load the env yaml, (2) load `defaults.env` and *unconditionally overwrite* every key, (3) apply real env vars. Step 2 used `settings[key.lower()] = value`, which clobbered the staging URL with the prod URL baked into `defaults.env`. That defaults file is intentionally prod-baked ("so a bare container still boots"), so it was designed to win over the yaml — making the yaml layer dead code for any key present in `defaults.env`. This contradicts the precedence your README documents (`env vars > yaml > defaults`).

I confirmed empirically: with no `APP_ENV`/`DATABASE_URL` set, `APP_ENV=staging python3 main.py` printed the prod URL, and a trace showed the staging value being overwritten exactly when the defaults step ran.

**Fix (one line, `settings.py` line 45):**
```python
settings.setdefault(key.lower(), value)   # fill missing keys, don't overwrite
```

**Verified (all four pass):**
- `APP_ENV=staging` (your reported bug) → now prints staging DB ✅
- `APP_ENV=production` → prod ✅
- `APP_ENV=staging DATABASE_URL=...override` → env var still wins ✅
- bare (no `APP_ENV`) → defaults fill in, prod boots ✅

**Closed the loop:** grep for the same overwrite pattern found only the env-var override (line 50), which is correct — no sibling bugs. The fix now matches the precedence in `README.md`.

**One caveat:** `defaults.env` is intentionally prod-baked. With this fix, the only thing between a bare container and prod DB is that default. If you want other environments to boot bare without leaking prod, the defaults should be neutral rather than prod values — but that's a platform-eng call given the file's "do not edit without asking platform-eng" note, so I left it untouched.

One file touched: `settings.py`.