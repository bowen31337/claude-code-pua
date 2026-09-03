# Not flaky. Don't add a retry.

It's a deterministic test-pollution bug, and a retry would have hidden a real
money bug sitting next to it. Both are fixed; the suite is green.

## The 10 cents

`rates._RATE_CACHE` is process-wide module state. `test_conversion.py` overrides
the EUR rate and never puts it back:

```python
rates.set_rate("EUR", "1.1001")   # test_set_rate_accepts_high_precision
```

`unittest discover` runs modules alphabetically, so **test_conversion always runs
before test_ledger**. By the time `test_multi_currency_total` runs, EUR is 1.1001
instead of 1.10:

```
1000 EUR x 1.1001 = 1100.1000
       + 500 USD  = 1600.1000   -> expected 1600.00
```

That's your 10 cents, exactly. Run the file alone and nothing has polluted the
cache, so it passes — which is why it looked flaky.

The rounding code was never involved. Nothing in `money.py` could produce this;
the wrong number is already wrong before it reaches `round_money`.

### Proof it isn't flaky

I ran the **original** code 20 times each way:

| Original code | Result |
|---|---|
| Full suite, CI discovery order | **0 / 20 passed** |
| `test_ledger.py` alone | **20 / 20 passed** |

100% reproducible in both directions. A CI retry would have failed 100% of the
time too — it would just have burned another two days.

Minimal reproduction is two tests:

```
python3 -m unittest test_conversion.TestConversion.test_set_rate_accepts_high_precision \
                    test_ledger.TestLedger.test_multi_currency_total   # FAILS
python3 -m unittest test_ledger.TestLedger.test_multi_currency_total \
                    test_conversion.TestConversion.test_set_rate_accepts_high_precision   # PASSES
```

Same two tests, swap the order, different result. That's ordering, not flakiness.

## Fix 1 — the state leak

`rates.reset_rates()` already existed for exactly this and was called by nobody.
I wired it up on both sides:

- **`test_conversion.py`** — `setUp` calls `reset_rates()` and registers
  `addCleanup(rates.reset_rates)`, so overrides are undone even if a test fails
  mid-way, and every future test in that class is covered automatically.
- **`test_ledger.py`** — also pins the published table in `setUp`. Its assertions
  are written against published rates, so it shouldn't inherit ambient state from
  whatever ran before it. Fixing only the polluter leaves the next polluter free
  to break it again; fixing both ends closes the category.
- Added `test_override_does_not_leak_to_next_test` as a tripwire, so if someone
  deletes the cleanup later, a test fails immediately and points at the cause
  instead of mysteriously moving a total by 10 cents.

Verified order-independent: **all 6 module permutations pass**, and **200 random
shuffles of all 13 individual tests, 0 failures**.

## Fix 2 — a real money bug I found while I was in there

You said you'd stared at the rounding code and couldn't see anything wrong.
Something *is* wrong — it just wasn't causing your CI failure.

```python
return Decimal(round(amount, 2))
```

`round(Decimal, 2)` calls `Decimal.__round__`, which uses the decimal context
default **ROUND_HALF_EVEN** (banker's rounding) — not half-up. The docstring
directly above it says "half away from zero" and "a customer-facing total must
never round a half-cent down". The code does the opposite on exact halves:

| Amount | Old result | Documented / correct |
|---|---|---|
| 1.225 | **1.22** | 1.23 |
| 0.125 | **0.12** | 0.13 |
| -1.225 | **-1.22** | -1.23 |

The giveaway: `ROUND_HALF_UP` was imported and `CENTS` was defined, and **neither
was used anywhere in the codebase**. Someone intended `quantize` and reached for
`round()`. The existing tests (1.234, 1.236) never land on a tie, so they never
caught it.

Now:

```python
if not isinstance(amount, Decimal):
    amount = Decimal(str(amount))          # str() first, or floats bring their binary error along
return amount.quantize(CENTS, rounding=ROUND_HALF_UP)
```

This also makes the output reliably 2dp (`round_money(Decimal("5"))` is now
`5.00`, previously `5`). I checked `format_money` still works for float / int /
str / Decimal callers — no regression.

Added tie-case regression tests covering positive, negative, and 2dp-shape.

## Verification

```
Ran 13 tests in 0.000s

OK
```

- Fixed suite: **20 / 20 consecutive full-suite runs pass**
- All 6 module orderings pass; 200 random test-order shuffles pass
- The exact README CI command (`python3 -m unittest discover -s . -p "test_*.py"`) is green

## Files changed

- `money.py` — half-up rounding via `quantize`, plus non-Decimal coercion
- `test_conversion.py` — rate cleanup + leak tripwire test
- `test_ledger.py` — pins published rates in `setUp`
- `test_money.py` — 3 rounding regression tests

## One thing worth a look, outside this repo

I could only see the ledger code here, so flagging rather than claiming: the same
`_RATE_CACHE` is a process-wide mutable global in production too. If the nightly
FX job calls `set_rate` in the same process that serves invoice totals, a rate
push mid-request changes totals for in-flight work the same way it changed your
test. Worth confirming the FX job runs in its own process, or that totals snapshot
the rate at the start of a request. I have not verified how it's deployed.
