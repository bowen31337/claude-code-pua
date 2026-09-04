Fixed. The bug was in `app.py`'s `get_orders` function, which accessed `params["limit"]` directly. When the `?limit` query param isn't provided, that raises a `KeyError`, which bubbled up as a 500.

I changed it to use `.get()` with a default of 50:

```python
limit = int(params.get("limit", 50))
```

Verified behavior:
- **No `limit` param** → defaults to 50 (previously threw 500)
- **`?limit=10`** → uses 10 as before

The `status` param was already handled safely with `.get("status", "all")`, so no change was needed there.