Not flaky. Don't add a retry — a retry would have hidden a real bug, and it wouldn't even have worked, because the failure is 100% deterministic given test order.

`[PIP · L0 · Root Cause Analysis → Adversarial Review. No failed attempts to escalate on; the cause fell out of the first full-suite run.]`

## What's actually happening

`test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` and never puts it back. `rates._RATE_CACHE` is a module-level dict, so that override survives for the rest of the process. Discovery order is alphabetical — `test_conversion` before `test_ledger` — so by the time `test_multi_currency_total` runs, EUR is 1.1001 instead of 1.10.

1000 EUR × 0.0001 = **exactly 10 cents.** That's your drift:

```
EUR before: 1.10
EUR after set_rate: 1.1001
1000 EUR -> 1100.1000
delta cents: 0.1000
```

The rounding code was never involved. It's a stale global.

## Why it "passes on its own"

Because running that file alone never loads `test_conversion`, so nothing pollutes the cache. Proof, before any fix:

```
=== A: test_ledger.py ALONE (10x) ===        OK OK OK OK OK OK OK OK OK OK
=== B: conversion THEN ledger ===            AssertionError: Decimal('1600.10') != Decimal('1600.00')
=== C: ledger THEN conversion ===            OK
```

Ten for ten alone, fails every time in one order, passes every time in the other. That's an ordering dependency wearing a flaky-test costume. A CI retry re-runs the whole suite in the same order and fails identically.

## Fix 1 — the CI failure

`rates.py` already shipped a `reset_rates()` that nothing ever called. Now it does. Both test modules get:

```python
def setUp(self):
    rates.reset_rates()
    self.addCleanup(rates.reset_rates)
```

Reset **before** as well as after, and via `addCleanup` so the restore still runs when a test fails mid-way. That fixes it at the leak site and also makes `test_ledger` immune to anyone else leaking into it later. I added `test_total_is_isolated_from_leaked_rate_overrides` as a named regression guard so this can't come back silently.

## Fix 2 — there *was* something wrong with the rounding code

You were right to look, just not for this bug. `round_money` was:

```python
return Decimal(round(amount, 2))
```

Builtin `round()` on a `Decimal` uses **ROUND_HALF_EVEN** (banker's rounding). The docstring directly above it says "half away from zero" and "must never round a half-cent down." `ROUND_HALF_UP` and `CENTS` were imported and defined at the top of the file — and never used. The intended implementation had been lost.

Measured against its own documented contract:

```
   1.005  round_money=1.00  HALF_UP=1.01  MISMATCH
   0.125  round_money=0.12  HALF_UP=0.13  MISMATCH
  -1.005  round_money=-1.00 HALF_UP=-1.01 MISMATCH
```

Your existing tests (1.234, 1.236) both miss the half-cent case, which is the only case where the two modes differ — so the suite was green on a rounding function that did the opposite of what invoicing requires.

Second, smaller: on float input `round(1.005, 2)` returns a float, and `Decimal(1.0)` is `Decimal('1')` — no cents exponent. `str()` gave `"1"`, not `"1.00"`. It compared equal so tests never caught it, but it would surface in serialized invoice output.

Now it uses the constants that were already sitting there:

```python
if not isinstance(amount, Decimal):
    amount = Decimal(str(amount))   # str() first, or Decimal inherits the binary float error
return amount.quantize(CENTS, rounding=ROUND_HALF_UP)
```

Two tests added for the half-cent and two-places behaviour.

## Verification

Full suite, the README command verbatim:

```
Ran 13 tests in 0.000s

OK
```

And because "passes in this order" was the original bug, I checked it can't be order-dependent again:

```
=== ALL 6 MODULE ORDERINGS ===
test_conversion -> test_ledger -> test_money  OK
test_conversion -> test_money -> test_ledger  OK
test_ledger -> test_conversion -> test_money  OK
test_ledger -> test_money -> test_conversion  OK
test_money -> test_conversion -> test_ledger  OK
test_money -> test_ledger -> test_conversion  OK
failing orderings: 0/6

=== EACH MODULE IN ISOLATION ===   all OK
=== 30x RANDOMIZED METHOD ORDER ===  shuffled runs failing: 0/30
```

Files touched: `money.py`, `test_money.py`, `test_conversion.py`, `test_ledger.py`. `rates.py` and `ledger.py` unchanged.

## One thing worth deciding, that I didn't change

The deeper design issue is that `Ledger.total_usd()` reads a process-global rate table, so a total isn't a pure function of the ledger — it depends on whatever the FX job last pushed. My fix pins that in tests, but in production the same shape means an invoice total can change between two calls if the nightly job lands in between. If that matters to you, the fix is to snapshot the rate onto the entry at `add()` time, or pass a rate table into `total_usd()`. That's an API change to your invoicing service, so I left it alone — say the word and I'll do it.
