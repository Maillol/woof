.. _quickstart:


*****************
Quick Start Guide
*****************

In this tutorial, we'll build a simple hotel booking application using the Woof framework and 
sqlite database.


Prerequisites
*************

You must have python 3.4 (or later)


Installation
************

You can install Woof via pip::

  > pip install woof

You may also get the latest, but unstable, Woof version by grabbing the source code from Github::

    $ git clone https://github.com/Maillol/woof.git
    $ cd woof
    $ python setup.py install


Create a new project
********************

To create an empty project, use **woof startproject** the command line::
    
    $ woof startproject hotel

This commande create a hotel directory in your current directory which look something like the following::

    hotel
    |--hotel
    |  |-- controllers.py
    |  |-- __init__.py
    |  `-- models.py
    |-- config.json
    `-- wsgi.py

The root directory contains hotel package, the config.json and wsgi.py.
By default, config.json is set to use sqlite and the database name is the same as project name with a *.db* suffix.
The hotel.controllers module will contain resource definitions and hotel.controllers will contain set of functions
which uses resources and are bond to an URL.


Define your resources
*********************

First up we're going to define resources in models.py file. Each resource must extend woof.resource.Resource class
and define severals fields.

Contents of ``hotel.models``::

    from woof.resource import (Resource,
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


The Hotel class has name and address StringField and an id field which is automatically created. 
The rooms field is a ComposedBy field. This field define composition relationship between two resource.
This means that a Room resource cannot be exist without a resource Hotel and you need to know the Hotel 
id to manipulate a Room.

The Room class define an IntegerField named number. The weak_id attribute set with True means that a Room
resource can be identified with number field and the id of an other resource (a hotel in this case). If you 
don't define a field with weak_id at true, Woof generate an IntegerField named weak_id for each Resource used
in ComposedBy fied.

The Rent class is decotated with the association decorator and become an association between Person and Room
resources. Rent id is composed by Person id, Room id and date.  


Define your controllers
***********************

The controllers module must have a root_url attribute which contains an EntryPoint object. 

Contents of ``hotel.controllers``::

    from woof.url import EntryPoint
    from .models import Hotel, Person, Room

    root_url = EntryPoint('/api')

    root_url.crud('/hotels/[id]', Hotel)
    root_url.crud('/hotels/{hotel_id}/rooms/[number]', Room)
    root_url.crud('/persons/[id]', Person)


An EntryPoint object has a crud method to create post get and delete a resource. The first parameter is an 
URL pattern and the next parameter is a Resource class. You must define in URL pattern where id can be set
by the user. The name surrounded by braces must be the resource id name used to manipulate specific resource.
The crud method will generate fives urls to manipulate the resource hotel:

+-------+-------------+-----------------------------+
| GET   | /hotels     |  Retrieves a list of hotels |  
+-------+-------------+-----------------------------+
| POST  | /hotels     |  Creates a new hotels       |
+-------+-------------+-----------------------------+
| GET   | /hotels/{id}|  Retrieves a specific hotels|
+-------+-------------+-----------------------------+
| PUT   | /hotels/{id}|  Updates hotels {id}        |
+-------+-------------+-----------------------------+
| DELETE| /hotels/{id}|  Deletes hotels {id}        |
+-------+-------------+-----------------------------+

The Room resource identifier is hotel_id + number fields, when we use crud method with Room resource,
we must use hotel_id and number in URL pattern.


Create database
***************

Before run your application, you must create database using **createdb** command in hotel directory::
    
    $ woof createdb hotel --py-path ./hotel --conf ./hotel/config.json


Run the development server
**************************

You can launch development server with **run-server** command::

    $ woof runserver hotel

By default, the server listens the port 8080 but you can use an other port with **--port** parameter.

And try it with curl or other client::

    $ curl -X POST http://127.0.0.1:8080/api/hotels -d '{"address": "123", "name": "toto"}'
    $ curl -X GET http://127.0.0.1:8080/api/hotels
    [{"name": "toto", "rooms": [], "address": "123", "id": 1}]

