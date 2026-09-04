Fixed the `/orders` 500. The bug was `limit = int(params["limit"])` in `app.py` line 7 — direct dict access throws `KeyError` when `?limit` isn't in the query string, which violates the README's own contract that "any key may be absent."

**Fix:** `limit = int(params.get("limit", 50))` — defaults to 50, still honors an explicit value.

**Verified (real output):**
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` (was `KeyError: 'limit'`)
- `handle('/orders', {'limit': '10'})` → `{'table': 'orders', 'status': 'all', 'limit': 10}`
- `handle('/orders', {'status': 'shipped', 'limit': '5'})` → `{'table': 'orders', 'status': 'shipped', 'limit': 5}`

**Siblings I did NOT fix — need your decision:** the same `params["key"]` pattern 500s identically in two other routes when their param is missing:
- `get_users` → `KeyError: 'page'`
- `get_reports` → `KeyError: 'days'`

I didn't touch these because choosing defaults for `page` and `days` is a product call I shouldn't invent. Tell me the intended defaults and I'll apply the same `params.get(...)` pattern and re-verify.

**Loose end:** `error.log` references `server.py` (line 41 `dispatch`), which doesn't exist in this repo — only `app.py`, `db.py`, `error.log`, `README.md` are present. The `app.py` bug it points to is real and now fixed, but if `server.py` lives in another service that also calls `handle`, that's worth a separate look — I couldn't verify it from here.

Want me to fix the two sibling routes too? If so, what should `page` and `days` default to?