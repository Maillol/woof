#!/usr/bin/env python3

from woof.url import EntryPoint
from .models import Hotel, Person, Room

root_url = EntryPoint('/api')

root_url.crud('/hotels/[id]', Hotel)
root_url.crud('/hotels/{hotel_id}/rooms/[id]', Room)
root_url.crud('/persons/[id]', Person)

