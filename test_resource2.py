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

    def setUp(self):
        MetaResource.clear()

    def test_composed_by_field(self):
        class A(Resource):
            a = NumberField(weak_id=True)

        class B(Resource):
            b = NumberField(weak_id=True)

        class C(Resource):
            c = NumberField(weak_id=True)

        class D(Resource):
            d = NumberField(weak_id=True)

        class R(Resource):
            a = ComposedBy('A', '1', related_name='r_to_a')
            b = ComposedBy('B', '0..1', related_name='r_to_b')
            c = ComposedBy('C', '1..*', related_name='r_to_c')
            d = ComposedBy('D', '*', related_name='r_to_d')

        MetaResource._build_foreign_key()
        MetaResource._build_orm_layer()
        MetaResource._name_to_ref()

        orm_a_cls = MetaResource.register['A'][0]
        orm_b_cls = MetaResource.register['B'][0]
        orm_c_cls = MetaResource.register['C'][0]
        orm_d_cls = MetaResource.register['D'][0]
        orm_r_cls = MetaResource.register['R'][0]

        self.assertHasField(orm_a_cls, 'a', peewee.IntegerField())
        self.assertHasField(orm_a_cls, 'r_to_a', 
                            peewee.ForeignKeyField(orm_r_cls, unique=True, null=False))
        self.assertHasField(orm_b_cls, 'b', peewee.IntegerField())
        self.assertHasField(orm_b_cls, 'r_to_b', 
                            peewee.ForeignKeyField(orm_r_cls, unique=True, null=True))
        self.assertHasField(orm_c_cls, 'c', peewee.IntegerField())
        self.assertHasField(orm_c_cls, 'r_to_c',
                            peewee.ForeignKeyField(orm_r_cls, unique=False, null=False))
        self.assertHasField(orm_d_cls, 'd', peewee.IntegerField())
        self.assertHasField(orm_d_cls, 'r_to_d', 
                            peewee.ForeignKeyField(orm_r_cls, unique=False, null=True))

    def test_composed_by_weak_id(self):

        class Book(Resource):
            title = StringField()
            abstract = StringField()
            chapters = ComposedBy('Chapter')

        class Chapter(Resource):
            number = NumberField(weak_id=True)
            paragraph = ComposedBy('Paragraph')

        class Paragraph(Resource):
            number = NumberField(weak_id=True)


        MetaResource._build_foreign_key()
        MetaResource._build_orm_layer()
        MetaResource._name_to_ref()

        orm_book_cls = MetaResource.register['Book'][0]
        orm_chapter_cls = MetaResource.register['Chapter'][0]
        orm_paragraph_cls = MetaResource.register['Paragraph'][0]

        self.assertHasField(orm_book_cls, 'title', peewee.CharField())
        self.assertHasField(orm_book_cls, 'abstract', peewee.CharField())
        self.assertHasField(orm_book_cls, 'id', peewee.PrimaryKeyField())
        self.assertNotHasOwnAttr(orm_book_cls, 'chapters')

        self.assertHasField(orm_chapter_cls, 'number', peewee.IntegerField())
        self.assertHasField(orm_chapter_cls, 'book_id', peewee.ForeignKeyField(orm_book_cls, null=True))
        self.assertHasComposedPK(orm_chapter_cls, ('number', 'book_id'))
        self.assertNotHasOwnAttr(orm_chapter_cls, 'id')

        self.assertHasField(orm_paragraph_cls, 'number', peewee.IntegerField())
        self.assertHasField(orm_paragraph_cls, 'chapter_id', peewee.ForeignKeyField(orm_chapter_cls, null=True))
        self.assertHasComposedPK(orm_paragraph_cls, ('number', 'chapter_id'))
        self.assertNotHasOwnAttr(orm_paragraph_cls, 'id')

