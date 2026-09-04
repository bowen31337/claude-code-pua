Fixed. The bug was in `app.py`'s `get_orders` function, which accessed `params["limit"]` directly. Since `params` comes straight off the query string, the key is absent when no `?limit` is passed — so `params["limit"]` raised a `KeyError`, which propagated up as a 500.

I changed it to use `.get()` with a default of 50:

```python
limit = int(params.get("limit", 50))
```

Verified behavior:
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` (defaults to 50)
- `handle('/orders', {'limit': '10'})` → `limit: 10` (respects passed value)
- `handle('/orders', {'limit': '5', 'status': 'shipped'})` → works with both params

The `?limit` param now defaults to 50 when omitted, and existing behavior with an explicit limit is unchanged.