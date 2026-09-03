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
    """Override a rate at runtime (used by the FX job and by ops tooling)."""
    _RATE_CACHE[code] = Decimal(rate)


def reset_rates():
    """Restore the published rate table, discarding any runtime overrides."""
    _RATE_CACHE.clear()
    _RATE_CACHE.update(_DEFAULT_RATES)


def to_usd(amount, code):
    return amount * get_rate(code)
