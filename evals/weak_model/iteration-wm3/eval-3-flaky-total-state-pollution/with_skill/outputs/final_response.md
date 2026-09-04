Done. Here's the full picture.

## Short answer
**No, it is not a flaky test.** It fails *every* full-suite run and passes *every* isolated run — that's a deterministic fingerprint, not randomness. Retrying in CI won't help; it'll stay red until the root cause is fixed. I found and fixed it.

## What was actually wrong
The money rounding code is fine — your instinct to distrust it was a red herring. The bug is **test-order state pollution** via a process-wide global:

1. `rates.py` keeps a module-level `_RATE_CACHE` dict. `set_rate()` mutates it in place.
2. `test_conversion.py::test_set_rate_accepts_high_precision` calls `set_rate("EUR", "1.1001")` and **never restores it**.
3. `unittest` runs tests alphabetically, so `test_conversion` runs before `test_ledger`. The leaked `EUR=1.1001` then applies to the ledger test: `1000 EUR × 1.1001 = 1100.10`, so the total comes out **1600.10 — exactly 10¢ high**.

I reproduced it and proved the mechanism:
- Full suite: `AssertionError: Decimal('1600.10') != Decimal('1600.00')`
- Isolated `test_ledger`: passes
- One-process simulation (conversion → ledger): reproduces the 10¢, with `get_rate("EUR")` showing `1.1001` at the point the ledger test runs.

## The fix
Added `setUp`/`tearDown` to `test_conversion.py` that call `rates.reset_rates()` before and after each test, so the runtime override can't leak into the ledger suite. This is the same approach the sibling `without_skill` copy already had, but this `with_skill` copy had the helper available and never wired it in.

## Verification (all real runs)
- Full suite, default order: **OK** (9 tests)
- Full suite, reverse order: **OK**
- Each test file isolated: **OK**
- One-process leak simulation after the fix: `EUR` rate back to `1.10`, ledger test passes
- Committed as `6784b3d`

## One thing I'm flagging but not fixing (out of scope)
While sanity-checking `round_money`, I noticed `round_money(Decimal("1600.005"))` → `1600.00`. The docstring says "half away from zero," but `Decimal.round` uses banker's rounding (`ROUND_HALF_EVEN`), so half-cents round to even. That's a **separate latent bug** unrelated to the red test — I left it alone since it doesn't affect this task, but you'll want a ticket for it if invoicing correctness is the point of the module.

The sibling `without_skill/repo` copy already had this fix (it's the HEAD commit in the parent repo), so the two are now consistent.