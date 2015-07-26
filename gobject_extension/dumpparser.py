from lxml import etree

from base_formatter import SymbolFactory, Symbol

class GIPropertyNode (object):
    def __init__(self, xml_node):
        self.xml_node = xml_node

class GISymbolFactory (SymbolFactory):
    def __init__(self, __doc_formatter):
        SymbolFactory.__init__(self, doc_formatter)
        self.__symbol_classes = {
                }

    def make (self, symbol, comment):
        pass        

class GIDumpParser(object):
    def __init__(self, xml_dump):
        root = etree.parse (xml_dump).getroot()
        symbols = {}
        for prop in root.findall(".//property"):
            symbols[prop.attrib["name"]] = GIPropertyNode (prop)
        print symbols
