## Woof - WSGI REST Framework

Woof is simple open source Python3 framework to develop API REST on database.

## Example

Create a new project 

```bash
woof startproject hotel
```

### Define your resources in models.py

__File: hotel/hotel/models.py__

```python
from woof.resource import Resource, StringField, IntegerField, ComposedBy


class Hotel(Resource):
    name = StringField()
    address = StringField()
    rooms = ComposedBy('Room')


class Room(Resource):
    number = IntegerField(weak_id=True)
    bed_count = IntegerField()
```

### Define your entry point in controllers.py

__hotel/hotel/controllers.py__

```python
from woof.url import EntryPoint
from models import Hotel, Room

root_url = EntryPoint('/api')  # Define API URL.

root_url.crud('/hotels/[id]', Hotel)  # Generate controllers using resource.

# Or write specific controllers
@root_url.post('/hotels/{hotel_id}/rooms')
def create_room(body, hotel_id):
    body["hotel_id"] = hotel_id
    new_room = Room(**body)
    new_room.save()
    return new_room

@root_url.delete('/hotels/{hotel_id}/rooms/{room_id}')
def delete_room(hotel_id, room_id):
    old_room = list(Room.select().where(
        (Room.hotel_id == hotel_id) &
        (Room.id == room_id)))[0]
    old_room.delete()
```

### Create database and start your WSGI server such as gunicorn.

```bash
$ cd hotel
$ woof createdb demo
$ gunicorn wsgi
```

## License
    GNU General Public License, Version 3. (GPLv3)
