Test suite is green — all 8 tests pass. I fixed three bugs in `slugify.py`:

1. **`test_underscores`** — The punctuation regex `[^a-z0-9\s-]` was treating `_` as punctuation and deleting it *before* the space-replacement step could turn it into a dash. I added `_` to the allowed set: `[^a-z0-9\s_-]`, so `hello_world` → `hello-world`.

2. **`test_max_length_no_trailing_dash`** — After slicing `s[:max_length]`, a cut could land on a dash and leave a trailing `-`. I added `.strip("-")` to the max_length branch, so `slugify("The Quick Brown", max_length=10)` → `the-quick`.

3. **`test_total_length_respects_limit`** — `truncate` appended the suffix without reserving room for it, exceeding the limit (`abcdefgh...` is 11 chars, not 8). I now cut to `limit - len(suffix)` before appending, so `truncate("abcdefghij", 8)` → `abcde...` (exactly 8 chars).

I also fixed `word_count` to use `text.split()` (no argument) so it correctly collapses all whitespace runs — this was already passing but is more robust.