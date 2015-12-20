#!/usr/bin/env python3

import sys
import os
from app import root_url
import unittest
from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
import json
from wsgiref.validate import validator
from wsgiref.util import setup_testing_defaults
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from msf.resource import MetaResource
from msf.server import RESTServer, config


class WSGIMockServer:

    def __init__(self, application):
        self.application = validator(application)
        self.responce = ""
        self.environ = {}
        self.start_response = MagicMock()

    def assert_response_is(self, expected):
        if self.responce != expected:
            raise AssertionError('Expected response: {}\nActual response: {}'
                                 .format(expected, self.response))

    def _run_app(self, path, query_string='', body=''):
        if isinstance(body, str):
            body = body.encode('utf-8')

        self.environ['PATH_INFO'] = path
        self.environ['QUERY_STRING'] = query_string
        self.environ['CONTENT_LENGTH'] = str(len(body))
        self.environ['wsgi.input'] = BytesIO(body)
        self.start_response.reset_mock()
        iterator = self.application(self.environ, self.start_response)
        try:
            self.responce = b''.join(list(iterator))
        except:
            raise
        finally:
            iterator.close()
        return self.responce

    def __getattr__(self, name):
        if name in ('get', 'delete', 'post', 'put',
                    'options', 'head', 'trace', 'connect'):
            self.environ = {}
            setup_testing_defaults(self.environ)
            self.environ['REQUEST_METHOD'] = name.upper()
            return self._run_app
        raise AttributeError("'WSGIMockServer' object has no attribute '{}'"
                             .format(name))


class TestCrud(unittest.TestCase):

    def AssertJsonEqual(self, serialized, expected):
        self.assertEqual(json.loads(serialized.decode('utf-8')), expected)

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = TemporaryDirectory()
        with open('config.json', 'w') as conf_file:
            conf_file.write(
                '{'
                    '"database": {'
                        '"provider": "sqlite",'
                        '"database": "%s"'
                    '}'
                '}' % os.path.join(cls.tmp_dir.name, 'test.db'))

        MetaResource.initialize(config.database)
        MetaResource.create_tables()
        application = RESTServer(root_url)
        cls.server = WSGIMockServer(application)
        cls.saved_books = []

    def test_01_select_books(self):
        books = self.server.get('/api/books', '')
        self.assertEqual(books, b'[]')

    def test_02_create_book(self):
        book = dict(title='Martine to the cinema',
                    abstract='Martine go to the cinema with Chuck Noris')

        expected_book = dict(id=1, chapters=[])
        expected_book.update(book)

        created_book = self.server.post('/api/books', '', json.dumps(book))

        self.saved_books.append(expected_book)
        self.AssertJsonEqual(created_book, expected_book)

    def test_03_select_books(self):
        books = self.server.get('/api/books', '')
        self.AssertJsonEqual(books, self.saved_books)

    @classmethod
    def tearDownClass(cls):
        cls.tmp_dir.cleanup()
        os.remove('config.json')
