Not flaky. Don't add a retry — a retry would have hidden it and it would have come back as a wrong invoice.

`test_multi_currency_total` fails **100% of the time** in the full suite and **passes 100% of the time** in isolation. That's not randomness, that's strict test-ordering dependence, and it's completely deterministic once you know the trigger.

## Root cause: one test leaks a global FX rate into every test after it

`rates._RATE_CACHE` is process-global module state. `test_conversion.py` did this:

```python
def test_set_rate_accepts_high_precision(self):
    rates.set_rate("EUR", "1.1001")     # never restored
    self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))
```

`set_rate` mutates the global table for the rest of the process. `test_conversion` sorts before `test_ledger` under `unittest discover`, so by the time the ledger test runs, EUR is 1.1001 instead of the published 1.10:

```
1000 EUR x 1.1001 = 1100.1000
+ 500 USD         = 1600.1000  ->  1600.10
```

Exactly the 10 cents. The arithmetic is right; the *input rate* was wrong.

I proved causation rather than assuming it:

```
=== A: test_ledger.py ALONE (x3) ===        OK / OK / OK
=== B: conversion THEN ledger ===           FAILED (failures=1)
=== C: ledger THEN conversion (reversed) == OK
=== D: just the 2 suspect tests ===         FAILED (failures=1)
```

Reversing the order makes it pass. That's the whole bug.

Telling detail: `rates.reset_rates()` already existed in the codebase and was called from nowhere. The safety net was written and then never used.

## Why staring at the rounding code found nothing — and what it *did* hide

The rounding code is not the cause of your red build. But there **is** a real bug in it, just not the one you were looking for:

```python
return Decimal(round(amount, 2))   # built-in round() on a Decimal is ROUND_HALF_EVEN
```

The docstring says *"half away from zero... a customer-facing total must never round a half-cent down."* The code does banker's rounding, which rounds half-cents down half the time — the precise thing the docstring forbids. And `ROUND_HALF_UP` was imported but unused, `CENTS` defined but unused, so this looks like a regression from an original `amount.quantize(CENTS, rounding=ROUND_HALF_UP)`.

Measured, before the fix:

```
   input   round_money   documented HALF_UP
   1.225      1.22            1.23      <- half-cent lost
   1.005      1.00            1.01      <- half-cent lost
   0.005      0.00            0.01      <- half-cent lost
  -1.225     -1.22           -1.23
```

This matters more than it looks, because your FX rates are 4-dp — 4-dp rates times 2-dp amounts routinely land exactly on a half-cent.

## What I changed

1. **`rates.py`** — added a `rate_override(code, rate)` context manager that restores the previous value on exit, including on exception. Kept `set_rate` for the FX job but documented the leak hazard on it.
2. **`test_conversion.py`** — uses `rate_override` instead of a bare `set_rate`, plus `setUp` doing `reset_rates()` + `addCleanup(reset_rates)` so nothing escapes even if a test fails midway.
3. **`test_ledger.py`** — same `setUp` guard, so ledger totals no longer depend on what ran before them, plus a regression test that deliberately plants a leaked rate and asserts the real test still passes.
4. **`money.py`** — `round_money` now does `amount.quantize(CENTS, rounding=ROUND_HALF_UP)`, matching its own docstring, and coerces non-`Decimal` input via `str()` so no binary-float error creeps in.
5. **`README.md`** — documented the global-FX-state hazard and the `setUp` pattern, so the next person doesn't rediscover this.

## Evidence

Full suite, CI's own discovery order:

```
Ran 16 tests in 0.000s

OK
```

All 6 module orderings, fresh process each:

```
OK    test_conversion test_ledger test_money
OK    test_conversion test_money test_ledger
OK    test_ledger test_conversion test_money
OK    test_ledger test_money test_conversion
OK    test_money test_conversion test_ledger
OK    test_money test_ledger test_conversion

6 permutations, 0 failing
```

200 runs with randomised test-method order, all in one process so globals are genuinely shared:

```
200 randomised-order runs -> 0 failing
global rate table after all runs: {'USD': 1.00, 'EUR': 1.10, 'GBP': 1.27}
```

I also mutation-checked both fixes so you know the new tests aren't vacuous. Removing the isolation guard brings the failure straight back:

```
AssertionError: test_multi_currency_total is not isolated from leaked FX overrides:
  AssertionError: Decimal('1600.10') != Decimal('1600.00')
```

Reverting `round_money` to `round()`:

```
FAIL: test_half_cent_rounds_up_not_to_even        AssertionError: Decimal('1.22') != Decimal('1.23')
FAIL: test_half_cent_rounds_away_from_zero...     AssertionError: Decimal('-1.22') != Decimal('-1.23')
```

## One thing to decide before you ship

The rounding fix **changes financial output**. I measured the blast radius across every 3-dp value from 0.000 to 100.000:

```
95001 identical, 5000 changed (5.0%)
non-half-cent divergences: NONE  <- change is confined to exact half-cents
```

Every divergence is an exact half-cent, and each moves up by one cent — which is what the docstring always promised. But if any downstream system reconciles against historical totals produced by the old half-to-even behaviour, those will now differ by a cent on half-cent cases. Your call whether that ships with the CI fix or as a separate, announced change. The test-isolation fix alone is enough to turn CI green and carries no behavioural risk.

## Also worth knowing

Nothing in the codebase besides that one test calls `set_rate`, so this was the only leak — I grepped. And stdlib `unittest` has no `--shuffle`/random-order flag, so ordering bugs like this can't be caught automatically here; if you want that safety net in CI, `pytest -p randomly` (pytest-randomly) would surface the whole class of them.
