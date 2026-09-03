Not flaky. Don't add a retry — a retry would have hidden a real bug and CI would have gone green while staying wrong. The failure is 100% deterministic; it just needs a second test file in the process to show up.

## What's actually happening

`test_conversion.py` has this test:

```python
def test_set_rate_accepts_high_precision(self):
    rates.set_rate("EUR", "1.1001")
```

`set_rate` writes into `rates._RATE_CACHE`, a module-level dict that lives for the whole process. That test never puts it back. `unittest discover` walks files alphabetically, so `test_conversion` runs before `test_ledger`, and by the time `test_multi_currency_total` runs, EUR is 1.1001 instead of the published 1.10.

1000 EUR x 0.0001 = **exactly your 10 cents**. Run the file alone and nothing has polluted the cache yet, so it passes every time — which is why isolation "proved" it was flaky.

Ironically `rates.py` already ships `reset_rates()` for exactly this purpose. Nothing in the test suite ever called it, and there wasn't a single `setUp`/`tearDown`/`addCleanup` in the repo.

Proof, before I changed anything:

```
python3 -m unittest test_conversion test_ledger   -> FAILED (failures=1)
python3 -m unittest test_ledger test_conversion   -> OK
test_ledger alone, 5 runs                         -> OK OK OK OK OK
```

and the 8-line minimal repro:

```
EUR rate at import: 1.10
EUR rate after that test: 1.1001
total: 1600.10
```

## The second bug — the rounding code you were staring at

You were right to be suspicious of it. It *is* wrong; it just isn't what broke CI.

```python
return Decimal(round(amount, 2))
```

The docstring promises half away from zero, "a customer-facing total must never round a half-cent down". But builtin `round()` on a `Decimal` defers to the decimal context, which defaults to **ROUND_HALF_EVEN** (banker's rounding). The `ROUND_HALF_UP` import and the `CENTS` constant at the top of the file were both sitting there unused — someone started this and never finished it.

Measured against the stated contract:

```
round_money(1.005) = 1.00   | should be 1.01
round_money(1.025) = 1.02   | should be 1.03
round_money(0.125) = 0.12   | should be 0.13
```

Also, floats survived into the result unfiltered:

```
round_money(1.235) = Decimal('1.2399999999999999911182158029987476766109466552734375')
```

The two existing rounding tests (1.234, 1.236) never hit a tie, so they could never catch this. Every half-cent tie in your invoicing has been rounding in the customer's favour and against the books — the exact failure mode the docstring warns about.

## What I changed

1. **`test_conversion.py`** — `setUp` now calls `rates.reset_rates()` and registers `self.addCleanup(rates.reset_rates)`, so an override cannot escape the test that made it (cleanup runs even on failure/exception). Added a test that `reset_rates()` genuinely restores the table, since isolation now depends on it.
2. **`test_ledger.py`** — same pin in `setUp`. Defence in depth: these tests assert against the published table, so they should not silently depend on which file ran first.
3. **`money.py`** — `round_money` now does `amount.quantize(CENTS, rounding=ROUND_HALF_UP)`, using the constants that were already imported, and routes non-Decimal input through `str()` so float artifacts can't leak. Added a comment explaining why builtin `round()` is not equivalent, so this doesn't get "simplified" back.
4. **`test_money.py`** — tests for half-cent ties (positive and negative), 2-place quantization, and float input.
5. **`README.md`** — documented the isolation rule for `_RATE_CACHE`.

## Verification

Full suite, the exact CI command from the README:

```
Ran 14 tests in 0.000s

OK
```

All 6 orderings of the three test modules — this is the one that matters, since order was the bug:

```
test_conversion test_ledger test_money  -> OK
test_conversion test_money test_ledger  -> OK
test_ledger test_conversion test_money  -> OK
test_ledger test_money test_conversion  -> OK
test_money test_conversion test_ledger  -> OK
test_money test_ledger test_conversion  -> OK
```

30 consecutive full-suite runs: `runs=30 failures=0`.

I also checked the new tests actually fail against the old code, because a regression test that passes on the broken version is worthless. New `test_money.py` against the original `round_money`: `FAILED (failures=3)` on 1.005, -1.005, and the float case.

And I planted a rogue test that calls `set_rate` with no cleanup and forced it to run before the ledger tests — the ledger tests still pass, so a future careless test can't re-break this the same way.

(One note on process: my first attempt at that old-code comparison reported a false OK because the shell's working directory reset between commands and it silently tested the new code. I caught it, re-ran it in the right directory, and the numbers above are from the corrected run.)

## Worth a follow-up

- **Check whether the half-cent bug reached production invoices.** If `round_money` has been live, any total landing exactly on a half-cent was rounded down. Depends how long it's been shipping and whether your reconciliation would have flagged sub-cent drift.
- **`ROUND_HALF_UP` is a policy decision.** I implemented what the docstring specifies. If your accountants actually want banker's rounding, the fix is to change the docstring and my tests, not to go back to builtin `round()` — the current explicitness is right either way.
- **Consider making the global cache harder to abuse.** The real root cause is that `rates` exposes process-wide mutable state with no scoping. A context manager (`with rates.overridden(EUR="1.1001"):`) or passing a rate table into `total_usd` would make this class of bug structurally impossible rather than convention-dependent. I didn't do it because it changes the public API that the nightly FX job calls — your call.
- **Add ordering pressure to CI.** Something like `pytest-randomly`, or just running the suite in a couple of different module orders, would catch the next order-dependent leak on the commit that introduces it instead of two days later.
