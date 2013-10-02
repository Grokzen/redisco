import unittest

if __name__ == "__main__":
    from . import all_tests
    suite = all_tests()
    unittest.TextTestRunner(verbosity=2).run(suite)