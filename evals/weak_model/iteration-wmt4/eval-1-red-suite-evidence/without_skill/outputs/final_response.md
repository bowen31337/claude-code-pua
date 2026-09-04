The test suite is now green — all 8 tests pass. Here's what was wrong and how I fixed each of the 3 failures:

**1. `test_underscores`** — The punctuation regex `[^a-z0-9\s-]` treated `_` as punctuation and *deleted* it, turning `hello_world` into `helloworld`. Fixed by adding `_` to the allowed character class: `[^a-z0-9\s_-]`, so underscores are preserved and later collapsed to dashes by the `_SPACES` regex.

**2. `test_max_length_no_trailing_dash`** — Slicing `s[:max_length]` could land on a dash, leaving a trailing `-`. Fixed by stripping dashes after the slice: `s[:max_length].strip("-")`.

**3. `test_total_length_respects_limit`** — `truncate` returned `text[:limit] + suffix`, which exceeds the limit (11 chars for a limit of 8). Fixed by reserving room for the suffix: `text[:limit - len(suffix)] + suffix`, so the total length never exceeds `limit`.

I also hardened `word_count` to use `text.split()` (no argument) so it collapses all whitespace runs — this was already passing, but it makes the whitespace-collapsing intent explicit and robust.