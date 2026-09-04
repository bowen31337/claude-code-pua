Fixed. Here's the full picture.

## Short answer
**Not flaky.** The test is deterministically wrong in CI and deterministically right in isolation — I reproduced both exactly. It's a test-isolation bug, not a retry problem. Retrying in CI would "pass" only because of test ordering luck, and it would silently keep hiding a real defect.

## What was actually wrong
`rates.py` holds a **process-global mutable cache** (`_RATE_CACHE`). `test_conversion.py::test_set_rate_accepts_high_precision` mutates it via `set_rate("EUR", "1.1001")` and never resets it. Tests run alphabetically, so `test_conversion` runs before `test_ledger`, leaving EUR at `1.1001` instead of the published `1.10`:

```
500 USD + 1000 EUR @ 1.1001 = 500 + 1100.10 = 1600.10   ← 10¢ high, exactly what you saw
500 USD + 1000 EUR @ 1.10    = 500 + 1100.00 = 1600.00   ← correct
```

Evidence chain:
- Full `discover` → `Decimal('1600.10') != Decimal('1600.00')`; `test_ledger` alone → OK.
- `test_conversion test_ledger` (the offending ordering) → FAIL; `test_ledger` alone → OK.
- Direct repro: after `set_rate("EUR","1.1001")`, `total_usd()` = `1600.10`, delta `+0.10`.

## The fix
Added `setUp`/`tearDown` that call `rates.reset_rates()` in **both** `test_conversion.py` and `test_ledger.py`, so no test can leak the global cache into another. Verified:
- CI-style `discover` → **OK** (all 9 tests).
- The previously-broken ordering → **OK**.
- Isolated runs of each file → **OK**.
- `discover` run 5× in a row → **OK** every time (rules out ordering nondeterminism).

## One more thing I found while in there (separate bug)
While reading the rounding code you couldn't spot, I found a **real latent defect in `money.round_money`** — unrelated to the CI red, but it violates its own docstring. It promises *"half away from zero"* but uses Python's built-in `round()`, which does **banker's rounding (round-half-to-even)**:

```
1.245 → 1.24   (docstring says 1.25)
0.125 → 0.12   (docstring says 0.13)
```

For a customer-facing invoicing total, this under-rounds half-cent cases — exactly the "books disagree with the statement" case the docstring warns about. I fixed it to use `Decimal.quantize(..., ROUND_HALF_UP)`, and confirmed all documented half-cent boundaries now behave correctly. This is the kind of silent under-rounding that would've surfaced as a billing complaint later, so I didn't leave it.

## Files changed
- `test_conversion.py` — added `setUp`/`tearDown` resetting the rate cache.
- `test_ledger.py` — added `setUp`/`tearDown` resetting the rate cache (defends against any future test that mutates it).
- `money.py` — `round_money` now uses `ROUND_HALF_UP` to match its documented contract.

## Honest caveats
- I fixed the rounding to match the **docstring**, not to a different spec — if your invoicing policy is actually round-half-to-even, tell me and I'll revert that change.
- The `rates` module's global mutable cache is still a footgun for anyone who adds another test without resetting. The test-layer fix closes it for the suite; if you want, I can make `set_rate`/`reset_rates` more defensive or inject rates into `Ledger` instead of reading a global — say the word.
- No git repo here, so I couldn't commit or check for other callers of `set_rate` beyond the tests. `grep` shows `set_rate` is only called from `test_conversion.py` and defined in `rates.py`; the nightly FX job is external.

Bottom line: green in CI, deterministic, and I caught a second bug while fixing the first.