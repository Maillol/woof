from collections import OrderedDict
import datetime
from decimal import Decimal
from .db import DataBase


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

    db = None
    register = {} # {resource_class_name:
                  #     (ORM_cls, {refered_name_field: refered_resource_class_name, ...})}

    fields_types = {} # {name: {field_name: python_type_caster}}

    _starting_block = {}

    def _init_nested_meta(cls):
        """
        Initializes nested class in Resource class.

            Meta:
                weak_id = []
                primary_key = [] # used by get_id_fields_names method and to push generated id after save.
                foreign_keys = []
                required_resource_for_pk = []
                association_meta_data = []
        """
        if not hasattr(cls, 'Meta'):
            cls.Meta = type('Meta', (), {})
        if not hasattr(cls.Meta, 'foreign_keys'):
            cls.Meta.foreign_keys = []
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

    @staticmethod
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

    @classmethod
    def _generate_weak_id_if_not_exist(mcs):
        """
        1) Search all resource pointed by a ComposedBy field.
        2) Add weak id field and  set Meta.required_resource_for_pk.
        """
        for resource_name, resource in MetaResource._starting_block.items():
            for field in resource._fields:
                if isinstance(field, ComposedBy):
                    try:
                        weak_entity = MetaResource._starting_block[field.other_resource]
                    except KeyError:
                        raise TypeError("Field '{}' in {} references a non-existing resource '{}'"
                                        .format(field.name, resource, field.other_resource))

                    if weak_entity.Meta.primary_key:
                        raise TypeError(weak_entity +
                                        ' cannot have primary key because it is contained in ' + resource)

                    if not weak_entity.Meta.weak_id:
                        mcs.add_field(weak_entity, 'weak_id', IntegerField(weak_id=True), 0)
                    weak_entity.Meta.required_resource_for_pk = [resource]

    @classmethod
    def _generate_primary_key_if_not_exist(mcs):
        """
        Search all resources which isn't weak entity and add a primary key field
        if it doesn't have a primary key.
        """
        for resource_name, resource in MetaResource._starting_block.items():
            if not resource.Meta.weak_id and not resource.Meta.primary_key:
                mcs.add_field(resource, 'id', IntegerField(primary_key=True), 0)

    @classmethod
    def _set_meta_foreign_key(mcs):
        """
        Set Meta.foreign_keys field of the associations and weak entities.
        """
        for resource_name, resource in MetaResource._starting_block.items():
            if resource.Meta.association_meta_data:
                for other_resource_name, card in resource.Meta.association_meta_data.items():
                    other_resource = MetaResource._starting_block[other_resource_name]

                    fk_names = [('{}_{}'.format(other_resource._table_name, name), field)
                                for name, field
                                in mcs.get_id_fields_names(other_resource)]

                    for fk_name, fk_field in fk_names:
                        mcs.add_field(resource, fk_name, type(fk_field)())

                    resource.Meta.foreign_keys.append(
                        ForeignKey([e[0] for e in fk_names], other_resource._table_name,
                                   other_resource._id_fields_names)
                    )

                    setattr(other_resource, resource._table_name + '_set',
                            ToAssociationField(resource))

                    setattr(resource, other_resource._table_name + '_ref',
                            FromAssociationField(other_resource))

            for field in resource._fields:
                if isinstance(field, ComposedBy):
                    other_resource = MetaResource._starting_block[field.other_resource]
                    id_names = mcs.get_id_fields_names(other_resource)
                    fk_names = id_names[len(other_resource.Meta.weak_id):]

                    for fk_name, fk_field in fk_names:
                        mcs.add_field(other_resource, fk_name, type(fk_field)())

                    other_resource.Meta.foreign_keys.append(
                        ForeignKey([e[0] for e in fk_names], resource._table_name,
                                   resource._id_fields_names)
                    )

    @staticmethod
    def get_id_fields_names(resource):
        if resource.Meta.weak_id:
            fields = [(field.name, field) for field in resource.Meta.weak_id]
            for required_cls in resource.Meta.required_resource_for_pk:
                prefix = required_cls._table_name
                fields.extend(
                    ('{}_{}'.format(prefix, field_name), field)
                    for (field_name, field)
                    in MetaResource.get_id_fields_names(required_cls)
                )
            return fields

        if resource.Meta.required_resource_for_pk:
            fields = [(field.name, field) for field in resource.Meta.primary_key]
            for required_cls_name in resource.Meta.required_resource_for_pk:
                required_cls = MetaResource._starting_block[required_cls_name]
                prefix = required_cls._table_name
                fields.extend(
                    ('{}_{}'.format(prefix, field_name), field)
                    for (field_name, field)
                    in MetaResource.get_id_fields_names(required_cls)
                )
            return fields

        return [(field.name, field) for field in resource.Meta.primary_key]

    @classmethod
    def _set_register(mcs):
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
                (field for field in resource._fields if isinstance(field, ScalarField)),
                resource._id_fields_names
            )
            mcs.db.execute(sql)
        for resource_name in resources_names:
            resource = mcs.register[resource_name][0]
            for sql in mcs.db.sql_translator.create_schema_constraints(
                resource._table_name, resource.Meta.foreign_keys):
                mcs.db.execute(sql)

    @classmethod
    def initialize(mcs, database):
        if not isinstance(database, DataBase):
            raise TypeError("Initialize's parameter must be DataBase object")
        mcs._generate_weak_id_if_not_exist()
        mcs._generate_primary_key_if_not_exist()
        for resource in MetaResource._starting_block.values():
            resource._id_fields_names = tuple(e[0] for e in mcs.get_id_fields_names(resource))
        mcs._set_meta_foreign_key()
        mcs._set_register()
        mcs._name_to_ref()
        mcs.db = database

    @classmethod
    def clear(mcs):
        mcs.register = {}
        mcs.fields_types = {}
        mcs._resource_fields = []
        mcs._starting_block = {}


