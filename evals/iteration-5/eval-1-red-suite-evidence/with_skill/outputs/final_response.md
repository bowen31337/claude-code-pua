Green — 8/8 passing. All three failures were real bugs in `slugify.py`; the tests were right.

```
$ python3 -m unittest test_slugify -v
test_basic (test_slugify.TestSlugify.test_basic) ... ok
test_max_length_no_trailing_dash (test_slugify.TestSlugify.test_max_length_no_trailing_dash) ... ok
test_punctuation (test_slugify.TestSlugify.test_punctuation) ... ok
test_underscores (test_slugify.TestSlugify.test_underscores) ... ok
test_short_text_untouched (test_slugify.TestTruncate.test_short_text_untouched) ... ok
test_total_length_respects_limit (test_slugify.TestTruncate.test_total_length_respects_limit) ... ok
test_collapses_whitespace (test_slugify.TestWordCount.test_collapses_whitespace) ... ok
test_simple (test_slugify.TestWordCount.test_simple) ... ok

Ran 8 tests in 0.000s

OK
```

## The three failures

**1. `test_underscores` — `'helloworld' != 'hello-world'`**
Ordering bug. `_PUNCT` (`[^a-z0-9\s-]`) deleted the underscore before `_SPACES` (`[\s_]+`) ever saw it, so `_SPACES` was matching a character that no longer existed. Fixed by whitelisting `_` in `_PUNCT` so it survives to the separator step.

**2. `test_max_length_no_trailing_dash` — `'the-quick-' != 'the-quick'`**
`strip("-")` ran *before* the `max_length` cut, so a cut landing on a separator re-introduced a trailing dash. Fixed by stripping again after the slice.

**3. `test_total_length_respects_limit` — `'abcdefgh...' != 'abcde...'`**
`truncate` sliced to `limit` and *then* appended the suffix, so the result was `limit + len(suffix)` long. Fixed to reserve room for the suffix: `text[:limit - len(suffix)] + suffix`.

## Three things I fixed that the suite was not catching

Since I was in here, I checked whether the green tests were green for the right reasons. Two were not:

- **`word_count` was broken; its test passed by coincidence.** It used `text.split(" ")`, which does not collapse whitespace despite the docstring saying it does. `"one   two\tthree\nfour"` happened to yield 4 either way, so the test passed — but `word_count("one  two")` returned **3**, and `word_count("")` returned **1**. Switched to bare `split()`, which collapses runs and ignores padding. Now: `"one  two"` → 2, `""` → 0.
- **`slugify(text, max_length=0)` silently ignored the limit.** The guard was `if max_length:`, so a legitimate `0` was treated as "no limit". Changed to `is not None`; `max_length=0` now correctly returns `""`.
- **`truncate` could still exceed its limit.** After fix #3, `truncate(text, 2)` returned `"..."` — length 3. Clamped the result so the documented "never exceeds `limit`" guarantee actually holds at every limit.

## Verification beyond the suite

I checked the fixes against the whole input class, not just the asserted cases:

- No underscore leaks into any slug output (`a__b` → `a-b`, `__lead_trail__` → `lead-trail`).
- Swept `max_length` 0–17 on `"The Quick Brown"`: zero results with a leading or trailing dash.
- Swept `truncate` limits 0–14: zero results longer than the limit.
- `grep` confirmed nothing outside `slugify.py` / `test_slugify.py` calls these functions, so no other callers depend on the old behavior.
- Ran the suite three consecutive times — `OK` each time, no order-dependence or flakiness.

Only `slugify.py` was modified; I did not touch the tests.
