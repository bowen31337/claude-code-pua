# ledger

Multi-currency ledger used by the invoicing service.

    python3 -m unittest discover -s . -p "test_*.py"

`money.round_money` is the single rounding chokepoint — every customer-facing
total goes through it. It rounds half **away from zero** (`ROUND_HALF_UP`), not
with Python's built-in `round()`, which is half-to-even and would round
half-cents down.

`rates` holds the published FX table; the nightly FX job calls `set_rate` to
push updates.

## Global FX state and tests

`rates._RATE_CACHE` is process-global. `set_rate()` mutates it for the lifetime
of the process, so an override made in one test leaks into every test that runs
afterwards — including tests in other files. That is invisible when you run a
file on its own and only shows up in full-suite runs, where it looks like
flakiness but is actually strict test-ordering dependence.

Rules:

- In tests and one-off ops work, prefer `rates.rate_override(code, rate)` — a
  context manager that restores the previous value on exit, including on
  exception.
- Any test class that reads or writes rates should pin the table in `setUp`:

      def setUp(self):
          rates.reset_rates()
          self.addCleanup(rates.reset_rates)
