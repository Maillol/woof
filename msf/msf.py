#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import json
import os

def parse_to_create(cls, extern, entity_conf):
    for k, v in entity_conf.items():
        nested = extern.get(k)
        if nested is not None and isinstance(v, dict):
            entity_conf[k] = parse_to_create(nested[0], nested[1], v)
    return cls.create(**entity_conf)


# query_string = [(k, fields_types[k.split('-')[0]](v)) for k, v in parse_qsl(query_string)]


class RESTServerError(Exception):
    pass


class RequestHasNotBodyError(RESTServerError):
    code = '500 No Body'
    body = b'{"error": "Request has no body"}'


class NotFoundError(RESTServerError):
    code = '404 Not Found'
    body = b'{"error": "Not Found"}'


class RESTServer:

    def __init__(self, entry_point):
        self.get_urls = entry_point.get_urls
        self.put_urls = entry_point.put_urls
        self.post_urls = entry_point.post_urls
        self.del_urls = entry_point.del_urls
        self.opt_urls = entry_point.opt_urls

    @staticmethod
    def _parse_body(environ):
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            request_body_size = 0

        if request_body_size:
            request_body = environ['wsgi.input'].read(request_body_size)
            return json.loads(request_body.decode('utf-8'))
        raise RequestHasNotBodyError()

    def __call__(self, environ, start_response):
        method = environ['REQUEST_METHOD']
        response_headers = [('Content-type', 'Application/json')]

        environ['QUERY_STRING']
        try:
            if method == 'GET':
                try:
                    controller, parameters = self.get_urls.get(environ['PATH_INFO'])
                except LookupError:
                    raise NotFoundError()

                resources = tuple(controller(*parameters))
                if hasattr(controller, 'single') and controller.single:
                    if resources:
                        code = '200 OK'
                        body = json.dumps(resources[0].to_dict()).encode('utf-8')

                    else:
                        code = '404 Not Found'
                        body = b'{"error": "Resource not found"}'

                else:
                    code = '200 OK'
                    if resources:
                        body = json.dumps([resource.to_dict()
                                           for resource
                                           in resources]).encode('utf-8')

                    else:
                        body = b'[]'

            elif method == 'POST':
                try:
                    controller, parameters = self.post_urls.get(environ['PATH_INFO'])
                except LookupError:
                    raise NotFoundError()

                resource = controller(self._parse_body(environ), *parameters)
                #response_headers.append(('Location', resource_location))
                code = '200 Created'
                body = json.dumps(resource.to_dict()).encode('utf-8')

            elif method == 'PUT':
                try:
                    controller, parameters = self.put_urls.get(environ['PATH_INFO'])
                except LookupError:
                    raise NotFoundError()

                controller(self._parse_body(environ), *parameters)
                code = '200 Updated'
                body = b'""'

            elif method == 'DELETE':
                try:
                    controller, parameters = self.del_urls.get(environ['PATH_INFO'])
                except LookupError:
                    raise NotFoundError()

                controller(*parameters)
                code = '200 Deleted'
                body = b'""'

            else:
                code = '405 Method Not Allowed'
                body = b'{"error": "Method Not Allowed"}'

        except RESTServerError as error:
            code = error.code
            body = error.body

        start_response(code, response_headers)
        yield body

