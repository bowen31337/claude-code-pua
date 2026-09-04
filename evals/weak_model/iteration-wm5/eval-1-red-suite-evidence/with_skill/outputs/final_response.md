Suite is green — 8/8 tests pass (`python3 -m unittest test_slugify` → OK).

Three real bugs in `slugify.py`, each with its own root cause:

1. **underscores dropped** — punctuation was stripped *before* spaces became dashes, so `hello_world` → `helloworld`. Fix: reorder to `_SPACES.sub("-", s)` then `_PUNCT.sub("", s)`.
2. **trailing dash after max_length cut** — `s[:max_length]` could end on `-`. Fix: `s[:max_length].strip("-")`.
3. **truncate exceeded the limit** — suffix was appended on top of the limit. Fix: `text[:limit - len(suffix)] + suffix` so total stays ≤ limit.

Scope: only `slugify.py` and `test_slugify.py` exist (no other callers/tests); `word_count` was already correct. Fix is contained.