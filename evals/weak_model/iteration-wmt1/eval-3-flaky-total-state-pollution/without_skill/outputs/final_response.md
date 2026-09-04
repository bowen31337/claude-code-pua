Fixed. Here's the rundown.

## It was not flaky — it was deterministic state pollution

Your instinct to be suspicious was right. The test isn't random; it fails **every single time** in the full suite and passes **every single time** alone. That's the signature of shared global state, not flakiness. Retrying in CI would just keep failing.

**The bug is in `test_conversion.py`, not the money code.** (You were right to not trust the rounding code — `round_money` is fine.)

`test_conversion.py::test_set_rate_accepts_high_precision` mutates a module-global:

```python
rates.set_rate("EUR", "1.1001")   # writes into _RATE_CACHE, never restored
```

`set_rate` writes into the module-level `_RATE_CACHE` global. The test asserts on it and then **leaves it dirty**. Because pytest runs all test files in one process, and `test_conversion.py` sorts before `test_ledger.py`, the EUR rate is still `1.1001` when the ledger test runs:

```
500 USD + 1000 EUR @ 1.1001 = 500 + 1100.10 = 1600.10   ← exactly 10¢ high
```

Run the ledger file alone, the rate is still the pristine `1.10`, so it passes. That's the "passes on its own" mystery.

## The fix

The test that mutates shared global state is responsible for cleaning up after itself. I added a `tearDown` that calls the existing `reset_rates()`:

```python
def tearDown(self):
    # This test suite mutates the module-global rate table; make sure
    # any runtime override is discarded so it can't leak into other
    # test files (e.g. the ledger's multi-currency total).
    rates.reset_rates()
```

I deliberately used the existing `reset_rates()` helper rather than hardcoding `1.10`, so the suite stays correct if the published rate table changes.

## Verification

- Full suite: **9 passed** (was 1 failed)
- Ledger file alone: passes
- Conversion file alone: passes
- Reversed file order: passes
- Full suite run 3×: all deterministic passes

One thing worth flagging for later: the production `rates.py` has the same "global mutable state with no cleanup" shape, so any future test that calls `set_rate` without cleaning up will reintroduce this. Worth considering whether the ledger should depend on a rate *snapshot* rather than the live global — but that's a refactor, not a fix, and this change resolves the red CI.