Fixed, and it's now deterministic across every ordering and repeated runs.

## Short answer: don't retry it — it wasn't flaky

`test_multi_currency_total` fails **100% of the time** in the full suite and **100% of the time** alone would pass. That's not a coin-flake; it's a deterministic bug. Retrying in CI would just give you a red build that looks random and erodes trust in your test runner.

## What was actually wrong

It was **test pollution via shared global state**, not a rounding bug. Your `round_money` code is correct.

1. `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")`, which mutates the module-level `_RATE_CACHE` global.
2. Nothing ever reset it — `reset_rates()` exists in `rates.py` but was never called.
3. `unittest discover` runs `test_conversion` **before** `test_ledger`, so by the time `test_multi_currency_total` runs, EUR is stuck at `1.1001`:

   `500 USD + 1000 EUR × 1.1001 = 500 + 1100.10 = 1600.10` → exactly 10 cents high.

It passed in isolation because the EUR rate was still `1.10` when that file ran alone. That's the tell that gave it away.

## The fix

One line of change in `test_conversion.py` — added `setUp`/`tearDown` that call the already-existing `rates.reset_rates()` so the test that mutates global state cleans up after itself:

```python
class TestConversion(unittest.TestCase):
    def setUp(self):
        rates.reset_rates()

    def tearDown(self):
        rates.reset_rates()
    # ... existing tests unchanged ...
```

I deliberately reused `reset_rates()` rather than hand-rolling a restore, since it's the module's own contract for this exact situation.

## Verification

- Full CI suite (`discover`): **OK**
- `test_ledger.py` alone: **OK**
- `test_conversion.py` alone: **OK**
- Reversed / alternate orderings: **OK**
- 5× repeat of the full run: **OK every time**

If you want belt-and-suspenders against future globals like this, the same `setUp`/`tearDown` reset pattern should be applied to any other test that touches shared state — but for now this single fix is all that's needed.