#!/usr/bin/env python3

from msf.url import EntryPoint
from .models import Hotel, Person

root_url = EntryPoint('/api')

root_url.crud('/hotels/[hotel_id]', Hotel)
root_url.crud('/persons/[person_id]', Person)

