"""Stub data layer — returns a description of the query instead of hitting a DB."""


def query(table, **kwargs):
    return {"table": table, **kwargs}
