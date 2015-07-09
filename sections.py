import os

from xml.etree import ElementTree as ET
from giscanner import ast

from base_formatter import NameFormatter

class SectionsGenerator(object):
    def __init__ (self, transformer):
        self.__transformer = transformer

        self.__name_formatter = NameFormatter (language='C')

        # Used to close the previous section if necessary
        self.__opened_section = None

    def generate (self, output):
        # Three passes but who cares
        self.__unsorted_symbols = ""
        filename = os.path.join (output, "%s-sections.txt" %
                self.__transformer.namespace.name)
        with open (filename, 'w') as f:
            f.write ("<SECTIONS>")
            self.__walk_node(output, self.__transformer.namespace, [], f)
            self.__transformer.namespace.walk(lambda node, chain:
                    self.__walk_node(output, node, chain, f))
            if self.__opened_section:
                f.write ("</SYMBOLS>")
                f.write ("</SECTION>")
            f.write ('<SYMBOLS>')
            f.write (self.__unsorted_symbols)
            f.write ('</SYMBOLS>')
            f.write ("</SECTIONS>")

        with open (filename, 'r') as f:
            contents = f.read ()
            root = ET.fromstring(contents)
            self.__indent(root)

        with open (filename, 'w') as f:
            f.write ('<?xml version="1.0"?>\n')
            f.write(ET.tostring(root))

        return root
    
    def __walk_node(self, output, node, chain, f):
        name = self.__name_formatter.get_full_node_name (node)

        if type (node) in [ast.Namespace, ast.DocSection, ast.Class,
                ast.Interface]:
            if self.__opened_section:
                f.write ("</SYMBOLS>")
                f.write ("</SECTION>")

            f.write ("<SECTION>")
            f.write ("<SYMBOL>%s</SYMBOL>" % name)
            f.write ("<SYMBOLS>")
            self.__opened_section = node
        elif hasattr (node, "parent") and self.__opened_section and \
                node.parent is not self.__opened_section:
            f.write ("</SYMBOLS>")
            f.write ("</SECTION>")
            self.__unsorted_symbols += "<SYMBOL>%s</SYMBOL>\n" % name
            self.__opened_section = None
        elif self.__opened_section:
            f.write ("<SYMBOL>%s</SYMBOL>" % name)
        else:
            self.__unsorted_symbols += "<SYMBOL>%s</SYMBOL>\n" % name

        return True

    def __indent (self, elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.__indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
