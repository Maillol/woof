#!/usr/bin/env python3

import unittest
from resource2 import *
import resource2
from datetime import date
from decimal import Decimal

class TestCrud(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        MetaResource.clear()
        class Hotel(Resource):
            name = StringField()
            address = StringField()
            rooms = ComposedBy('Room')

        class Room(Resource):
            number = IntegerField(weak_id=True)
            bed_count = IntegerField()

        cls.Hotel = Hotel
        cls.Room = Room
        MetaResource.initialize('sqlite', ':memory:', isolation_level=None)
        MetaResource.create_tables()

    def test_01_create_hotel(self):
        hotel = self.Hotel(name="Hotel California", 
                           address="route de radis")
        hotel.save()

        hotel = self.Hotel(name="Tokio Hotel", 
                           address="125 main street")
        hotel.save()

        result = MetaResource.db.execute('SELECT * FROM hotel;').fetchall()
        
        self.assertEqual(result, 
                         [(1, 'Hotel California', 'route de radis'),
                          (2, 'Tokio Hotel', '125 main street')])

    def test_02_iter_on_select_hotel(self):
        loop = iter(self.Hotel.select())
        hotel = next(loop)
        self.assertEqual(hotel.id, 1)
        self.assertEqual(hotel.name, 'Hotel California')
        self.assertEqual(hotel.address, 'route de radis')

        hotel = next(loop)
        self.assertEqual(hotel.id, 2)
        self.assertEqual(hotel.name, 'Tokio Hotel')
        self.assertEqual(hotel.address, '125 main street')

        with self.assertRaises(StopIteration):
            hotel = next(loop)

    def test_03_select_hotel_where(self):
        hotels = list(self.Hotel.select().where(self.Hotel.name == 'Hotel California'))
        self.assertEqual(len(hotels), 1)
        self.assertEqual(hotels[0].id, 1)

        hotels = list(self.Hotel.select().where(
            self.Hotel.name == 'Tokio Hotel').where(
            self.Hotel.address == '125 main street'))

        self.assertEqual(len(hotels), 1)
        self.assertEqual(hotels[0].id, 2)

    def test_04_create_room(self):
        self.Room(hotel_id=1, number=1, bed_count=3).save()
        self.Room(hotel_id=1, number=2, bed_count=2).save()
        self.Room(hotel_id=2, number=1, bed_count=1).save()
        self.Room(hotel_id=2, number=2, bed_count=4).save()

        result = MetaResource.db.execute(
            'SELECT hotel_id, number, bed_count FROM room;').fetchall()
        self.assertEqual(result, [(1, 1, 3), (1, 2, 2), (2, 1, 1), (2, 2, 4)])

    def test_05_create_room_raise_integrity_error(self):
        with self.assertRaises(IntegrityError):
            self.Room(hotel_id=1, number=1, bed_count=3).save()
        with self.assertRaises(IntegrityError):
            self.Room(hotel_id=456, number=1, bed_count=3).save()

    def test_06_get_room_from_hotel(self):
        hotels = list(self.Hotel.select())
        rooms = list(hotels[0].rooms)
        self.assertEqual(rooms[0].bed_count, 3)
        self.assertEqual(rooms[1].bed_count, 2)

        rooms = list(hotels[1].rooms)
        self.assertEqual(rooms[0].bed_count, 1)
        self.assertEqual(rooms[1].bed_count, 4)

