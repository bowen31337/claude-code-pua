All 7 files present, backup cleaned up. The `ls` builtin is misbehaving in this shell, but `find` confirms the repo is in its final state.

Here's the full report.

---

## It's not flaky — it's deterministic state pollution. Retrying in CI won't fix it.

I reproduced the exact failure and traced it. The total is 10¢ high because a **different test file mutates the shared FX rate table and never resets it**, and `unittest discover` happens to run that file *before* the ledger test.

### The chain (verified with output)

1. `test_conversion.py::test_set_rate_accepts_high_precision` calls `rates.set_rate("EUR", "1.1001")`. That writes into the **module-global** `_RATE_CACHE` — the same published FX table `ledger.total_usd()` reads. The test asserts the value but **never restores it**.
2. `unittest discover` loads files alphabetically: `test_conversion` → `test_ledger`. So when `test_multi_currency_total` runs, the live EUR rate is `1.1001`, not `1.10`.
3. `1000 EUR × 1.1001 = 1100.10` → total `1600.10`. **Exactly 10¢ high.**

I proved each link:

```
EUR rate before anything: 1.10
EUR rate after set_rate(1.1001): 1.1001
Ledger total with leaked rate: 1600.10
```

And confirmed the order:

```
test_conversion.TestConversion.test_set_rate_accepts_high_precision   ← mutates global rate
test_ledger.TestLedger.test_multi_currency_total                      ← reads it, fails
```

That's why it passes in isolation: run `test_ledger` alone, the cache starts clean at `1.10` → `1600.00`. In CI the leak precedes it. It's **deterministic**, not random — "retry" is the wrong tool.

### The fix (one line, in the leaking test)

```python
def test_set_rate_accepts_high_precision(self):
    self.addCleanup(rates.reset_rates)   # <-- added: undo the global mutation
    rates.set_rate("EUR", "1.1001")
    self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))
```

`addCleanup` guarantees the published table is restored after the test, regardless of pass/fail. This is the right place to fix it — the test that owns the mutation should clean it up, not the test that suffers from it.

### Verification (all real output)

- Full suite (`python3 -m unittest discover`): **OK**, 3 consecutive runs — no more `1600.10`.
- `test_conversion test_ledger` and reversed `test_ledger test_conversion`: **OK both ways** — robust to ordering.
- Confirmed the cache is back to `1.10` after `test_conversion` runs.

### One thing I found while I was in there — flagging, not fixing

You said you'd been staring at `money.py`'s rounding and couldn't see the bug. **The rounding code is actually fine for the failing test** (the failure is in the FX table, not the rounding). But I stress-tested `round_money` against its own docstring — *"half away from zero"* — and it's **wrong**:

```
amount   round_money  half-away(quantize)  match?
  1.245           1.24                 1.25      False   ← rounds DOWN
  1.225           1.22                 1.23      False   ← rounds DOWN
  0.125           0.12                 0.13      False   ← rounds DOWN
```

`round_money` calls Python's built-in `round()`, which does **banker's rounding** (round-half-to-even), directly contradicting the docstring that says half-away-from-zero. The test suite doesn't catch it because none of the test inputs hit a true half-cent. This is a **latent invoicing bug** — a real 0.5¢ that would under-collect — but it's unrelated to the CI red. I left `money.py` untouched since it's out of scope for the ticket; say the word and I'll fix it (`.quantize(Decimal("0.01"), ROUND_HALF_UP)`) and add a half-cent test so it can't regress.

### Bottom line
- **Not flaky.** Deterministic order-dependent state leak. Don't retry.
- **Fixed** in `test_conversion.py` (one line). Full suite green, verified repeatedly and across orderings.
- **Bonus:** `money.py` has a real rounding bug that the tests currently miss — flagged, not changed.