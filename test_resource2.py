#!/usr/bin/env python3

import unittest
from imp import reload
from resource2 import *
import peewee


class TestMetaRegister(unittest.TestCase):

    def assertHasField(self, obj, attr_name, field):
        self.assertIn(attr_name, vars(obj))
        self.assertEqual(type(getattr(obj, attr_name)), type(field))
        
        msg = "%s field mustn't be unique" % attr_name
        if field.unique:
            msg = "%s field must be unique" % attr_name         
        self.assertEqual(getattr(obj, attr_name).unique,
                         field.unique, msg)

        msg = "%s field must be not null" % attr_name
        if field.null:
            msg = "%s field must be null" % attr_name         
        self.assertEqual(getattr(obj, attr_name).null,
                         field.null, msg)

        msg = "%s field must be primary_key" % attr_name
        if field.primary_key:
            msg = "%s field mustn't be primary_key" % attr_name      
        self.assertEqual(getattr(obj, attr_name).primary_key,
                         field.primary_key, msg)

        if isinstance(field, peewee.ForeignKeyField):
            self.assertEqual(getattr(obj, attr_name).rel_model,
                             field.rel_model)

    def assertNotHasOwnAttr(self, obj, attr_name):
        self.assertNotIn(attr_name, vars(obj))

    def assertHasComposedPK(self, model, fields):
        self.assertEqual(
            sorted(model._meta.primary_key.field_names),
            sorted(fields))


class TestComposedByCardinality(TestMetaRegister):

    @classmethod
    def setUpClass(cls):
        MetaResource.clear()
        class A(Resource):
            num = NumberField(weak_id=True)

        class B(Resource):
            num = NumberField(weak_id=True)

        class C(Resource):
            num = NumberField(weak_id=True)

        class D(Resource):
            num = NumberField(weak_id=True)

        class R(Resource):
            a = ComposedBy('A', '1', related_name='r_to_a')
            b = ComposedBy('B', '0..1', related_name='r_to_b')
            c = ComposedBy('C', '1..*', related_name='r_to_c')
            d = ComposedBy('D', '*', related_name='r_to_d')

        MetaResource._build_foreign_key()
        MetaResource._build_orm_layer()
        MetaResource._name_to_ref()

        cls.orm_a_cls = MetaResource.register['A'][0]
        cls.orm_b_cls = MetaResource.register['B'][0]
        cls.orm_c_cls = MetaResource.register['C'][0]
        cls.orm_d_cls = MetaResource.register['D'][0]
        cls.orm_r_cls = MetaResource.register['R'][0]

    def test_cardinality_only_one(self):
        self.assertHasField(self.orm_a_cls, 'num', peewee.IntegerField())
        self.assertHasField(self.orm_a_cls, 'r_to_a', 
                            peewee.ForeignKeyField(self.orm_r_cls, unique=True, null=False))

    def test_cardinality_zero_or_one(self):
        self.assertHasField(self.orm_b_cls, 'num', peewee.IntegerField())
        self.assertHasField(self.orm_b_cls, 'r_to_b', 
                            peewee.ForeignKeyField(self.orm_r_cls, unique=True, null=True))

    def test_cardinality_one_or_more(self):
        self.assertHasField(self.orm_c_cls, 'num', peewee.IntegerField())
        self.assertHasField(self.orm_c_cls, 'r_to_c',
                            peewee.ForeignKeyField(self.orm_r_cls, unique=False, null=False))

    def test_cardinality_zero_or_more(self):
        self.assertHasField(self.orm_d_cls, 'num', peewee.IntegerField())
        self.assertHasField(self.orm_d_cls, 'r_to_d', 
                            peewee.ForeignKeyField(self.orm_r_cls, unique=False, null=True))


class TestComposedWeakId(TestMetaRegister):

    @classmethod
    def setUpClass(cls):
        MetaResource.clear()
        class A(Resource):
            b = ComposedBy('B', related_name='a_to_b')

        class B(Resource):
            num = NumberField(weak_id=True)
            c = ComposedBy('C', related_name='b_to_c')

        class C(Resource):
            phony = NumberField()

        MetaResource._build_foreign_key()
        MetaResource._build_orm_layer()
        MetaResource._name_to_ref()

        cls.orm_a_cls = MetaResource.register['A'][0]
        cls.orm_b_cls = MetaResource.register['B'][0]
        cls.orm_c_cls = MetaResource.register['C'][0]

    def test_defined_weak_id_is_used_in_composed_pk(self):
        self.assertHasComposedPK(self.orm_b_cls, ('num', 'a_to_b'))

    def test_undefined_weak_id_is_generated_and_used_in_composed_pk(self):  
        self.assertHasField(self.orm_c_cls, 'weak_id', peewee.IntegerField(unique=False))
        self.assertHasComposedPK(self.orm_c_cls, ('weak_id', 'b_to_c'))

    def test_composed_by_field_is_not_mounted(self):
       self.assertNotHasOwnAttr(self.orm_a_cls, 'b')
       self.assertNotHasOwnAttr(self.orm_b_cls, 'c')

    def test_weak_entity_has_no_primary_key(self):
        self.assertNotHasOwnAttr(self.orm_b_cls, 'id')
        self.assertNotHasOwnAttr(self.orm_c_cls, 'id')

    def test_generate_related_name(self):
        MetaResource.clear()
        class A(Resource):
            bbbb = ComposedBy('B')

        class B(Resource):
            num = NumberField(weak_id=True)


        MetaResource._build_foreign_key()
        MetaResource._build_orm_layer()
        MetaResource._name_to_ref()

        orm_a_cls = MetaResource.register['A'][0]
        orm_b_cls = MetaResource.register['B'][0]

        self.assertHasComposedPK(orm_b_cls, ('num', 'a_id'))
        self.assertHasField(orm_b_cls, 'a_id', 
                            peewee.ForeignKeyField(orm_a_cls, null=True))


