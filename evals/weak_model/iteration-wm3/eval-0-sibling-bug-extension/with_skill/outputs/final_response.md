## Fixed

The 500 on `/orders` was a `KeyError: 'limit'` in `app.py:7`. The handler did `int(params["limit"])`, which crashes when the query string has no `?limit` — and the README explicitly says "any key may be absent."

**Change (one line in `app.py`):**
```python
# before
limit = int(params["limit"])
# after
limit = int(params.get("limit", 50))
```

**Evidence — all run against the live code:**
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅ (was 500)
- `handle('/orders', {'limit': '10'})` → `{'table': 'orders', 'status': 'all', 'limit': 10}` ✅ (explicit value still honored)
- `handle('/orders', {'limit': '5', 'status': 'shipped'})` → `{'table': 'orders', 'status': 'shipped', 'limit': 5}` ✅
- `handle('/health', {})` → `{'ok': True}` ✅ (other routes unaffected)

Default is 50 as requested; `status` still defaults to `all`.

## Siblings I found (not fixed — need your call)

While verifying, I hit the **same bug class** on two other routes. I did *not* change these because the correct default is a product decision I shouldn't invent, and you scoped this to `/orders`:

- `/users` → `KeyError: 'page'` (`app.py:13`)
- `/reports` → `KeyError: 'days'` (`app.py:18`)

Both will 500 the same way when their param is omitted. Want me to apply the same `.get(...)` pattern? If so, tell me the intended defaults (e.g. `page=0`? `days=30`?) and I'll fix them the same way.

## Note on scope

I only touched `app.py`. `server.py` referenced in the traceback doesn't exist in this repo — the traceback is from the deployed environment, but the source of truth here is `app.py`, which is what I fixed and verified.