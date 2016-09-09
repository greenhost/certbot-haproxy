"""Certbot HAProxy Tests"""
import unittest


def load_tests(loader, tests, pattern=None):
    """Find all python files in the tests folder"""
    if pattern is None:
        pattern = 'test_*.py'
    print "loader: ", loader

    suite = loader.discover('certbot_haproxy/tests', pattern=pattern)
    suite.addTests(tests)
    return suite
