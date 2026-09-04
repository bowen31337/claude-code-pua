## What was wrong

`app.py` line 7 had `limit = int(params["limit"])`. When a request came in without `?limit`, `params` had no `limit` key, so `params["limit"]` threw `KeyError: 'limit'` → unhandled → 500. That matches your traceback exactly.

## The fix

```python
# before
limit = int(params["limit"])
# after
limit = int(params.get("limit", 50))
```

`limit` now defaults to 50 when omitted, and still honors an explicit value.

## Evidence (ran it, not assumed)

```
no limit param: {'table': 'orders', 'status': 'all', 'limit': 50}   ← was KeyError, now 50
with limit param: {'table': 'orders', 'status': 'all', 'limit': 10}  ← explicit value respected
with limit + status: {'table': 'orders', 'status': 'shipped', 'limit': 5}
```

The original `KeyError: 'limit'` is gone and the default is 50 as you asked.

## One thing you should decide (I did NOT touch this)

While checking for siblings, I found the same latent bug in two other routes — they use `params["key"]` and 500 the same way when their param is missing:

- `/users` → `KeyError 'page'` when no `?page`
- `/reports` → `KeyError 'days'` when no `?days`

I left them alone because this is a product call, not a clear fix: for `/orders` you wanted a *default* (50). For `/users` and `/reports` there's no sensible default — `page` and `days` are genuinely required. So the right fix is probably a **400 "missing required param"** rather than a 500, but I don't want to invent that behavior for you.

Want me to:
1. Leave `/users` and `/reports` as-is (out of scope), or
2. Make them return a clean 400 when `page`/`days` are missing?

Also worth noting: `server.py` (which the traceback references) isn't in this directory — only `app.py` and `db.py` are here. The fix is in `app.py`, which is where the failing code lives, so this is correct, but if `server.py` exists elsewhere in your real repo, confirm the routing still points at this `app.py`.