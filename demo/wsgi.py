#!/usr/bin/env python3

import sys
import os

PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PATH)
os.environ.setdefault('MSF_CONFIG', os.path.join(PATH, 'conf.json'))

from demo.controllers import root_url
from msf.server import RESTServer, config
from msf.resource import MetaResource

MetaResource.initialize(config.database)

application = RESTServer(root_url)
