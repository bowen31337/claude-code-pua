Fixed. Here's what was happening and what I changed.

## The bug
In `app.py`, the `get_orders` handler read the limit directly from the params dict:

```python
limit = int(params["limit"])
```

When a request to `/orders` didn't include a `?limit` query param, `params` had no `"limit"` key, so `params["limit"]` raised a `KeyError`. That exception propagated up through `handle()` → `dispatch()` and surfaced as a **500**.

## The fix
Changed line 6 in `app.py` to default to `50` when the param is missing, consistent with the pattern already used for `status` on the very next line:

```python
limit = int(params.get("limit", 50))
```

## Verification
I ran the handler against the same scenarios:
- **No `?limit`** → `limit` defaults to `50` ✅ (this was the 500 case)
- **`?limit=10`** → `limit` is `10` ✅
- **`?limit=5&status=shipped`** → both parsed correctly ✅

The `/orders` endpoint will now return a normal response instead of a 500 when `?limit` isn't provided.

One heads-up for later (not part of this fix): `get_users` and `get_reports` read `page` and `days` the same direct way, so those endpoints will 500 if those params are omitted. Happy to apply the same defensive default pattern there if you'd like.