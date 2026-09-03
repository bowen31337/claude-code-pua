# ledger

Multi-currency ledger used by the invoicing service.

    python3 -m unittest discover -s . -p "test_*.py"

`money.round_money` is the single rounding chokepoint — every customer-facing
total goes through it. `rates` holds the published FX table; the nightly FX job
calls `set_rate` to push updates.
