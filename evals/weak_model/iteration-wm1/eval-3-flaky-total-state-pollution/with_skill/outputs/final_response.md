**It's not a flaky test — do not retry it in CI.** Retrying would never fix it; the failure is 100% deterministic and reproducible every single time the suite runs. I reproduced it, proved the root cause with evidence, and fixed it. The full suite now passes (9 tests, exit 0), and it passes regardless of test order.

## What was actually wrong

This is **test-order-dependent state pollution**, not flakiness and not a rounding bug (your rounding code is fine).

The chain, with receipts:

1. `python3 -m unittest discover` runs test files **alphabetically**, so `test_conversion.py` runs *before* `test_ledger.py`.
2. `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")`. That mutates the **module-level `_RATE_CACHE` dict** in `rates.py` — a global, process-wide singleton.
3. **No test ever calls `reset_rates()`** (grep confirmed the function exists but is unused everywhere). So the EUR rate stays at `1.1001` for the rest of the process.
4. When `test_multi_currency_total` runs, it converts EUR at the polluted rate: `1000 × 1.1001 = 1100.10`, then `500 + 1100.10 = 1600.10` — **exactly 10 cents high**, matching your symptom precisely.
5. Run `test_ledger.py` on its own, `test_conversion.py` never executes, the cache is still `1.10`, and the test passes. That's why your isolation runs always passed.

The reason it "looks" flaky: the failure only appears when the two files run together, and the specific 10-cent delta is a red herring that pointed you at rounding. The rounding chokepoint is working correctly — it's just rounding a wrong input.

## The fix

I added `setUp`/`tearDown` to `TestConversion` so the FX cache is reset to the published table before *and* after every test. This closes the leak at its source:

```python
class TestConversion(unittest.TestCase):
    def setUp(self):
        rates.reset_rates()   # start each test from the published table
    def tearDown(self):
        rates.reset_rates()   # leave nothing behind for later test files
```

I deliberately put the reset in the test that owns the mutation (`test_conversion.py`), rather than patching `test_ledger.py` — the ledger test's expectation of `1600.00` is correct; the FX state it was fed was the thing that was wrong.

## Verification (all real runs)

- **Full suite (CI command):** `Ran 9 tests ... OK`, exit 0 — was `FAILED (failures=1)` before.
- **`test_ledger.py` alone:** still passes (was passing before, still passes).
- **Order independence:** `test_conversion test_ledger` explicitly → OK. The discovery order no longer matters.
- **Cache actually cleaned:** after running the full conversion suite, `rates.get_rate("EUR")` returns `1.10`, not `1.1001` — proves `tearDown` runs.
- **Determinism:** repeated full-suite runs all return OK.

## One thing worth your attention (the "siblings" check)

The `reset_rates()` function already existed in `rates.py` and was clearly *meant* to be used for exactly this — it's the intended isolation primitive — but nobody wired it into the tests. That's a smell: either there's a shared fixture pattern that's half-built, or other test files that touch `rates` could have the same latent leak. I only found and fixed `test_conversion.py`; if you have more test files exercising `set_rate`, they'd want the same `setUp`/`tearDown` treatment. Worth a quick grep for other `set_rate` callers if this ledger module grows.

Note: these files aren't git-tracked in this directory, so I couldn't commit — the fix is applied directly to `test_conversion.py` on disk. If you want it tracked, let me know and I'll set that up.