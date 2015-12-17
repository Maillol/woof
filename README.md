## MSF - WSGI REST Framework

MSF is simple open source Python3 framework to develop API REST on database.

## Example

### Define your resources

```python
from msf.resource import Resource, StringField, IntegerField, ComposedBy


class Hotel(Resource):
    name = StringField()
    address = StringField()
    rooms = ComposedBy('Room')


class Room(Resource):
    number = IntegerField(weak_id=True)
    bed_count = IntegerField()
```

### Define your entry point

```python
from msf.url import EntryPoint
from models import Hotel, Room

root_url = EntryPoint('/api')  # Define API URL.

root_url.crud('/hotels/[hotel_id]', Hotel)  # Generate controllers using resource.

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

## License
    GNU General Public License, Version 3. (GPLv3)
