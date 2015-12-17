#!/usr/bin/env python3
from .sqltranslator import MetaSQLTranslator

import threading
import importlib


class IntegrityError(Exception):
    pass


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
        module = importlib.import_module(connector_adapter.PROVIDER_MODULE)
        self.connector = module.connect
        self.integrity_error = module.IntegrityError
        self.connection_parameters = connector_adapter(connection_parameters).connection_parameters

    def execute(self, sql_query, parameters=()):
        connection = self.pool.setdefault(threading.current_thread(),
                                          self.connector(**self.connection_parameters))
        cursor = connection.cursor()
        try:
            cursor.execute(sql_query, parameters)
            return cursor
        except self.integrity_error as error:
            raise IntegrityError(error.args[0])


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


class ConnectorAdapter(metaclass=MetaConnectorAdapter):
    """
    Class base to translate parameters of connection to the concrete database connector.
    after instantiation, translated parameters are accessible by connection_parameters attribute
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
            translated_kwargs[translated_name] = parameters[std_name]

        for std_name, translated_name in cls.OPTIONAL_ARGS.items():
            if std_name in parameters:
                translated_kwargs[translated_name] = parameters[std_name]

        return translated_kwargs


class SqliteConnectorAdapter(ConnectorAdapter):
    EXPECTED_ARGS = {'database': 'database'}
    OPTIONAL_ARGS = {'timeout': 'timeout',
                     'cached_statements': 'cached_statements',
                     'isolation_level': 'isolation_level'}
    PROVIDER_MODULE = 'sqlite3'


class MysqlConnectorAdapter(ConnectorAdapter):
    EXPECTED_ARGS = {'host': 'host',
                     'user': 'user',
                     'password': 'password',
                     'database': 'db'}
    OPTIONAL_ARGS = {'charset': 'charset'}
    PROVIDER_MODULE = 'pymysql'


class PostgresqlConnectorAdapter(ConnectorAdapter):
    EXPECTED_ARGS = {}
    OPTIONAL_ARGS = {}
    PROVIDER_MODULE = 'pyPgSQL'
