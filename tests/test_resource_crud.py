#!/usr/bin/env python3

import sys
import os
import unittest
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from woof.resource import *
from woof.db import IntegrityError
from woof.db import DataBase


class TestLoyaltyCardSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        MetaResource.clear()

        class LoyaltyCard(Resource):
            points = IntegerField()
            expiration_date = DateField()
            price = FloatField()

        class Customer(Resource):
            name = StringField()
            loyalty_card = Has('LoyaltyCard', '0..1')

        data_base = DataBase('sqlite', database=':memory:', isolation_level=None)
        MetaResource.initialize(data_base)
        MetaResource.create_tables()

        cls.LoyaltyCard = LoyaltyCard
        cls.Customer = Customer


class TestCrudLoyaltyCardSchema(TestLoyaltyCardSchema):
    def test_01_create_card(self):
        card = self.LoyaltyCard(points=0, expiration_date="2015-12-03", price=29.99)
        card.save()

    def test_02_create_card(self):
        card = self.LoyaltyCard(points=120, expiration_date="2015-12-05", price=15.00)
        card.save()

    def test_03_create_customer(self):
        customer = self.Customer(name="George")
        customer.save()

    def test_04_select_card(self):
        cards = list(self.LoyaltyCard.select())
        self.assertEqual(len(cards), 2)

        card = cards[0]
        self.assertEqual(card.id, 1)
        self.assertEqual(card.expiration_date, date(2015, 12, 3))
        self.assertEqual(card.price, 29.99)

        card = cards[1]
        self.assertEqual(card.id, 2)
        self.assertEqual(card.expiration_date, date(2015, 12, 5))
        self.assertEqual(card.price, 15.00)

    def test_05_select_customer(self):
        customers = self.Customer.select()
        customer = list(customers)[0]
        self.assertEqual(customer.id, 1)
        self.assertEqual(customer.name, "George")
        self.assertEqual(customer.loyalty_card, None)

    def test_06_customer_has_card(self):
        customers = self.Customer.select()
        customer = list(customers)[0]
        cards = self.LoyaltyCard.select()
        card = list(cards)[1]
        customer.loyalty_card = card
        customer.update()

    def test_07_select_customer(self):
        customers = self.Customer.select()
        customer = list(customers)[0]
        self.assertEqual(customer.id, 1)
        self.assertEqual(customer.name, "George")
        self.assertEqual(customer.loyalty_card, {'id': 2})

    def test_08_select_card(self):
        cards = self.LoyaltyCard.select()
        card = list(cards)[1]
        self.assertEqual(card.id, 2)
        self.assertEqual(card.customer_id, 1)
        self.assertEqual(card.expiration_date, date(2015, 12, 5))
        self.assertEqual(card.price, 15.00)


class TestCarWheelSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        MetaResource.clear()

        class Car(Resource):
            numberplate = IntegerField(primary_key=True)
            name = StringField()
            wheels = Has('Wheel', '0..*')

        class Wheel(Resource):
            name = StringField()

        data_base = DataBase('sqlite', database=':memory:', isolation_level=None)
        MetaResource.initialize(data_base)
        MetaResource.create_tables()

        cls.Car = Car
        cls.Wheel = Wheel


class TestCrudCarWheelSchema(TestCarWheelSchema):
    def test_01_create_whell(self):
        whell = self.Wheel(name='toto')
        whell.save()

    def test_02_create_whell(self):
        whell = self.Wheel(name='tata')
        whell.save()

    def test_03_create_car(self):
        customer = self.Car(name="Bombo")
        customer.save()

    def test_04_select_whell(self):
        whells = list(self.Wheel.select())
        self.assertEqual(len(whells), 2)

        whell = whells[0]
        self.assertEqual(whell.id, 1)
        self.assertEqual(whell.name, "toto")

        whell = whells[1]
        self.assertEqual(whell.id, 2)
        self.assertEqual(whell.name, "tata")

    def test_05_select_car(self):
        cars = self.Car.select()
        car = list(cars)[0]
        self.assertEqual(car.numberplate, 1)
        self.assertEqual(car.name, "Bombo")
        self.assertEqual(car.wheels, [])

    def test_06_add_whells_to_car(self):
        cars = self.Car.select()
        car = list(cars)[0]
        whells = self.Wheel.select()

        # TODO use car.wheels.add(...) insteadof car.wheels = ...
        for whell in whells:
            car.wheels = whell
            car.update()

    def test_07_select_car(self):
        cars = self.Car.select()
        car = list(cars)[0]
        self.assertEqual(car.numberplate, 1)
        self.assertEqual(car.name, "Bombo")
        self.assertEqual(car.wheels, [{'id': 1}, {'id': 2}])


class TestWithHotelSchema(unittest.TestCase):

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


        data_base = DataBase('sqlite', database=':memory:', isolation_level=None)
        MetaResource.initialize(data_base)
        MetaResource.create_tables()


class TestCrud(TestWithHotelSchema):

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

    def test_02_10_iter_on_select_hotel(self):
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

    def test_02_20_iter_on_select_hotel_restrict_field(self):
        loop = iter(self.Hotel.select('name'))
        hotel = next(loop)

        self.assertEqual(hotel.id, NotSelectedField)
        self.assertEqual(hotel.name, 'Hotel California')
        self.assertEqual(hotel.address, NotSelectedField)

        hotel = next(loop)
        self.assertEqual(hotel.id, NotSelectedField)
        self.assertEqual(hotel.name, 'Tokio Hotel')
        self.assertEqual(hotel.address, NotSelectedField)

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


class TestResourceToDict(TestWithHotelSchema):

    def test_hotel_to_dict(self):
        hotel = self.Hotel(name="Tokio Hotel", address="125 main street")
        hotel.save()
        hotel = list(self.Hotel.select())[0]

        expected = dict(
            id=1,
            name="Tokio Hotel",
            address="125 main street",
            rooms=[]
        )
        self.assertEqual(hotel.to_dict(), expected)

    def test_hotel_with_room_to_dict(self):
        self.Room(hotel_id=1, number=1, bed_count=2).save()
        hotel = list(self.Hotel.select())[0]
        expected = dict(
            id=1,
            name="Tokio Hotel",
            address="125 main street",
            rooms=[dict(
                hotel_id=1,
                number=1,
                bed_count=2
            )]
        )
        self.assertEqual(hotel.to_dict(), expected)
