#!/usr/bin/env python3

from msf.msf import RESTServer
from msf.db import DataBase
from msf.resource import MetaResource
from .controlers import root_url

database = DataBase('sqlite', database='test.db')
MetaResource.initialize(database)
MetaResource.create_tables()

application = RESTServer(root_url)
