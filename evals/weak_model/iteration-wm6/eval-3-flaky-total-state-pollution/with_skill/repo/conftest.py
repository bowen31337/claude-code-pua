import pytest

import rates


@pytest.fixture(autouse=True)
def _reset_fx_rates():
    """Isolate tests from the shared FX rate cache.

    ``rates`` keeps its published rates in a module-level dict that
    ``set_rate`` mutates in place. A test that overrides a rate and never
    restores it would otherwise leak into later tests and change their
    conversions. Reset before and after every test so each one sees the
    published table regardless of ordering.
    """
    rates.reset_rates()
    yield
    rates.reset_rates()
