Not flaky. Don't add a retry — a retry would have hidden a real bug and CI would have gone green while lying to you.

## What's actually happening

`test_multi_currency_total` fails **100% of the time** in a full run and passes **100% of the time** alone. That's not randomness, that's test *order dependence*. The deciding factor is which tests ran before it in the same process.

The culprit is three files away from where you were looking:

```python
# test_conversion.py
def test_set_rate_accepts_high_precision(self):
    rates.set_rate("EUR", "1.1001")     # writes to a process-global dict, never undone
```

`rates._RATE_CACHE` is module-level global state. `set_rate` mutates it permanently, and that test never restores it. Under `unittest discover`, modules run alphabetically — `test_conversion` before `test_ledger` — so by the time the ledger test runs, EUR is still pinned at `1.1001` instead of the published `1.10`:

```
1000 EUR x 1.1001 = 1100.10   (instead of 1100.00)
500 + 1100.10     = 1600.10   -> exactly your 10 cents
```

Ten cents, exactly, every time. That's the signature of a wrong rate, not a rounding error — which is why staring at the rounding code turned up nothing. The rounding code was innocent.

I confirmed the causal chain by running the two modules in both orders:

```
test_ledger test_conversion   -> OK        (ledger runs first, clean state)
test_conversion test_ledger   -> FAILED    (pollution flows downhill)
```

## The fix

The test that dirties global state is responsible for cleaning it. `rates.py` already shipped a `reset_rates()` helper for exactly this and nobody was calling it. Added to `test_conversion.py`:

```python
class TestConversion(unittest.TestCase):
    def setUp(self):
        # rates._RATE_CACHE is process-global module state. Restore the
        # published table around every test so overrides made here cannot
        # leak into tests that run later in the same process.
        rates.reset_rates()

    def tearDown(self):
        rates.reset_rates()
```

`setUp` as well as `tearDown` — that way this suite is also immune to anyone *else* polluting the cache later, not just prevented from causing it.

## Verification

- All **6** module permutations: green (was 3/6 failing before).
- `unittest discover` 20 consecutive runs: 0 failures.
- `pytest`: 9 passed.

I deliberately did not touch `ledger.py` or `money.py`. The production code was correct; the test was lying about it.

## One separate thing worth your attention

While ruling out the rounding code I found a genuine latent bug in it. **This is not what broke CI**, and I have not changed it — it alters customer-facing money behavior, so it's your call:

```python
# money.py
from decimal import Decimal, ROUND_HALF_UP   # imported, never used
CENTS = Decimal("0.01")                      # defined, never used

def round_money(amount):
    """Round a monetary amount to 2 places, half away from zero. ..."""
    return Decimal(round(amount, 2))         # <-- this is ROUND_HALF_EVEN
```

Python's `round()` on a `Decimal` does banker's rounding (half-to-even), which is **not** what the docstring promises. The unused `ROUND_HALF_UP` import and unused `CENTS` constant strongly suggest the intended body was `amount.quantize(CENTS, rounding=ROUND_HALF_UP)`. Real divergence today:

```
0.005 -> 0.00   (half-up: 0.01)
1.225 -> 1.22   (half-up: 1.23)
1.245 -> 1.24   (half-up: 1.25)
```

Per your own docstring ("a customer-facing total must never round a half-cent down, or the books disagree with the statement"), the current behavior is exactly the failure mode you were guarding against. No existing test covers a true half-cent case, so this is silently unverified. The fix is one line, but it changes invoice totals, so it likely wants a deliberate decision and possibly a backfill review rather than me slipping it into a CI-green commit. Say the word and I'll do it with tests covering the half-cent cases.

## Takeaway for CI

If it were flaky, retrying would be the wrong instinct anyway — but here the "flakiness" was 100% reproducible information pointing at real shared-state leakage. Worth adding `pytest-randomly` (or randomized `unittest` ordering) so order-dependent bugs like this surface immediately in the offending PR instead of two days later.
