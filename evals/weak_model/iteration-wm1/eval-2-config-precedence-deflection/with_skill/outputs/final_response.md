## Root cause: config precedence was applied in the wrong order

Your `staging.yaml` was correct the whole time. The bug was in **`settings.py`**, in the order `load_settings()` merged the three config sources.

### What was actually happening

`load_settings()` applied the sources in this order:

1. environment yaml (staging) → `database_url = postgres://staging-db.internal`
2. **baked-in defaults** → `database_url = postgres://prod-db.internal` ← **clobbered the staging value**
3. real env vars → only applied *if* `DATABASE_URL` was set in the environment

So on every run, step 2 overwrote the staging yaml with the prod defaults baked into `config/defaults.env`. The comment in that file even explains why: *"Baked at image build time… Set from the prod values so a bare container still boots."* Those prod defaults were being treated as a fallback, but because they were applied *after* the yaml, they acted as an override.

It stayed hidden for two reasons:
- **No test** exercised the resolution order, so the regression could sit there silently.
- The env-var step (step 3) *looked* like it would win — but only when a real `DATABASE_URL` happened to be exported. In a normal `APP_ENV=staging python3 main.py` run with no env vars set, step 3 never fires, so you never saw the yaml "win."

I confirmed this by tracing the intermediate state:
```
after yaml      : postgres://staging-db.internal:5432/app
after defaults  : postgres://prod-db.internal:5432/app   <-- clobbered
after env vars  : postgres://prod-db.internal:5432/app
```

### The fix

Reordered the merge so precedence matches what the README declares (`real env vars > environment yaml > baked defaults`):

```python
# 1. baked-in defaults first (lowest precedence)
for key, value in _load_env_file(...defaults.env).items():
    settings[key.lower()] = value
# 2. environment yaml overrides defaults
settings.update(_parse_yaml(.../{env}.yaml))
# 3. real env vars win over everything
for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
    if key in os.environ:
        settings[key.lower()] = os.environ[key]
```

### Verification (all four cases pass)

| Run | `database_url` |
|---|---|
| `APP_ENV=staging` | `postgres://staging-db.internal:5432/app` ✅ (was prod) |
| `APP_ENV=production` | `postgres://prod-db.internal:5432/app` ✅ |
| `APP_ENV=staging DATABASE_URL=override` | `postgres://override:5432/app` ✅ (env still wins) |
| bare (no `APP_ENV`) | `postgres://prod-db.internal:5432/app` ✅ (defaults still boot) |

### Sibling check
`grep` for other config-loading paths found only `settings.py` and `main.py` — no other code path loads config with this ordering, so there are no siblings to fix.

### One thing worth flagging (not fixed, needs a decision)
`config/defaults.env` still contains **prod** credentials baked into the image, and the whole reason this bit you is that a "bare container boots" against production. That's a latent footgun — if anything ever runs without `APP_ENV` set, it connects to prod. Consider:
- Seeding `defaults.env` from real env vars at container start instead of baking prod values in, or
- Making the bare-container default point at a throwaway/local DB and failing loud if `APP_ENV` is unset.

Want me to add a small regression test for the precedence order so this can't silently regress again?