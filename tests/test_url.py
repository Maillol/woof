#!/usr/bin/env python3

import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from msf.url import EntryPoint, URLPathTree


def hotels():
    ...

def hotel(id):
    ...

def rooms():
    ...

def room(id):
    ...

def persons():
    ...

def person(id):
    ...


class TestURLPathTree(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.url_path_tree = URLPathTree()
        cls.url_path_tree.add("/hotel", hotels)
        cls.url_path_tree.add("/hotel/{id}", hotel)
        cls.url_path_tree.add("/hotel/{id}/room", rooms)
        cls.url_path_tree.add("/hotel/{id}/room/{id}", room)
        cls.url_path_tree.add("/person", persons)
        cls.url_path_tree.add("/person/{id}", person)

    def test_get_hotels(self):
        ctrl, parameters = self.url_path_tree.get("/hotel")
        self.assertEqual(ctrl, hotels)
        self.assertEqual(parameters, [])

    def test_get_hotel(self):
        ctrl, parameters = self.url_path_tree.get("/hotel/33")
        self.assertEqual(ctrl, hotel)
        self.assertEqual(parameters, ['33'])

    def test_get_rooms(self):
        ctrl, parameters = self.url_path_tree.get("/hotel/33/room")
        self.assertEqual(ctrl, rooms)
        self.assertEqual(parameters, ['33'])

    def test_get_room(self):
        ctrl, parameters = self.url_path_tree.get("/hotel/33/room/42")
        self.assertEqual(ctrl, room)
        self.assertEqual(parameters, ['33', '42'])

    def test_get_person(self):
        ctrl, parameters = self.url_path_tree.get("/person")
        self.assertEqual(ctrl, persons)
        self.assertEqual(parameters, [])

    def test_get_persons(self):
        ctrl, parameters = self.url_path_tree.get("/person/martin")
        self.assertEqual(ctrl, person)
        self.assertEqual(parameters, ['martin'])


class TestEntryPoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        root = EntryPoint('/api')

        @root.get('/hotel')
        def get_hotel():
            return 1

        @root.put('/hotel/{id}')
        def put_hotel(id):
            return 2

        @root.post('/hotel')
        def post_hotel():
            return 3

        @root.delete('/hotel/{id}')
        def del_hotel(id):
            return 4
        
        cls.root = root

    def test_get(self):
        ctrl = self.root.get_urls.get('/hotel')[0]
        self.assertEqual(ctrl(), 1)

    def test_put(self):
        ctrl, params = self.root.put_urls.get('/hotel/11')
        self.assertEqual(ctrl(params[0]), 2)

    def test_post(self):
        ctrl = self.root.post_urls.get('/hotel')[0]
        self.assertEqual(ctrl(), 3)

    def test_del(self):
        ctrl, params = self.root.del_urls.get('/hotel/55')
        self.assertEqual(ctrl(params[0]), 4)
