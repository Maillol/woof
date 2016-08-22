#!/usr/bin/env python3

import sys
import os
from decimal import Decimal
import unittest
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from woof.resource import *
import woof.sqltranslator
import woof.resource


class MockedDataBase(woof.resource.DataBase):
    calls = []
    module = type('MockModule', (), {'paramstyle': 'qmark'})

    def __init__(self, *args):
        self.sql_translator = woof.sqltranslator.SQLTranslator

    def connect(self, *args):
        ...
        
    def execute(self, sql_query, parameters=()):
        self.calls.append(sql_query)


MetaResource.db = MockedDataBase()


class TestPyToSql(unittest.TestCase):

    def setUp(self):
        MockedDataBase.calls = []
        MetaResource.clear()

    def assertExecute(self, sql):
        self.assertIn(sql, MockedDataBase.calls)


class TestFieldToSql(TestPyToSql):

    def test_float_field(self):
        class FooBar(Resource):
            a = FloatField()            
            b = FloatField(nullable=True)
            c = FloatField(primary_key=True)

        MetaResource.initialize(MockedDataBase())
        MetaResource.create_tables()

        self.assertExecute(
            'CREATE TABLE foo_bar('
            'a REAL NOT NULL, '
            'b REAL NULL, '
            'c REAL NOT NULL, '
            'PRIMARY KEY (c));')           

    def test_date_field(self):
        class FooBar(Resource):
            a = DateField()            
            b = DateField(nullable=True)
            c = DateField(primary_key=True)

        MetaResource.initialize(MockedDataBase())
        MetaResource.create_tables()

        self.assertExecute(
            'CREATE TABLE foo_bar('
            'a DATE NOT NULL, '
            'b DATE NULL, '
            'c DATE NOT NULL, '
            'PRIMARY KEY (c));')           

    def test_numeric_field(self):
        class FooBar(Resource):
            a = NumericField()            
            b = NumericField(nullable=True, precision=12, scale=4)
            c = NumericField(primary_key=True)

        MetaResource.initialize(MockedDataBase())
        MetaResource.create_tables()

        self.assertExecute(
            'CREATE TABLE foo_bar('
            'a NUMERIC(10, 3) NOT NULL, '
            'b NUMERIC(12, 4) NULL, '
            'c NUMERIC(10, 3) NOT NULL, '
            'PRIMARY KEY (c));')  

    def test_integer_field(self):
        min_small_int = -32768
        max_small_int = 32767
        min_int = -2147483648
        max_int = 2147483647
        max_unsigned_small_int = 65535
        max_unsigned_int = 4294967295

        class FooBar(Resource):
            a = IntegerField()
            b = IntegerField(nullable=True)
            c = IntegerField(primary_key=True)
            d = IntegerField(min_value=min_small_int, max_value=max_small_int)
            e = IntegerField(min_value=min_small_int -1, max_value=max_small_int)
            f = IntegerField(min_value=min_small_int, max_value=max_small_int + 1)
            g = IntegerField(min_value=min_int, max_value=max_int)
            h = IntegerField(min_value=min_int - 1, max_value=max_int)
            i = IntegerField(min_value=min_int, max_value=max_int + 1)
            j = IntegerField(min_value=0, max_value=max_unsigned_small_int)
            k = IntegerField(min_value=0, max_value=max_unsigned_small_int + 1)
            l = IntegerField(min_value=0, max_value=max_unsigned_int)
            m = IntegerField(min_value=0, max_value=max_unsigned_int + 1)

        MetaResource.initialize(MockedDataBase())
        MetaResource.create_tables()

        self.assertExecute(
            'CREATE TABLE foo_bar('
            'a INTEGER NOT NULL, '
            'b INTEGER NULL, '
            'c INTEGER NOT NULL, '
            'd SMALLINT NOT NULL, '
            'e INTEGER NOT NULL, '
            'f INTEGER NOT NULL, '
            'g INTEGER NOT NULL, '
            'h BIGINT NOT NULL, '
            'i BIGINT NOT NULL, '
            'j SMALLINT UNSIGNED NOT NULL, '
            'k INTEGER UNSIGNED NOT NULL, '
            'l INTEGER UNSIGNED NOT NULL, '
            'm BIGINT UNSIGNED NOT NULL, '
            'PRIMARY KEY (c));')  

    def test_string_field(self):
        class FooBar(Resource):
            a = StringField()            
            b = StringField(nullable=True)
            c = StringField(primary_key=True)
            d = StringField(fixe_length=True, length=32)            

        MetaResource.initialize(MockedDataBase())
        MetaResource.create_tables()

        self.assertExecute(
            'CREATE TABLE foo_bar('
            'a VARCHAR(255) NOT NULL, '
            'b VARCHAR(255) NULL, '
            'c VARCHAR(255) NOT NULL, '
            'd CHAR(32) NOT NULL, '
            'PRIMARY KEY (c));')

    def test_composed_by(self):
        class ResA(Resource):
            a = StringField()

        class ResB(Resource):
            a = StringField()
            res_a_set = ComposedBy('ResA')

        class ResC(Resource):
            a = StringField()
            res_a_set = ComposedBy('ResB')

        MetaResource.initialize(MockedDataBase())
        MetaResource.create_tables()

        self.assertExecute(
            'CREATE TABLE res_a('
            'weak_id INTEGER NOT NULL, '
            'a VARCHAR(255) NOT NULL, '
            'res_b_weak_id INTEGER NOT NULL, '
            'res_b_res_c_id INTEGER NOT NULL, '
            'PRIMARY KEY (weak_id, res_b_weak_id, res_b_res_c_id));')

        self.assertExecute(
            'CREATE TABLE res_b(weak_id INTEGER NOT NULL, '
            'a VARCHAR(255) NOT NULL, '
            'res_c_id INTEGER NOT NULL, '
            'PRIMARY KEY (weak_id, res_c_id));')

        self.assertExecute(
            'CREATE TABLE res_c('
            'id INTEGER NOT NULL, '
            'a VARCHAR(255) NOT NULL, '
            'PRIMARY KEY (id));')

        self.assertExecute(
            'ALTER TABLE res_a '
            'ADD FOREIGN KEY (res_b_weak_id, res_b_res_c_id) '
            'REFERENCES res_b(weak_id, res_c_id);')

        self.assertExecute(
            'ALTER TABLE res_b '
            'ADD FOREIGN KEY (res_c_id) '
            'REFERENCES res_c(id);')


