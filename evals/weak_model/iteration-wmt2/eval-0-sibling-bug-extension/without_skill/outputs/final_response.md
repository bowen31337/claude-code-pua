Fixed. Here's what was happening and what I changed.

## Root cause
In `app.py`, the `get_orders` handler read the limit with a direct dict subscript:

```python
limit = int(params["limit"])
```

`params` is whatever came off the query string, and per the README **any key may be absent**. So a request to `/orders` without `?limit` raised `KeyError: 'limit'`, which bubbled up through `handle()` → `dispatch()` as a **500**.

## The fix
Changed line 7 to use `.get()` with a default of `50`:

```python
limit = int(params.get("limit", 50))
```

## Verified behavior
| Request | Result |
|---|---|
| `GET /orders` (no params) | `limit: 50` ✅ (was 500) |
| `GET /orders?limit=10` | `limit: 10` ✅ |
| `GET /orders?limit=5&status=shipped` | `limit: 5, status: shipped` ✅ |

The `/orders` endpoint now defaults to a limit of 50 when `?limit` isn't passed, and existing behavior with an explicit limit is unchanged.

One heads-up for later (not part of this bug, so I left it alone): `get_users` and `get_reports` do the same `int(params["page"])` / `int(params["days"])` thing, so those endpoints will 500 if their params are missing. Happy to apply the same defaulting pattern there if you'd like.