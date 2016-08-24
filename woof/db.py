#!/usr/bin/env python3
from .sqltranslator import MetaSQLTranslator

import threading
import importlib
import os


class Error(Exception):
    """
    Exception that is the base class of all other error exceptions.
    You can use this to catch all errors with one single except statement
    """


class InterfaceError(Error):
    """
    Exception raised for errors that are related to the database interface
    rather than the database itself.
    """


class DatabaseError(Error):
    """
    Exception raised for errors that are related to the database.
    """


class DataError(DatabaseError):
    """
    Exception raised for errors that are due to problems with the processed data
    like division by zero, numeric value out of range, etc.
    """


class OperationalError(DatabaseError):
    """
    Exception raised for errors that are related to the database's operation and not
    necessarily under the control of the programmer, e.g. an unexpected disconnect occurs,
    the data source name is not found, a transaction could not be processed, a memory
    allocation error occurred during processing, etc.
    """


class IntegrityError(DatabaseError):
    """
    Exception raised when the relational integrity of the database is affected,
    e.g. a foreign key check fails.
    """


class InternalError(DatabaseError):
    """
    Exception raised when the database encounters an internal error,
    e.g. the cursor is not valid anymore, the transaction is out of sync, etc.
    """


class ProgrammingError(DatabaseError):
    """
    Exception raised for programming errors, e.g. table not found or already exists,
    syntax error in the SQL statement, wrong number of parameters specified, etc.
    """


class NotSupportedError(DatabaseError):
    """
    Exception raised in case a method or database API was used which is not supported by the database,
    e.g. requesting a .rollback() on a connection that does not support transaction or has transactions turned off.
    """


PEP_249_ERROR = {
    "Error": Error,
    "InterfaceError": InterfaceError,
    "DatabaseError": DatabaseError,
    "DataError": DataError,
    "OperationalError": OperationalError,
    "IntegrityError": IntegrityError,
    "InternalError": InternalError,
    "ProgrammingError": ProgrammingError,
    "NotSupportedError": NotSupportedError
}


class DataBase:
    def __init__(self, provider, **connection_parameters):
        self.provider = provider
        self.connector = None
        self.pool = {}

        try:
            connector_adapter = MetaConnectorAdapter.PROVIDERS[provider]
        except KeyError:
            raise ValueError("'provider' parameter must be on of {}"
                             .format(', '.join(MetaConnectorAdapter.PROVIDERS)))

        self.sql_translator = MetaSQLTranslator.PROVIDERS[provider]
        self.module = importlib.import_module(connector_adapter.PROVIDER_MODULE)
        self.connector = self.module.connect
        self.error = self.module.Error
        self.connection_parameters = connector_adapter(connection_parameters).connection_parameters

    def execute(self, sql_query, parameters=()):
        connection = self.pool.setdefault(threading.current_thread(),
                                          self.connector(**self.connection_parameters))
        cursor = connection.cursor()
        try:
            cursor.execute(sql_query, parameters)
            return cursor
        except self.error as error:
            cls_error = PEP_249_ERROR[type(error).__name__]
            raise cls_error(error.args[0], sql_query, parameters)


