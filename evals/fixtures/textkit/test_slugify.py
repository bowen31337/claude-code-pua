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


class TestWordCount(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(word_count("one two three"), 3)

    def test_collapses_whitespace(self):
        self.assertEqual(word_count("one   two\tthree\nfour"), 4)


if __name__ == "__main__":
    unittest.main()
