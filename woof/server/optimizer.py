import opcode
import textwrap
from types import CodeType, FunctionType

from ..resource import MetaResource, Query, ScalarField
from ..db import DataBase


def build_get_single_ctrl(query, args_names, field_names):
    """
    Create optimized controller.
    """

    codes = [
        opcode.opmap['LOAD_GLOBAL'], 0, 0,
        opcode.opmap['LOAD_CONST'], 1, 0
    ]

    for i in range(len(args_names)):
        codes.extend((opcode.opmap['LOAD_FAST'], i, 0))

    codes.extend((
        opcode.opmap['BUILD_TUPLE'], len(args_names), 0,
        opcode.opmap['CALL_FUNCTION'], 2, 0,
        opcode.opmap['LOAD_ATTR'], 1, 0,
        opcode.opmap['CALL_FUNCTION'], 0, 0,
        opcode.opmap['STORE_FAST'], len(args_names), 0,  # store to 'values'

        opcode.opmap['LOAD_FAST'], len(args_names), 0,  # load from 'values'
        opcode.opmap['LOAD_CONST'], 0, 0,
        opcode.opmap['COMPARE_OP'], 8, 0,
        opcode.opmap['POP_JUMP_IF_FALSE'], len(args_names) * 3 + 37, 0,

        opcode.opmap['LOAD_FAST'], len(args_names), 0,
        opcode.opmap['RETURN_VALUE'],

        opcode.opmap['LOAD_GLOBAL'], 2, 0, # (dict)
        opcode.opmap['LOAD_GLOBAL'], 3, 0, # (zip)
        opcode.opmap['LOAD_CONST'], 2, 0,
        opcode.opmap['LOAD_FAST'], len(args_names), 0, # load from 'values'
        opcode.opmap['CALL_FUNCTION'], 2, 0,
        opcode.opmap['CALL_FUNCTION'], 1, 0,
        opcode.opmap['RETURN_VALUE'],
    ))

    ctrl = FunctionType(
        CodeType(
            len(args_names),  #  argcount
            0,  #  kwonlyargcount
            len(args_names) + 1,  # + nb var used
            7,  # stacksize
            67,  # flags
            bytes(codes),  # codestring
            (None, query, field_names),  # constants
            ('sql_execute', 'fetchone', 'dict', 'zip'),  # names
            tuple(args_names) + ('values',),  # varnames + var used
            __file__,  # filename
            'ctrl',  # name
            0,  # firstlineno
            b'\x00\x01\x1b\x01\x0c\x01\x04\x01'  # lnotab
        ), {'dict': dict, 'zip': zip, 'sql_execute': MetaResource.db.execute}
    )
    ctrl.single = True
    ctrl.optimizable = True
    return ctrl


def build_get_ctrl(query, args_names, field_names):
    """
    Create optimized controller for get request.
    """

    src = """
    def ctrl({args}):
        cursor = sql_execute({query!r}, ({query_params}))
        return [dict(zip({field_names!r}, record))
                for record
                in cursor]
    """.format(
        args=', '.join(args_names),
        query_params=', '.join(args_names) + (', ' if len(args_names) == 1 else ''),
        query=query,
        field_names=field_names)

    locals_env = {'dict': dict,
                  'zip': zip,
                  'sql_execute': MetaResource.db.execute}

    exec(compile(textwrap.dedent(src), __file__, 'single'), locals_env)

    ctrl = locals_env['ctrl']
    ctrl.optimizable = True
    return ctrl


class Analyser:
    """
    Analyse controller to extract sql query performed and parameter used.
    """

    def __init__(self, controller, url_parameters_names):
        self.controller = controller
        self._backup_mtd = None
        self.query = None
        self.ctrl_arguments = None
        self.selected_fields = None
        self.kwargs_names = {name: name
                             for name
                             in url_parameters_names}

    def run(self):
        self._backup_mtd = DataBase.execute
        DataBase.execute = self._database_execute
        try:
            self.controller(**self.kwargs_names)
        except AttributeError: # 'NoneType' object has no attribute 'fetchone'
            pass
        DataBase.execute = self._backup_mtd

        self._backup_mtd = Query.__init__
        Query.__init__ = self._query_init
        try:
            self.controller(**self.kwargs_names)
        except AttributeError: # 'NoneType' object has no attribute 'fetchone'
            pass
        Query.__init__ = self._backup_mtd

    def _database_execute(self, sql_query, parameters):
        self.query = sql_query
        self.ctrl_arguments = parameters

    def _query_init(self, resource, fields):
        if fields:
            self.selected_fields = fields
        else:
            self.selected_fields = tuple(field.name for field
                                         in resource._fields
                                         if isinstance(field, ScalarField))


def optimize(url_tree):
    """
    Replace controllers in url_tree by optimized controllers.
    """
    for controller, args_names in url_tree.get_controllers():

        if getattr(controller, 'optimizable', False):
            analyser = Analyser(controller, args_names)
            analyser.run()

            if getattr(controller, "single", False):
                url_tree.replace_controller(
                    controller,
                    build_get_single_ctrl(
                        analyser.query,
                        analyser.ctrl_arguments,
                        analyser.selected_fields
                    )
                )

            else:
                url_tree.replace_controller(
                    controller,
                    build_get_ctrl(
                        analyser.query,
                        analyser.ctrl_arguments,
                        analyser.selected_fields
                    )
                )

