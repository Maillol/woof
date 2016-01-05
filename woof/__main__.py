#!/usr/bin/env python3

from .resource import MetaResource
from .server import config
import argparse
import re
import os
import sys
import importlib
import traceback


WSGI_TEMPLATE = """
#!/usr/bin/env python3

import sys
import os

PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PATH)
os.environ.setdefault('WOOF_CONFIG', os.path.join(PATH, 'conf.json'))

from {args.project_name}.controllers import root_url
from woof.server import RESTServer, config
from woof.resource import MetaResource

MetaResource.initialize(config.database)

application = RESTServer(root_url)
""".lstrip()

CONF_TEMPLATE = """
{{
  "database": {{
    "database": "{args.project_name}.db",
    "provider": "sqlite"
  }}
}}
"""

CTRL_TEMPLATE = """
#!/usr/bin/env python3

from woof.url import EntryPoint
# from .models import ...

root_url = EntryPoint('/api')
""".lstrip()


def create_db(args):
    """
    Read configuration file and create database.
    """
    if args.path_to_conf is not None:
        os.environ.setdefault('WOOF_CONFIG_FILE', args.path_to_conf)

    if args.pypath is not None:
        sys.path.insert(0, os.path.abspath(args.pypath))
    controller = importlib.import_module(args.ctrl)
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
        file.write(CONF_TEMPLATE.format(args=args))
    with open(models_file_name, "w") as file:
        file.write("from woof.resource import Resource")
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

    def path_to_module(string):
        """
        string must be a path to module through package name.
        """
        if re.match('^[a-z][\._a-z]+$', string) is None:
            msg = "name must be all-lowercase names separate by dot"
            raise argparse.ArgumentTypeError(msg)
        return string

    parser = argparse.ArgumentParser('Woof')
    subparsers = parser.add_subparsers(help='sub-command help')

    start_project_parser = subparsers.add_parser('startproject')
    start_project_parser.add_argument("project_name", metavar="project-name",  type=module_name)
    start_project_parser.set_defaults(func=start_project)

    create_db_parser = subparsers.add_parser('createdb')
    create_db_parser.add_argument("ctrl", metavar="controllers-module", type=path_to_module)
    create_db_parser.add_argument("--conf", metavar="configuration-file", action='store',
                                  help='path to configuration file', dest="path_to_conf", type=path_exist)
    create_db_parser.add_argument("--py-path", metavar="py-path", action='store',
                                  help='path to directory containing python package', dest="pypath")
    create_db_parser.set_defaults(func=create_db)

    try:
        user_args = parser.parse_args()
    except SystemExit:
        return 1

    try:
        if hasattr(user_args, 'func'):
            user_args.func(user_args)
        else:
            parser.parse_args(['-h'])
    except:
        traceback.print_exc()
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
