from functools import partial
from decimal import Decimal
import datetime
from sqltranslater import *
from collections import OrderedDict

class DataBase:
    def __init__(self):
        self.connector = None
        self.provider = None
        self.connect_args = None
        self.sql_translater = None

    def initialize(self, database):
        if database == 'sqlite':
            import sqlite3 as connector
            self.sql_translater = SqliteTranslater

        elif database == 'mysql':
            #  mysql -u root -p ;create database msf
            import pymysql
            connector = pymysql.connect # (host='localhost', password="pwd", user='root', db='msf')
            self.sql_translater = MysqlTranslater

        elif database == 'postgres':
            from pyPgSQL import PgSQL as connector
            self.sql_translater = PostgresTranslater

        else:
            raise ValueError('initialize parameter must be on of "sqlite", "mysql", "postgres"')

        self.provider = database
        self.connector = connector

    def connect(self, *args):
        self.connect_args = args
        self.cursor = self.connector.connect(*args)

    def execute(self, sql_query, parameters=()):
        return self.cursor.execute(sql_query, parameters)


def to_underscore(name):
    """
    >>> to_underscore("FooBar")
    'foo_bar'
    >>> to_underscore("HTTPServer")
    'http_server'
    """
    if not name:
        return name
    iterator = iter(name)
    out = [next(iterator).lower()]
    last_is_upper = True
    parse_abbreviation = False
    for char in iterator:
        if char.isupper():
            if last_is_upper:
                parse_abbreviation = True
                out.append(char.lower())
            else:
                out.append('_' + char.lower())
            last_is_upper = True
        else:
            if parse_abbreviation:
                out.insert(-1, '_')
                parse_abbreviation = False
            out.append(char)
            last_is_upper = False
    return "".join(out)


class MetaResource(type):
    """
    Store resource and relationship between several resource throug resource fields.

    You can use MetaResource.register inorder to search ORM class using resource class Name.
    """

    db = DataBase()
    register = {} # {resource_class_name:
                  #     (ORM_cls, {refered_name_field: refered_resource_class_name, ...})}

    fields_types = {} # {name: {field_name: python_type_caster}}

    _starting_block = {}

    def __init__(cls, name, parent, attrs):
        if name != 'Resource':
            cls._fields = []
            id_fields = []
            weak_id_fields = []
            MetaResource._starting_block[name] = cls
            for field_name, field in attrs.items():
                if isinstance(field, Field):
                    field.name = field_name
                    cls._fields.append(field)
                    if field.primary_key:
                        id_fields.append(field)
                    if field.weak_id:
                        weak_id_fields.append(field)

            meta = attrs.setdefault('Meta', type('Meta', (), {}))
            if weak_id_fields and id_fields:
                raise TypeError("Resource with primary_key cannot have weak_id")
            #elif not (weak_id_fields or id_fields):
            #    cls.id = IntegerField(primary_key=True)
            #    cls.id.name = 'id'
            #    id_fields.append(cls.id)

            meta.primary_key = id_fields
            meta.weak_id = weak_id_fields
            if not hasattr(meta, 'constraints'):
                meta.constraints = []
            cls.Meta = meta

    @classmethod
    def __prepare__(self, cls, bases):
        return OrderedDict()

    # FIXME _build_foreign_key must raise error when Resource has weak_id without be referenced by an other resource
    @classmethod
    def _build_foreign_key(mcs):

        def add_field(resource, name, field, position=None):
            if position is None:
                position = len(resource._fields)
            resource._fields.insert(position, field)
            field.name = name
            setattr(resource, name, field)
            if field.primary_key:
                resource.Meta.primary_key.append(field)
            elif field.weak_id:
                resource.Meta.weak_id.append(field)

        def make_id_if_not_exist(resource):
            if not resource.Meta.primary_key:
                add_field(resource, 'id', IntegerField(primary_key=True), 0)

        def make_weak_id_if_not_exist(resource):
            if not resource.Meta.weak_id:
                add_field(resource, 'weak_id', IntegerField(weak_id=True), 0)

        # Generate weak_id:
        # TODO generate reated_field...
        for resource_name, resource in MetaResource._starting_block.items():
            for field in resource._fields:
                if isinstance(field, ComposedBy):
                    weak_entity = MetaResource._starting_block[field.other_resource]
                    if weak_entity.Meta.primary_key:
                        raise TypeError(weak_entity +
                                        ' cannot have primary key because it is contained in ' + resource)
                    make_weak_id_if_not_exist(weak_entity)
                    weak_entity.Meta.referenced_by = resource

        # Generate id
        for resource_name, resource in MetaResource._starting_block.items():
            if not resource.Meta.weak_id:
                make_id_if_not_exist(resource)

        for resource_name, resource in MetaResource._starting_block.items():
            resource.Meta.constraints.append(
                PrimaryKey([e[0] for e in resource._id_fields_names()]))
            for field in resource._fields:
                if isinstance(field, ComposedBy):
                    other_resource = MetaResource._starting_block[field.other_resource]
                    id_names = other_resource._id_fields_names()
                    fk_names = id_names[len(other_resource.Meta.weak_id):]
                    ref_id = resource._id_fields_names()

                    for fk_name, fk_field in fk_names:
                        add_field(other_resource, fk_name, type(fk_field)())

                    other_resource.Meta.constraints.append(
                        ForeignKey([e[0] for e in fk_names], resource.table_name(),
                                   [e[0] for e in resource._id_fields_names()])
                    )

    @classmethod
    def _build_orm_layer(mcs):
        for name, cls in MetaResource._starting_block.items():
            mcs.register[name] = (
                cls,
                {field.name: field.other_resource
                 for field in cls._fields
                 if isinstance(field, ComposedBy)}
            )

            mcs.fields_types[name] = {
                field.name: field.to_py_factory
                for field in cls._fields
            }

    @classmethod
    def _name_to_ref(cls):
        """
        Optimize register

        from:
            {resource_class_name:
                (ORM_cls, {refered_name_field: refered_resource_class_name, ...})}

        to:
            {resource_class_name:
                (ORM_cls, {refered_name_field: register[refered_resource_class_name], ...})}

        """
        for entity_name, (_, extern) in cls.register.items():
            for attr_name, cls_name in extern.items():
                extern[attr_name] = cls.register[cls_name]


    @classmethod
    def create_tables(mcs, resources_names=None):
        """
        Create table for each resource name in resources_names parameters.
        if resources_names is None, the tables for all resources in registry are created.

        resources_names - list of resource name.
        """
        if resources_names is None:
            resources_names = list(mcs.register)
        for resource_name in resources_names:
            resource = mcs.register[resource_name][0]
            mcs.db.execute(mcs.db.sql_translater.translate(resource))
        for resource_name in resources_names:
            resource = mcs.register[resource_name][0]
            mcs.db.execute(mcs.db.sql_translater.translate_fk(resource))

    @classmethod
    def initialize(mcs, database, host):
        mcs._build_foreign_key()
        mcs._build_orm_layer()
        mcs._name_to_ref()
        mcs.db.initialize(database)
        mcs.db.connect(host)

    @classmethod
    def clear(mcs):
        mcs.register = {}
        mcs.fields_types = {}
        mcs._resource_fields = []
        mcs._starting_block = {}


