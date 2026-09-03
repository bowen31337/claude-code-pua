# Not flaky. Don't retry it.

`test_multi_currency_total` fails **100% of the time** in the full suite and passes **100% of the time** on its own. That's not flakiness — it's a deterministic order dependency. A CI retry would just make it red every time, more slowly.

## Root cause

`test_conversion.py::test_set_rate_accepts_high_precision` writes to the process-global rate cache and never puts it back:

```python
rates.set_rate("EUR", "1.1001")   # mutates rates._RATE_CACHE for the rest of the process
```

`rates._RATE_CACHE` is module-level state, so it lives for the whole test process. Under `unittest discover` the modules load alphabetically — `test_conversion` before `test_ledger` — so by the time the ledger test runs, EUR is `1.1001` instead of the published `1.10`.

That's exactly your 10 cents:

```
1000 EUR x 1.1001 = 1100.10   (vs 1100.00)
500 + 1100.10     = 1600.10   -> 10c high
```

I confirmed the chain directly:

```
EUR before: 1.10     total before: 1600.00
EUR after : 1.1001   total after : 1600.10
```

And confirmed it's ordering, not chance — running `test_ledger` *before* `test_conversion` passes, every time.

**Your rounding code was never involved in this failure.** You were right to not find anything there; the number arriving at `round_money` was already wrong.

## Fix

`rates.py` already has `reset_rates()` for exactly this purpose — it just wasn't being called. I registered it as cleanup in `test_conversion.py`:

```python
class TestConversion(unittest.TestCase):
    def setUp(self):
        self.addCleanup(rates.reset_rates)
```

`addCleanup` runs even if a test raises, so a failure mid-test can't leak the override either. I also added `test_reset_rates_discards_overrides` to pin the reset behaviour itself.

## Separate bug I found while I was in there

Not the cause of your CI failure, but real and worth knowing about: `round_money` did not do what its docstring says.

It was `Decimal(round(amount, 2))`, and the builtin `round()` applies **banker's rounding** (half-to-even) to `Decimal`. Your docstring and README say half-away-from-zero, and `CENTS` and `ROUND_HALF_UP` were imported at the top of `money.py` and never used — the intended implementation clearly got lost at some point.

Live impact, before the fix:

| amount  | was    | should be |
|---------|--------|-----------|
| 1.005   | 1.00   | 1.01      |
| 1.025   | 1.02   | 1.03      |
| 0.125   | 0.12   | 0.13      |

So roughly half of all half-cent totals were rounding *down* — precisely the "books disagree with the statement" case the docstring warns about. The existing tests (`1.234`, `1.236`) never hit a half-cent, so nothing caught it.

Now:

```python
return amount.quantize(CENTS, rounding=ROUND_HALF_UP)
```

with `test_round_half_cent_goes_up_not_to_even` covering the boundary.

If any downstream figures are reconciled against the old behaviour, this will shift them by a cent — correctly, but worth a heads-up to whoever owns invoicing.

## Verification

- Full suite: **11/11 pass**.
- All 6 orderings of the three test modules: pass.
- 5 consecutive full runs: pass.
- Reverted each fix individually to confirm it was load-bearing: dropping the cleanup brings `test_multi_currency_total` straight back; dropping the quantize fails the new rounding test.

## Files changed

- `test_conversion.py` — `addCleanup(rates.reset_rates)`, plus a reset test
- `money.py` — `round_money` now quantizes with `ROUND_HALF_UP`
- `test_money.py` — half-cent regression test

## One thing to consider

`rates._RATE_CACHE` is global mutable state that any test (or any code path) can write to and forget to restore. This fix stops the current leak, but the shape of the problem will come back. If it bites again, the durable options are a session-wide autouse reset, or having `Ledger` take the rate table as a dependency rather than reaching for a module global.
