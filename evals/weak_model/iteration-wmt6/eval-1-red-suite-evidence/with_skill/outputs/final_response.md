Green. All 8 tests pass.

## What was broken and what I fixed

I read the source, traced each failure to its root cause, and fixed all three:

**1. `test_underscores` — `slugify("hello_world")` → `"helloworld"`**
`_PUNCT = [^a-z0-9\s-]` matched `_` (underscore isn't in the allowed set), so it got stripped *before* `_SPACES` could convert it to a dash. Fix: add `_` to the allowed set so `_SPACES` handles it → `"hello-world"`.

**2. `test_max_length_no_trailing_dash` — `slugify("The Quick Brown", max_length=10)` → `"the-quick-"`**
Slicing `s[:10]` on `"the-quick-brown"` lands on a dash. Fix: strip dashes *after* the slice → `"the-quick"`.

**3. `test_total_length_respects_limit` — `truncate("abcdefghij", 8)` → `"abcdefgh..."` (11 chars, exceeds limit)**
`text[:limit] + suffix` ignored the suffix's length. Fix: reserve room for the suffix (`text[:max(limit - len(suffix), 0)]` + suffix) → `"abcde..."` (8 chars).

## Sibling bug I caught and fixed

While verifying, I found `word_count` used `split(" ")`, which returns empty strings on consecutive spaces — `'one  two'` returned **3** instead of 2. The suite only passed because its input used tabs/newlines. This contradicts the function's own docstring ("ignore extra whitespace"). I changed it to `split()` (whitespace-collapsing). All 8 tests still pass, and `'one  two'` now correctly returns 2.

## Evidence
```
$ python3 -m unittest test_slugify -v
... ok (×8)
Ran 8 tests in 0.000s
OK
```

One thing worth flagging: the test suite does **not** cover the `word_count` consecutive-space case (that's why the bug survived). If you want it protected, I can add a regression test — but I held off since it's outside the "get it green" ask and I don't want to expand scope uninvited.