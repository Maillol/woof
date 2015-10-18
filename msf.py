#!/usr/bin/env python3
#-*- coding:utf-8 -*-

from playhouse.shortcuts import model_to_dict
import json
from urllib.parse import parse_qsl
from functools import partial
from resource2 import MetaResource
from url_parser import path_to_sql, query_string_to_where_clause, select
import peewee


def parse_to_create(cls, extern, entity_conf):
    for k, v in entity_conf.items():
        nested = extern.get(k)
        if nested is not None and isinstance(v, dict):
            entity_conf[k] = parse_to_create(nested[0], nested[1], v)
    return cls.create(**entity_conf)



class RESTServer:

    def get(self, url, query_string):
        entity_name, entity, entity_id, join_criterias = path_to_sql(MetaResource.register, url)
        query = select(entity, entity_id, join_criterias)
        
        if query_string:
            fields_types = MetaResource.fields_types[entity_name]
            query_string = [(k, fields_types[k.split('-')[0]](v)) for k, v in parse_qsl(query_string)]
            query = query.where(query_string_to_where_clause(entity, query_string))

        with MetaResource.db.atomic():
            response = json.dumps([model_to_dict(e) for e in query]).encode('utf-8')
            return response

    def post(self, url, query_string, entity_config):
        with MetaResource.db.atomic():
            entity_name, entity_id = next(cut_path(environ['PATH_INFO']))
            Entity = MetaResource.register[entity_name][0]
            entity = Entity[entity_id]
            
            entity.set(**entity_config)
            start_response('200 OK', response_headers)
            # update(e.set() for e in Entity if e.id == entity_id)
            # update(p.set(price=price * 1.1) for p in Product if p.category.name == "T-Shirt")
            # entity.set(**dict_with_new_values)
            return json.dumps(entity.to_dict()).encode('utf-8')

    def __call__(self, environ, start_response):
        method = environ['REQUEST_METHOD']
        response_headers = [('Content-type', 'Application/json')]
        if method == 'GET':
            response = self.get(environ['PATH_INFO'], environ['QUERY_STRING'])
            start_response('200 OK', response_headers)
            yield response

        elif method == 'POST':
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))

            except ValueError:
                request_body_size = 0

            if request_body_size:
                request_body = environ['wsgi.input'].read(request_body_size)
                entity_config = json.loads(request_body.decode('utf-8'))
                try:                
                    self.post(environ['PATH_INFO'], environ['QUERY_STRING'], entity_config)
                except ObjectNotFound:
                    start_response('404 Not Found', response_headers)
                    yield 'resource doesn\'t exist' # FIXME: I would id and type resource in msg

            else:
                start_response('500 No Body', response_headers)
                yield b'"Request has not body"'

        elif method == 'PUT':
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0

            path, entity_name = environ['PATH_INFO'].rstrip('/').rsplit('/', 1)
            if path:
                _, entity, entity_id, join_criterias = path_to_sql(MetaResource.register, path)
                query = select(entity, entity_id, join_criterias).get()

            request_body = environ['wsgi.input'].read(request_body_size)
            entity_config = json.loads(request_body.decode('utf-8'))

            # url = '/Lieu-dep/1/Trajet/'
            # Trajet.create(dep=1, name="Cheval", arr=paris)

            with MetaResource.db.atomic():
                entity = parse_to_create(MetaResource.register[entity_name][0],
                                         MetaResource.register[entity_name][1],
                                         entity_config)

            start_response('201 Created', response_headers)
            yield json.dumps(model_to_dict(entity)).encode('utf-8')

        elif method == 'DELETE':
            with MetaResource.db.atomic():
                entity_name, entity_id = next(cut_path(environ['PATH_INFO']))
                Entity = MetaResource.register[entity_name][0]
                try:                
                    entity = Entity[entity_id]
                
                except ObjectNotFound:
                    start_response('404 Not Found', response_headers)
                    yield '"resource {} doesn\'t exist"'.format(entity_id).encode('utf-8')               

                else:
                    deleted = json.dumps(entity.to_dict()).encode('utf-8')
                    entity.delete()
                    start_response('200 OK', response_headers)
                    yield deleted

