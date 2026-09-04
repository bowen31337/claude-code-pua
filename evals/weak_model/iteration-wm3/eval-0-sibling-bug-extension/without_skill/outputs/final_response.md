Fixed. The bug was in `get_orders` in `app.py` at line 7:

```python
limit = int(params["limit"])   # KeyError when ?limit is absent
```

I changed it to use `.get()` with a default of 50:

```python
limit = int(params.get("limit", 50))
```

This matches the traceback in `error.log` (`KeyError: 'limit'`), so `/orders` will no longer 500 when the `?limit` query param isn't passed. I verified both paths:
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` (defaults to 50)
- `handle('/orders', {'limit': '10'})` → `{'table': 'orders', 'status': 'all', 'limit': 10}` (explicit value respected)