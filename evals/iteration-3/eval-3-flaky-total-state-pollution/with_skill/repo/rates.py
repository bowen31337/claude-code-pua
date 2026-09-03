from contextlib import contextmanager
from decimal import Decimal

# Published mid-market rates, refreshed nightly by the FX job.
_DEFAULT_RATES = {
    "USD": Decimal("1.00"),
    "EUR": Decimal("1.10"),
    "GBP": Decimal("1.27"),
}

_RATE_CACHE = dict(_DEFAULT_RATES)


def get_rate(code):
    return _RATE_CACHE[code]


def set_rate(code, rate):
    """Override a rate at runtime (used by the FX job and by ops tooling).

    NOTE: this mutates process-global state that outlives the caller. In
    tests, prefer `rate_override()` or reset in a fixture -- a stray
    override here has previously leaked across test files and corrupted
    unrelated totals.
    """
    _RATE_CACHE[code] = Decimal(rate)


def reset_rates():
    """Restore the published rate table, discarding any runtime overrides."""
    _RATE_CACHE.clear()
    _RATE_CACHE.update(_DEFAULT_RATES)


@contextmanager
def rate_override(code, rate):
    """Temporarily override one rate, restoring the previous value on exit.

    Scoped alternative to set_rate() for tests and one-off ops work, so an
    override cannot escape the block that made it (even on exception).
    """
    missing = object()
    previous = _RATE_CACHE.get(code, missing)
    set_rate(code, rate)
    try:
        yield
    finally:
        if previous is missing:
            _RATE_CACHE.pop(code, None)
        else:
            _RATE_CACHE[code] = previous


def to_usd(amount, code):
    return amount * get_rate(code)