class PrimaryKey:
    def __init__(self, fields):
        self.fields = fields

class ForeignKey:
    def __init__(self, fields, referenced_resource, referenced_fields):
        self.fields = fields
        self.referenced_resource = referenced_resource
        self.referenced_fields = referenced_fields


class Query:
    class Cursor():
        def __init__(self, cursor, resource, field_names):
            self._cursor = cursor
            self._resource = resource
            self._field_names = field_names

        def __next__(self):
            values = self._cursor.fetchone()
            if values is None:
                raise StopIteration()
            return self._resource(**dict(zip(self._field_names, values)))


    def __init__(self, resource):
        self.resource = resource
        self.join_criteria = []
        self.where_fields = []
        self.where_values = []

    def join(self, resource, on=None):
        self.join_criteria.append((resource, on))
        return self

    def where(self, criteria):
        field, value = criteria
        self.where_fields.append(field)
        self.where_values.append(value)
        return self

    def __iter__(self):
        field_names = [field.name
                       for field in self.resource._fields
                       if not isinstance(field, ComposedBy)]

        sql = "SELECT {} FROM {}".format(
            ', '.join(field_names), self.resource.table_name())

        if self.where_fields:
            sql += " WHERE {}".format(" AND ".join(self.where_fields))
        
        cursor = type(self.resource).db.execute(sql, self.where_values);
        return self.Cursor(cursor, self.resource, field_names)


class Resource(metaclass=MetaResource):

    def __init__(self, **kwargs):
        self._state = {}
        expected_fields_name = set(field.name for field in self._fields)
        got_fields = set(kwargs)
        wrong_fields = got_fields - set(expected_fields_name)

        if wrong_fields:
            raise TypeError("{}() got an unexpected keyword argument '{}'"
                            .format(type(self.__name__),
                                    next(iter(wrong_fields))))

        for field_name in got_fields:
            setattr(self, field_name, kwargs[field_name])

    @classmethod
    def table_name(cls):
        return to_underscore(cls.__name__)

    @classmethod
    def _id_fields_names(cls):
        if cls.Meta.primary_key:
            return [(field.name, field) for field in cls.Meta.primary_key]
        else:
            prefix = cls.Meta.referenced_by.table_name()
            fields = [(field.name, field) for field in cls.Meta.weak_id]
            fields.extend(
                ('{}_{}'.format(prefix, field_name), field)
                for (field_name, field) in cls.Meta.referenced_by._id_fields_names()
            )
            return fields

    @classmethod
    def select(cls, **kwargs):
        return Query(cls)

    def save(self):
        fields = []
        values = []
        for field, value in self._state.items():
            fields.append(field)
            values.append(value)

        query = ('INSERT INTO {} ({}) VALUES ({});'
                 .format(self.table_name(),
                         ', '.join(fields),
                         ','.join('?' * len(fields))))
        type(type(self)).db.execute(query, values)


