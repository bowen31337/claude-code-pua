Fixed and verified. Here's the summary.

## Was it flaky? No.

This was a **deterministic test-ordering bug**, not a flaky test. Retrying in CI would have been the wrong move — the failure is reproducible every single time in the full run, which is the opposite of flaky. Flaky tests are nondeterministic; this one was 100% consistent.

## Root cause

The 10-cent offset came from **global state pollution**, not the rounding code (you were right to trust your eyes on `money.py`).

- `rates.py` keeps a module-level global `_RATE_CACHE` that is never reset between tests.
- `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` and **never restores it**.
- `unittest discover` runs `test_conversion.py` before `test_ledger.py` (alphabetical). So when `test_multi_currency_total` ran, the EUR rate was still `1.1001`.
- `500 USD + 1000 EUR × 1.1001 = 500 + 1100.10 = 1600.10` — exactly 10 cents high. (10¢ = `1000 × (1.1001 − 1.10)`.)
- In isolation, the cache is still the default `1.10`, so it passed every time — which is precisely why it looked "flaky" and why you couldn't find anything wrong with the money code.

## The fix

One line of cleanup in the offending test. `rates.reset_rates()` already existed for this exact purpose; the test just wasn't using it. I added a `tearDown` to `test_conversion.py` so it restores the published FX table after the test mutates it:

```python
def tearDown(self):
    # This test mutates the module-level FX cache; restore it so we
    # don't leak a 4-dp EUR rate into later test modules (e.g. the
    # ledger total test, which assumes the published 1.10 rate).
    rates.reset_rates()
```

## Verification

- Full discovery run (the CI scenario): **OK**
- Isolation runs of each file: **OK**
- Both orderings (conversion→ledger and ledger→conversion): **OK**
- 5 consecutive full runs: **all OK** — deterministic.

The test file now passes in CI and in isolation, and the fix is order-independent, so it can't regress if the run order changes.

One thing worth flagging for later: `rates.py`'s global cache is a latent footgun — any future test that calls `set_rate` and forgets to clean up will reintroduce this exact class of bug. If you want, I can make `reset_rates` run automatically (e.g. a module-level guard or a shared base test case) so the leak can't happen again silently.