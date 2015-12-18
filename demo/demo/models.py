#!/usr/bin/env python3

from msf.resource import (Resource,
                          association,
                          StringField,
                          IntegerField,
                          ComposedBy,
                          DateField)


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
