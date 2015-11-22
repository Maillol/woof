import resource2


class SQLTranslater:

    @classmethod
    def translate(cls, resource):
        field_def = ', '.join(cls.field_definition(field) 
                              for field in resource._fields
                              if not isinstance(field, resource2.ComposedBy))

        table_name = resource.table_name()
        pk_def = cls.translate_pk(resource)
        return "CREATE TABLE {table_name}({field_def}{pk_def});".format(**locals())  

    @classmethod
    def translate_pk(cls, resource):
        for constrainte in resource.Meta.constraints:
            if isinstance(constrainte, resource2.PrimaryKey):
                return ", PRIMARY KEY ({})".format(", ".join(constrainte.fields))
        return ""

    @classmethod
    def translate_fk(cls, resource):
        return '\n'.join(
            cls.foreign_key(constrainte, resource)
            for constrainte in resource.Meta.constraints
            if isinstance(constrainte, resource2.ForeignKey))

    @classmethod
    def foreign_key(cls, fk, resource):
        table = resource.table_name()
        fields = ", ".join(fk.fields)
        referenced_fields = ", ".join(fk.referenced_fields)
        referenced_table = fk.referenced_resource 

        return (
            "ALTER TABLE {table} "
            "ADD FOREIGN KEY ({fields}) "
            "REFERENCES {referenced_table}({referenced_fields});"
        ).format(**locals())

    @classmethod
    def field_definition(cls, field):
        field_cls_name = type(field).__name__
        mth_name = "".join(('_' + e.lower() if e.isupper() else e
                           for e in field_cls_name)).lstrip('_')

        values = {k: getattr(field, k) for k in dir(field) if not k.startswith('_')}
        values.update(vars(field))
        return getattr(cls, mth_name)(field).format(**values)

    @staticmethod
    def float_field(field):
        return '{name} REAL {null}'

    @staticmethod
    def binary_field(field):
        return '{name} BLOB  {null}'

    @staticmethod
    def date_field(field): 
        return '{name} DATE {null}'

    @staticmethod
    def date_time_field(field): 
        return '{name} DATETIME {null}'

    @staticmethod
    def numeric_field(field): 
        return '{name} NUMERIC({precision}, {scale}) {null}'

    @staticmethod
    def integer_field(field):
        if field.min_value < 0:
            if field.min_value >= -32768 and field.max_value <= 32767:
                sql = '{name} SMALLINT {null}'            
            elif field.min_value >= -2147483648 and field.max_value <= 2147483647:
                sql = '{name} INTEGER {null}'
            else:
                sql = '{name} BIGINT {null}'
        else:
            if field.max_value <= 65535:
                sql = '{name} SMALLINT UNSIGNED {null}'            
            elif field.max_value <= 4294967295:
                sql = '{name} INTEGER UNSIGNED {null}'
            else:
                sql = '{name} BIGINT UNSIGNED {null}'
        return sql

    @staticmethod
    def string_field(field): 
        if field.fixe_length:
            sql = "{name} CHAR({length}) {null}"
        else:
            sql = "{name} VARCHAR({length}) {null}"
        return sql


class MysqlTranslater(SQLTranslater):
    pass


class SqliteTranslater(SQLTranslater):
    @classmethod
    def translate_fk(cls, resource):
        return ';'


class PostgresTranslater(SQLTranslater):

    @staticmethod
    def binary_field(field):
        return '{name} BYTEA  {null}'
