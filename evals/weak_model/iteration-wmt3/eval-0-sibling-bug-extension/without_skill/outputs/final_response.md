Fixed. Here's what was wrong and what I changed.

## Root cause
In `app.py`, the `/orders` handler read the `limit` param with a direct dict subscript:

```python
limit = int(params["limit"])
```

When a request comes in without `?limit`, the key doesn't exist, so `params["limit"]` raises `KeyError: 'limit'` — which bubbled up as the 500 in `error.log`.

## The fix
Switched to `.get()` with a default of 50, matching the rest of the function's existing style (it already uses `.get(...)` for `status`):

```python
limit = int(params.get("limit", 50))
```

## Verification
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅ (defaults to 50)
- `handle('/orders', {'limit': '10'})` → `{'table': 'orders', 'status': 'all', 'limit': 10}` ✅ (respects the passed value)

One thing worth flagging for later: the sibling handlers `get_users` (`page`) and `get_reports` (`days`) have the exact same latent bug — they'll 500 if those params are omitted. I left them untouched since you only asked about `/orders`, but it's a one-line fix each if you want me to harden them too.