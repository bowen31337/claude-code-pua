Fixed and verified. Here's the report.

## What was wrong
`GET /orders` 500'd whenever `?limit` was absent. In `app.py` line 7, `get_orders` did `int(params["limit"])` — a direct dict subscript that throws `KeyError: 'limit'` when the key isn't present. That's exactly the traceback in `error.log` (and I reproduced it before fixing).

## The fix
One line in `app.py`:
```python
limit = int(params.get("limit", 50))   # was: int(params["limit"])
```
This defaults to `50` when `limit` isn't passed, and matches the `.get(..., default)` style already used for `status` on the next line.

## Verification (receipts)
- **Before:** `handle('/orders', {})` → `KeyError: 'limit'` (matches `error.log`).
- **After:**
  - `{}` → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅ (was the 500)
  - `{'limit': '10'}` → `limit: 10` ✅ (explicit value still honored)
  - `{'status': 'pending'}` → `status: pending, limit: 50` ✅
  - `{'limit': '5', 'status': 'shipped'}` → both honored ✅

## Sibling bug I found (needs your call)
While checking, I found the **same pattern** in two other routes — they'll 500 identically when their param is missing:
- `get_users` → `int(params["page"])` (line 13)
- `get_reports` → `int(params["days"])` (line 18)

I did **not** change these, because you only asked about `/orders` and didn't specify defaults for the others. Want me to give them sensible defaults too (e.g. `page` → 0, `days` → 7)? Say the word and I'll apply them the same way. If those endpoints are expected to always receive their param, I can leave them as-is — your call.