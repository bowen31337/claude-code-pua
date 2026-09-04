"""Tiny request router. No framework — params come in as a dict of strings."""

from db import query


def get_orders(params):
    limit = int(params.get("limit", 50))
    status = params.get("status", "all")
    return query("orders", status=status, limit=limit)


def get_users(params):
    page = int(params["page"])
    return query("users", offset=page * 20, limit=20)


def get_reports(params):
    days = int(params["days"])
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
