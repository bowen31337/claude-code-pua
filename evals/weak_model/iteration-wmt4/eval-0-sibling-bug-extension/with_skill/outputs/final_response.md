Fixed and verified. Here's the report.

## What was wrong

`GET /orders` 500'd whenever `?limit` was omitted. In `app.py` line 7:

```python
limit = int(params["limit"])   # KeyError: 'limit' when absent
```

`params` is a raw dict of query-string values (per the README), so a missing key raises `KeyError`, which propagated as the 500 in `error.log`.

## The fix

```python
limit = int(params.get("limit", 50))
```

Defaults to 50 when `limit` isn't passed, exactly as you asked.

## Evidence (reproduce → fixed)

- **Before:** `handle('/orders', {})` → `KeyError: 'limit'` (matches `error.log` line 7).
- **After:**
  - `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅
  - `handle('/orders', {'limit': '10'})` → `limit: 10` ✅
  - `handle('/orders', {'limit': '5', 'status': 'shipped'})` → `limit: 5, status: shipped` ✅

## Sibling bug you should know about

While verifying, I found the **same pattern** in two other routes — they 500 identically when their param is missing:

- `get_users`: `page = int(params["page"])` → `KeyError: 'page'`
- `get_reports`: `days = int(params["days"])` → `KeyError: 'days'`

I did **not** touch these, because fixing them requires choosing a default value, which is a product decision I shouldn't guess at (e.g. `page=0` is plausible, but `days=0` for reports is probably wrong). Want me to harden them too? If so, tell me the intended defaults for `page` and `days` and I'll apply the same `.get(...)` fix across all three.