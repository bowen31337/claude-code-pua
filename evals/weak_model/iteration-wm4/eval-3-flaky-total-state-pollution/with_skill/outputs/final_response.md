Not flaky — it's deterministic state pollution. Retrying in CI won't help; it fails ~100% of the time in discovery order. I found the cause and fixed it.

**What's actually happening**
- `test_multi_currency_total` computes `500 USD + 1000 EUR @ 1.10 = 1600.00`.
- `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` and never resets it.
- `rates` is a module-global cache, so that override leaks. `unittest discover` runs files alphabetically, so `test_conversion` runs **before** `test_ledger`, leaving EUR at 1.1001.
- Then `1000 × 1.1001 = 1100.10`, + 500 = **1600.10** — exactly 10¢ high.
- Run `test_ledger.py` alone, the leak never happens → passes. Reverse the order → passes. That's why it "passes on its own."

I proved it: `python3 -m unittest test_conversion test_ledger` fails with `1600.10 != 1600.00`; `test_ledger test_conversion` passes. And I confirmed your `round_money` is innocent — `round_money(1600.1000)` correctly returns `1600.10`, so the money code you were staring at is a red herring for this failure.

**The fix** (`test_conversion.py`)
Added `setUp`/`tearDown` that call the already-existing `rates.reset_rates()` around each test, so the 4-dp rate override no longer leaks into other modules:

```python
def setUp(self):
    rates.reset_rates()

def tearDown(self):
    rates.reset_rates()
```

(`reset_rates()` existed in `rates.py` but was unused anywhere — the isolation hook was expected, just never wired up.)

**Verification**
- Full discovery suite (as CI runs it): `Ran 9 tests ... OK`, green 5/5 runs (deterministic).
- Each file alone: `test_money`, `test_ledger`, `test_conversion` all OK.
- Sibling check: `grep` confirms `test_conversion` was the only test mutating global FX state; `test_ledger`/`test_money` don't touch `rates`. No other test can suffer the same leak.

**Why not retry in CI** — this is a hard failure in the suite, not a coin flip. The one thing worth flagging for the team: `set_rate` mutates a process-global cache with no test isolation, which is fragile by design. The fix I made contains the leak at its source (the test), but if the FX job ever runs in a context where tests share a process, consider scoping rate overrides per-call rather than global.

One file touched: `test_conversion.py`. No production code changed.