"""
    Utility functions.
"""


class MemoiseNoArgs(object):  # pylint:disable=too-few-public-methods
    """
        Remember the output of a function with NO arguments so it does not have
        to be determined after the first time it's called.
    """
    def __init__(self, function):
        self.function = function
        self.memo = None

    def __call__(self, caching_disabled=False):
        if self.memo is None or caching_disabled:
            self.memo = self.function()
        return self.memo


class Memoise(object):  # pylint:disable=too-few-public-methods
    """
        Remember the output of a function with NO arguments so it does not have
        to be determined after the first time it's called.
    """
    def __init__(self, function):
        self.function = function
        self.memo = {}

    def __call__(self, caching_disabled=False, *args):
        if args not in self.memo or caching_disabled:
            self.memo[args] = self.function(*args)
        return self.memo[args]
