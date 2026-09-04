Fixed. The bug was in `app.py` in the `get_orders` function.

It was reading the limit with a direct dict lookup:
```python
limit = int(params["limit"])
```
When the `?limit` query param is absent, `params` has no `"limit"` key, so this raised `KeyError: 'limit'`, which propagated up as a 500.

I changed it to use `.get()` with a default of 50:
```python
limit = int(params.get("limit", 50))
```

Verified behavior:
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` (defaults to 50, no more 500)
- `handle('/orders', {'limit': '10'})` → `{'table': 'orders', 'status': 'all', 'limit': 10}` (respects passed value)
- `handle('/orders', {'status': 'shipped'})` → `{'table': 'orders', 'status': 'shipped', 'limit': 50}` (works alongside other params)

Note: I left the other routes (`/users`, `/reports`) untouched since you only asked about `/orders` — but they have the same latent `KeyError` risk if their params are missing. Let me know if you'd like me to harden those too.