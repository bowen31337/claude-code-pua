"""Tiny request router. No framework — params come in as a dict of strings."""

from db import query


def int_param(params, key, default):
    """Read an int query param. Absent key -> default (query strings are optional)."""
    if key not in params:
        return default
    return int(params[key])


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
