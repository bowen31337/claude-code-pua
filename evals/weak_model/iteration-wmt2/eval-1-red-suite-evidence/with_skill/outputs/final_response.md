Suite is green — 8/8 passing. Here's the rundown.

## The 3 failures (all in `slugify.py`)

1. **`test_underscores`** — `hello_world` → `helloworld`. The `_PUNCT` regex `[^a-z0-9\s-]` treated `_` as punctuation and *deleted* it, and `_SPACES` (which converts `_`→`-`) ran afterward and never saw it. Fix: add `_` to the keep-set → `[^a-z0-9\s_-]`.

2. **`test_max_length_no_trailing_dash`** — `slugify("The Quick Brown", max_length=10)` → `the-quick-`. Slicing left a trailing dash with nothing to clean it. Fix: `s[:max_length].rstrip("-")`.

3. **`test_total_length_respects_limit`** — `truncate("abcdefghij", 8)` → `abcdefgh...` (11 chars). The total must respect the limit, so the visible portion must leave room for the suffix. Fix: `text[:max(0, limit - len(suffix))] + suffix`.

## Sibling I found and fixed

While checking the file, I caught a latent bug in `word_count`: its docstring says it "collapses whitespace," but `split(" ")` doesn't — it only passed its test by luck (tab/newline coincidentally kept counts aligned). Real input like `'a  b  c'` returned 5 instead of 3. Since it's in the same file and violates its own contract, I fixed it to `split()` and verified the suite stays green.

## Evidence
- `python3 -m unittest test_slugify` → `Ran 8 tests ... OK`
- Sibling verified: `word_count('a  b  c')` → `3`, `'one   two\tthree\nfour'` → `4`, `'  leading and trailing  '` → `3`.

Only `slugify.py` was touched.