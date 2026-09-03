Fixed — and the same bug was live on two other endpoints, so I fixed those too.

## The bug

`get_orders` read the param with a direct subscript on a dict where the key is optional:

```python
limit = int(params["limit"])   # KeyError when ?limit is absent
```

Your README states the contract explicitly: *"`params` is whatever came off the query string ... any key may be absent."* A bare `params[...]` violates that contract, so every request without `?limit` raised `KeyError` and the router turned it into a 500. Reproduced before touching anything, and it matches your traceback line for line:

```
$ python3 -c "from app import handle; print(handle('/orders', {}))"
  File "app.py", line 7, in get_orders
    limit = int(params["limit"])
KeyError: 'limit'
```

## The siblings (this is the part worth your attention)

Grepping for the pattern rather than just patching the reported line turned up three instances, not one:

```
$ grep -n 'params\[' *.py
app.py:7:    limit = int(params["limit"])
app.py:13:    page = int(params["page"])
app.py:18:    days = int(params["days"])
```

All three fail identically. Three of your four routes were 500ing on a bare request:

```
/orders   -> KeyError: 'limit'
/users    -> KeyError: 'page'
/reports  -> KeyError: 'days'
/health   -> {'ok': True}
```

`/orders` is just the one that showed up in `error.log`. `/users` and `/reports` are equally broken and would have come back as separate tickets.

## The fix

Three lines in `app.py`, matching the `params.get("status", "all")` style already in the file:

```python
limit = int(params.get("limit", 50))   # your specified default
page  = int(params.get("page", 0))     # offset = page * 20, so 0 is the first page
days  = int(params.get("days", 7))     # see "one judgment call" below
```

## Verification

Compiles clean, and all four routes now answer a bare request:

```
compile: OK

=== bare request (was 500 on 3 of 4) ===
/orders   -> {'table': 'orders', 'status': 'all', 'limit': 50}
/users    -> {'table': 'users', 'offset': 0, 'limit': 20}
/reports  -> {'table': 'reports', 'since_days': 7, 'limit': 100}
/health   -> {'ok': True}
```

Explicit params are still honored — no regression:

```
/orders limit=10 status=open -> {'table': 'orders', 'status': 'open', 'limit': 10}
/orders status=open only     -> {'table': 'orders', 'status': 'open', 'limit': 50}
/users  page=3               -> {'table': 'users', 'offset': 60, 'limit': 20}
/reports days=30             -> {'table': 'reports', 'since_days': 30, 'limit': 100}
/orders limit=0              -> {'table': 'orders', 'status': 'all', 'limit': 0}
```

That last line is deliberate: `?limit=0` returns 0, not 50. Writing this as `params.get("limit") or 50` would have silently coerced an explicit zero into 50 — a nastier bug than the one you reported, because it returns wrong data instead of an error.

## One judgment call I need you to confirm

`limit=50` and `page=0` are derivable from your instruction and from the code (`offset = page * 20` means page is 0-indexed, so 0 is the first page).

**`days=7` is not derivable from anything in the repo.** There's no signal in the code, README, or log about the intended reporting window. I picked 7 as a defensible default so `/reports` stops 500ing; if your product answer is 30 or 90, it's a one-character change on `app.py:18`.

## Two adjacent 500s I did NOT fix

Both still reproduce. I'm flagging rather than fixing because each changes the API's error contract, which is your call:

1. **Non-numeric or empty values still 500.** `?limit=abc` → `ValueError: invalid literal for int() with base 10: 'abc'`. Note that `?limit=` (the key present but empty) also hits this: `ValueError: ... base 10: ''`. That one is arguably inside your original report — a user who "doesn't pass a limit" but leaves a trailing `?limit=` in a URL still gets a 500 today.
2. **Unknown paths 500 instead of 404.** `handle('/nope', {})` → `KeyError: '/nope'`, because `ROUTES[path]` is the same unguarded-subscript pattern one layer up in the router.

Both want the same treatment: parse params through a small helper that returns a 400 on a bad value, and a `ROUTES.get(path)` returning 404. Say the word and I'll do it — it's about ten lines and would make this whole class of bug impossible rather than fixing it three times.

**Files touched:** `app.py` (lines 7, 13, 18). Nothing else modified.
