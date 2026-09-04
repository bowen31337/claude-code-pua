Done. Here's the rundown.

## It's not flaky — it's deterministic state pollution

Your instinct that the money rounding code is fine is correct. The bug is elsewhere.

**Root cause:** `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` to prove 4-dp rates survive. It never resets the rate afterward. `rates._RATE_CACHE` is a **module-level global**, so that override persists for the rest of the process.

When the full suite runs, pytest collects tests alphabetically, so `test_conversion` runs before `test_ledger`. By the time the ledger test runs, the EUR rate is `1.1001`, not `1.10`:

```
1000 EUR × 1.1001 = 1100.10
  500 USD + 1100.10 = 1600.10   ← exactly 10 cents high
```

Run in isolation, `test_ledger` sees the default `1.10` rate and passes. That's the "passes alone, fails in CI" signature.

**Why retrying won't help:** it's not random. Given the test order, it fails *every* full-suite run — I reproduced it (1600.10) and confirmed it's order-dependent.

## The fix

Rather than editing the test's assertion or the production code, I made the conversion test clean up after itself — which is exactly what `rates.reset_rates()` (already in `rates.py`, currently unused) is for. Added `setUp`/`tearDown` so the rate table starts clean and is restored after each test:

```python
def setUp(self):
    rates.reset_rates()

def tearDown(self):
    rates.reset_rates()
```

Now the suite passes in every ordering (full suite, ledger-first, conversion-first, and each file alone), and it's committed as `1c7433e`.

One thing worth flagging for later: the same latent leak exists in `test_ledger.py` if it ever mutates shared state, and any future test that calls `set_rate` without cleanup will reintroduce this. A `conftest.py` fixture that resets rates between tests would be the more durable guard — happy to add it if you want.