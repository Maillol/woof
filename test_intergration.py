#!/usr/bin/env python3

import unittest
from imp import reload

import os
from tempfile import TemporaryDirectory
import json

from url_parser import path_to_sql
from resource2 import *
from msf import RESTServer
import peewee


class TestCrud(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        MetaResource.clear()

        class Book(Resource):
            title = StringField()
            abstract = StringField()
            chapters = ComposedBy('Chapter')

        class Chapter(Resource):
            number = NumberField(weak_id=True)

        cls.tmp_dir = TemporaryDirectory()

        MetaResource.initialize(peewee.SqliteDatabase(os.path.join(cls.tmp_dir.name, 'test.db')))
        MetaResource.create_tables()
        cls.server = RESTServer()
        cls.saved_books = []

    def test_01_select_books(self):
        books = self.server.get('/Book/', '')
        self.assertEqual(books, b'[]')

    def test_02_create_book(self):
        book = dict(title='Martine to the cinema',
                    abstract='Martine go to the cinema with Chuck Noris')

        expected_book = dict(id=1)
        expected_book.update(book)

        created_book = self.server.post('/Book/', '', book)
        created_book = json.loads(created_book.decode('utf-8'))

        self.saved_books.append(expected_book)
        self.assertEqual(created_book, expected_book)

    def test_03_select_books(self):
        books = self.server.get('/Book/', '')
        books = json.loads(books.decode('utf-8'))        
        self.assertEqual(books, self.saved_books)

    @unittest.skip('not implemented feature')
    def test_04_create_book(self):
        book = dict(title='Cheval 2 3',
                    abstract='Il était une fin',
                    Chapter=[dict(number=1), dict(number=2)]
        )

        expected_book = dict(id=2)
        expected_book.update(book)

        created_book = self.server.post('/Book/', '', book)
        created_book = json.loads(created_book.decode('utf-8'))

        self.saved_books.append(expected_book)
        self.assertEqual(created_book, expected_book)

    def test_O5_add_chapter_to_book_1(self):
        chapter = dict(number=1, book_id=1)
        expected_chapter = dict(
            number=1,
            book_id={'id': 1,
                     'title': 'Martine to the cinema',
                     'abstract': 'Martine go to the cinema with Chuck Noris'}
        )

        created_chapter = self.server.post('/Chapter/', '', chapter)
        created_chapter = json.loads(created_chapter.decode('utf-8'))
        self.assertEqual(created_chapter, expected_chapter)

    @classmethod
    def tearDownClass(cls):
        cls.tmp_dir.cleanup()
