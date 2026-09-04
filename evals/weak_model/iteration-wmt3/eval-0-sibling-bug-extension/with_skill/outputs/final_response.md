Fixed and verified. Here's the full picture.

## What was wrong

`error.log` showed `KeyError: 'limit'` at `app.py:7`. The root cause: `get_orders` read the param with `int(params["limit"])`, which blows up when `limit` isn't in the query string. The README even documents that "any key may be absent," so this was a latent bug exposed the moment someone hit `/orders` without `?limit`.

## The fix

```python
# before
limit = int(params["limit"])
# after
limit = int(params.get("limit", 50))
```

## Evidence (all run, all pass)

| Request | Result |
|---|---|
| `handle('/orders', {})` | `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅ defaults to 50 |
| `handle('/orders', {'limit': '10'})` | `{'table': 'orders', 'status': 'all', 'limit': 10}` ✅ explicit value honored |
| `handle('/orders', {'status': 'shipped'})` | `{'table': 'orders', 'status': 'shipped', 'limit': 50}` ✅ |

The original traceback is reproduced and now gone.

## Sibling bug I found (needs your call)

While checking for the same pattern, I found `/users` and `/reports` have the identical `int(params["..."])` bug — they'll 500 if you omit `?page` or `?days`:

- `app.py:13` — `page = int(params["page"])` → `KeyError: 'page'`
- `app.py:18` — `days = int(params["days"])` → `KeyError: 'days'`

I did **not** touch these, because I can't safely invent defaults for them. `page` has an obvious sensible default (`0` = first page, consistent with the `offset = page * 20` math), but `days` (how many days back for reports) genuinely depends on your product intent — I won't guess that one.

**My recommendation:** apply the same `.get(..., default)` fix to all three. For `page` I'd default to `0`; for `days` I need you to tell me the intended default (or should it be required?). Say the word and I'll apply it.

One file touched: `app.py`. No config or dependencies changed.