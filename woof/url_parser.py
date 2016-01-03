#!/usr/bin/env python
#-*- coding:utf-8 -*-

import operator

def path_to_sql(register, path):
    """
    return the list:
        [<entity_name>, <entity>, <entity_id>, <join_criterias>]
        where:
            <entity_name> is entity name selected
            <entity> is class pewee selected
            <entity_id> is entity selected
            <join_criterias> is list of 3-tuple (<Class peewee>, <id>, <field-name-jointure>)
            this list of 3-tuple may be used to join tables.
    """
    i_path = iter(path[1:].split('/'))
    join_criterias = []

    entity_name = next(i_path)
    try:
        entity_name, field_name = entity_name.split('-', 1)
    except ValueError:
        field_name = None
    entity_id = next(i_path, '')
    entity = register[entity_name][0]

    while True:
        try:
            entity_name = next(i_path)
        except StopIteration:
            break

        join_criterias.append((entity, entity_id, field_name))

        try:
            entity_name, field_name = entity_name.split('-', 1)
        except ValueError:
            field_name = None

        entity_id = next(i_path, '')
        entity = register[entity_name][0]

    # q = Trajet.select().where(Trajet.id == 1)
    #           .join(Lieu, on=Lieu.id == Trajet.dep).where(Lieu.id==1)

    return entity_name, entity, entity_id, join_criterias

def select(entity, entity_id, join_criterias):
    sql_q = entity.select()
    if entity_id:
        sql_q = sql_q.where(entity.id == entity_id)
    previous_entity = entity

    for entity, entity_id, join_field_name in join_criterias:
        if join_field_name is None:
            sql_q = sql_q.join(entity)
        else:
            sql_q = sql_q.join(entity, on=entity.id == getattr(previous_entity, join_field_name))
        if entity_id:
            sql_q = sql_q.where(entity.id == entity_id)
        previous_entity = entity

    return sql_q


def query_string_to_where_clause(entity, query_string):
    """
    return where clause statement.

    arguments:
        entity - Class peewee
        query_string - [('<field_name>-<op>', '<value-transtyped>')]
    """
    qs_iterator = iter(query_string)
    k, v = next(qs_iterator)
    field, ope = k.split('-')
    expression = getattr(operator, ope)(getattr(entity, field), v)
    for k, v in qs_iterator:
        field, ope = k.split('-')
        expression = expression & (getattr(operator, ope)(getattr(entity, field), v))
    return expression


