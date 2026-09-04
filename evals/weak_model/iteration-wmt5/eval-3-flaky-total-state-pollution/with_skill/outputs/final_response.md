The fix is complete and verified. Here's the report.

## Short answer

**No, it's not a flaky test — don't retry it in CI.** It fails 100% of the time when the full suite runs; it's deterministic. Retrying would just keep showing red. I found the root cause and fixed it.

## What was actually wrong

The money rounding code is fine. The bug was **test-order-dependent state pollution** in `rates.py`'s module-level global cache.

1. `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")`, which mutates the shared `_RATE_CACHE` global. Nothing ever resets it.
2. pytest runs files alphabetically, so `test_conversion.py` runs *before* `test_ledger.py`.
3. By the time `test_multi_currency_total` runs, EUR is stuck at `1.1001` instead of `1.10`, so `1000 EUR × 1.1001 = 1100.10`, and the total comes out `1600.10` — **exactly 10 cents high**.
4. Run in isolation, the cache is still `1.10`, so it passes. That's why your "runs green alone" instinct was right — it's a symptom, not a cure.

I reproduced the exact failure (`Decimal('1600.10') != Decimal('1600.00')`) before touching anything, then confirmed the mechanism directly.

## The fix

`test_conversion.py` mutates a shared global, so it must clean up after itself. I added `setUp`/`tearDown` that snapshot and restore `_RATE_CACHE`:

```python
def setUp(self):
    self._saved = dict(rates._RATE_CACHE)

def tearDown(self):
    rates._RATE_CACHE.clear()
    rates._RATE_CACHE.update(self._saved)
```

## Verification (evidence)

- **Full suite (CI scenario, alphabetical):** 9 passed, was 1 failed. ✅
- **Reverse order:** 9 passed — proves it's now order-independent, not just accidentally green. ✅
- **Isolated run of the old-failing test:** still green. ✅
- **Sibling check:** `grep` showed `test_conversion.py` is the *only* place that mutates the cache; `rates.py` already ships a `reset_rates()` helper (currently unused). No other test is at risk.

## One thing worth your attention

The real design smell is that `set_rate` mutates process-global state with no isolation — that's fine for the FX job, but it makes any test that touches it fragile. The `reset_rates()` function already exists and would be a cleaner fixture hook than reaching into `_RATE_CACHE`. If you want, I can switch the test to use `reset_rates()` in `tearDown` instead, so it doesn't depend on a private attribute. Say the word and I'll make that change.