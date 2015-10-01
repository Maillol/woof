#!/usr/bin/env python3

import unittest
from url_parser import path_to_sql

class TestPathToSql1(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        class Book:
            title = 'Manual'

        class Chapter:
            book = 23

        class Paragraphe:
            chapter = 45

        cls.book = Book
        cls.chapter = Chapter
        cls.paragraphe = Paragraphe

        cls.register = {
            'books': (cls.book, {}),
            'chapters': (cls.chapter, {}),
            'paragraphes': (cls.paragraphe, {})
        }
        cls.register['chapters'][1]['book'] = cls.register['books']
        cls.register['paragraphes'][1]['chapter'] = cls.register['chapters']

    def test_01(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/books/23/chapters/45/paragraphes/2')
        self.assertEqual(name, 'paragraphes')        
        self.assertEqual(entity_cls, self.paragraphe)        
        self.assertEqual(entity_id, '2')
        self.assertEqual(query_data, [(self.book, '23', None), (self.chapter, '45', None)])

    def test_02(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/books/23/chapters/45/paragraphes/')
        self.assertEqual(name, 'paragraphes')        
        self.assertEqual(entity_cls, self.paragraphe)        
        self.assertEqual(entity_id, '')
        self.assertEqual(query_data, [(self.book, '23', None), (self.chapter, '45', None)])

    def test_03(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/books/23/chapters/45/paragraphes')
        self.assertEqual(name, 'paragraphes')        
        self.assertEqual(entity_cls, self.paragraphe)        
        self.assertEqual(entity_id, '')
        self.assertEqual(query_data, [(self.book, '23', None), (self.chapter, '45', None)])

    def test_04(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/books/23/chapters/45')
        self.assertEqual(name, 'chapters')
        self.assertEqual(entity_cls, self.chapter)
        self.assertEqual(entity_id, '45')
        self.assertEqual(query_data, [(self.book, '23', None)])

    def test_05(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/books/23/chapters/')
        self.assertEqual(name, 'chapters')
        self.assertEqual(entity_cls, self.chapter)
        self.assertEqual(entity_id, '')
        self.assertEqual(query_data, [(self.book, '23', None)])

    def test_06(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/books/23')
        self.assertEqual(name, 'books')
        self.assertEqual(entity_cls, self.book)
        self.assertEqual(entity_id, '23')
        self.assertEqual(query_data, [])

    def test_07(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/books/')
        self.assertEqual(name, 'books')
        self.assertEqual(entity_cls, self.book)
        self.assertEqual(entity_id, '')
        self.assertEqual(query_data, [])

    def test_08(self):
        with self.assertRaises(KeyError):
            path_to_sql(self.register, '/')

        with self.assertRaises(KeyError):
            path_to_sql(self.register, '/car')

        with self.assertRaises(KeyError):
            path_to_sql(self.register, '/books/3/')


class TestPathToSql2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        class Building:
            name = '121 foo street'

        class Person:
            work_in = 81
            live_in = 82

        cls.person = Person
        cls.building = Building

        cls.register = {
            'persons': (cls.person, {}),
            'buildings': (cls.building, {}),
        }
        cls.register['persons'][1]['work_in'] = cls.register['buildings']
        cls.register['persons'][1]['live_in'] = cls.register['buildings']

    def test_01(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/buildings-work_in/81/persons/')
        self.assertEqual(name, 'persons')        
        self.assertEqual(entity_cls, self.person)
        self.assertEqual(entity_id, '')
        self.assertEqual(query_data, [(self.building, '81', 'work_in')])

    def test_02(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/buildings-live_in/81/persons/')
        self.assertEqual(name, 'persons')        
        self.assertEqual(entity_cls, self.person)
        self.assertEqual(entity_id, '')
        self.assertEqual(query_data, [(self.building, '81', 'live_in')])

    def test_03(self):
        name, entity_cls, entity_id, query_data = path_to_sql(self.register, '/buildings-any_thing/9')
        self.assertEqual(name, 'buildings')        
        self.assertEqual(entity_cls, self.building)
        self.assertEqual(entity_id, '9')
        self.assertEqual(query_data, [])

