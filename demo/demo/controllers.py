#!/usr/bin/env python3

from msf.url import EntryPoint
from .models import Hotel

root_url = EntryPoint('/api')

root_url.crud('/hotels/[hotel_id]', Hotel)

