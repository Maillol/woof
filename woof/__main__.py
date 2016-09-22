#!/usr/bin/env python3

from .resource import MetaResource
from .server import config
from wsgiref.simple_server import make_server
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
os.environ.setdefault('{var_name}', os.path.join(PATH, '{conf_file_name}'))

from {{args.project_name}}.controllers import root_url
from woof.server import RESTServer, config
from woof.resource import MetaResource

MetaResource.initialize(config.database)

application = RESTServer(root_url)
""".lstrip().format(var_name=config.ENVIRON_VAR_NAME,
                    conf_file_name=config.DEFAULT_FILE_NAME)


CONF_TEMPLATE = """
{{
  "database": {{
    "database": "{args.project_name}.db",
    "provider": "sqlite"
  }}
}}
""".lstrip()

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
        os.environ[config.ENVIRON_VAR_NAME] = args.path_to_conf

    if args.pypath is not None:
        sys.path.insert(0, args.pypath)

    try:
        controller = importlib.import_module(args.application + '.controllers')
    except ImportError:
        print("Error: No module named `{}.controllers' found in PYTHONPATH".format(args.application))
        print("PYTHONPATH:")
        for path in sorted(sys.path):
            print("\t{}".format(path))
        print("Try to use '--py-path' option in order to specify directories to search for `{}' package.".format(args.application))
    else:     
        MetaResource.initialize(config.database)
        MetaResource.create_tables()


def run_server(args):
    """
    Launch the development server.
    """

    if args.path_to_conf is not None:
        os.environ[config.ENVIRON_VAR_NAME] = args.path_to_conf

    else:
        os.environ.setdefault(config.ENVIRON_VAR_NAME,
                              os.path.join(args.project_dir, config.DEFAULT_FILE_NAME))

    sys.path.insert(0, args.project_dir)
    wsgi = importlib.import_module('wsgi')
    server = make_server('', args.port, wsgi.application)
    server.serve_forever()


def start_project(args):
    """
    Create directory structure for a new project.

       {project}
        +-- {project}
        |    +-- __init__.py
        |    +-- controllers.py
        |    +-- models.py
        +-- config.json
        +-- wsgi.py
    """
    pkg = args.project_name
    sub_pkg = os.path.join(args.project_name, args.project_name)

    os.mkdir(pkg)
    os.mkdir(sub_pkg)
    wsgi_file_name = os.path.join(pkg, 'wsgi.py')
    conf_file_name = os.path.join(pkg, config.DEFAULT_FILE_NAME)
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

    class PathExist:
        """
        Factory to test if path is an existing file or directory
        """

        def __init__(self, is_dir=False):
            """
            String must be an existing file or dir if is_dir is true
            """
            self.dir_expected = is_dir
            self.file_expected = not is_dir

        def __call__(self, string):
            """
            Return absolute path of string if string is an existing path.
            """
            if self.dir_expected and not os.path.isdir(string):
                msg = "'{}' isn't directory".format(string)
                raise argparse.ArgumentTypeError(msg)

            if self.file_expected and not os.path.isfile(string):
                msg = "'{}' isn't file".format(string)
                raise argparse.ArgumentTypeError(msg)

            return os.path.abspath(string)

    parser = argparse.ArgumentParser('Woof')
    subparsers = parser.add_subparsers(help="See 'woof <command> -h' for more information on a specific command.")

    start_project_parser = subparsers.add_parser('startproject', 
                                                 help="Creates a new project directory with application "
                                                      "package structure and configuration file in the "
                                                      "current directory")
    start_project_parser.add_argument("project_name", metavar="project-name", type=module_name)
    start_project_parser.set_defaults(func=start_project)

    create_db_parser = subparsers.add_parser('createdb', help='Generates database')
    create_db_parser.add_argument("application", metavar="application-package")
    create_db_parser.add_argument("--conf", metavar="configuration-file", action='store',
                                  help='path to configuration file', dest="path_to_conf",
                                  type=PathExist())
    create_db_parser.add_argument("--py-path", metavar="py-path", action='store',
                                  type=PathExist(is_dir=True), dest="pypath", default=os.getcwd(),
                                  help='path to directory containing python package (default: %(default)s)')
    create_db_parser.set_defaults(func=create_db)

    run_server_parser = subparsers.add_parser('runserver', help="Runs a woof application on a local development server")
    run_server_parser.add_argument("project_dir", metavar="project-directory",
                                   type=PathExist(is_dir=True))
    run_server_parser.add_argument("--conf", metavar="configuration-file", action='store',
                                   help='path to configuration file', dest="path_to_conf",
                                   type=PathExist())
    run_server_parser.add_argument("--port", action='store', help='port to listen',
                                   dest="port", type=int, default=8080)
    run_server_parser.set_defaults(func=run_server)

    try:
        user_args = parser.parse_args()
    except SystemExit:
        return 1

    if hasattr(user_args, 'func'):
        try:
            user_args.func(user_args)
        except:
            traceback.print_exc()
            return 1
    else:
        parser.parse_args(['-h'])

    return 0

if __name__ == '__main__':
    sys.exit(main())

