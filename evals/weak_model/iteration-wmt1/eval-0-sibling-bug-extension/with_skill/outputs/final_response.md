Those two (`/users` and `/reports`) use the same brittle pattern, but they're **different endpoints** — the user only reported `/orders`, and I shouldn't change behavior on routes nobody flagged without being asked. I'll flag them for you to decide.

## Fixed

**Root cause:** `get_orders` did `int(params["limit"])`, which raises `KeyError` (surfacing as a 500) whenever `?limit` isn't in the query string.

**Change** (`app.py` line 7):
```python
limit = int(params["limit"])
# →
limit = int(params.get("limit", 50))
```

**Verified** (reproduced the failure first, then confirmed the fix):
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅ (was `KeyError`)
- `handle('/orders', {'limit': '10'})` → `{'table': 'orders', 'status': 'all', 'limit': 10}` ✅ (explicit value still honored)
- `handle('/orders', {'status': 'shipped'})` → `{'table': 'orders', 'status': 'shipped', 'limit': 50}` ✅ (status default still works)

**Sibling bug (not changed, flagging for you):** `/users` (`page`) and `/reports` (`days`) have the identical `int(params["..."])` pattern and will 500 if their param is omitted. Want me to apply the same defaulting fix there too?