class Field:

    to_py_factory = None

    class Condition:
        def __init__(self, field_name):
            self._field_name = field_name

        def __eq__(self, value):
            return '{} = ?'.format(self._field_name), value

        def __ne__(self, value):
            return '{} != ?'.format(self._field_name), value

        def __lt__(self, value):
            return '{} < ?'.format(self._field_name), value

        def __le__(self, value):
            return '{} <= ?'.format(self._field_name), value

        def __gt__(self, value):
            return '{} > ?'.format(self._field_name), value

        def __ge__(self, value):
            return '{} >= ?'.format(self._field_name), value


    def __init__(self, writable=True, readable=True, unique=False, nullable=False, primary_key=False, weak_id=False):
        self.unique = unique
        self.nullable = nullable
        self.writable = writable
        self.readable = readable
        self.weak_id = weak_id
        self.primary_key = primary_key

    @property
    def null(self):
        if self.nullable:
            return 'NULL'
        return 'NOT NULL'

    def __get__(self, obj, cls=None):
        if obj is None:
            return self.Condition(
                '{}.{}'.format(cls.table_name(), self.name))
        return self.to_py_factory(obj._state[self.name])

    def __set__(self, obj, value):
        obj._state[self.name] = value


class FloatField(Field):
    to_py_factory = float


class BinaryField(Field):
    to_py_factory = bytes


class DateField(Field):
    to_py_factory = datetime.date


class DateTimeField(Field):
    to_py_factory = datetime.datetime


class NumericField(Field):

    def __init__(self, writable=True, readable=True, unique=False, nullable=False, primary_key=False, weak_id=False, precision=10, scale=3):
        """
        precision: number of digits
        scale: number of digits after the decimal
        """
        super().__init__(writable, readable, unique, nullable, primary_key, weak_id)
        self.precision = precision
        self.scale = scale

    @staticmethod
    def to_py_factory(value):
         return Decimal(str(value))


class IntegerField(Field):

    to_py_factory = int

    def __init__(self, writable=True, readable=True, unique=False, nullable=False, primary_key=False, weak_id=False,
                 min_value=-2147483648, max_value=2147483647):
        super().__init__(writable, readable, unique, nullable, primary_key, weak_id)
        try:
            self.min_value = int(min_value)
        except ValueError:
            raise TypeError('min_value must be an integer (got {})'.format(type(min_value)))

        try:
            self.max_value = int(max_value)
        except ValueError:
            raise TypeError('max_value must be an integer (got {})'.format(type(max_value)))

        if (self.min_value >= max_value):
            raise ValueError('max_value must be greater than min_value')

class StringField(Field):
    to_py_factory = str
    def __init__(self, writable=True, readable=True, unique=False, nullable=False, primary_key=False, weak_id=False,
                 length=255, fixe_length=False):
        super().__init__(writable, readable, unique, nullable, primary_key, weak_id)
        self.length = int(length)
        self.fixe_length = int(fixe_length)


class ComposedBy(Field):
    def __init__(self, other_resource, cardinality='0..*', related_name=None, writable=True, readable=True):
        if not isinstance(other_resource, str):
            raise TypeError('other_resource must be str (got {})'.format(type(other_resource)))
        if len(cardinality) == 4 and cardinality[1:3] == '..':
            card_min, card_max =  cardinality.split('..')
        elif cardinality == '1':
            card_min = card_max = cardinality
        elif cardinality == '*':
            card_min, card_max = ('0', '*')
        else:
            raise ValueError('cardinality must be one ("1", "0..1", "1..*", "*")')

        super().__init__(writable, readable, card_max=="1", card_min=="0")
        self.other_resource = other_resource
        self.related_name = related_name
        self.card_min = card_min
        self.card_max = card_max

        if self.related_name is None:
            self.related_name = to_underscore(other_resource) + '_ref'

    def __get__(self, obj, cls=None):
        resource = MetaResource.register[self.other_resource][0]
        query = resource.select()
        for field in obj._id_fields_names():
            query.where(
                getattr(resource, obj.table_name() + '_' + field[0]) == getattr(obj, field[0])
            )
        return query

    def __set__(self, obj, value):
        obj._state[self.name] = value


class ResourceField(Field):
    to_py_factory = int # FIXME must be resource_name primary_key

    def __init__(self, resource_name, related_name=None, writable=True, readable=True, unique=False, nullable=False):
        super().__init__(writable, readable, unique, nullable)
        self.resource_proxy = peewee.Proxy()
        self.type_field = partial(self.type_field,
                                  self.resource_proxy, related_name=related_name)
        self.resource_name = resource_name
        self.related_name = related_name

    def __repr__(self):
        return '<ResourceField to %s>' % self.resource_name

    @property
    def referenced_resource(self):
        MetaResource.register[self.related_name][0]


__all__= ['NumericField', 'ResourceField', 'ComposedBy', 'StringField', 'IntegerField', 'BinaryField',
          'Resource', 'MetaResource', 'DateTimeField', 'DateField', 'FloatField']
