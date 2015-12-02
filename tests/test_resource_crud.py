#!/usr/bin/env python3

import sys
import os
import unittest
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from msf.resource import *


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

        class Person(Resource):
            first_name = StringField()
            last_name = StringField()

        @association(
            Person='0..n',
            Room='0..n'
        )
        class Rent(Resource):
            date = DateField(primary_key=True)
            nb_night = IntegerField()

        cls.Hotel = Hotel
        cls.Room = Room
        cls.Person = Person
        cls.Rent = Rent

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
            (self.Hotel.name == 'Tokio Hotel') &
            (self.Hotel.address == '125 main street')))

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

    def test_07_create_person(self):
        self.Person(first_name='Claude', last_name='Monet').save()
        self.Person(first_name='Vincent', last_name='Van Gogh').save()
        result = MetaResource.db.execute(
            'SELECT id, first_name, last_name FROM Person;').fetchall()
        self.assertEqual(result, [(1, 'Claude', 'Monet'),
                                  (2, 'Vincent', 'Van Gogh')])

    def test_08_select_person(self):
        persons = list(self.Person.select())
        self.assertEqual(persons[0].first_name, 'Claude')
        self.assertEqual(persons[0].last_name, 'Monet')
        self.assertEqual(persons[1].first_name, 'Vincent')
        self.assertEqual(persons[1].last_name, 'Van Gogh')

    def test_09_person_rent_room(self):
        self.Rent(
            date=date(2015, 11, 3),
            nb_night=4,
            person_id=1,
            room_hotel_id=1,
            room_number=2).save()

        self.Rent(
            date=date(2015, 11, 4),
            nb_night=14,
            person_id=2,
            room_hotel_id=2,
            room_number=1).save()

        result = MetaResource.db.execute(
            'SELECT date, nb_night, person_id, room_hotel_id, room_number FROM Rent;').fetchall()
        self.assertEqual(result, [('2015-11-03', 4, 1, 1, 2),
                                  ('2015-11-04', 14, 2, 2, 1)])

    def test_10_create_rent_raise_integrity_error(self):
        with self.assertRaises(IntegrityError):
            self.Rent(
                date=date(2015, 11, 3),
                nb_night=4,
                person_id=1,
                room_hotel_id=1,
                room_number=2).save()

        with self.assertRaises(IntegrityError):
            self.Rent(
                date=date(2018, 5, 19),
                nb_night=23,
                person_id=927,
                room_hotel_id=1,
                room_number=2).save()

        with self.assertRaises(IntegrityError):
            self.Rent(
                date=date(2018, 5, 19),
                nb_night=23,
                person_id=1,
                room_hotel_id=927,
                room_number=2).save()

        with self.assertRaises(IntegrityError):
            self.Rent(
                date=date(2018, 5, 19),
                nb_night=23,
                person_id=1,
                room_hotel_id=1,
                room_number=927).save()

    def test_11_select_person_rent_room_using_join(self):
        persons = list(
            self.Person.select()
            .join(self.Rent,
                  on=self.Person.id == self.Rent.person_id)
            .join(self.Room,
                  on=(self.Room.hotel_id == self.Rent.room_hotel_id) &
                     (self.Room.number == self.Rent.room_number))
            .where((self.Room.hotel_id == 1) & (self.Room.number == 2))
        )

        self.assertEqual(len(persons), 1)
        self.assertEqual(persons[0].first_name, 'Claude')
        self.assertEqual(persons[0].last_name, 'Monet')

        persons = list(
            self.Person.select()
            .join(self.Rent,
                  on=self.Person.id == self.Rent.person_id)
            .join(self.Room,
                  on=(self.Room.hotel_id == self.Rent.room_hotel_id) &
                     (self.Room.number == self.Rent.room_number))
            .where(self.Room.bed_count == 1)
        )

        self.assertEqual(len(persons), 1)
        self.assertEqual(persons[0].first_name, 'Vincent')
        self.assertEqual(persons[0].last_name, 'Van Gogh')

    def test_12_select_rent_from_person(self):
        person1, person2 = self.Person.select()
        renting = list(person1.rent_set)
        self.assertEqual(len(renting), 1)
        self.assertEqual(renting[0].date, date(2015, 11, 3))
        self.assertEqual(renting[0].nb_night, 4)

        renting = list(person2.rent_set)
        self.assertEqual(len(renting), 1)
        self.assertEqual(renting[0].date, date(2015, 11, 4))
        self.assertEqual(renting[0].nb_night, 14)

    def test_13_select_room_from_person(self):
        person1, person2 = self.Person.select()
        renting = list(person1.rent_set)
        room = list(renting[0].room_ref)[0]
        self.assertEqual(room.bed_count, 2)

        renting = list(person2.rent_set)
        room = list(renting[0].room_ref)[0]
        self.assertEqual(room.bed_count, 1)

    def test_14_delete_persons_raise_integrity_error(self):
        person1, person2 = self.Person.select()
        with self.assertRaises(IntegrityError):
            person1.delete()
        with self.assertRaises(IntegrityError):
            person2.delete()

    def test_15_delete_room_in_rent_raise_integrity_error(self):
        rooms = self.Room.select().join(
            self.Rent, on=((self.Room.hotel_id == self.Rent.room_hotel_id) &
                           (self.Room.number == self.Rent.room_number)))
        for room in rooms:
            with self.assertRaises(IntegrityError):
                room.delete()

    def test_16_delete_hotel_with_room_raise_integrity_error(self):
        for hotel in self.Hotel.select():
            with self.assertRaises(IntegrityError):
                hotel.delete()

    def test_17_delete_room_not_in_rent(self):
        rooms = self.Room.select().where(
            (self.Room.bed_count == 3) | (self.Room.bed_count == 4))
        for room in rooms:
            room.delete()

    def test_18_delete_rent(self):
        for rent in self.Rent.select():
            rent.delete()
        self.assertEqual(list(self.Rent.select()), [])

    def test_19_delete_person(self):
        for person in self.Person.select():
            person.delete()
        self.assertEqual(list(self.Person.select()), [])

    def test_20_delete_room(self):
        for room in self.Room.select():
            room.delete()
        self.assertEqual(list(self.Room.select()), [])

    def test_21_delete_hotel(self):
        for hotel in self.Hotel.select():
            hotel.delete()
        self.assertEqual(list(self.Hotel.select()), [])
