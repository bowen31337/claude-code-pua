"""Tiny request router. No framework — params come in as a dict of strings."""

from db import query

# Applied when the caller omits the param entirely (or sends it blank).
DEFAULT_LIMIT = 50
DEFAULT_PAGE = 0
DEFAULT_REPORT_DAYS = 30
PAGE_SIZE = 20


def int_param(params, name, default):
    """Read an integer off the query string, falling back to `default`.

    Every value in `params` is a string and any key may be absent, so a
    missing key — or a blank one, e.g. "?limit=" from a caller that
    interpolated an undefined value — means "not supplied" and yields
    `default`.

    A present but non-numeric value still raises ValueError: the caller asked
    for something specific we can't honour, and quietly substituting the
    default would hide their bug instead of surfacing it.
    """
    raw = params.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return int(raw)


def get_orders(params):
    limit = int_param(params, "limit", DEFAULT_LIMIT)
    status = params.get("status", "all")
    return query("orders", status=status, limit=limit)


def get_users(params):
    page = int_param(params, "page", DEFAULT_PAGE)
    return query("users", offset=page * PAGE_SIZE, limit=PAGE_SIZE)


def get_reports(params):
    days = int_param(params, "days", DEFAULT_REPORT_DAYS)
    return query("reports", since_days=days, limit=100)


def get_health(params):
    return {"ok": True}


ROUTES = {
    "/orders": get_orders,
    "/users": get_users,
    "/reports": get_reports,
    "/health": get_health,
}


def handle(path, params):
    return ROUTES[path](params)
