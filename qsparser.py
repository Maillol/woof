#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import operator

def build_filter(entity, query_string):
    iqs = iter(query_string)
    k, v = next(iqs)
    field, ope = k.split('-')
    
    expression = getattr(operator, ope)(getattr(entity, field), v)
    
    for k, v in iqs:
        field, ope = k.split('-')
        expression = expression & (getattr(operator, ope)(getattr(entity, field), v))
    return expression

