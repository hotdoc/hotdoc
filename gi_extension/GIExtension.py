from lxml import etree

from symbols import Symbol, FunctionSymbol, ClassSymbol
import clang.cindex
from giscanner.annotationparser import GtkDocParameter

class GISymbol(object):
    def _make_name(self):
        return self._symbol.attrib["name"]

    def make_qualified_symbol (self, type_name):
        type_link = self.get_named_link (type_name)
        if type_link:
            tokens = [type_link]
        else:
            tokens = [type_name]

        utype = self._lookup_underlying_type(type_name)
        if utype == clang.cindex.CursorKind.STRUCT_DECL:
            tokens.append('*')

        return self._symbol_factory.make_qualified_symbol (type_name, None, tokens)


class GIPropertySymbol (GISymbol, Symbol):
    def _make_unique_id(self):
        parent_name = self._symbol.getparent().attrib['name']
        return "%s:::%s---%s" % (parent_name, self._symbol.attrib["name"],
                'property')

    def do_format (self):
        type_name = self._symbol.attrib["type"]
        self.type_ = self.make_qualified_symbol(type_name)
        return Symbol.do_format(self)


class GISignalSymbol (GISymbol, FunctionSymbol):
    def _make_unique_id(self):
        parent_name = self._symbol.getparent().attrib['name']
        return "%s:::%s---%s" % (parent_name, self._symbol.attrib["name"],
                'signal')

    def do_format (self):
        parent_name = self._symbol.getparent().attrib['name']
        rtype_name = self._symbol.attrib["return"]
        self.return_value = self.make_qualified_symbol (rtype_name)
        self.return_value.do_format()
        self.parameters = []

        i = 0
        dumped_params = list (self._symbol.findall ('param'))
        for param_name, param_comment in self._comment.params.iteritems():
            if i == 0:
                type_ = self.make_qualified_symbol (parent_name)
            else:
                type_ = self.make_qualified_symbol(
                        dumped_params[i - 1].attrib['type'])
            parameter = self._symbol_factory.make_custom_parameter_symbol\
                    (param_comment, type_.type_tokens, param_name)
            parameter.do_format()
            self.parameters.append(parameter)

        udata_type = self.make_qualified_symbol ("gpointer")
        udata_comment = GtkDocParameter ("user_data")
        udata_comment.description = "user data set when the signal handler was connected."
        udata_param = self._symbol_factory.make_custom_parameter_symbol\
                (udata_comment, udata_type.type_tokens, 'user_data')
        udata_param.do_format()
        self.parameters.append (udata_param)

        return Symbol.do_format(self)


class GIClassSymbol (ClassSymbol):
    def symbol_init (self, comments, extra_args):
        xml_node = extra_args['xml_node']
        self.xml_node = xml_node
        self._register_typed_symbol (GIPropertySymbol, "Properties")
        self._register_typed_symbol (GISignalSymbol, "Signals")

        for prop_node in xml_node.findall('property'):
            parent_name = prop_node.getparent().attrib['name']
            block_name = '%s:%s' % (parent_name, prop_node.attrib['name'])
            comment = comments.get(block_name)
            self.add_symbol (self._symbol_factory.make_custom (prop_node,
                comment, GIPropertySymbol))
        for prop_node in xml_node.findall('signal'):
            parent_name = prop_node.getparent().attrib['name']
            block_name = '%s::%s' % (parent_name, prop_node.attrib['name'])
            comment = comments.get(block_name)
            if not comment: # We do need a comment here
                continue
            self.add_symbol (self._symbol_factory.make_custom (prop_node,
                comment, GISignalSymbol))


class GIExtension(object):
    def __init__(self, xml_dump):
        self._gi_classes = {}
        root = etree.parse (xml_dump).getroot()
        for klass in root.findall("class"):
            self._gi_classes[klass.attrib["name"]] = klass

    def get_section_type (self, symbol):
        if type (symbol) != clang.cindex.Cursor:
            return (None, None)

        if not symbol.spelling in self._gi_classes:
            return (None, None)

        extra_args = {'xml_node': self._gi_classes[symbol.spelling]}
        return (GIClassSymbol, extra_args)
