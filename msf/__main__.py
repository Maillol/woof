#!/usr/bin/env python3

from .resource import MetaResource
from .msf import config
import argparse
import re
import os
import importlib


WSGI_TEMPLATE = """
#!/usr/bin/env python3

import sys
import os

PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PATH)
os.environ.setdefault('MSF_CONFIG', os.path.join(PATH, 'conf.json'))

from {args.project_name}.controllers import root_url
from msf.msf import RESTServer, config
from msf.resource import MetaResource

MetaResource.initialize(config.database)

application = RESTServer(root_url)
""".lstrip()

CONF_TEMPLATE = """
{
  "database": {
    "database": "demo.db",
    "provider": "sqlite"
  }
}
"""

CTRL_TEMPLATE = """
#!/usr/bin/env python3

from msf.url import EntryPoint
# from .models import ...

root_url = EntryPoint('/api')
""".lstrip()


def create_db(args):
    """
    Read configuration file and create database.
    """
    if args.path_to_conf is not None:
        os.environ.setdefault('MSF_CONFIG', args.path_to_conf)

    importlib.import_module(args.ctrl)
    MetaResource.initialize(config.database)
    MetaResource.create_tables()


def start_project(args):
    """
    Create directory structure for a new project.

       {project}
        +-- {project}
        |    +-- __init__.py
        |    +-- controllers.py
        |    +-- models.py
        +-- conf.json
        +-- wsgi.py
    """
    pkg = args.project_name
    sub_pkg = os.path.join(args.project_name, args.project_name)

    os.mkdir(pkg)
    os.mkdir(sub_pkg)
    wsgi_file_name = os.path.join(pkg, 'wsgi.py')
    conf_file_name = os.path.join(pkg, 'config.json')
    models_file_name = os.path.join(sub_pkg, 'models.py')
    ctrl_file_name = os.path.join(sub_pkg, 'controllers.py')

    open(os.path.join(sub_pkg, '__init__.py'), 'w').close()
    with open(wsgi_file_name, "w") as file:
        file.write(WSGI_TEMPLATE.format(args=args))
    with open(conf_file_name, "w") as file:
        file.write(CONF_TEMPLATE)
    with open(models_file_name, "w") as file:
        file.write("from msf.resource import Resource")
    with open(ctrl_file_name, "w") as file:
        file.write(CTRL_TEMPLATE)


def main():
    """
    Programme entry point.
    """

    def module_name(string):
        """
        string must be a valid python module name which doesn't exist.
        """
        if re.match('^[a-z][_a-z]+$', string) is None:
            msg = "name must be all-lowercase names without spaces or digits"
            raise argparse.ArgumentTypeError(msg)
        if os.path.exists(string):
            msg = "directory '{}' exists".format(string)
            raise argparse.ArgumentTypeError(msg)
        return string

    def path_exist(string):
        """
        string must be an existing file.
        """
        if not os.path.isfile(string):
            msg = "'{}' isn't file".format(string)
            raise argparse.ArgumentTypeError(msg)
        return string

    parser = argparse.ArgumentParser('MSF')
    subparsers = parser.add_subparsers(help='sub-command help')

    start_project_parser = subparsers.add_parser('startproject')
    start_project_parser.add_argument("project_name", metavar="project-name",  type=module_name)
    start_project_parser.set_defaults(func=start_project)

    create_db_parser = subparsers.add_parser('createdb')
    create_db_parser.add_argument("ctrl", metavar="controllers-module")
    create_db_parser.add_argument("--conf", metavar="configuration file", action='store',
                                  help='path to configuration file', dest="path_to_conf", type=path_exist)
    create_db_parser.set_defaults(func=create_db)

    user_args = parser.parse_args()
    if hasattr(user_args, 'func'):
        user_args.func(user_args)
    else:
        parser.parse_args(['-h'])


if __name__ == '__main__':
    main()
