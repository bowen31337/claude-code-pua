import unittest

from slugify import slugify, truncate, word_count


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_punctuation(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_underscores(self):
        self.assertEqual(slugify("hello_world"), "hello-world")

    def test_max_length_no_trailing_dash(self):
        # "the-quick-brown"[:12] would be "the-quick-br" -- fine,
        # but a cut landing on a dash must not leave a trailing dash.
        self.assertEqual(slugify("The Quick Brown", max_length=10), "the-quick")

    def test_max_length_mid_word_is_kept(self):
        # A cut that lands mid-word keeps the partial word; only a dangling
        # separator gets trimmed.
        self.assertEqual(slugify("The Quick Brown", max_length=12), "the-quick-br")

    def test_separator_runs_collapse(self):
        # Whitespace, underscores and literal dashes are all separators, and
        # a run of them must collapse to exactly one "-".
        self.assertEqual(slugify("Hello -- World"), "hello-world")
        self.assertEqual(slugify("___hello___world___"), "hello-world")
        self.assertEqual(slugify("  Hello   World  "), "hello-world")

    def test_empty_and_punctuation_only(self):
        self.assertEqual(slugify(""), "")
        self.assertEqual(slugify("!!!"), "")


class TestTruncate(unittest.TestCase):
    def test_short_text_untouched(self):
        self.assertEqual(truncate("hi", 10), "hi")

    def test_total_length_respects_limit(self):
        # The result including the suffix must not exceed the limit.
        self.assertEqual(truncate("abcdefghij", 8), "abcde...")

    def test_never_exceeds_limit_at_any_limit(self):
        # The length contract must hold for every limit, including limits too
        # small to fit the suffix at all.
        for limit in range(0, 14):
            with self.subTest(limit=limit):
                result = truncate("abcdefghij", limit)
                self.assertLessEqual(len(result), max(limit, len("abcdefghij")))
                if limit < len("abcdefghij"):
                    self.assertLessEqual(len(result), limit)

    def test_suffix_dropped_when_it_cannot_fit(self):
        # A negative slice index here would silently return almost the whole
        # string, which is worse than no suffix.
        self.assertEqual(truncate("abcdefghij", 2), "ab")

    def test_custom_suffix(self):
        self.assertEqual(truncate("abcdefghij", 6, "…"), "abcde…")


class TestWordCount(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(word_count("one two three"), 3)

    def test_collapses_whitespace(self):
        self.assertEqual(word_count("one   two\tthree\nfour"), 4)

    def test_repeated_spaces_do_not_count_as_words(self):
        # The case above passes even with str.split(" ") purely by coincidence
        # (the empty strings happen to number the same as the missed words).
        # These do not.
        self.assertEqual(word_count("one  two"), 2)
        self.assertEqual(word_count("a\tb"), 2)

    def test_empty_and_whitespace_only(self):
        self.assertEqual(word_count(""), 0)
        self.assertEqual(word_count("   "), 0)
        self.assertEqual(word_count("  a  "), 1)


if __name__ == "__main__":
    unittest.main()
