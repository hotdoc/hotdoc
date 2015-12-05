import os, ast, glob
from ..core.base_extension import BaseExtension
from hotdoc.utils.loggable import Loggable, progress_bar
from hotdoc.core.symbols import *
from hotdoc.extensions.python_doc_parser import google_doc_to_native
from hotdoc.core.doc_tool import HotdocWizard
from hotdoc.core.wizard import QuickStartWizard
from hotdoc.core.comment_block import comment_from_tag

class PythonScanner(Loggable):
    def __init__(self, doc_tool, sources):
        Loggable.__init__(self)
        self.doc_tool = doc_tool

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
        class_symbol = self.doc_tool.get_or_create_symbol(ClassSymbol,
                comment=comment,
                display_name=klass_name)

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
            return_tag = comment.tags.get('returns')
            return_comment = comment_from_tag(return_tag)
            retval = ReturnValueSymbol (type_tokens=[],
                    comment=return_comment)
        else:
            retval = None

        func_symbol = self.doc_tool.get_or_create_symbol(FunctionSymbol,
                parameters=parameters,
                return_value=retval,
                comment=comment,
                display_name=func_name)

    def __parse_parameters(self, args, comment):
        parameters = []
        if comment:
            param_comments = comment.params
        else:
            param_comments = {}

        for arg in args.args:
            param_comment = param_comments.get (arg.id)
            param = ParameterSymbol (argname=arg.id,
                    type_tokens=[],
                    comment=param_comment)
            parameters.append (param)

        return parameters

DESCRIPTION=\
"""
Parse python source files and extract symbols and comments.
"""

PYTHON_SOURCES_PROMPT=\
"""
Please pass a list of python source files.

You can pass wildcards here, for example:

>>> ['../foo/*.py', '../foo//bar/*.py]

These wildcards will be evaluated each time hotdoc is run.

You will be prompted for source files to ignore afterwards.
"""

PYTHON_FILTERS_PROMPT=\
"""
Please pass a list of python source files to ignore.

You can pass wildcards here, for example:

>>> ['../foo/*priv*.py']

These wildcards will be evaluated each time hotdoc is run.
"""

def validate_filters(wizard, thing):
    if not QuickStartWizard.validate_globs_list(wizard, thing):
        return False

    source_files = resolve_patterns(wizard.config.get('python_sources', []), wizard)

    filters = resolve_patterns(thing, wizard)

    source_files = [item for item in source_files if item not in filters]

    print "The files to be parsed would now be %s" % source_files

    return wizard.ask_confirmation()

def resolve_patterns(source_patterns, conf_path_resolver):
    source_files = []
    for item in source_patterns:
        item = conf_path_resolver.resolve_config_path(item)
        source_files.extend(glob.glob(item))

    return source_files

def source_files_from_config(config, conf_path_resolver):
    sources = resolve_patterns(config.get('python_sources', []), conf_path_resolver)
    filters = resolve_patterns(config.get('python_source_filters', []),
            conf_path_resolver)
    sources = [item for item in sources if item not in filters]
    return [os.path.abspath(source) for source in sources]

class PythonExtension(BaseExtension):
    EXTENSION_NAME = 'python-extension'

    def __init__(self, doc_tool, config):
        BaseExtension.__init__(self, doc_tool, config)
        self.sources = source_files_from_config(config, doc_tool)
        self.python_index = config.get('python_index')
        doc_tool.doc_tree.page_parser.register_well_known_name('python-api',
                self.python_index_handler)

    def setup(self):
        if not self.sources:
            return

        self.scanner = PythonScanner (self.doc_tool, self.stale_source_files)

    def get_source_files(self):
        return self.sources

    def python_index_handler (self, doc_tree):
        index_path = os.path.join(doc_tree.prefix, self.python_index)
        index_path = self.doc_tool.resolve_config_path(index_path)
        new_page = doc_tree.build_tree(index_path, 'python-extension')
        return index_path

    @staticmethod
    def add_arguments (parser):
        group = parser.add_argument_group('Python extension',
                DESCRIPTION)
        group.add_argument ("--python-sources", action="store", nargs="+",
                dest="python_sources", help="Python source files to parse",
                extra_prompt=PYTHON_SOURCES_PROMPT,
                validate_function=QuickStartWizard.validate_globs_list,
                finalize_function=HotdocWizard.finalize_paths)
        group.add_argument ("--python-source-filters", action="store", nargs="+",
                dest="python_source_filters", help="Python source files to ignore",
                extra_prompt=PYTHON_FILTERS_PROMPT,
                validate_function=validate_filters,
                finalize_function=HotdocWizard.finalize_paths)
        group.add_argument ("--python-index", action="store",
                dest="python_index",
                help="Path to the python root markdown file",
                finalize_function=HotdocWizard.finalize_path)
