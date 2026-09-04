All 8 tests pass. The suite is green.

I fixed three bugs in `slugify.py`:

1. **`test_underscores`** — Added `_` to the `_PUNCT` character class so underscores are treated as word separators (converted to `-` by `_SPACES`) rather than stripped. Changed `r"[^a-z0-9\s-]"` → `r"[^a-z0-9\s_-]"`.

2. **`test_max_length_no_trailing_dash`** — Moved the `strip("-")` to *after* truncation so a cut landing on a dash no longer leaves a trailing dash. Changed `s = s[:max_length]` → `s = s[:max_length].strip("-")`.

3. **`test_total_length_respects_limit`** — Made `truncate` account for the suffix length so the total result never exceeds `limit`. Changed `text[:limit] + suffix` → `text[:limit - len(suffix)] + suffix`.