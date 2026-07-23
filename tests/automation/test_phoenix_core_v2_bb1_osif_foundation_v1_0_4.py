import unittest

from phoenix.osif.version import OSIF_VERSION


class BB1V104Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(OSIF_VERSION, "1.0.4")


if __name__ == "__main__":
    unittest.main()
