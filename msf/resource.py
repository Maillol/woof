from collections import OrderedDict
import datetime
from decimal import Decimal
from .sqltranslator import (MysqlTranslator,
                            SqliteTranslator,
                            PostgresTranslator)


class IntegrityError(Exception):
    pass


class DataBase:
    def __init__(self):
        self.connector = None
        self.provider = None
        self.connect_args = None
        self.sql_translator = None
        self.integrity_error = None

    def initialize(self, database):
        if database == 'sqlite':
            import sqlite3
            connector = sqlite3.connect
            self.integrity_error = sqlite3.IntegrityError
            self.sql_translator = SqliteTranslator
            Condition.substitution = '?'

        elif database == 'mysql':
            #  mysql -u root -p ;create database msf
            import pymysql
            connector = pymysql.connect # (host='localhost', password="pwd", user='root', db='msf')
            self.sql_translator = MysqlTranslator
            Condition.substitution = '%s'

        elif database == 'postgres':
            from pyPgSQL import PgSQL as connector
            self.sql_translator = PostgresTranslator
            Condition.substitution = '%s'

        else:
            raise ValueError('initialize parameter must be on of "sqlite", "mysql", "postgres"')

        self.provider = database
        self.connector = connector

    def connect(self, *args, **kwargs):
        self.connect_args = args
        self.cursor = self.connector(*args, **kwargs)

    def execute(self, sql_query, parameters=()):
        try:
            return self.cursor.execute(sql_query, parameters)
        except self.integrity_error as error:
            raise IntegrityError(error.args[0])


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


def association(**resources):
    def decorator(cls):
        cls._init_nested_meta()
        cls.Meta.required_resource_for_pk = list(resources)
        cls.Meta.association_meta_data = resources
        return cls
    return decorator


