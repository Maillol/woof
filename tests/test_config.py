#!/usr/bin/env python3

import sys
import os
import unittest
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from woof.server.config import (ConfigIsNotValidError, ChoiceValidator, IntValidator,
                               FloatValidator, StrValidator, DictValidator, 
                               ListValidator, TranstypingValidator)


def stub_constructor(a, b):
    return (a, b)


class TestMetaConnectorAdapter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.validator = DictValidator(children={
            'a': IntValidator(int_min=3, int_max=7),
            'b': FloatValidator(float_min=3, float_max=7),
            'c': StrValidator(),
            'd': ChoiceValidator(choices=("toto", "tata")),
            'e': TranstypingValidator(int, unpacking=False),
            'f': TranstypingValidator(stub_constructor),
            'g': DictValidator(children={
                'ga': IntValidator(),
                'gb': IntValidator(is_required=False)
            })
        })

    def setUp(self):
        self.valid_conf = {
            'a': 5,
            'b': 7.0,
            'c': 'cheval 2 3',
            'd': 'toto',
            'e': '22',
            'f': {
                'a': 11,
                'b': 22
            },
            'g': {
                'ga': 45,
                'gb': 73
            }
        }

    def test_clean_conf(self):
        clean_conf = self.validator.valid(self.valid_conf)
        expected = {
            'a': 5,
            'b': 7.0,
            'c': 'cheval 2 3',
            'd': 'toto',
            'e': 22,
            'f': (11, 22),
            'g': {
                'ga': 45,
                'gb': 73
            }
        }
        self.assertEqual(clean_conf, expected)

    def test_int(self):
        self.valid_conf['a'] = 8
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'a: must be an integer between 3 and 7')

        self.valid_conf['a'] = 2
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'a: must be an integer between 3 and 7')

        self.valid_conf['a'] = '4'
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'a: must be an integer between 3 and 7')

    def test_float(self):
        self.valid_conf['b'] = 7.1
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'b: must be a float between 3 and 7')

        self.valid_conf['b'] = 2.9
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'b: must be a float between 3 and 7')

        self.valid_conf['b'] = 4
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'b: must be a float between 3 and 7')

    def test_str(self):
        self.valid_conf['c'] = 7
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'c: must be a string')

    def test_dict(self):
        self.valid_conf['g'] = 7
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'g: must be a object')

    def test_nested(self):
        self.valid_conf['g']['ga'] = 'toto'
        with self.assertRaises(ConfigIsNotValidError) as cm:
            clean_conf = self.validator.valid(self.valid_conf)
        self.assertEqual(str(cm.exception), 'g.ga: must be an integer between -inf and inf')

    def test_optional(self):
        del self.valid_conf['g']['gb']
        try:
            self.validator.valid(self.valid_conf)
        except ConfigIsNotValidError:
            self.fail("valid() raised ConfigIsNotValidError unexpectedly!")

        
        

