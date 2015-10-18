#!/usr/bin/env python3

import unittest
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
        print('make DB')
        class Book(Resource):
            title = StringField()
            abstract = StringField()

        class Chapter(Resource):
            number = NumberField()

        class Paragraphe(Resource):
            number = NumberField()


        cls.tmp_dir = TemporaryDirectory()

        MetaResource._name_to_ref()
        MetaResource._initialize_db(peewee.SqliteDatabase(os.path.join(cls.tmp_dir.name, 'test.db')))
        MetaResource.db.connect()
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
        #import pprint
        #print("°"* 30)
        #pprint.pprint(created_book)

        self.saved_books.append(expected_book)
        self.assertEqual(created_book, expected_book)


    @classmethod
    def tearDownClass(cls):
        print('dro DB')
        cls.tmp_dir.cleanup()


