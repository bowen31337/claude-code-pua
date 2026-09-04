Everything passes, deterministically, regardless of test order. Here's the bottom line.

## It was not flaky — it was state pollution

**Don't retry it in CI.** A retry masks the failure with luck, but this bug is fully deterministic and would reappear the moment test ordering changes (parallel runners, a new module that sorts earlier, etc.). That's the trap with state pollution: it *looks* flaky but is actually a landmine.

**What was actually wrong** (nothing in the money rounding code — your instinct was right):

1. `rates.py` holds a module-level `_RATE_CACHE` dict. `set_rate()` mutates it in place, and nothing ever resets it.
2. `test_conversion.py::test_set_rate_accepts_high_precision` deliberately sets `EUR → 1.1001` and **never restores it**.
3. `unittest discover` runs modules alphabetically, so `test_conversion` runs *before* `test_ledger`. By the time `test_multi_currency_total` runs, EUR is stuck at `1.1001`.
4. Result: `500 + 1000 × 1.1001 = 1600.10` — **exactly 10 cents high, every time.**

Run `test_ledger.py` alone and `test_conversion` never runs, so EUR stays at `1.10` and the test passes. That's the isolation-vs-suite discrepancy you were seeing.

**The fix** — `test_conversion` is the test that leaks shared global state, so it owns the cleanup. I added a `setUp`/`addCleanup` that calls the existing `rates.reset_rates()` after every test in that module:

```python
def setUp(self):
    self._cleanup = rates.reset_rates
    self.addCleanup(self._cleanup)
```

I deliberately scoped the fix to the polluting test rather than "fixing" `test_multi_currency_total` to expect `1600.10` — that assertion is correct, and the default rate of `1.10` is the published FX table. The bug was the leaked override, not the test's expectation.

**Verification:** full suite passes, isolated runs pass, 5 consecutive runs all pass, and it passes even in reverse test order. The EUR cache is clean after `test_conversion` runs.

One thing worth flagging for you: the same `_RATE_CACHE` mutation pattern exists in production via `set_rate` (the nightly FX job / ops tooling). If any long-lived process caches rates without ever calling `reset_rates`, a stale override could leak into real totals the same way. Worth a quick look, but that's separate from the CI red you reported.