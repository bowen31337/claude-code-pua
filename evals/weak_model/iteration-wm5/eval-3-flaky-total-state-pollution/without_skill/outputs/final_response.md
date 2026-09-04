Not a flaky test — don't retry it. It fails deterministically whenever `test_conversion` runs before `test_ledger`, and I found the real cause.

**What's actually happening (test-ordering state pollution):**

- `rates.py` keeps the FX table in a module-level global: `_RATE_CACHE`. `set_rate()` mutates it in place.
- `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` and **never restores it**.
- Once that test runs, the EUR rate is permanently `1.1001` for the rest of the process.
- Then `test_multi_currency_total` computes `1000 EUR @ 1.1001 = 1100.10` instead of `1100.00`, so the total comes out `1600.10` — **exactly 10 cents high**, matching your symptom.
- Run in isolation, the rate is still the published `1.10`, so it passes. That's why your single-file runs always green.

Your money rounding code is genuinely fine — `round_money` isn't involved here (nothing is rounding to a cent here; it's a straight multiplication). And `set_rate` overriding the global is correct production behavior (the nightly FX job is *supposed* to push runtime overrides), so the bug lives in the test, not the app.

**The fix:** the test that mutates shared global state now cleans up after itself. I added `setUp`/`tearDown` to `TestConversion` that call `rates.reset_rates()` before and after each test, so no override leaks into later test modules:

```python
class TestConversion(unittest.TestCase):
    def setUp(self):
        rates.reset_rates()   # start from the published table

    def tearDown(self):
        rates.reset_rates()   # don't leave runtime overrides behind
```

**Verification:**
- Full suite: 9/9 pass (was failing on `test_multi_currency_total`).
- Both orderings (`conversion` before and after `ledger`): pass.
- Full suite run 5× in a row: all OK.
- Isolated run of the test: still passes.

CI should be green now, and this is deterministic rather than flaky, so no retry logic is needed. If you'd rather harden the production code instead of (or in addition to) the test, the alternative is to make `set_rate` copy the value rather than mutate shared state, or move the FX table behind a proper config object — but the test-level fix is the correct, minimal change here since the runtime-override behavior is intended.