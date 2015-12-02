
class SQLTranslator:

    @classmethod
    def create_schema(cls, table_name, primary_key, fields):
        field_def = ', '.join(cls.field_definition(field) for field in fields) 
        if primary_key is not None:
            pk_def = cls.translate_pk(primary_key.fields)
        else:
            pk_def = ""   
        return "CREATE TABLE {table_name}({field_def}{pk_def});".format(**locals())  

    @classmethod
    def translate_pk(cls, primary_key_fields):
        if primary_key_fields:
            return ", PRIMARY KEY ({})".format(", ".join(primary_key_fields))
        return ""

    @classmethod
    def create_schema_constraints(cls, table_name, foreign_keys):
        return (cls.foreign_key(table_name, fk) for fk in foreign_keys)

    @classmethod
    def foreign_key(cls, table_name, fk):
        fields = ", ".join(fk.fields)
        referenced_fields = ", ".join(fk.referenced_fields)
        referenced_table = fk.referenced_resource 

        return (
            "ALTER TABLE {table_name} "
            "ADD FOREIGN KEY ({fields}) "
            "REFERENCES {referenced_table}({referenced_fields});"
        ).format(**locals())

    @classmethod
    def field_definition(cls, field):
        field_cls_name = type(field).__name__
        mth_name = "".join(('_' + e.lower() if e.isupper() else e
                           for e in field_cls_name)).lstrip('_')

        values = {k: getattr(field, k) for k in dir(field) if not k.startswith('_')}
        if field.nullable:
            values['null'] = 'NULL'        
        else:
            values['null'] = 'NOT NULL'
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

    @staticmethod
    def save(table_name, field_names):
        return ('INSERT INTO {} ({}) VALUES ({});'
                .format(table_name, ', '.join(field_names),
                        ','.join('%s' * len(field_names))))

    @staticmethod
    def delete(table_name, id_names):
        where_criteria = " AND ".join(
            "{} == %s".format(id_name) for id_name in id_names)
        return "DELETE FROM {} WHERE {};".format(table_name, where_criteria)


class MysqlTranslator(SQLTranslator):
    pass


class SqliteTranslator(SQLTranslator):

    @staticmethod
    def save(table_name, field_names):
        return ('INSERT INTO {} ({}) VALUES ({});'
                .format(table_name, ', '.join(field_names),
                        ','.join('?' * len(field_names))))

    @staticmethod
    def delete(table_name, id_names):
        where_criteria = " AND ".join(
            "{} == ?".format(id_name) for id_name in id_names)
        return "DELETE FROM {} WHERE {};".format(table_name, where_criteria)

    @classmethod
    def create_schema_constraints(cls, table_name, foreign_keys):
        sql = []
        for fk in foreign_keys:
            sql.extend(cls.foreign_key(table_name, fk))
        return sql

    @classmethod
    def foreign_key(cls, table_name, fk):
        fields = ", ".join(fk.fields)
        referenced_fields = ", ".join(fk.referenced_fields)
        referenced_table = fk.referenced_resource

        where_clause = " AND ".join(
            "{}.{} == NEW.{}".format(referenced_table, ref_field, field)
            for field, ref_field in zip(fk.fields, fk.referenced_fields))

        delete_where_clause = " AND ".join(
            "{}.{} == OLD.{}".format(table_name, ref_field, field)
            for field, ref_field in zip(fk.referenced_fields, fk.fields))

        return (
            "CREATE TRIGGER fk_{table_name}_to_{referenced_table}_i "
            "BEFORE INSERT ON {table_name} "
            "FOR EACH ROW "
            "WHEN (SELECT 1 FROM {referenced_table} WHERE {where_clause}) IS NULL "
            "BEGIN "
            "SELECT RAISE (ROLLBACK, "
            "'Foreign key mismatch: Value inserted into the {table_name} column ({fields}) "
            "does not correspond to row in the {referenced_table} table'); "
            "END;".format(**locals()),

            "CREATE TRIGGER fk_{table_name}_to_{referenced_table}_u "
            "BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW "
            "WHEN (SELECT 1 FROM {referenced_table} WHERE {where_clause}) IS NULL "
            "BEGIN "
            "SELECT RAISE (ROLLBACK, "
            "'Foreign key mismatch: Value updated into the {table_name} column ({fields}) "
            "does not correspond to row in the {referenced_table} table'); "
            "END;".format(**locals()),

            "CREATE TRIGGER fk_{table_name}_to_{referenced_table}_d "
            "BEFORE DELETE ON {referenced_table} "
            "FOR EACH ROW "
            "WHEN (SELECT 1 FROM {table_name} WHERE {delete_where_clause}) IS NOT NULL "
            "BEGIN "
            "SELECT RAISE (ROLLBACK, "
            "'Foreign key mismatch: Value deleted into the {referenced_table} column ({fields}) "
            "correspond to row in the {table_name} table'); "
            "END;".format(**locals()))


class PostgresTranslator(SQLTranslator):

    @staticmethod
    def binary_field(field):
        return '{name} BYTEA  {null}'
