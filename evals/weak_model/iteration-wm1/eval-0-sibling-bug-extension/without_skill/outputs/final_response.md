Fixed the bug in app.py. The `get_orders` function was accessing `params["limit"]` directly, which raised `KeyError: 'limit'` (surfacing as a 500) whenever the `?limit` query param was absent. I changed it to use `params.get("limit", 50)` so it defaults to 50 when not passed.

Verified:
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` (defaults to 50)
- `handle('/orders', {'limit': '10'})` → `{'table': 'orders', 'status': 'all', 'limit': 10}` (respects passed value)