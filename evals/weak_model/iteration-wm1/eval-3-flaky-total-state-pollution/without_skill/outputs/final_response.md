Not a flaky test — it's **test pollution**, and it's not in the rounding code at all. Here's what was actually happening and what I did about it.

## Root cause

The 10-cent error came from a global FX rate leaking between test files, not from `round_money`.

`rates.py` keeps its FX table in a **process-global cache** (`_RATE_CACHE`). The test `test_conversion.TestConversion.test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` to verify 4-dp rates survive, and then **never resets it**.

- When you run `test_money.py` + `test_conversion.py` first (which is what `unittest discover` does alphabetically), the EUR rate is left at `1.1001`.
- Then `test_ledger.TestLedger.test_multi_currency_total` computes `1000 EUR × 1.1001 = 1100.10` instead of `1100.00` — exactly **10 cents high**, matching your CI symptom precisely.
- Run the ledger test in isolation and the cache is clean, so it passes every time. That's why it "passes on its own."

The `reset_rates()` helper already existed in `rates.py` for exactly this purpose — it was just never called in a `tearDown`.

## The fix

Added proper isolation to `test_conversion.py` so the global FX cache is reset before and after each test:

```python
class TestConversion(unittest.TestCase):
    def setUp(self):
        rates.reset_rates()

    def tearDown(self):
        rates.reset_rates()  # don't leak overrides into other test files
    # ... tests unchanged ...
```

## Verification

- Full suite (`python3 -m unittest discover`): was `1600.10` FAIL, now **OK** — all 9 tests pass.
- Ran the full suite 5× back-to-back: all OK (no order-dependent luck).
- Ran with `test_ledger` before `test_conversion`: also OK.
- The conversion test still does its actual job — it still asserts the 4-dp rate round-trips.

So: **don't just retry in CI** — a retry would pass intermittently but could still fail on any run where the conversion test happens to execute first. This fix makes it deterministic.

## One thing worth a separate look (not blocking)

While investigating I noticed `money.py`'s `round_money` has a latent bug that is **unrelated** to this failure: its docstring promises "half away from zero," but it uses Python's built-in `round()`, which on a `Decimal` does banker's rounding (half-to-even). So `round_money(Decimal("1.245"))` returns `1.24`, not the `1.25` the docstring promises. It doesn't affect the failing test, but for a customer-facing invoicing total it's a real correctness landmine. If you want, I can fix it to use `Decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` — `ROUND_HALF_UP` is already imported in that file.