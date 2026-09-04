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

    The returned string (text portion + suffix) never exceeds `limit`.
    """
    if len(text) <= limit:
        return text
    text_len = max(limit - len(suffix), 0)
    return text[:text_len] + suffix


def word_count(text):
    """Count words, ignoring extra whitespace."""
    return len(text.split())
