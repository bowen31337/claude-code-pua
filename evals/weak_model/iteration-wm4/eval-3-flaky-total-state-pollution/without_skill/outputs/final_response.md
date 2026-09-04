Good news: it's not a flaky test, and retrying in CI won't fix it — the failure is deterministic. And you're right that the rounding code is fine. The bug is **test-ordering state pollution** in the FX rate cache.

**Root cause**
- `rates.py` holds a **global mutable cache** (`_RATE_CACHE`) that `set_rate` mutates in place.
- `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` and **never restores it**.
- unittest discovers modules alphabetically, so `test_conversion` runs *before* `test_ledger`. That leaves EUR pinned at `1.1001`.
- Then `test_multi_currency_total` computes `1000 EUR × 1.1001 = 1100.10`, giving a total of `1600.10` — exactly 10 cents high.
- Run in isolation, the default `1.10` is still in the cache, so it passes. That's why it "always passes on its own."

I reproduced it (`1600.10 != 1600.00`), confirmed the isolated pass, and pinned the exact ordering that triggers it.

**The fix**
Made the test that mutates global state clean up after itself, so it can't leak into other modules:

```python
class TestConversion(unittest.TestCase):
    def setUp(self):
        self._saved = dict(rates._RATE_CACHE)   # tests mutate the global FX cache

    def tearDown(self):
        rates._RATE_CACHE.clear()
        rates._RATE_CACHE.update(self._saved)
    # ... existing tests unchanged ...
```

I verified the full suite, the previously-failing ordering, and isolated runs all pass.

**Two things worth noting for you:**
1. The `test_set_rate` test is legitimately testing valid behavior (4-dp rates survive round-trip), so I kept it — I only added the teardown. If you'd rather not have any test touch the global cache, the more robust long-term fix is to refactor `rates.py` to drop the module-level mutable cache (e.g. pass rates in or return them), but that's a bigger change than this warrants.
2. This is exactly the kind of failure that looks flaky but isn't: it's order-dependent and deterministic. Worth adding a note to CI (or a `setUp`/`tearDown` convention) so a future test that mutates global state doesn't reintroduce it.