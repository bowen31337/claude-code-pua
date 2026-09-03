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


class TestTruncate(unittest.TestCase):
    def test_short_text_untouched(self):
        self.assertEqual(truncate("hi", 10), "hi")

    def test_total_length_respects_limit(self):
        # The result including the suffix must not exceed the limit.
        self.assertEqual(truncate("abcdefghij", 8), "abcde...")

    def test_limit_shorter_than_suffix(self):
        # Even when there is no room for the suffix, never exceed the limit.
        self.assertEqual(truncate("abcdefghij", 2), "..")


class TestWordCount(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(word_count("one two three"), 3)

    def test_collapses_whitespace(self):
        self.assertEqual(word_count("one   two\tthree\nfour"), 4)

    def test_runs_of_spaces(self):
        # Guards the coincidence that made the case above pass while
        # word_count was still splitting on a single literal space.
        self.assertEqual(word_count("one   two"), 2)

    def test_empty_and_blank(self):
        self.assertEqual(word_count(""), 0)
        self.assertEqual(word_count("   "), 0)


if __name__ == "__main__":
    unittest.main()
