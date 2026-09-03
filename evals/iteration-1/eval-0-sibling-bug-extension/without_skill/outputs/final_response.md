Fixed. `/orders` now defaults `limit` to 50 when the param is absent.

**The change** — `app.py:7`:

```python
# before
limit = int(params["limit"])
# after
limit = int(params.get("limit", 50))
```

That's the exact line in the traceback (`KeyError: 'limit'`). `params` is a plain dict off the query string, so a missing key raised instead of falling back — `status` on the next line was already written defensively with `.get`, `limit` just wasn't.

**Verified** locally:

```
handle('/orders', {})                 -> {'table': 'orders', 'status': 'all', 'limit': 50}
handle('/orders', {'limit': '10'})    -> {'table': 'orders', 'status': 'all', 'limit': 10}
handle('/orders', {'status': 'open'}) -> {'table': 'orders', 'status': 'open', 'limit': 50}
```

An explicit `?limit=` still wins; only the missing case changes.

**Two sibling endpoints have the identical bug** — I left them alone since you scoped this to `/orders`, but they will 500 the same way:

- `app.py:13` — `get_users` does `int(params["page"])`, so `GET /users` with no `?page` raises `KeyError: 'page'`
- `app.py:18` — `get_reports` does `int(params["days"])`, so `GET /reports` with no `?days` raises `KeyError: 'days'`

Both confirmed against the current code. They're a one-line fix each, but the right defaults aren't mine to guess — `page` probably wants `0` to match the existing `offset=page * 20` math, and `days` has no obvious answer. Say the word and I'll apply them.

One thing I did not touch: a non-numeric value (`?limit=abc`) still raises `ValueError` and 500s on all these routes. That's a separate input-validation concern from the missing-key one you reported, so I left it as-is.
