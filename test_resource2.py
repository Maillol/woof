#!/usr/bin/env python3

import unittest
from imp import reload
from resource2 import *
import peewee


class TestMetaRegister(unittest.TestCase):

    def assertHasField(self, obj, attr_name, field):
        self.assertIn(attr_name, vars(obj))
        self.assertEqual(type(getattr(obj, attr_name)), type(field))
        self.assertEqual(getattr(obj, attr_name).unique,
                         field.unique)
        self.assertEqual(getattr(obj, attr_name).null,
                         field.null)
        self.assertEqual(getattr(obj, attr_name).primary_key,
                         field.primary_key)

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

    def test_composed_by(self):

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
        self.assertHasField(orm_chapter_cls, 'book_id', peewee.ForeignKeyField(orm_book_cls))
        self.assertHasComposedPK(orm_chapter_cls, ('number', 'book_id'))
        self.assertNotHasOwnAttr(orm_chapter_cls, 'id')

        self.assertHasField(orm_paragraph_cls, 'number', peewee.IntegerField())
        self.assertHasField(orm_paragraph_cls, 'chapter_id', peewee.ForeignKeyField(orm_chapter_cls))
        self.assertHasComposedPK(orm_paragraph_cls, ('number', 'chapter_id'))
        self.assertNotHasOwnAttr(orm_paragraph_cls, 'id')

