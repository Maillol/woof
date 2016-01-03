#!/usr/bin/env python3

import sys
import os
import unittest
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from woof.db import ConnectorAdapter, MetaConnectorAdapter


class TestMetaConnectorAdapter(unittest.TestCase):

    def test_created_class_is_stored(self):
        class FooConnectorAdapter(ConnectorAdapter):
            EXPECTED_ARGS = {}
            OPTIONAL_ARGS = {}

        self.assertIn('foo', MetaConnectorAdapter.PROVIDERS)

    def test_cannot_create_class_without_expected_attr(self):
        with self.assertRaises(AttributeError):
            class FooConnectorAdapter(ConnectorAdapter):
                EXPECTED_ARGS = {}

        with self.assertRaises(AttributeError):
            class FooConnectorAdapter(ConnectorAdapter):
                OPTIONAL_ARGS = {}

    def test_translate_kwargs(self):
        class FooConnectorAdapter(ConnectorAdapter):
            EXPECTED_ARGS = {'cheval': 'horse',
                             'oiseau': 'bird'}
            OPTIONAL_ARGS = {'fleur': 'flower'}

        with self.assertRaises(TypeError) as cm:
            FooConnectorAdapter(dict(cheval=33))

        self.assertEqual(str(cm.exception),
            "missing required arguments (oiseau) to foo database provider")

        with self.assertRaises(TypeError) as cm:
            FooConnectorAdapter(dict(cheval=33, oiseau=42, crabe=22))

        self.assertEqual(str(cm.exception),
                         "foo database provider got unexpected keywords arguments (crabe)")

        translated_params = FooConnectorAdapter(dict(cheval=33, oiseau=42, fleur=22))
        self.assertEqual(translated_params.connection_parameters,
                         dict(horse=33, bird=42, flower=22))
