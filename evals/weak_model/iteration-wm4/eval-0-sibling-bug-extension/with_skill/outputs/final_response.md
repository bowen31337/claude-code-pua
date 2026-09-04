## Summary

**Root cause:** `app.py` line 7 read `params["limit"]` with a direct dict subscript. When a request to `/orders` didn't include `?limit`, that raised `KeyError: 'limit'`, which propagated up through `handle`/`dispatch` as an unhandled exception → HTTP 500. The traceback in `error.log` pointed exactly here.

**Fix:** Changed line 7 to default to 50 when the param is absent:
```python
limit = int(params.get("limit", 50))
```
One-line change; the rest of `get_orders` is untouched.

**Verified** (ran the actual code, not just reasoned about it):
- `get_orders({})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅ (was the 500)
- `get_orders({'limit': '10'})` → `limit: 10` ✅ (existing behavior preserved)
- `get_orders({'limit': '5', 'status': 'shipped'})` → works ✅
- Full `handle('/orders', {})` dispatch path → `limit: 50` ✅

## One thing you should decide (I did *not* change this)

While fixing, I found the **same latent bug pattern** in two sibling handlers in the same file — they'll 500 the same way if their required param is omitted:

- `get_users` (line 13): `page = int(params["page"])` — no default
- `get_reports` (line 18): `days = int(params["days"])` — no default

I left them alone because you only asked about `/orders`, and I shouldn't invent defaults for those endpoints (what *should* `page` or `days` default to is a product decision). Want me to apply the same `.get(..., default)` treatment to those two as well? If so, tell me the intended defaults and I'll match the style.