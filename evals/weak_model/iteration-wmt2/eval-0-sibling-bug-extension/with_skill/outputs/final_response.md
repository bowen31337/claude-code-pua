Fixed and verified. Here's the summary.

## What was wrong

The traceback in `error.log` was unambiguous:

```
File "app.py", line 7, in get_orders
    limit = int(params["limit"])
KeyError: 'limit'
```

`get_orders` accessed `params["limit"]` directly. Since `params` is a dict that may be missing keys (per the README), omitting `?limit` raised `KeyError`, which bubbled up as a 500.

## The fix

`app.py` line 7, one character-class change — direct indexing → `.get()` with a default of 50:

```python
limit = int(params.get("limit", 50))
```

## Evidence (ran it, not assumed)

- **Before:** `handle('/orders', {})` → `KeyError: 'limit'` (reproduced the exact 500).
- **After:**
  - `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✓ defaults to 50
  - `handle('/orders', {'limit': '10'})` → `limit: 10` ✓ explicit value still honored
  - `handle('/orders', {'limit': '5', 'status': 'shipped'})` → `limit: 5, status: shipped` ✓ other params unaffected

## Sibling bug I found (flagging, not fixing — out of scope for this ticket)

The same fragile pattern exists in three other routes that will 500 if their required param is missing:

- `get_users` → `int(params["page"])` (line 13)
- `get_reports` → `int(params["days"])` (line 18)

These are *required* params (no sensible default), so they're arguably meant to fail — but they fail with an opaque `KeyError` 500 rather than a clear 400. If you want, I can add a small guard that returns a 400 with a message like `missing required param: page` for those, so the failure mode is consistent and debuggable. Say the word and I'll do it.