"""Tiny request router. No framework — params come in as a dict of strings."""

from db import query


def int_param(params, name, default):
    """Read an integer param off the query string.

    Any key may be absent (see README), so a missing key falls back to
    `default` rather than raising KeyError and 500ing the request.
    """
    return int(params.get(name, default))


def get_orders(params):
    limit = int_param(params, "limit", 50)
    status = params.get("status", "all")
    return query("orders", status=status, limit=limit)


def get_users(params):
    page = int_param(params, "page", 0)
    return query("users", offset=page * 20, limit=20)


def get_reports(params):
    days = int_param(params, "days", 7)
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
