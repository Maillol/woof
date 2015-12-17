#!/usr/bin/env python3
#-*- coding:utf-8 -*-

from ..db import DataBase
import os
import json


class ConfigIsNotValidError(Exception):
    def __init__(self, msg, path=[]):
        super().__init__(msg)
        self.msg = msg
        self.path_through_conf = list(path)

    def __str__(self):
        path = '.'.join(self.path_through_conf)
        return "{}: {}".format(path, self.msg)

    __repr__ = __str__


class ChoiceValidator:
    """
    Valide if item is one of choices.
    """
    def __init__(self, choices, is_required=True):
        self.is_required = is_required
        self.choices = choices

    def valid(self, item):
        if item not in self.choices:
            msg = 'must be one of {}'.format(self.choices)
            raise ConfigIsNotValidError(msg)
        return item


class IntValidator:
    """
    Valide if item is int between min and max. 
    By default min is minus infinity and max is infinity
    """

    def __init__(self, int_min=float("-inf"), int_max=float("+inf"), is_required=True):
        self.is_required = is_required
        self.max = int_max
        self.min = int_min

    def valid(self, item):
        if not isinstance(item, int) or not self.max >= item >= self.min:
            msg = 'must be an integer between {s.min} and {s.max}'.format(s=self)
            raise ConfigIsNotValidError(msg)
        return item

class FloatValidator:
    """
    Valide if item is float between min and max. 
    By default min is minus infinity and max is infinity
    """

    def __init__(self, float_min=float("-inf"), float_max=float("+inf"), is_required=True):
        self.is_required = is_required
        float()
        self.min = float_min
        self.max = float_max

    def valid(self, item):
        if not isinstance(item, float) or not self.max >= item >= self.min:
            msg = 'must be a float between {s.min} and {s.max}'.format(s=self)
            raise ConfigIsNotValidError(msg)
        return item

class IsTypeValidator:
    expected_type = NotImplemented
    name_type = NotImplemented

    def __init__(self, can_be_null=False, is_required=True):
        self.is_required = is_required
        self.can_be_null = can_be_null

    def valid(self, item):
        if item is None and self.can_be_null:
            return None

        if not isinstance(item, self.expected_type):
            msg = 'must be a {}'.format(self.name_type)
            if self.can_be_null:
                msg += ' or null'
            raise ConfigIsNotValidError(msg)
        return item


class StrValidator(IsTypeValidator):
    expected_type = str
    name_type = 'string'


class DictValidator(IsTypeValidator):
    expected_type = dict
    name_type = 'object'

    def __init__(self, can_be_null=False, is_required=True, children={}):
        super().__init__(can_be_null, is_required)
        self.children = children.copy()

    def valid(self, item):
        clean_item = super().valid(item)
        clean_children = {}
        for key, validator in self.children.items():
            if key in clean_item:
                try:
                    clean_children[key] = validator.valid(clean_item[key])
                except ConfigIsNotValidError as error:
                    path = [key] + error.path_through_conf
                    raise ConfigIsNotValidError(error.msg, path)
            elif validator.is_required:
                raise ConfigIsNotValidError("is required", [key])
        return clean_children


class ListValidator(IsTypeValidator):
    expected_type = list
    name_type = 'list'


class TranstypingValidator:
    """
    Transtype item using constructor. If unpacking is True
    constructor will called using unpacking with item else
    item is directly given.
    """
    def __init__(self, constructor, unpacking=True, is_required=True):
        self.is_required = is_required
        self.constructor = constructor
        self.unpacking = unpacking

    def valid(self, item):
        if self.unpacking:
            if not isinstance(item, dict):
                raise ConfigIsNotValidError(
                    'must be a dict of parameters to {}'.format(self.constructor))
            try:
                return self.constructor(**item)
            except TypeError as error:
                msg = '{} {}'.format(self.constructor, str(error))
                raise ConfigIsNotValidError(msg)
        return self.constructor(item)


class ConfigReader:

    FILE_NAME = 'config.json'
    VALIDATOR = None
    _not_loaded = True

    def reload_config(self):
        self.clear_config()
        cls = type(self)
        cls.path_to_conf = os.environ.get(
            'MSF_CONFIG_FILE', os.path.abspath(cls.FILE_NAME))
        with open(cls.path_to_conf, 'r') as config_file:
            configuration = json.load(config_file)

        if not isinstance(configuration, dict):
            raise ConfigIsNotValidError(
                "'{}' config file must contain a json dict".format(cls.path_to_conf))

        clean = cls.VALIDATOR.valid(configuration)

        for key, value in clean.items():
            setattr(self, key, value)

    def clear_config(self):
        for key in vars(self).copy().keys():
            delattr(self, key)

    def __getattr__(self, name):
        if type(self)._not_loaded:
            self.reload_config()
            type(self)._not_loaded = False
            return getattr(self, name)


ConfigReader.VALIDATOR = DictValidator(children={
    "database": TranstypingValidator(DataBase)
})


config = ConfigReader()