class ForeignKey:
    def __init__(self, fields, referenced_resource, referenced_fields):
        self.fields = fields
        self.referenced_resource = referenced_resource
        self.referenced_fields = referenced_fields


class Query:
    class Cursor:
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

    def get_sql(self):
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

        return sql, user_input, field_names

    def __iter__(self):
        sql, user_input, field_names = self.get_sql()
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
        last_id = db.execute(sql, values).lastrowid  # FIXME push last_id to _state.
        for field in self.Meta.primary_key:
            if field.name == 'id':
               self.id = last_id

    def delete(self):
        values = []
        for field_name in self._id_fields_names:
            values.append(self._state[field_name])

        db = type(type(self)).db
        sql = db.sql_translator.delete(self._table_name, self._id_fields_names)
        db.execute(sql, values)

    def to_dict(self):
        dictionary = {}
        for field in self._fields:
            value = getattr(self, field.name)
            if isinstance(value, Query):
                value = [e.to_dict() for e in value]
            dictionary[field.name] = value
        return dictionary


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

        field_name = obj._id_fields_names[0]
        related = getattr(self.association,
                          obj._table_name + '_' + field_name)
        local = getattr(type(obj), field_name)

        join_criteria = related == local
        where_criteria = local == getattr(obj, field_name)
        for field_name in obj._id_fields_names[1:]:
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
        field_name = self.resource._id_fields_names[0]
        association_field_value = getattr(
            association, self.resource._table_name + '_' + field_name)
        resource_field_name = getattr(self.resource, field_name)
        where_criteria = resource_field_name == association_field_value

        for field_name in self.resource._id_fields_names[1:]:
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
                                obj._table_name + '_' + field) == getattr(obj, field))

        for field in obj._id_fields_names[1:]:
            clause_where &= (
                getattr(other_resource, obj._table_name + '_' + field) == getattr(obj, field))

        query.where(clause_where)
        return query

    def __set__(self, obj, value):
        raise AttributeError("can't set attribute {}".format(self.name))


__all__ = ['ToAssociationField', 'NumericField', 'ComposedBy', 'StringField', 'IntegerField', 'BinaryField',
           'Resource', 'MetaResource', 'DateTimeField', 'DateField', 'FloatField', 'association']

