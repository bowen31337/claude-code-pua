Fixed. Here's what was happening and what I changed.

## The bug
In `app.py`, the `get_orders` handler read the limit with a direct dict subscript:

```python
limit = int(params["limit"])
```

When a request to `/orders` didn't include a `?limit` query param, `params` had no `"limit"` key, so `params["limit"]` raised `KeyError: 'limit'` — which bubbled up as the 500 in `error.log`.

## The fix
Changed line 7 to use `.get()` with a default of `50`:

```python
limit = int(params.get("limit", 50))
```

This mirrors the existing pattern on the very next line (`params.get("status", "all")`) and matches the requirement that the limit defaults to 50 when not passed.

## Verification
- `/orders` with no params → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅ (no more 500)
- `/orders?limit=10` → `limit: 10` ✅ (explicit value still respected)
- `/orders?status=shipped` (no limit) → `limit: 50` ✅

One thing worth flagging for later (not part of this bug, so I left it alone): `get_users` and `get_reports` use the same direct-subscript pattern for `page` and `days`, so those endpoints will 500 if their params are missing. Happy to apply the same defensive default there if you'd like.