Fixed. Here's what was wrong and what I changed:

**Root cause:** In `app.py`, the `get_orders` handler read the limit with `int(params["limit"])`. Since `params` is a plain dict, accessing `params["limit"]` when the query string has no `?limit` raises a `KeyError`, which propagated up as a 500.

**Fix:** Changed line 7 to use `.get()` with a default:

```python
limit = int(params.get("limit", 50))
```

Now `/orders` returns a limit of **50** when `?limit` isn't passed, and still respects an explicit value (e.g. `?limit=10`) when it is.

Note: I left `get_users` and `get_reports` untouched since they have the same latent `KeyError` bug (`params["page"]`, `params["days"]`) — but those endpoints weren't reported as failing, so I only touched what you asked for. Happy to harden those too if you'd like.