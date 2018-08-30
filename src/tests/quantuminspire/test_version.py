import re
import unittest
from quantuminspire import __version__


class TestVersion(unittest.TestCase):

    def test_version_HasCorrectFormat(self):
        search_pattern = re.compile(r'\d+.\d+.\d+')
        match = search_pattern.match(__version__)
        self.assertIsNotNone(match)
