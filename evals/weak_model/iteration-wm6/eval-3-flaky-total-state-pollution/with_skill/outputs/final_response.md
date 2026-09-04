**It is not flaky.** I reproduced the CI failure deterministically and found the root cause. The 10-cent error is a test-ordering bug, not a coin-flip.

## What I found

**Reproduced the exact failure.** Running the full suite gives `Decimal('1600.10') != Decimal('1600.00')` — precisely 10 cents high, matching your CI. Running `test_ledger.py` alone passes, also matching.

**It's deterministic, not random.** It fails *only* when `test_conversion.py` runs before `test_ledger.py`:
- `conversion → ledger` → **fails** (1600.10)
- `ledger → conversion` → **passes**
- `ledger` alone → **passes**

**Root cause: leaked global state in the FX rate cache.** `rates.py` keeps published rates in a module-level dict (`_RATE_CACHE`) that `set_rate()` mutates in place. `test_conversion.py::test_set_rate_accepts_high_precision` sets `EUR` to `1.1001` and **never restores it** (there's no `reset_rates()` call, and no `conftest.py` to isolate tests). So once that test runs, EUR stays at 1.1001 for the rest of the session:

```
500 USD + 1000 EUR @ 1.1001 = 500 + 1100.10 = 1600.10   ← 10¢ high
```

I confirmed this directly: after `set_rate("EUR","1.1001")`, the ledger total is exactly `1600.10`. This is why it "passes on its own" — the pollution only happens when another test file runs first, which is why it looks flaky but isn't.

## The fix

Added `conftest.py` that resets the FX cache before and after **every** test, isolating each test from the shared cache regardless of order:

```python
import pytest
import rates

@pytest.fixture(autouse=True)
def _reset_fx_rates():
    rates.reset_rates()
    yield
    rates.reset_rates()
```

`reset_rates()` already existed in `rates.py` for exactly this purpose — it was just never wired into the test suite. Verified: full suite passes 3× in a row, the previously-failing order passes, and ledger-alone still passes.

## One thing I want to flag (separate from the CI failure)

While investigating, I found a **latent bug in `round_money`** that is *not* what's breaking CI. It uses Python's built-in `round()` (banker's rounding + float), which contradicts its own docstring ("half away from zero"):

```
round_money(Decimal("1.245")) → 1.24   (half-up should be 1.25)
```

It happens to not affect the multi-currency test (the numbers there don't hit a rounding half), so it's not your red CI — but it's a real invoicing-correctness bug that will bite later. I did **not** change `money.py`, since it's out of scope for this ticket. Say the word and I'll fix it properly (it should use `Decimal.quantize(Decimal("0.01"), ROUND_HALF_UP)`).

## Bottom line
- Not flaky — deterministic state pollution. Don't just retry in CI; it will keep failing whenever conversion runs first.
- Fixed with the `conftest.py` isolation above.
- Sibling latent bug in `round_money` flagged but left untouched pending your go-ahead.

Files touched: `conftest.py` (new). Nothing else changed.