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
from woof.resource import MetaResource
from woof.server import RESTServer, config


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

    def test_03_create_book(self):
        book = dict(title='The life of Martine',
                    abstract='Martine has a hetic life')

        expected_book = dict(id=2, chapters=[])
        expected_book.update(book)

        created_book = self.server.post('/api/books', '', json.dumps(book))

        self.saved_books.append(expected_book)
        self.AssertJsonEqual(created_book, expected_book)

    def test_04_select_books(self):
        books = self.server.get('/api/books', '')
        self.AssertJsonEqual(books, self.saved_books)

    def test_05_update_books(self):
        book = dict(title='Martine go to the cinema',
                    abstract='Martine go to the cinema with Chuck Noris')
        updated = self.server.put('/api/books/1', '', json.dumps(book))
        book.update(dict(id=1, chapters=[]))
        self.AssertJsonEqual(updated, book)

    def test_06_create_chapter(self):
        chapter = dict(number=1, title="First step")
        created = self.server.post('/api/books/1/chapters', '', json.dumps(chapter))
        chapter['book_id'] = 1
        self.AssertJsonEqual(created, chapter)

    def test_07_create_chapter(self):
        chapter = dict(number=1, title="Init")
        created = self.server.post('/api/books/2/chapters', '', json.dumps(chapter))
        chapter['book_id'] = 2
        self.AssertJsonEqual(created, chapter)

    def test_08_update_chapter(self):
        chapter = dict(number=1, title="Introduction")
        updated = self.server.put('/api/books/1/chapters/1', '', json.dumps(chapter))
        chapter['book_id'] = 1
        self.AssertJsonEqual(updated, chapter)

    def test_09_select_chapter(self):
        chapter = self.server.get('/api/books/1/chapters/1', '')
        expected = dict(book_id=1, number=1, title="Introduction")
        self.AssertJsonEqual(chapter, expected)

    def test_10_select_chapters(self):
        chapter = self.server.get('/api/books/1/chapters', '')
        expected = [{"book_id": 1, "number": 1, "title": "Introduction"}]
        self.AssertJsonEqual(chapter, expected)

    def test_11_select_chapters(self):
        chapter = self.server.get('/api/books/2/chapters', '')
        expected = [{"book_id": 2, "number": 1, "title": "Init"}]
        self.AssertJsonEqual(chapter, expected)

    def test_12_delete_chapter(self):
        chapter = self.server.delete('/api/books/1/chapters/1', '')
        self.AssertJsonEqual(chapter, '')

    def test_13_select_chapters(self):
        chapter = self.server.get('/api/books/1/chapters', '')
        expected = []
        self.AssertJsonEqual(chapter, expected)

    def test_14_select_chapters(self):
        chapter = self.server.get('/api/books/2/chapters', '')
        expected = [{"book_id": 2, "number": 1, "title": "Init"}]
        self.AssertJsonEqual(chapter, expected)

    @classmethod
    def tearDownClass(cls):
        cls.tmp_dir.cleanup()
        os.remove('config.json')