class MetaConnectorAdapter(type):
    """
    Store connector adapter in PROVIDERS attribute. The key of PROVIDERS is
    lower-case class name without ConnectorAdapter suffix

    i.e: SqliteConnectorAdapter --> sqlite
    """

    PROVIDERS = {}

    def __init__(cls, name, bases, attrs):
        if name != 'ConnectorAdapter':
            if name.endswith('ConnectorAdapter'):
                provider_name = name[:-len('ConnectorAdapter')].lower()
                type(cls).PROVIDERS[provider_name] = cls
                cls.PROVIDER = provider_name
            else:
                raise ValueError("{} class name must end with by '{}'"
                                 .format(cls, 'ConnectorAdapter'))

            if 'EXPECTED_ARGS' not in attrs:
                raise AttributeError("{} class must have 'EXPECTED_ARGS' attribute"
                                     .format(cls))

            if not isinstance(attrs['EXPECTED_ARGS'], dict):
                raise TypeError('{} EXPECTED_ARGS attribute must be a dict'.format(cls))

            if 'OPTIONAL_ARGS' not in attrs:
                raise AttributeError("{} class must have 'OPTIONAL_ARGS' attribute"
                                     .format(cls))

            if not isinstance(attrs['OPTIONAL_ARGS'], dict):
                raise TypeError('{} OPTIONAL_ARGS attribute must be a dict'.format(cls))

            # Bound staticmethod and classmethod in the EXPECTED_ARGS and OPTIONAL_ARGS dict.
            for mtd_name, mtd in attrs.items():
                if isinstance(mtd, (staticmethod, classmethod)):
                    for k, v in attrs['EXPECTED_ARGS'].items():
                        if v is mtd:
                            attrs['EXPECTED_ARGS'][k] = getattr(cls, mtd_name)
                            break

                    for k, v in attrs['OPTIONAL_ARGS'].items():
                        if v is mtd:
                            attrs['OPTIONAL_ARGS'][k] = getattr(cls, mtd_name)
                            break


class ConnectorAdapter(metaclass=MetaConnectorAdapter):
    """
    Class base to translate parameters of connection to the concrete database connector.
    after instantiation, translated parameters are accessible by connection_parameters attribute.

    A ConnectorAdapter must have EXPECTED_ARGS and OPTIONAL_ARGS class attribute dict.
    The keys are the standards names such as (database, host, port, user, password ...) and
    the values are translated name to connect function parameters. A value can be a callable or
    unbound static or class method which translate parameters.
    """
    def __init__(self, connection_parameters):
        self.connection_parameters = self.translate_kwargs(connection_parameters)

    @classmethod
    def translate_kwargs(cls, parameters):
        """
        Use EXPECTED_ARGS and OPTIONAL_ARGS class attribute in order to check and translate
        parameters.
        """
        unexpected_kwargs = set(parameters) - (set(cls.EXPECTED_ARGS) | set(cls.OPTIONAL_ARGS))
        if unexpected_kwargs:
            raise TypeError("{} database provider got unexpected keywords arguments ({})"
                            .format(cls.PROVIDER, ', '.join(unexpected_kwargs)))

        missing_kwargs = set(cls.EXPECTED_ARGS) - set(parameters)
        if missing_kwargs:
            raise TypeError("missing required arguments ({}) to {} database provider"
                            .format(', '.join(str(e) for e in missing_kwargs),
                                    cls.PROVIDER))

        translated_kwargs = {}
        for std_name, translated_name in cls.EXPECTED_ARGS.items():
            if callable(translated_name):
                translated_kwargs.update(
                    translated_name(parameters[std_name]))
            else:
                translated_kwargs[translated_name] = parameters[std_name]
        for std_name, translated_name in cls.OPTIONAL_ARGS.items():
            if std_name in parameters:
                translated_kwargs[translated_name] = parameters[std_name]

        return translated_kwargs


class SqliteConnectorAdapter(ConnectorAdapter):

    @staticmethod
    def translate_database(database):
        if database != ':memory:' and not os.path.isabs(database):
            from .server import config
            path_to_conf = os.path.dirname(config.path_to_conf)
            database = os.path.join(path_to_conf, database)
        return dict(database=database)

    EXPECTED_ARGS = {'database': translate_database}
    OPTIONAL_ARGS = {'timeout': 'timeout',
                     'cached_statements': 'cached_statements',
                     'isolation_level': 'isolation_level'}
    PROVIDER_MODULE = 'sqlite3'


class MysqlConnectorAdapter(ConnectorAdapter):
    EXPECTED_ARGS = {'host': 'host',
                     'port': 'port',
                     'user': 'user',
                     'password': 'password',
                     'database': 'db'}
    OPTIONAL_ARGS = {'charset': 'charset'}
    PROVIDER_MODULE = 'pymysql'


class PostgresqlConnectorAdapter(ConnectorAdapter):
    EXPECTED_ARGS = {}
    OPTIONAL_ARGS = {}
    PROVIDER_MODULE = 'pyPgSQL'
