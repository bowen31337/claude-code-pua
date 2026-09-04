The test suite is now green — all 8 tests pass (previously 3 failures).

I fixed three bugs in `slugify.py`:

1. **test_underscores** — The `_PUNCT` regex `[^a-z0-9\s-]` was stripping underscores *before* the space-replacement step could turn them into dashes. I added `_` to the allowed set: `[^a-z0-9\s_-]`, so `hello_world` → `hello-world`.

2. **test_max_length_no_trailing_dash** — Slicing at `max_length` could leave a trailing dash (e.g. `the-quick-brown`[:10] → `the-quick-`). I added `.strip("-")` after the slice so it becomes `the-quick`.

3. **test_total_length_respects_limit** — `truncate` returned `text[:limit] + suffix`, which could exceed the limit (e.g. `truncate("abcdefghij", 8)` → `abcdefgh...` = 11 chars). I now reserve space for the suffix: `text[:limit - len(suffix)] + suffix`, giving `abcde...` (exactly 8 chars).