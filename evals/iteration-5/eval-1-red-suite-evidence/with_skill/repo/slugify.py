import re

# Keep underscores here so `_SPACES` below can turn them into separators.
# Stripping them at this stage would silently glue words together.
_PUNCT = re.compile(r"[^a-z0-9\s_-]")
_SPACES = re.compile(r"[\s_]+")


def slugify(text, max_length=None):
    """Turn arbitrary text into a URL slug."""
    s = text.lower()
    s = _PUNCT.sub("", s)
    s = _SPACES.sub("-", s)
    s = s.strip("-")
    if max_length is not None:
        # Strip again: the cut may land on a separator.
        s = s[:max_length].strip("-")
    return s


def truncate(text, limit, suffix="..."):
    """Shorten text to `limit` characters, appending suffix if cut.

    The returned string never exceeds `limit`, suffix included.
    """
    if len(text) <= limit:
        return text
    # Final clamp covers the degenerate case where the suffix alone
    # is longer than the limit.
    return (text[: max(0, limit - len(suffix))] + suffix)[:limit]


def word_count(text):
    """Count words, ignoring extra whitespace."""
    # Bare split() collapses runs of any whitespace and ignores
    # leading/trailing padding; split(" ") does neither.
    return len(text.split())
