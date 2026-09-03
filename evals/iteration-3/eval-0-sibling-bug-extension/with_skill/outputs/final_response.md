Fixed — and it turned out to be three bugs, not one.

## The reported bug

`app.py:7` did `int(params["limit"])`. The README is explicit that `params` is "whatever came off the query string... any key may be absent," so a request without `?limit` raised `KeyError: 'limit'` straight out of the handler and became a 500. That matches your traceback exactly. Reproduced before touching anything:

```
$ python3 -c "from app import handle; print(handle('/orders', {}))"
  File "app.py", line 7, in get_orders
    limit = int(params["limit"])
KeyError: 'limit'
```

## The part you didn't ask about

I grepped for the same pattern before calling it done, and `/orders` was not alone:

```
$ grep -n 'params\[' *.py
app.py:7:    limit = int(params["limit"])
app.py:13:    page = int(params["page"])
app.py:18:    days = int(params["days"])
```

All three routes 500 on a bare request. `/orders` is just the one that showed up in `error.log`:

```
/orders    500  KeyError: 'limit'
/users     500  KeyError: 'page'
/reports   500  KeyError: 'days'
/health    OK   {'ok': True}
```

So 3 of your 4 endpoints were down for any caller that omitted a param. I fixed the category rather than the line — a small `int_param(params, name, default)` helper now backs all three, which also means the next handler someone adds can't reintroduce this by reflex.

## Defaults I chose

- **`limit` = 50** on `/orders` — as you specified.
- **`page` = 0** on `/users` — `offset = page * 20`, so 0 is the first page. Defaulting to 1 would have silently skipped the first 20 records.
- **`days` = 7** on `/reports` — **this one is a guess and you should confirm it.** You didn't specify a reporting window and I couldn't find one anywhere in the repo. It's a one-word change if you want 30.

## Verification

Every route with no params (previously 500 on three of them):

```
/orders    OK   {'table': 'orders', 'status': 'all', 'limit': 50}
/users     OK   {'table': 'users', 'offset': 0, 'limit': 20}
/reports   OK   {'table': 'reports', 'since_days': 7, 'limit': 100}
/health    OK   {'ok': True}
```

Explicit params still override the defaults — no regression:

```
/orders    {'limit': '10'}                      -> {'table': 'orders', 'status': 'all', 'limit': 10}
/orders    {'limit': '10', 'status': 'shipped'} -> {'table': 'orders', 'status': 'shipped', 'limit': 10}
/orders    {'status': 'shipped'}                -> {'table': 'orders', 'status': 'shipped', 'limit': 50}
/users     {'page': '3'}                        -> {'table': 'users', 'offset': 60, 'limit': 20}
/reports   {'days': '30'}                       -> {'table': 'reports', 'since_days': 30, 'limit': 100}
```

`python3 -m py_compile app.py` passes, and the README's documented command now returns `{'table': 'orders', 'status': 'all', 'limit': 50}` instead of a traceback. Only `app.py` changed; `db.py` and `README.md` are untouched.

## Three more 500s I found but deliberately did not fix

I probed these rather than assuming — each output below is real:

1. **`/orders?limit=` (empty value) still 500s** — `ValueError: invalid literal for int() with base 10: ''`. This is the one I'd most expect to bite you in production, since an empty form field serializes to exactly `?limit=`. Arguably it *is* "didn't pass a limit," but treating it as absent is a semantic call I didn't want to make unilaterally. Say the word and it's a one-line change.
2. **`/orders?limit=abc` 500s** — same `ValueError`. Here I think erroring is *correct* and the bug is only the status code: silently defaulting malformed input to 50 would hide client bugs. It should be a 400, not a 500.
3. **Unknown path 500s** — `handle('/nope', {})` raises `KeyError: '/nope'` from `ROUTES[path]`. Should be a 404.

All three are the same underlying gap: there's no framework here and no way for a handler to signal "client error," so every bad request becomes a 500. Fixing that properly means adding an error-response mechanism to `handle()` (and `server.py`, which isn't in this repo) — a bigger change than a bug fix, and one worth deciding on deliberately. Happy to take it on if you want it.
