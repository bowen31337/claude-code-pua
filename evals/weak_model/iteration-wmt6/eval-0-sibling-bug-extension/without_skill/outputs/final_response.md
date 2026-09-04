The fix works. Here's a summary of what was wrong and what I changed.

## The bug

In `app.py`, the `get_orders` handler read the limit with direct dict bracket access:

```python
limit = int(params["limit"])   # KeyError when ?limit is absent
```

When a request to `/orders` didn't include a `?limit` query param, `params` had no `"limit"` key, so `params["limit"]` raised `KeyError`, which propagated up as a 500.

## The fix

Changed line 7 to use `.get()` with a default of 50, matching the pattern already used for `status` on the very next line:

```python
limit = int(params.get("limit", 50))
```

## Verification

- `/orders` with no params → now returns `limit: 50` (previously 500'd) ✓
- `/orders?limit=10` → returns `limit: 10` ✓
- `/orders?limit=5&status=shipped` → returns both params correctly ✓

The `/orders` endpoint now defaults `limit` to 50 when it's not passed, and existing behavior with an explicit limit is unchanged.

One heads-up while I was in there: the sibling handlers `get_users` (`params["page"]`) and `get_reports` (`params["days"]`) use the same brittle bracket-access pattern, so `/users` and `/reports` will 500 if their required params are missing. I left those untouched since you only asked about `/orders`, but let me know if you'd like me to harden them too.