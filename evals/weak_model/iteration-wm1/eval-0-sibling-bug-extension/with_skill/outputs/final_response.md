Fixed. The `/orders` endpoint no longer 500s when `?limit` is omitted — it now defaults to 50.

**Root cause:** `app.py:7` used `params["limit"]`, which raises `KeyError` (surfacing as HTTP 500) whenever the request omits `?limit`.

**Fix:** Changed it to `params.get("limit", 50)`.

**Verified (ran it, output below):**
- `get_orders({})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` (was the 500 case)
- `get_orders({'limit': '5'})` → `{'table': 'orders', 'status': 'all', 'limit': 5}` (existing behavior preserved)

**Flag, not changed:** `get_users` (`app.py:13`, `params["page"]`) and `get_reports` (`app.py:18`, `params["days"]`) have the identical failure pattern and would 500 the same way if their param is missing. I left them alone because I don't know their intended defaults — tell me the defaults and I'll apply the same `params.get(...)` pattern.

Files touched: `app.py` (one line).