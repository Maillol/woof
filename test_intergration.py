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

    def test_01_select_books(self):
        books = self.server.get('/Book/', '')
        self.assertEqual(books, b'[]')

    def test_02_create_book(self):
        book = dict(title='Martine to the cinema',
                    abstract='Martine go to the cinema with Chuck Noris')

        created_book = self.server.post('/Book/', '', book)
        created_book = json.loads(created_book)
        self.assertIn(created_book, 'title') 
        self.assertIn(created_book, 'abstract')
        self.assertIn(created_book, 'id')
        self.assertIn(created_book, book)

    @classmethod
    def tearDownClass(cls):
        print('dro DB')
        cls.tmp_dir.cleanup()


