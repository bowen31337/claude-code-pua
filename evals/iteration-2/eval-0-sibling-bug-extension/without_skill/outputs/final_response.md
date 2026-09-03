Fixed. `/orders` now defaults `limit` to 50.

**The change** — `app.py:7`:

```python
# before
limit = int(params["limit"])
# after
limit = int(params.get("limit", 50))
```

`params["limit"]` did a hard subscript on a key that isn't guaranteed to be there. Per the README, `params` is whatever came off the query string, so any key may be absent — the missing key raised `KeyError`, which bubbled up through `handle` and out as a 500.

**Verified:**

```
no limit      -> {'table': 'orders', 'status': 'all', 'limit': 50}
limit=10      -> {'table': 'orders', 'status': 'all', 'limit': 10}
limit+status  -> {'table': 'orders', 'status': 'shipped', 'limit': 5}
```

The missing-param case returns 50, and explicitly-passed limits still work.

## Two other routes have the identical bug

I checked the rest of the router, since the mistake is a pattern rather than a one-off. Calling every route with empty params:

```
/orders    OK     {'table': 'orders', 'status': 'all', 'limit': 50}
/users     500   KeyError: 'page'
/reports   500   KeyError: 'days'
/health    OK
```

- `app.py:13` — `get_users` does `int(params["page"])`
- `app.py:18` — `get_reports` does `int(params["days"])`

Same hard subscript, same 500, and they're throwing in production right now for anyone who omits `?page=` or `?days=` — they just haven't shown up in the traceback you handed me.

I did **not** fix these, because the right default is a product decision rather than a mechanical one, and I'd rather you pick the number than have me guess it into your API. The obvious candidates are `page` → 0 (first page, matching the existing `offset=page * 20` math) and `days` → 7 or 30. Say the word and it's a two-line change.

## One thing worth flagging

The same class of crash still exists on the fixed line: `int()` raises `ValueError` on `?limit=abc`, which is also an uncaught 500. That's a different failure from the one you reported, so I left it alone. The real fix is probably validation at the dispatch layer — coercing params and returning a 400 for malformed input — rather than defensive `.get()` calls sprinkled through each handler. Worth doing if these endpoints are exposed to anything you don't control.
