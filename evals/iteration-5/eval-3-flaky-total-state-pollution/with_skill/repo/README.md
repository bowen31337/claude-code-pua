# ledger

Multi-currency ledger used by the invoicing service.

    python3 -m unittest discover -s . -p "test_*.py"

`money.round_money` is the single rounding chokepoint — every customer-facing
total goes through it. `rates` holds the published FX table; the nightly FX job
calls `set_rate` to push updates.

## Test isolation

`rates._RATE_CACHE` is process-global module state. Any test that calls
`set_rate` must restore it (`self.addCleanup(rates.reset_rates)`), and any
test asserting on converted totals should pin the table in `setUp`. A missing
cleanup here shows up as an order-dependent failure in a *different* test file.
