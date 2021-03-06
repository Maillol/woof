
class MetaSQLTranslator(type):

    PROVIDERS = {}

    def __init__(cls, name, bases, attrs):
        if name != 'SQLTranslator':
            if name.endswith('Translator'):
                provider_name = name[:-len('Translator')].lower()
                type(cls).PROVIDERS[provider_name] = cls
                cls.PROVIDER = provider_name
            else:
                raise ValueError("{} class name must end with by '{}'"
                                 .format(cls, 'Translator'))


class SQLTranslator(metaclass=MetaSQLTranslator):
    substitution_char = '%s'

    @classmethod
    def create_schema(cls, table_name, fields, primary_key_field_name=[]):
        field_def = ', '.join(cls.field_definition(field) for field in fields)
        pk_def = cls.translate_pk(primary_key_field_name)
        return "CREATE TABLE {table_name}({field_def}{pk_def});".format(**locals())

    @classmethod
    def translate_pk(cls, primary_key_field_name):
        if primary_key_field_name:
            return ", PRIMARY KEY ({})".format(", ".join(primary_key_field_name))
        return ""

    @classmethod
    def create_schema_constraints(cls, table_name, foreign_keys, uniques):
        """
        :param table_name: name of table
        :param foreign_keys: List of ForeignKey objects
        :param uniques: list of list of fields name unique together.
        :return: list of SQL constraints
        """
        constraints = []
        for fk in foreign_keys:
            constraints.append(cls.foreign_key(table_name, fk))
        for unique in uniques:
            constraints.append(cls.unique(table_name, unique))
        return constraints

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
    def unique(cls, table_name, fields):
        fields_names = ", ".join(fields)
        return (
            "ALTER TABLE {table_name} "
            "ADD UNIQUE ({fields_names});"
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
                        ','.join(['%s'] * len(field_names))))

    @staticmethod
    def update(table_name, field_names, id_names):
        set_expression = ', '.join("{} = %s".format(name)
                                  for name in field_names)
        where_criteria = " AND ".join(
            "{} = %s".format(id_name) for id_name in id_names)
        return ("UPDATE {} SET {} WHERE {}"
                .format(table_name, set_expression, where_criteria))

    @staticmethod
    def delete(table_name, id_names):
        where_criteria = " AND ".join(
            "{} = %s".format(id_name) for id_name in id_names)
        return "DELETE FROM {} WHERE {};".format(table_name, where_criteria)


class MysqlTranslator(SQLTranslator):

    @staticmethod
    def integer_field(field):
        sql = SQLTranslator.integer_field(field)
        if field.auto_increment:
            sql += ' AUTO_INCREMENT'
        return sql


class SqliteTranslator(SQLTranslator):

    substitution_char = '?'

    @staticmethod
    def save(table_name, field_names):
        return ('INSERT INTO {} ({}) VALUES ({});'
                .format(table_name, ', '.join(field_names),
                        ','.join('?' * len(field_names))))

    @staticmethod
    def update(table_name, field_names, id_names):
        set_expression = ','.join("{} = ?".format(name)
                                  for name in field_names)
        where_criteria = " AND ".join(
            "{} == ?".format(id_name) for id_name in id_names)
        return ("UPDATE {} SET {} WHERE {}"
                .format(table_name, set_expression, where_criteria))

    @staticmethod
    def delete(table_name, id_names):
        where_criteria = " AND ".join(
            "{} == ?".format(id_name) for id_name in id_names)
        return "DELETE FROM {} WHERE {};".format(table_name, where_criteria)

    @classmethod
    def create_schema_constraints(cls, table_name, foreign_keys, uniques):
        sql = []
        for fk in foreign_keys:
            sql.extend(cls.foreign_key(table_name, fk))
        for unique in uniques:
            idx_name = "idx_{}_{}".format(table_name, '_'.join(unique))
            sql.append(
                "CREATE UNIQUE INDEX {} ON {}({});"
                .format(idx_name, table_name, ', '.join(unique)))
        return sql

    @classmethod
    def foreign_key(cls, table_name, fk):
        fields = ", ".join(fk.fields)
        referenced_fields = ", ".join(fk.referenced_fields)
        referenced_table = fk.referenced_resource

        where_clause = " AND ".join(
            "{}.{} == NEW.{}".format(referenced_table, ref_field, field)
            for field, ref_field in zip(fk.fields, fk.referenced_fields))

        field_is_not_null_close = " AND ".join(
            "NEW.{} IS NOT NULL".format(field)
            for field in fk.fields)

        delete_where_clause = " AND ".join(
            "{}.{} == OLD.{}".format(table_name, ref_field, field)
            for field, ref_field in zip(fk.referenced_fields, fk.fields))

        return (
            "CREATE TRIGGER fk_{table_name}_to_{referenced_table}_i "
            "BEFORE INSERT ON {table_name} "
            "FOR EACH ROW "
            "WHEN ((SELECT 1 FROM {referenced_table} WHERE {where_clause}) IS NULL) AND ({field_is_not_null_close})"
            "BEGIN "
            "SELECT RAISE (ROLLBACK, "
            "'Foreign key mismatch: Value inserted into the {table_name} column ({fields}) "
            "does not correspond to row in the {referenced_table} table'); "
            "END;".format(**locals()),

            "CREATE TRIGGER fk_{table_name}_to_{referenced_table}_u "
            "BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW "
            "WHEN ((SELECT 1 FROM {referenced_table} WHERE {where_clause}) IS NULL) AND ({field_is_not_null_close})"
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


class PostgresqlTranslator(SQLTranslator):

    @staticmethod
    def binary_field(field):
        return '{name} BYTEA {null}'
