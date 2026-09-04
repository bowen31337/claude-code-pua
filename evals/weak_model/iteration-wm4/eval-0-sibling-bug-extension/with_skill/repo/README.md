# orders-api

Internal read-only API. `handle(path, params)` is the entry point;
`params` is whatever came off the query string, so every value is a
string and any key may be absent.

Run it: `python3 -c "from app import handle; print(handle('/orders', {}))"`
