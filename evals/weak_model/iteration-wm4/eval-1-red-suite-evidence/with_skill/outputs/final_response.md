Test suite is green — all 8 tests pass (was 3 failures).

**Root causes and fixes in `slugify.py`:**

1. **`test_underscores`** — `_PUNCT` ran *before* `_SPACES`, so it deleted the `_` before `_SPACES` could convert it to `-`. Reordered the two substitutions (`_SPACES` → `_PUNCT`), which fixes underscores without breaking `test_punctuation`.

2. **`test_max_length_no_trailing_dash`** — `s[:max_length]` could land on a `-`, leaving a trailing dash. Added `.strip("-")` after the slice.

3. **`test_total_length_respects_limit`** — `truncate` appended the suffix without subtracting its length from the limit, so the result exceeded `limit`. Now computes `cut = max(0, limit - len(suffix))` so the total never exceeds the limit.

`word_count` was already passing (two tests) and I left it untouched — no other callers of these functions exist in the repo, so the changes are self-contained.

Verified with `python3 -m unittest test_slugify -v` → `Ran 8 tests ... OK`.