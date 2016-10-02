import sys
import os
import unittest
import tempfile
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from woof.server.server import traceback_to_dict


def raise_exc():
    raise TypeError('error_msg', 'error_num')


def raise_explicitly_chained():
    try:
        raise_exc()
    except TypeError as error:
        raise ValueError('value_error_msg') from error


def raise_implicitly_chained():
    try:
        raise_exc()
    except TypeError as error:
        raise ValueError('value_error_msg')


class TestTracebackToDict(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            raise_explicitly_chained()
        except ValueError as error:
             cls.explicitly_tb = traceback_to_dict(error)

        try:
            raise_implicitly_chained()
        except ValueError as error:
             cls.implicitly_tb = traceback_to_dict(error)

    def test_explicitly_type(self):
        self.assertEqual(self.explicitly_tb['error'], 'ValueError')

    def test_explicitly_args(self):
        self.assertEqual(self.explicitly_tb['args'], ('value_error_msg',))

    def test_explicitly_chained(self):
        self.assertEqual(self.explicitly_tb['explicitly_chained'], True)

    def test_explicitly_context_type(self):
        self.assertEqual(self.explicitly_tb['context']['error'], 'TypeError')

    def test_explicitly_context_args(self):
        self.assertEqual(self.explicitly_tb['context']['args'], ('error_msg', 'error_num'))

    def test_implicitly_type(self):
        self.assertEqual(self.implicitly_tb['error'], 'ValueError')

    def test_implicitly_args(self):
        self.assertEqual(self.implicitly_tb['args'], ('value_error_msg',))

    def test_implicitly_chained(self):
        self.assertEqual(self.implicitly_tb['explicitly_chained'], False)

    def test_implicitly_context_type(self):
        self.assertEqual(self.implicitly_tb['context']['error'], 'TypeError')

    def test_implicitly_context_args(self):
        self.assertEqual(self.implicitly_tb['context']['args'], ('error_msg', 'error_num'))

