#!/usr/bin/env python3
from .sqltranslator import (MysqlTranslator,
                            SqliteTranslator,
                            PostgresTranslator)

import threading

class IntegrityError(Exception):
    pass


class DataBase:
    def __init__(self, provider, **connection_parameters):
        self.provider = provider
        self.connector = None
        self.cursor = None
        self.connection_parameters = connection_parameters
        self.pool = {}

        if provider == 'sqlite':
            import sqlite3
            self.connector = sqlite3.connect
            self.integrity_error = sqlite3.IntegrityError
            self.sql_translator = SqliteTranslator

        elif provider == 'mysql':
            #  mysql -u root -p ;create database msf
            import pymysql
            self.connector = pymysql.connect # (host='localhost', password="pwd", user='root', db='msf')
            self.integrity_error = pymysql.IntegrityError
            self.sql_translator = MysqlTranslator

        elif provider == 'postgres':
            from pyPgSQL import PgSQL
            self.connector = PgSQL.connect
            self.integrity_error = None
            self.sql_translator = PostgresTranslator

        else:
            raise ValueError('initialize parameter must be on of "sqlite", "mysql", "postgres"')

    def execute(self, sql_query, parameters=()):
        connection = self.pool.setdefault(threading.current_thread(),
                                          self.connector(**self.connection_parameters))

        cursor = connection.cursor()
        try:
            return cursor.execute(sql_query, parameters)
        except self.integrity_error as error:
            raise IntegrityError(error.args[0])
