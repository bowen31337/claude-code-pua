# orders-api

Internal read-only API. `handle(path, params)` is the entry point;
`params` is whatever came off the query string, so every value is a
string and any key may be absent.

Run it: `python3 -c "from app import handle; print(handle('/orders', {}))"`

## Query params

Every param is optional; an absent (or blank) one falls back to its default.
A param that *is* supplied but isn't a number raises `ValueError` rather than
silently falling back — that's a caller bug worth seeing.

| Route | Param | Default |
|---|---|---|
| `/orders` | `limit` | 50 |
| `/orders` | `status` | `all` |
| `/users` | `page` | 0 (first page, 20 per page) |
| `/reports` | `days` | 30 |
