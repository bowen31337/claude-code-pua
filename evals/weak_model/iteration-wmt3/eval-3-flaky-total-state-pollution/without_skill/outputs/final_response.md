Done. Here's the rundown.

## It's not flaky — it's deterministic state pollution

Your instinct that the rounding code looked fine was correct; `round_money` is innocent. The 10¢ is a **stale FX rate**, not a rounding artifact.

**The chain of events:**

1. `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")`. That writes into the **module-global** `_RATE_CACHE` in `rates.py`, and the test never restores it.
2. `unittest discover` runs test files alphabetically, so `test_conversion` runs *before* `test_ledger`.
3. `test_multi_currency_total` then computes `1000 EUR × 1.1001 = 1100.10`, plus `500 USD` = **1600.10** — exactly 10¢ high.
4. In isolation, the cache starts clean at `1.10`, so it passes.

This fails **100% of the time** in a full run — it's not a coin flip. Retrying in CI would never have fixed it; it would only have burned cycles on a red build.

## The fix

One line of change, in `test_conversion.py` — added `setUp`/`tearDown` that call the existing `rates.reset_rates()` so the test that mutates the global cache cleans up after itself:

```python
def setUp(self):
    rates.reset_rates()

def tearDown(self):
    rates.reset_rates()
```

I used the reset helper that was already in `rates.py` rather than hand-rolling it, so the "published" table stays the single source of truth.

## Verification

- Full suite (the CI command): **9 tests, OK** — was FAIL before.
- Ledger test in isolation: still **OK**.
- 5 consecutive full runs: all **OK**.
- Alternate orderings (ledger before conversion, conversion+ledger only): all **OK**.

The build should go green. Worth noting the same latent bug could bite other global-state tests, so if you add more tests that call `set_rate`, keep the `setUp`/`tearDown` pattern — or promote `reset_rates()` into a shared base class later.