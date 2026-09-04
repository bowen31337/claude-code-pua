import re

_PUNCT = re.compile(r"[^a-z0-9\s_-]")
_SPACES = re.compile(r"[\s_]+")


def slugify(text, max_length=None):
    """Turn arbitrary text into a URL slug."""
    s = text.lower()
    s = _PUNCT.sub("", s)
    s = _SPACES.sub("-", s)
    s = s.strip("-")
    if max_length:
        s = s[:max_length].strip("-")
    return s


def truncate(text, limit, suffix="..."):
    """Shorten text to `limit` characters, appending suffix if cut.

    The returned string never exceeds `limit` characters in total
    (content + suffix).
    """
    if len(text) <= limit:
        return text
    return text[:max(0, limit - len(suffix))] + suffix


def word_count(text):
    """Count words, ignoring extra whitespace."""
    return len(text.split(" "))