class TestComposedByCardinality(unittest.TestCase):

    def assertExecute(self, sql):
        self.assertIn(sql, MockedDataBase.calls)

    @classmethod
    def setUpClass(cls):
        MockedDataBase.calls = []
        MetaResource.clear()

        class A(Resource):
            num = IntegerField(weak_id=True)

        class B(Resource):
            num = IntegerField(weak_id=True)

        class C(Resource):
            num = IntegerField(weak_id=True)

        class D(Resource):
            num = IntegerField(weak_id=True)

        class R(Resource):
            a = ComposedBy('A', '1')
            b = ComposedBy('B', '0..1')
            c = ComposedBy('C', '1..*')
            d = ComposedBy('D', '*')

        MetaResource.initialize(MockedDataBase())
        MetaResource.create_tables()

        cls.orm_a_cls = A
        cls.orm_b_cls = B
        cls.orm_c_cls = C
        cls.orm_d_cls = D
        cls.orm_r_cls = R

    def test_cardinality_only_one(self):
        self.assertExecute(
            'CREATE TABLE a('
            'num INTEGER NOT NULL, '
            'r_id INTEGER NOT NULL, '
            'PRIMARY KEY (num, r_id));')
        self.assertExecute(
            'ALTER TABLE a '
            'ADD FOREIGN KEY (r_id) REFERENCES r(id);')
        self.assertExecute(
            'ALTER TABLE a '
            'ADD UNIQUE (r_id);')

    def test_cardinality_zero_or_one(self):
        self.assertExecute(
            'CREATE TABLE b('
            'num INTEGER NOT NULL, '
            'r_id INTEGER NOT NULL, '
            'PRIMARY KEY (num, r_id));')
        self.assertExecute(
            'ALTER TABLE b '
            'ADD FOREIGN KEY (r_id) REFERENCES r(id);')
        self.assertExecute(
            'ALTER TABLE a '
            'ADD UNIQUE (r_id);')

    def test_cardinality_one_or_more(self):
        self.assertExecute(
            'CREATE TABLE c('
            'num INTEGER NOT NULL, '
            'r_id INTEGER NOT NULL, '
            'PRIMARY KEY (num, r_id));') 
        self.assertExecute(
            'ALTER TABLE c '
            'ADD FOREIGN KEY (r_id) REFERENCES r(id);')

    def test_cardinality_zero_or_more(self):
        self.assertExecute(
            'CREATE TABLE d('
            'num INTEGER NOT NULL, '
            'r_id INTEGER NOT NULL, '
            'PRIMARY KEY (num, r_id));')
        self.assertExecute(
            'ALTER TABLE d '
            'ADD FOREIGN KEY (r_id) REFERENCES r(id);')


class TestTypeFieldMetaData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        MetaResource.clear()

        class A(Resource):
            ref = ComposedBy('B')
            ref_c = ComposedBy('C')

        class B(Resource):
            n = IntegerField(weak_id=True)
            b = BinaryField()
            f = FloatField()
        
        class C(Resource):
            s = StringField(weak_id=True)
            d = DateField()
            n = NumericField()

        MetaResource.initialize(MockedDataBase())
        MetaResource.create_tables()

    def test_number_field_type(self):
        self.assertEqual(MetaResource.fields_types['B']['n'], int)

    def test_bool_field_type(self):
        self.assertEqual(MetaResource.fields_types['B']['b'], bytes)

    def test_string_field_type(self):
        self.assertEqual(MetaResource.fields_types['B']['f'], float)

    def test_reference_field_type(self):
        self.assertEqual(MetaResource.fields_types['B']['a_id'], int)

    def test_weak_id_string_field_type(self):
        self.assertEqual(MetaResource.fields_types['C']['s'], str)

    def test_date_field_type(self):
        self.assertEqual(MetaResource.fields_types['C']['d'], DateField.to_py_factory)

    def test_numeric_field_type(self):
        self.assertEqual(MetaResource.fields_types['C']['n']('3.14'),
            Decimal('3.14'))

    def test_generated_pk_field_type(self):
        self.assertEqual(MetaResource.fields_types['A']['id'], int)
