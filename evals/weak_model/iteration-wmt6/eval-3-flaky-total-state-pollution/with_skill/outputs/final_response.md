Done. Here's the full picture.

## Short answer
**No, it's not a flaky test — do not just retry it.** It's a deterministic bug that only *looks* flaky. Retrying in CI would leave it red forever. I found the cause and fixed it.

## What was actually wrong
The rounding code is fine. The bug is **global state leaking between test files**:

1. `rates.py` keeps its FX table in a **module-level mutable dict** `_RATE_CACHE`. `set_rate()` mutates it in place; `reset_rates()` exists to restore it — but nothing ever calls it.
2. `test_conversion.py::test_set_rate_accepts_high_precision` calls `set_rate("EUR", "1.1001")` and never cleans up. EUR is now permanently `1.1001` for the rest of the process.
3. `unittest discover` runs files **alphabetically**, so `test_conversion` runs *before* `test_ledger`. By the time `test_multi_currency_total` runs, `1000 EUR × 1.1001 = 1100.10`, so the total is `1600.10` — exactly your 10-cent-high number.
4. Run `test_ledger.py` alone and the EUR test never ran, so the cache is clean → it passes. That's the "passes on its own" mystery.

I verified the whole chain: reproduced `1600.10` in the full suite, confirmed each file passes alone, and proved that calling `set_rate("EUR","1.1001")` then `total_usd()` produces `1600.10`.

## The fix
One line of cleanup in the test that leaks the state — a `tearDown` that restores the published table:

```python
class TestConversion(unittest.TestCase):
    def tearDown(self):
        rates.reset_rates()   # set_rate mutates the module-level FX cache
    ...
```

## Evidence (all run just now)
- Full suite: `Ran 9 tests ... OK` (was 1 failure).
- Ran twice → `OK`, `OK` (deterministic, not flaky).
- Order-independent: `test_conversion; test_ledger` → OK, and `test_ledger; test_conversion` → OK.
- Confirmed EUR cache is `1.10` after the conversion test runs.
- Sibling check: `grep` shows `set_rate` is only called in `test_conversion.py` — no other test leaks this state.

## One thing worth flagging (out of scope, but real)
The production `rates.py` has the same footgun: `set_rate` mutates global state with no isolation, so any real caller (the nightly FX job, ops tooling) that overrides a rate leaves it overridden forever. That's not what broke CI, but it's the same class of bug and would bite in production. If you want, I can harden it (e.g. snapshot/restore or make `set_rate` return a context manager) — say the word and I'll do it.

The only file I touched is `test_conversion.py`.