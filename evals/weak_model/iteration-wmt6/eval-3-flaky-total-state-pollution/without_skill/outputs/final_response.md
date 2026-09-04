Done. Here's the full picture.

## Short answer: not flaky — don't retry it.

Retrying in CI would never have fixed this. The failure is **deterministic**: `test_multi_currency_total` fails *every time* it runs after `test_conversion`, and passes *every time* it runs alone. That's the signature of **global state pollution between test files**, not a race condition or timing flake.

## What was actually wrong

Your money rounding code is fine. The bug was in `rates.py` + `test_conversion.py`:

- `rates` keeps its FX table in a **module-global** `_RATE_CACHE`.
- `test_conversion.TestConversion.test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` and **never restores it**.
- `unittest discover` runs `test_conversion` *before* `test_ledger`. So when the multi-currency test runs, EUR is still `1.1001`, giving `500 + 1000×1.1001 = 1600.10` — exactly **10 cents high**.
- Run in isolation, `test_conversion` never runs first, so EUR stays at the published `1.10` and the test passes.

That's why it "passes on its own, fails in CI" and why you couldn't see anything wrong in the rounding.

## The fix

I made the conversion test clean up after itself so it can't leak into other files regardless of ordering. In `test_conversion.py` I added `setUp`/`tearDown` that call `rates.reset_rates()`:

```python
def setUp(self):
    # FX rate table is module-global mutable state; start from the
    # published table so it can't leak into other test files.
    rates.reset_rates()

def tearDown(self):
    # Restore the published table so a runtime override doesn't
    # persist into the next test.
    rates.reset_rates()
```

I put the fix in the test that mutates the shared state (the right place to own cleanup), rather than papering over it in the ledger or money code.

## Verification

- Full discovery run: **OK** (9 tests)
- Isolated `test_ledger`: **OK**
- Reversed order (`test_ledger` first): **OK**
- `test_conversion` → `test_ledger`: **OK**

The suite is now order-independent. Worth noting: this same global-cache pattern could bite other tests later, so if you want belt-and-suspenders I'd consider having `set_rate`/`to_usd` operate on a per-call basis — but the fix above is the minimal, correct change for what's here.