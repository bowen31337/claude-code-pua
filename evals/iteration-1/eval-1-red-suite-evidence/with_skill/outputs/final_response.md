Green. All three failures were real bugs in `slugify.py` — the tests were right, the implementation was wrong — and while I was in there I found a fourth bug that the suite was *hiding*.

## Final run

```
$ python3 -m unittest test_slugify
...........
----------------------------------------------------------------------
Ran 11 tests in 0.000s

OK
exit=0
```

11 tests, not 8 — I added 3 regression tests. More on that below.

## The three failures

**1. `test_underscores` — `'helloworld' != 'hello-world'`**

Ordering bug. `_PUNCT` ran first and its class `[^a-z0-9\s-]` did not whitelist `_`, so underscores were deleted outright — `_SPACES` (`[\s_]+`) never got the chance to turn them into separators. It was dead code for the `_` branch. Fixed by whitelisting underscore in `_PUNCT`:

```python
_PUNCT = re.compile(r"[^a-z0-9\s_-]")
```

**2. `test_max_length_no_trailing_dash` — `'the-quick-' != 'the-quick'`**

`strip("-")` ran *before* the `max_length` slice, so a cut landing on a separator re-introduced the trailing dash. Fixed by stripping again after the cut. I also changed the guard from `if max_length:` to `if max_length is not None:` — the truthiness test made `max_length=0` silently return the *entire* slug instead of `""`.

**3. `test_total_length_respects_limit` — `'abcdefgh...' != 'abcde...'`**

`truncate` sliced to `limit` and *then* appended the suffix, so the result always overshot by `len(suffix)`. Fixed to reserve room for the suffix, with a clamp so a limit smaller than the suffix still can't overshoot:

```python
cut = max(limit - len(suffix), 0)
return (text[:cut] + suffix)[:limit]
```

## The bug the suite was hiding

`word_count` used `text.split(" ")` — splitting on a single literal space, which neither collapses runs of whitespace nor handles tabs/newlines. `test_collapses_whitespace` was passing **by coincidence**:

```
>>> "one   two\tthree\nfour".split(" ")
['one', '', '', 'two\tthree\nfour']     # len 4 — right answer, wrong reason
```

Two empty strings and one un-split blob happened to total 4. The same function returned `1` for `""`, `3` for `"   "`, and `1` for `"one\ttwo"`. Fixed to bare `text.split()`, which collapses any whitespace run and drops empty leading/trailing fields.

## Regression tests added

Three of the four bugs sat in untested space, so I pinned them:

- `TestTruncate.test_limit_shorter_than_suffix` — the clamp path
- `TestWordCount.test_runs_of_spaces` — kills the coincidence above
- `TestWordCount.test_empty_and_blank` — `""` and `"   "` → 0

I verified these are genuine guards rather than decoration by running the new suite against the *original* `slugify.py`: **6 failures** (the 3 you reported plus the 3 new ones). They fail on the old code and pass on the new.

## Edge cases I checked beyond the assertions

All pass: `slugify` with mixed punctuation and underscores, repeated underscores (`a__b___c` → `a-b-c`), leading/trailing separators, `max_length` of 0 / mid-word / larger than the string, empty input, punctuation-only input, already-slugged input. For `truncate` I brute-forced every `(text, limit)` pair over 4 strings × limits 0–11 and confirmed no result ever exceeds its limit.

## Not covered

`slugify` still strips non-ASCII rather than transliterating it — `"café"` → `"caf"`, `"日本語"` → `""`. That's the pre-existing behaviour and no test pins it either way, so I left it alone; if you want Unicode slugs that's a `unicodedata.normalize("NFKD", ...)` change and a design decision rather than a bug fix. `truncate` also assumes `limit` is non-negative — a negative limit returns `""` rather than raising.

Files touched: `slugify.py`, `test_slugify.py`. Python 3.12.12.
