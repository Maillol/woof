import peewee
from functools import partial

class MetaResource(type):
    """
    Store resource and relationship between several resource throug resource fields.

    You can use MetaResource.register inorder to search ORM class using resource class Name.
    """

    db = peewee.Proxy()
    register = {} # {resource_class_name:
                  #     (ORM_cls, {refered_name_field: refered_resource_class_name, ...})}

    fields_types = {} # {name: {field_name: python_type_caster}}

    _resource_fields = []
    # TODO name_field doit pouvoir contenir également le type... Il faut amméliorer le parsing pour cast.
    # merge fields_type and register ??
    #
    # {resource_class_name:
    #     (ORM_cls, {refered_name_field: (refered_resource_class_name, type), ...})}
    #

    _starting_block = {}

    def __init__(cls, name, parent, attrs):
        if name != 'Resource':
            MetaResource._starting_block[name] = (cls, parent, attrs)

    @classmethod
    def _build_foreign_key(mcs):
        for name, (_, _, attrs) in MetaResource._starting_block.items():
            composed_by_fields = []
            for attr_name, attr in attrs.items():
                if isinstance(attr, ComposedBy):
                    reference_attrs = MetaResource._starting_block[attr.composite_name][2]

                    # Search references weak_id
                    weak_id_name = None
                    for ref_attr_name, ref_attr in reference_attrs.items():
                        if isinstance(ref_attr, Field):
                            if ref_attr.weak_id:
                                weak_id_name = ref_attr_name

                    if weak_id_name is None:
                        weak_id_name = 'weak_id'
                        reference_attrs[weak_id_name] = NumberField(null=False)

                    related_name = attr.related_name or "{}_id".format(name.lower())
                    meta = reference_attrs.setdefault('Meta', type('Meta', (), {}))
                    meta.primary_key = peewee.CompositeKey(related_name, weak_id_name)

                    reference_attrs[related_name] = ResourceField(
                        name, related_name, unique=attr.unique, null=attr.null)

                    composed_by_fields.append(attr_name)

            for e in composed_by_fields:
                del attrs[e]

    @classmethod
    def _build_orm_layer(mcs):

        for name, (cls, parent, attrs) in MetaResource._starting_block.items():

            entity_attrs = {attr_name: attr_value.type_field()
                            for attr_name, attr_value in attrs.items()
                            if isinstance(attr_value, Field)}

            meta = attrs.get('Meta', type('Meta', (), {}))
            meta.database = MetaResource.db
            entity_attrs['Meta'] = meta

            cls.register[name] = (
                type(name, (peewee.Model,), entity_attrs),
                {attr_name: attr_value.resource_name
                 for attr_name, attr_value in attrs.items()
                 if isinstance(attr_value, ResourceField)}
            )

            cls.fields_types[name] = {
                attr_name: attr_value.to_py_factory
                for attr_name, attr_value in attrs.items()
                if isinstance(attr_value, Field)
            }

            cls._resource_fields.extend(field
                                        for field in attrs.values()
                                        if isinstance(field, ResourceField))

    @classmethod
    def _name_to_ref(cls):
        """
        Optimize register and initialize foreign key proxy

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

        for field in cls._resource_fields:
            entity = cls.register[field.resource_name][0]
            field.resource_proxy.initialize(entity)


    @classmethod
    def create_tables(mcs, resources_names=None):
        """
        Create table for each resource name in resources_names parameters.
        if resources_names is None, the tables for all resources in registry are created.

        resources_names - list of resource name.
        """
        if resources_names is None:
            resources_names = list(mcs.register)

        mcs.db.create_tables(
            [mcs.register[name][0] for name in resources_names]
        )

    @classmethod
    def initialize(mcs, database):
        mcs._build_foreign_key()
        mcs._build_orm_layer()
        mcs._name_to_ref()
        mcs.db.initialize(database)
        MetaResource.db.connect()

    @classmethod
    def clear(mcs):
        mcs.register = {}
        mcs.fields_types = {}
        mcs._resource_fields = []
        mcs._starting_block = {}


class Resource(metaclass=MetaResource):
    pass


class Field:
    to_py_factory = None

    def __init__(self, writable=True, readable=True, unique=False, null=False, weak_id=False):
        self.unique = unique
        self.null = null
        self.writable = writable
        self.readable = readable
        self.weak_id = weak_id
        self.type_field = partial(type(self).type_field, unique=unique, null=null)


class BoolField(Field):
    to_py_factory = bool
    type_field = peewee.BooleanField


class NumberField(Field):
    to_py_factory = int
    type_field = peewee.IntegerField


class StringField(Field):
    to_py_factory = str
    type_field = peewee.CharField


class ComposedBy(Field):
    type_field = lambda a: a
    def __init__(self, composite_name, cardinality='0..*', related_name=None, writable=True, readable=True):
        if len(cardinality) == 4 and cardinality[1:3] == '..':
            card_min, card_max =  cardinality.split('..')
        elif cardinality == '1':
            card_min = card_max = cardinality
        elif cardinality == '*':
            card_min, card_max = ('0', '*')
        else:
            raise ValueError('cardinality must be one ("1", "0..1", "1..*", "*")')

        super().__init__(writable, readable, card_max=="1", card_min=="0")
        self.composite_name = composite_name
        self.related_name = related_name
        self.card_min = card_min 
        self.card_max = card_max


class ResourceField(Field):
    type_field = peewee.ForeignKeyField

    def __init__(self, resource_name, related_name=None, writable=True, readable=True, unique=False, null=False):
        super().__init__(writable, readable, unique, null)
        self.resource_proxy = peewee.Proxy()
        self.type_field = partial(self.type_field,
                                  self.resource_proxy, related_name=related_name)
        self.resource_name = resource_name
        self.related_name = related_name

    def __repr__(self):
        return '<ResourceField to %s>' % self.resource_name


__all__= ['ResourceField', 'ComposedBy', 'StringField', 'NumberField',
          'BoolField', 'Resource', 'MetaResource']
