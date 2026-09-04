Done. Here's the full picture.

## Short answer
**No, it's not a flaky test — don't retry it.** It fails deterministically (10 cents high, every time) whenever the full suite runs, and passes whenever the file runs alone. That's not randomness; it's a deterministic ordering bug. Retrying in CI would just keep failing.

## What was actually wrong
The money rounding code is fine. The culprit is **global state leaking between test files**:

1. `rates.py` keeps a module-level `_RATE_CACHE` dict. There's a `set_rate()` to mutate it and a `reset_rates()` to restore it — but nothing forces tests to reset.
2. `test_conversion.py::test_set_rate_accepts_high_precision` calls `set_rate("EUR", "1.1001")` and **never resets it**.
3. Test files run alphabetically, so `test_conversion` runs *before* `test_ledger`. By the time `test_multi_currency_total` runs, EUR is stuck at `1.1001`.
4. So the total computes as `500 + 1000 × 1.1001 = 1600.10` — exactly 10 cents high. Run the file alone and the leak never happens, which is why it looked green.

I verified this end to end: full suite gives `Decimal('1600.10') != Decimal('1600.00')`; the leaked-rate arithmetic reproduces `1600.10` exactly; and `grep` confirms `reset_rates()` is only ever defined, never called in tests.

## The fix
One line of isolation in the test that owns the global mutation — `test_conversion.py` now calls `rates.reset_rates()` in `setUp()` so it can't bleed into other files. I left `money.py` untouched; it was innocent.

## Evidence
- Full suite: **9/9 pass**, was failing before.
- Ran the suite 5× in a row: all `OK` (deterministic, not flaky).
- Each file individually: all `OK`.
- Removed my backup file; nothing left dirty.

## Sibling check
I searched for other tests mutating shared state — `grep` shows `reset_rates()` is only defined in `rates.py`, never called anywhere else. `test_money` and `test_ledger` don't touch the global cache, so there are no other offenders in this suite.

One thing worth flagging for the future: `rates.py`'s module-level cache is a latent footgun — any future test that calls `set_rate` and forgets to reset will cause the same silent cross-file bleed. If you want, I can add a `tearDown`/module-level guard so the cache auto-resets after every test and this class of bug becomes impossible. Say the word.