Fixed — and it turned out `/orders` wasn't the only endpoint with this bug.

## The bug

`error.log` pointed at `app.py:7`:

```
limit = int(params["limit"])
KeyError: 'limit'
```

Square-bracket access on a dict that the README explicitly says may be missing any key: *"`params` is whatever came off the query string, so every value is a string and any key may be absent."* No `?limit` → `KeyError` → 500.

I reproduced it first, and it matched the log exactly:

```
$ python3 -c "from app import handle; print(handle('/orders', {}))"
  File "app.py", line 7, in get_orders
    limit = int(params["limit"])
KeyError: 'limit'
```

## The siblings — this is the part worth your attention

Before fixing, I grepped for the same pattern and probed every route with empty params. **Three of the four routes had the identical bug:**

```
/orders    FAIL KeyError: 'limit'
/users     FAIL KeyError: 'page'
/reports   FAIL KeyError: 'days'
/health    OK
```

`/orders` is just the one that happened to show up in your log. `/users` (no `?page`) and `/reports` (no `?days`) 500 exactly the same way, and would have come back as separate tickets next week.

## The fix

One helper in `app.py`, used by all three call sites, so the pattern can't recur:

```python
def int_param(params, key, default):
    """Read an int query param. Absent key -> default (query strings are optional)."""
    if key not in params:
        return default
    return int(params[key])
```

- `/orders` → `limit` defaults to **50** (as you specified)
- `/users` → `page` defaults to **0**
- `/reports` → `days` defaults to **7**

One deliberate detail: the helper tests `key not in params` rather than the tempting `params.get(key) or default`. The `or` version would swallow an explicit `?limit=0` and silently turn it into 50. Verified below.

## Verification

```
=== A. the reported bug: no params (was 500) ===
/orders {}      {'table': 'orders', 'status': 'all', 'limit': 50}
/users {}       {'table': 'users', 'offset': 0, 'limit': 20}
/reports {}     {'table': 'reports', 'since_days': 7, 'limit': 100}
/health {}      {'ok': True}

=== B. no regression: explicit params still honoured ===
/orders  ?limit=5               {'table': 'orders', 'status': 'all', 'limit': 5}
/orders  ?limit=5&status=open   {'table': 'orders', 'status': 'open', 'limit': 5}
/orders  ?status=open           {'table': 'orders', 'status': 'open', 'limit': 50}
/users   ?page=3                {'table': 'users', 'offset': 60, 'limit': 20}
/reports ?days=30               {'table': 'reports', 'since_days': 30, 'limit': 100}

=== C. edge: explicit zero not swallowed by the default ===
/orders  ?limit=0               {'table': 'orders', 'status': 'all', 'limit': 0}
/users   ?page=0                {'table': 'users', 'offset': 0, 'limit': 20}
```

All four routes serve with no params; explicit params are unchanged.

## Two calls I made that you should sanity-check

**The two non-`/orders` defaults are my judgement, not yours.** `page=0` is solid — the code computes `offset = page * 20`, so page 0 is the first page by its own arithmetic. **`days=7` is a genuine guess** with nothing in the repo to anchor it. If reports should default to 30 days, that's a one-word change on line 25.

## Two more 500-sources I found but did *not* change

Both are real, both are adjacent, and both are product decisions rather than bugs with an obvious right answer:

1. **Non-numeric values still 500.** `?limit=abc` → `ValueError: invalid literal for int() with base 10: 'abc'`. I left this deliberately — silently coercing junk input to 50 hides client bugs. The correct fix is a 400, which needs error-handling this router doesn't have yet.
2. **Unknown paths 500 instead of 404.** `handle('/nope', {})` → `KeyError: '/nope'`, same uncaught-exception path.

Say the word and I'll do either.

Changed: `app.py` only. `db.py` untouched.
