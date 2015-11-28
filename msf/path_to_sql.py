def path_to_sql(register, path):
    i_path = iter(path[1:].split('/'))
    for_sql_query = []

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

        for_sql_query.append((entity, entity_id, field_name))

        try:
            entity_name, field_name = entity_name.split('-', 1)
        except ValueError:
            field_name = None

        entity_id = next(i_path, '')
        entity = register[entity_name][0]

    # q = Trajet.select().where(Trajet.id == 1)
    #           .join(Lieu, on=Lieu.id == Trajet.dep).where(Lieu.id==1)

    #print(entity, repr(entity_id))
    #print(repr(for_sql_query))

    sql_q = entity.select()
    if entity_id:
        sql_q = sql_q.where(entity.id == entity_id)
    previous_entity = entity

    for entity, entity_id, join_field_name in for_sql_query:
        if join_field_name is None:
            sql_q = sql_q.join(entity)
        else:
            sql_q = sql_q.join(entity, on=entity.id == getattr(previous_entity, join_field_name))
        if entity_id:
            sql_q = sql_q.where(entity.id == entity_id)
        previous_entity = entity
    return sql_q

