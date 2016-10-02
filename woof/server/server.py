#!/usr/bin/env python3
#-*- coding:utf-8 -*-

from traceback import extract_tb
import json
import os

from .optimizer import optimize
from ..db import IntegrityError


OPTIMIZE = False


class RESTServerError(Exception):
    pass


class RequestHasNotBodyError(RESTServerError):
    code = '500 No Body'
    body = b'{"error": "Request has no body"}'


class NotFoundError(RESTServerError):
    code = '404 Not Found'
    body = b'{"error": "Not Found"}'


def traceback_to_dict(error):
    """
    Extract traceback from an exception.
    """
    traceback = {'error': type(error).__name__,
                 'args': error.args,
                 'traceback': extract_tb(error.__traceback__),
                 'context': None,
                 'explicitly_chained': False}

    if error.__cause__ is not None:
        traceback['explicitly_chained'] = True

    if error.__context__ is not None:
        traceback['context'] = traceback_to_dict(error.__context__)

    return traceback


class RESTServer:

    def __init__(self, entry_point):
        self.get_urls = entry_point.get_urls
        self.put_urls = entry_point.put_urls
        self.post_urls = entry_point.post_urls
        self.del_urls = entry_point.del_urls
        self.opt_urls = entry_point.opt_urls
        if OPTIMIZE:
            optimize(self.get_urls)

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

                resources = controller(**parameters)
                if hasattr(controller, 'single') and controller.single:
                    if resources:
                        code = '200 OK'
                        body = json.dumps(resources).encode('utf-8')

                    else:
                        code = '404 Not Found'
                        body = b'{"error": "Resource not found"}'

                else:
                    code = '200 OK'
                    body = json.dumps(resources).encode('utf-8')

            elif method == 'POST':
                try:
                    controller, parameters = self.post_urls.get(environ['PATH_INFO'])
                except LookupError:
                    raise NotFoundError()

                resource = controller(self._parse_body(environ), **parameters)
                #response_headers.append(('Location', resource_location))
                code = '200 Created'
                body = json.dumps(resource).encode('utf-8')

            elif method == 'PUT':
                try:
                    controller, parameters = self.put_urls.get(environ['PATH_INFO'])
                except LookupError:
                    raise NotFoundError()

                resource = controller(self._parse_body(environ), **parameters)
                code = '200 Updated'
                body = json.dumps(resource).encode('utf-8')

            elif method == 'DELETE':
                try:
                    controller, parameters = self.del_urls.get(environ['PATH_INFO'])
                except LookupError:
                    raise NotFoundError()

                controller(**parameters)
                code = '200 Deleted'
                body = b'""'

            else:
                code = '405 Method Not Allowed'
                body = b'{"error": "Method Not Allowed"}'

        except RESTServerError as error:
            code = error.code
            body = error.body

        except IntegrityError as error:
            code = '409 Conflict'
            body = json.dumps({"error": error.args[0]}).encode('utf-8')

        except Exception as error:
            code = '500 Internal Server Error'
            body = json.dumps(traceback_to_dict(error)).encode('utf-8')

        start_response(code, response_headers)
        yield body