class MetaResource(type):
    """
    Store resource and relationship between several resource throug resource fields.

    You can use MetaResource.register in order to search ORM class using resource class Name.
    """

    db = DataBase()
    register = {} # {resource_class_name:
                  #     (ORM_cls, {refered_name_field: refered_resource_class_name, ...})}

    fields_types = {} # {name: {field_name: python_type_caster}}

    _starting_block = {}

    def _init_nested_meta(cls):
        """
        Initializes nested class in Resource class.

            Meta:
                weak_id = []
                primary_key = [] # used by get_id_fields_names method
                constraints = {'pk': None, # A PrimaryKey object
                               'fks': []}
                required_resource_for_pk = []
                association_meta_data = []
        """
        if not hasattr(cls, 'Meta'):
            cls.Meta = type('Meta', (), {})
        if not hasattr(cls.Meta, 'constraints'):
            cls.Meta.constraints = {}
        cls.Meta.constraints.setdefault('pk', None)
        cls.Meta.constraints.setdefault('fks', [])
        if not hasattr(cls.Meta, 'primary_key'):
            cls.Meta.primary_key = []
        if not hasattr(cls.Meta, 'weak_id'):
            cls.Meta.weak_id = []
        if not hasattr(cls.Meta, 'required_resource_for_pk'):
            cls.Meta.required_resource_for_pk = []
        if not hasattr(cls.Meta, 'association_meta_data'):
            cls.Meta.association_meta_data = []

    def __init__(cls, name, parent, attrs):
        if name != 'Resource':
            MetaResource._starting_block[name] = cls
            cls._init_nested_meta()
            cls._table_name = to_underscore(cls.__name__)
            cls._fields = []
            for field_name, field in attrs.items():
                if isinstance(field, Field):
                    field.name = field_name
                    cls._fields.append(field)
                    if field.primary_key:
                        cls.Meta.primary_key.append(field)
                    if field.weak_id:
                        cls.Meta.weak_id.append(field)

            if cls.Meta.weak_id and cls.Meta.primary_key:
                raise TypeError("Resource with primary_key cannot have weak_id")

    @classmethod
    def __prepare__(self, cls, bases):
        return OrderedDict()

    # FIXME _build_foreign_key must raise error when Resource has weak_id without be referenced by an other resource
    @classmethod
    def _build_foreign_key(mcs):

        def get_id_fields_names(cls):
            if cls.Meta.weak_id:
                fields = [(field.name, field) for field in cls.Meta.weak_id]
                for required_cls in cls.Meta.required_resource_for_pk:
                    prefix = required_cls._table_name
                    fields.extend(
                        ('{}_{}'.format(prefix, field_name), field)
                        for (field_name, field)
                        in get_id_fields_names(required_cls)
                    )
                return fields

            if cls.Meta.required_resource_for_pk:
                fields = [(field.name, field) for field in cls.Meta.primary_key]
                for required_cls_name in cls.Meta.required_resource_for_pk:
                    required_cls = type(cls)._starting_block[required_cls_name]
                    prefix = required_cls._table_name
                    fields.extend(
                        ('{}_{}'.format(prefix, field_name), field)
                        for (field_name, field)
                        in get_id_fields_names(required_cls)
                    )
                return fields

            return [(field.name, field) for field in cls.Meta.primary_key]

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
                    weak_entity.Meta.required_resource_for_pk = [resource]

        # Generate id
        for resource_name, resource in MetaResource._starting_block.items():
            if not resource.Meta.weak_id:
                make_id_if_not_exist(resource)

        # Set _id_fields_name
        for resource in MetaResource._starting_block.values():
            resource._id_fields_names = get_id_fields_names(resource)
            resource.Meta.constraints['pk'] = PrimaryKey([e[0] for e in resource._id_fields_names])

        for resource_name, resource in MetaResource._starting_block.items():
            if resource.Meta.association_meta_data:
                for other_resource_name, card in resource.Meta.association_meta_data.items():
                    other_resource = MetaResource._starting_block[other_resource_name]

                    fk_names = [('{}_{}'.format(other_resource._table_name, name), field)
                                for name, field
                                in other_resource._id_fields_names]

                    for fk_name, fk_field in fk_names:
                        add_field(resource, fk_name, type(fk_field)())

                    setattr(other_resource, resource._table_name + '_set',
                            ToAssociationField(resource))

                    setattr(resource, other_resource._table_name + '_ref',
                            FromAssociationField(other_resource))

                    resource.Meta.constraints['fks'].append(
                        ForeignKey([e[0] for e in fk_names], other_resource._table_name,
                                   [e[0] for e in other_resource._id_fields_names])
                    )

            for field in resource._fields:
                if isinstance(field, ComposedBy):
                    other_resource = MetaResource._starting_block[field.other_resource]
                    id_names = other_resource._id_fields_names
                    fk_names = id_names[len(other_resource.Meta.weak_id):]

                    for fk_name, fk_field in fk_names:
                        add_field(other_resource, fk_name, type(fk_field)())

                    other_resource.Meta.constraints['fks'].append(
                        ForeignKey([e[0] for e in fk_names], resource._table_name,
                                   [e[0] for e in resource._id_fields_names])
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
            sql = mcs.db.sql_translator.create_schema(
                resource._table_name,
                resource.Meta.constraints['pk'],
                (field for field in resource._fields if isinstance(field, ScalarField))
            )
            mcs.db.execute(sql)
        for resource_name in resources_names:
            resource = mcs.register[resource_name][0]
            for sql in mcs.db.sql_translator.create_schema_constraints(
                resource._table_name, resource.Meta.constraints['fks']):
                mcs.db.execute(sql)

    @classmethod
    def initialize(mcs, database, *args, **kwargs):
        mcs._build_foreign_key()
        mcs._build_orm_layer()
        mcs._name_to_ref()
        mcs.db.initialize(database)
        mcs.db.connect(*args, **kwargs)

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
        self.where_criteria = None

    def join(self, resource, on):
        self.join_criteria.append((resource, on.sql))
        return self

    def where(self, criteria):
        self.where_criteria = criteria
        return self

    def __iter__(self):
        field_names = [field.name
                       for field in self.resource._fields
                       if isinstance(field, ScalarField)]

        sql = "SELECT DISTINCT {} FROM {}".format(
            ', '.join(field_names), self.resource._table_name)

        for resource, criteria in self.join_criteria:
            sql += " INNER JOIN {} ON {}".format(resource._table_name, " ".join(criteria))

        user_input = ()
        if self.where_criteria:
            sql += " WHERE {}".format(' '.join(self.where_criteria.sql))
            user_input = self.where_criteria.user_input

        cursor = type(self.resource).db.execute(sql, user_input)
        return self.Cursor(cursor, self.resource, field_names)


class Resource(metaclass=MetaResource):

    def __init__(self, **kwargs):
        self._state = {}
        expected_fields_name = set(field.name for field in self._fields)
        got_fields = set(kwargs)
        wrong_fields = got_fields - set(expected_fields_name)

        if wrong_fields:
            raise TypeError("{}() got an unexpected keyword argument '{}'"
                            .format(type(self).__name__,
                                    next(iter(wrong_fields))))

        for field_name in got_fields:
            setattr(self, field_name, kwargs[field_name])

    @classmethod
    def select(cls, **kwargs):
        return Query(cls)

    def save(self):
        fields = []
        values = []
        for field, value in self._state.items():
            fields.append(field)
            values.append(value)

        db = type(type(self)).db
        sql = db.sql_translator.save(self._table_name, fields)
        db.execute(sql, values)

    def delete(self):
        id_names = []
        values = []
        for field_name, _ in self._id_fields_names:
            id_names.append(field_name)
            values.append(self._state[field_name])

        db = type(type(self)).db
        sql = db.sql_translator.delete(self._table_name, id_names)
        db.execute(sql, values)


class Condition(object):
    substitution = '?'

    def __init__(self, sql):
        self.sql = [sql]
        self.user_input = []

    def __or__(self, other):
        if isinstance(other, Condition):
            self.sql.insert(0, '(')
            self.sql.append("OR")
            self.sql.extend(other.sql)
            self.sql.append(")")
            self.user_input.extend(other.user_input)
            return self

    def __and__(self, other):
        if isinstance(other, Condition):
            self.sql.insert(0, '(')
            self.sql.append("AND")
            self.sql.extend(other.sql)
            self.sql.append(")")
            self.user_input.extend(other.user_input)
            return self

    def _update(self, other):
        if isinstance(other, Condition):
            self.sql.extend(other.sql)
            self.user_input.extend(other.user_input)
        else:
            self.sql.append(self.substitution)
            self.user_input.append(other)

    def __eq__(self, other):
        self.sql.append("==")
        self._update(other)
        return self

    def __ne__(self, other):
        self.sql.append("!=")
        self._update(other)
        return self

    def __gt__(self, other):
        self.sql.append(">")
        self._update(other)
        return self

    def __lt__(self, other):
        self.sql.append("<")
        self._update(other)
        return self

    def __le__(self, other):
        self.sql.append("<=")
        self._update(other)
        return self

    def __ge__(self, other):
        self.sql.append(">=")
        self._update(other)
        return self

    def __repr__(self):
        return 'Condition({})'.format(" ".join(self.sql))


class Field:

    to_py_factory = None

    def __init__(self, writable=True, readable=True, unique=False, nullable=False, primary_key=False, weak_id=False):
        self.unique = unique
        self.nullable = nullable
        self.writable = writable
        self.readable = readable
        self.weak_id = weak_id
        self.primary_key = primary_key

    def __get__(self, obj, cls=None):
        if obj is None:
            return Condition(
                '{}.{}'.format(cls._table_name, self.name))
        return self.to_py_factory(obj._state[self.name])

    def __set__(self, obj, value):
        obj._state[self.name] = value


class ScalarField(Field):
    pass


class FloatField(ScalarField):
    to_py_factory = float


class BinaryField(ScalarField):
    to_py_factory = bytes


class DateField(ScalarField):
    @staticmethod
    def to_py_factory(value):
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()


class DateTimeField(ScalarField):
    @staticmethod
    def to_py_factory(value):
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


class NumericField(ScalarField):

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


class IntegerField(ScalarField):

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

        if self.min_value >= max_value:
            raise ValueError('max_value must be greater than min_value')


class StringField(ScalarField):

    to_py_factory = str

    def __init__(self, writable=True, readable=True, unique=False, nullable=False, primary_key=False, weak_id=False,
                 length=255, fixe_length=False):
        super().__init__(writable, readable, unique, nullable, primary_key, weak_id)
        self.length = int(length)
        self.fixe_length = int(fixe_length)


class ToAssociationField(Field):

    def __init__(self, association):
        self.association = association

    def __get__(self, obj, cls=None):
        query = self.association.select()

        field_name = obj._id_fields_names[0][0]
        related = getattr(self.association,
                          obj._table_name + '_' + field_name)
        local = getattr(type(obj), field_name)

        join_criteria = related == local
        where_criteria = local == getattr(obj, field_name)
        for field_name, _ in obj._id_fields_names[1:]:
            related = getattr(self.association,
                              obj._table_name + '_' + field_name)
            local = getattr(type(obj), field_name)
            join_criteria &= (related == local)
            where_criteria &= (local == getattr(obj, field_name))

        return query.join(obj, on=join_criteria).where(where_criteria)


class FromAssociationField(Field):

    def __init__(self, resource):
        self.resource = resource

    def __get__(self, association, cls=None):
        field_name = self.resource._id_fields_names[0][0]
        association_field_value = getattr(
            association, self.resource._table_name + '_' + field_name)
        resource_field_name = getattr(self.resource, field_name)
        where_criteria = resource_field_name == association_field_value

        for field_name, _ in self.resource._id_fields_names[1:]:
            association_field_value = getattr(
                association, self.resource._table_name + '_' + field_name)
            resource_field_name = getattr(self.resource, field_name)
            where_criteria &= (resource_field_name == association_field_value)

        return self.resource.select().where(where_criteria)


class ComposedBy(Field):
    def __init__(self, other_resource, cardinality='0..*', related_name=None, writable=True, readable=True):
        if not isinstance(other_resource, str):
            raise TypeError('other_resource must be str (got {})'.format(type(other_resource)))
        if len(cardinality) == 4 and cardinality[1:3] == '..':
            card_min, card_max = cardinality.split('..')
        elif cardinality == '1':
            card_min = card_max = cardinality
        elif cardinality == '*':
            card_min, card_max = ('0', '*')
        else:
            raise ValueError('cardinality must be one ("1", "0..1", "1..*", "*")')

        super().__init__(writable, readable, card_max == "1", card_min == "0")
        self.other_resource = other_resource
        self.related_name = related_name
        self.card_min = card_min
        self.card_max = card_max

        if self.related_name is None:
            self.related_name = to_underscore(other_resource) + '_ref'

    def __get__(self, obj, cls=None):
        other_resource = MetaResource.register[self.other_resource][0]
        query = other_resource.select()

        field = obj._id_fields_names[0]
        clause_where = (getattr(other_resource,
                                obj._table_name + '_' + field[0]) == getattr(obj, field[0]))

        for field in obj._id_fields_names[1:]:
            clause_where &= (
                getattr(other_resource, obj._table_name + '_' + field[0]) == getattr(obj, field[0]))

        query.where(clause_where)
        return query

    def __set__(self, obj, value):
        raise AttributeError("can't set attribute {}".format(self.name))


__all__ = ['ToAssociationField', 'NumericField', 'ComposedBy', 'StringField', 'IntegerField', 'BinaryField',
           'Resource', 'MetaResource', 'DateTimeField', 'DateField', 'FloatField', 'IntegrityError', 'association']

