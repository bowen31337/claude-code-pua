Fixed. `/orders` now defaults `limit` to 50 when the param is absent.

**The bug** — `app.py:7` indexed the params dict directly:

```python
limit = int(params["limit"])   # KeyError when ?limit is omitted
```

Since `handle()` has no error handling, that `KeyError` propagated straight out of `dispatch` and surfaced as a 500, exactly as in the traceback.

**The fix** (`app.py:7`):

```python
limit = int(params.get("limit", 50))
```

The default is the bare int `50`, and `int()` accepts both an int and the query-string text, so an explicitly-passed `?limit=10` still parses correctly.

**Verified:**

| Request | Result |
| --- | --- |
| `/orders` (no params) | `{'table': 'orders', 'status': 'all', 'limit': 50}` |
| `/orders?limit=10` | `{'table': 'orders', 'status': 'all', 'limit': 10}` |
| `/orders?limit=10&status=open` | `{'table': 'orders', 'status': 'open', 'limit': 10}` |
| `/orders?status=open` | `{'table': 'orders', 'status': 'open', 'limit': 50}` |

## One thing worth flagging

`get_orders` was not the only route with this pattern. Two siblings in the same file index a required param the same way, and I confirmed both still throw:

- `app.py:13` — `get_users`: `int(params["page"])` → `KeyError: 'page'` on `/users`
- `app.py:18` — `get_reports`: `int(params["days"])` → `KeyError: 'days'` on `/reports`

Per the README, "any key may be absent," so both are 500ing today for anyone who omits the param — same root cause, just not yet in your error log. I left them alone because I don't know what the right defaults are, and guessing changes what those endpoints return: page 0 is the obvious default for `/users`, but `/reports` defaults could reasonably be 7 or 30 days and that's a product call, not a mechanical one. Tell me the values and it's a two-line change.
