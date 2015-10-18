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
    def __init__(cls, name, parent, attrs):
        if name != 'Resource': 
        
            entity_attrs = {attr_name: attr_value.type_field()
                            for attr_name, attr_value in attrs.items()
                            if isinstance(attr_value, Field)
                            or attr_name == 'Meta'}

            # TODO setdefault
            entity_attrs['Meta'] = type('Meta', (), dict(database=MetaResource.db))

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

        for field in cls._resource_fields:
            entity = cls.register[field.resource_name][0]
            field.resource_proxy.initialize(entity)

    @classmethod
    def _initialize_db(mcs, database):
        print("_initialize_db", mcs.db)
        mcs.db.initialize(database)

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




class Resource(metaclass=MetaResource):
    pass

class Field:
    to_py_factory = None

    def __init__(self, writable=True, readable=True, unique=False, null=False):        
        self.unique = unique
        self.writable = writable
        self.readable = readable
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


class ResourceField(Field):
    type_field = peewee.ForeignKeyField

    def __init__(self, resource_name, related_name=None, writable=True, readable=True, unique=False, null=False):
        super().__init__(writable, readable, unique, null)
        self.resource_proxy = peewee.Proxy()
        self.type_field = partial(self.type_field, 
                                  self.resource_proxy, related_name=related_name)
        self.resource_name = resource_name
        self.related_name = related_name

