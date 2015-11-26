from ..core.base_extension import BaseExtension
from hotdoc.utils.loggable import Loggable, progress_bar
from hotdoc.core.symbols import *
from hotdoc.extensions.python_doc_parser import google_doc_to_native
import pyment.docstring as docs
import os, ast

class PythonScanner(Loggable):
    def __init__(self, sources):
        Loggable.__init__(self)
        self.symbols = {}

        self.__node_parsers = {
                    ast.ClassDef: self.__parse_class,
                    ast.FunctionDef: self.__parse_function,
                }

        for source in sources:
            self.__current_filename = source
            with open (source, 'r') as f:
                code = f.read()
            tree = ast.parse(code)
            modname = os.path.basename (os.path.splitext(source)[0])
            self.__parse_module (tree.body, modname)

    def __parse_module (self, body, modname):
        for node in body:
            f = self.__node_parsers.get(type(node))
            if f:
                f (node, modname)

    def __parse_class (self, klass, parent_name):
        klass_name = '.'.join((parent_name, klass.name))
        comment = google_doc_to_native(ast.get_docstring (klass)) 
        comment.filename = self.__current_filename
        class_symbol = ClassSymbol([], {}, comment, klass_name, None)
        self.symbols[klass_name] = class_symbol

        for node in klass.body:
            f = self.__node_parsers.get (type(node))
            if f:
                f(node, klass_name)

    def __params_doc_to_dict (self, params_doc):
        dict_ = {}
        for param in params_doc:
            dict_[param[0]] = (param[1], param[2])

        return dict_

    def __parse_function (self, function, parent_name):
        func_name = '.'.join ((parent_name, function.name))

        docstring = ast.get_docstring (function)
        if docstring:
            comment = google_doc_to_native(docstring)
            comment.filename = self.__current_filename
        else:
            comment = None

        parameters = self.__parse_parameters(function.args, comment)

        if comment:
            return_comment = comment.tags.pop('returns', None)
            retval = ReturnValueSymbol ([], return_comment)
        else:
            retval = None

        func_symbol = FunctionSymbol (parameters, retval, comment, func_name,
                None)
        self.symbols[func_name] = func_symbol

    def __parse_parameters(self, args, comment):
        parameters = []
        if comment:
            param_comments = comment.params
        else:
            param_comments = {}

        for arg in args.args:
            param_comment = param_comments.get (arg.id)
            param = ParameterSymbol (arg.id, [arg.id], param_comment)
            parameters.append (param)

        return parameters

DESCRIPTION=\
"""
Parse python source files and extract symbols and comments.
"""

class PythonExtension(BaseExtension):
    EXTENSION_NAME = 'python-extension'

    def __init__(self, doc_tool, config):
        BaseExtension.__init__(self, doc_tool, config)
        self.sources = config.get('python_sources')

    def setup(self):
        if not self.sources:
            return

        self.scanner = PythonScanner (self.sources)

    def get_extra_symbols (self):
        return self.scanner.symbols

    @staticmethod
    def add_arguments (parser):
        group = parser.add_argument_group('Python extension',
                DESCRIPTION)
        group.add_argument ("--python-sources", action="store", nargs="+",
                dest="python_sources", help="Python source files to parse")
