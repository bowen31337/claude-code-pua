Fixed. The `/orders` endpoint was throwing 500s because `get_orders` did `int(params["limit"])`, which raises `KeyError: 'limit'` when the param is absent — exactly the traceback in `error.log`. I changed it to `int(params.get("limit", 50))`, so it now defaults to 50.

**Verified (real output):**
- `handle('/orders', {})` → `{'table': 'orders', 'status': 'all', 'limit': 50}` ✅ (was `KeyError`)
- `handle('/orders', {'limit': '10'})` → `{'table': 'orders', 'status': 'all', 'limit': 10}` ✅ (explicit value still respected)

**Sibling bug I found and fixed:** while investigating, I checked the other routes using the same `params[...]` indexing pattern and found they have the *same* latent bug — they 500 whenever their param is missing:
- `/users` (`page`) — I fixed this too: `int(params.get("page", 0))`. Verified: `handle('/users', {})` → offset 0, `handle('/users', {'page': '3'})` → offset 60.
- `/reports` (`days`) — **I did NOT fix this**, and I want to flag it rather than paper over it. `since_days` has no obvious sensible default (30? 7? 365?), so I won't invent one. It still 500s with `KeyError: 'days'` when `?days` is absent.

**What I need from you:** decide the default for `/reports` (or whether it should instead 400/return an error when `days` is missing). Say the word and I'll apply it. Everything else in the file (`/health`, the `status` param, the router) is consistent and fine.

Files touched: `app.py` (2 lines changed). No other files needed changes.