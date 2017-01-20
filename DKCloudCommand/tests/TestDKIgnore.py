import unittest
from DKIgnore import DKIgnore


class TestDKIgnore(unittest.TestCase):
    def test_ignore(self):
        ignore = DKIgnore()

        test = 'not_ignore'
        self.assertFalse(ignore.ignore(test))

        test = '.DS_Store'
        self.assertTrue(ignore.ignore(test))

        test = 'base/path/directory/.DS_Store'
        self.assertTrue(ignore.ignore(test))


if __name__ == '__main__':
    unittest.main()
