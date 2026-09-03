import re

# NOTE: "_" is deliberately allowed through here so that _SPACES (below) can
# turn it into a "-". Stripping it at this stage would delete the separator
# instead of converting it.
_PUNCT = re.compile(r"[^a-z0-9\s_-]")
# Runs of whitespace, underscores and dashes all collapse to a single "-",
# so "Hello -- World" and "hello___world" both yield one separator.
_SPACES = re.compile(r"[\s_-]+")


def slugify(text, max_length=None):
    """Turn arbitrary text into a URL slug."""
    s = text.lower()
    s = _PUNCT.sub("", s)
    s = _SPACES.sub("-", s)
    s = s.strip("-")
    if max_length is not None:
        # Truncating can land mid-separator, so re-trim afterwards. Leading
        # dashes are already gone, so only the tail can be left dangling.
        s = s[:max_length].rstrip("-")
    return s


def truncate(text, limit, suffix="..."):
    """Shorten text to `limit` characters, appending suffix if cut.

    The returned string never exceeds `limit`; the suffix is counted as part
    of the budget, not added on top of it.
    """
    if len(text) <= limit:
        return text
    cut = limit - len(suffix)
    if cut <= 0:
        # No room for the suffix at all -- a hard cut still beats overflowing.
        return text[:limit]
    return text[:cut] + suffix


def word_count(text):
    """Count words, ignoring extra whitespace."""
    # split() with no argument splits on runs of any whitespace and discards
    # empties; split(" ") does neither.
    return len(text.split())
