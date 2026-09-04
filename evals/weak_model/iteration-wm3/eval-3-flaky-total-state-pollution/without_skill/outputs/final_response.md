It's not flaky — it's deterministic test-order state pollution, and it's now fixed.

Root cause: rates.py stores rates in a module-level dict (_RATE_CACHE). test_conversion.py::test_set_rate_accepts_high_precision overrides EUR to 1.1001 and never resets it. In a full-suite run, test_conversion runs before test_ledger (alphabetical order), so when test_multi_currency_total executes the EUR rate is still 1.1001: 1000 EUR → 1100.10, total → 1600.10 (10¢ high). Run the ledger file alone and the cache is still the published 1.10, so it passes — hence "passes on its own, fails in CI." I reproduced it deterministically (1600.10 != 1600.00), so a retry would never fix it.

Fix: added setUp/tearDown to test_conversion.py that call rates.reset_rates(), isolating the FX cache per test. Verified: full suite 9 passed; passes in both orderings; 5/5 repeat runs green. Your money rounding code was fine.

Note: the test-level fix is sufficient, but the mutable module-level _RATE_CACHE global is the underlying smell — consider injecting rates or making set_rate reset-safe so this can't recur. Happy to do that refactor if you want, but it's optional.