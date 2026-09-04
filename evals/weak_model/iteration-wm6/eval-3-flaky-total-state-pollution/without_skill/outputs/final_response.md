Fixed and verified. Here's the full story.

## It's not flaky — it's test-order-dependent state pollution

Your instinct that the money rounding code looked fine was correct; the bug was never in `round_money`. The 10-cent discrepancy is a **deterministic** failure that only appears when tests run together, which is exactly why it's so easy to miss.

**The chain of events:**

1. `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")` to verify the FX job's 4-dp rates survive.
2. `set_rate` mutates a **module-level global** (`_RATE_CACHE`) and the test never resets it.
3. When the whole suite runs, pytest collects files alphabetically, so `test_conversion.py` runs *before* `test_ledger.py`. EUR stays pinned at `1.1001`.
4. `test_multi_currency_total` computes `1000 EUR × 1.1001 = 1100.10`, giving a total of `1600.10` — **exactly 10 cents high**.
5. Run the ledger test on its own, the cache is clean (`1.10`), and it passes. That's the "passes alone, fails in CI" pattern.

**Why not just retry it?** No — a retry would mask it, not fix it. The failure is 100% reproducible in CI given the collection order; it's not random. Retrying would just make CI look green while the real bug (a stale global FX rate) could still bite production tooling or other test runs.

## The fix

I made `test_conversion.py` clean up after itself with `setUp`/`tearDown` that call `rates.reset_rates()`, so the runtime override can never leak into other test files:

```python
def setUp(self):
    rates.reset_rates()

def tearDown(self):
    rates.reset_rates()
```

I confirmed:
- Full suite: **9 passed** (was 1 failed)
- `test_conversion.py` → `test_ledger.py` in that order: passes
- Ledger test alone: passes
- Repeated/odd orderings: all pass

## Worth considering

- **`reset_rates()` already existed** in `rates.py` but was unused — the fix just puts it to work. If you'd rather not touch the test, the alternative is making `set_rate`/`to_usd` not depend on mutable global state, but that's a bigger refactor than a test-ordering bug warrants.
- **CI collection order isn't guaranteed.** If you ever run tests in parallel or with a plugin that changes ordering, this could resurface. If you want belt-and-suspenders, I can add `reset_rates()` to a shared `setUp`/conftest so *every* test file starts from a clean FX table. Want me to do that?

Bottom line: not flaky, fixed at the source, CI should be green now.