#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

dir_ = os.path.dirname(os.path.abspath(__file__))
sys.path.append (os.path.abspath(os.path.join(dir_, os.pardir, "src")))

import StringIO
from lxml import etree as ET
import subprocess

OUTPUT=sys.argv[3]

def db_to_md (content):
    with open ("tmpfile", 'w') as f:
        f.write (content)
    cmd = ['pandoc', '-s', '-f', 'docbook', '-t', 'markdown']
    cmd.append ("tmpfile")
    converted = subprocess.check_output (cmd)
    os.unlink ('tmpfile')
    return converted

def convert_file (filename, new_name):
    with open(os.devnull, 'w') as f:
        xincluded = subprocess.check_output (["xmllint", "--xinclude",
            filename], stderr=f)

    converted = db_to_md (xincluded)
    print "writing conversion to", new_name
    with open (os.path.join (OUTPUT, new_name + ".markdown"), 'w') as f:
        f.write (converted)
    return os.path.join (OUTPUT, new_name + ".markdown")

def create_symbol_file (section_node, name):
    name = '_'.join(name.split())
    child = section_node.getchildren()[-1]
    symbols = child.tail.split("\n")
    print "writing symbols to", name
    with open (os.path.join (OUTPUT, name + ".markdown"), 'w') as f:
        f.write ("### %s\n\n" % name)
        for symbol in symbols:
            if symbol:
                f.write ("* [%s]()\n" % symbol)
    return os.path.join (OUTPUT, name + ".markdown")

def parse_sgml_chapters (part, filename, path, level, sections):
    out = ""
    out += "# %s\n\n" % part.find("title").text
    for elem in part.iterchildren ("{http://www.w3.org/2003/XInclude}include", "chapter"):
        if elem.tag == "{http://www.w3.org/2003/XInclude}include":
            nested_filename = elem.attrib["href"]
            title = os.path.basename (nested_filename)
            title = os.path.splitext (title)[0]
            if not title in sections:
                new_filename = convert_file (os.path.join (path,
                    nested_filename), title)
            else:
                section_node = sections[title]
                title_node = section_node.find("TITLE")
                if title_node is not None:
                    new_filename = create_symbol_file (sections[title],
                            title_node.text)
                else:
                    new_filename = create_symbol_file (sections[title], title)
            out += "#### [%s](%s)\n\n" % (title, os.path.basename(new_filename))
        else:
            title = elem.find("title").text
            nested_filename = '_'.join(title.split()) + ".markdown"
            out += "### [%s](%s)\n" % (title, nested_filename)
            parse_sgml_chapters (elem, os.path.join (OUTPUT,
                nested_filename), path, level + 1, sections)

    with open (filename, 'w') as f:
        f.write (out)

def parse_sgml_parts (parent, new_parent, path, sections):
    out = ""
    for part in parent.findall ("part"):
        title = part.find("title").text
        filename = '_'.join(title.split()) + ".markdown"
        out += "### [%s](%s)\n\n" % (title, filename)

        parse_sgml_chapters (part, os.path.join (OUTPUT,
            filename), path, 2, sections)

    with open (os.path.join (OUTPUT, "index.markdown"), 'w') as f:
        f.write (out)

def parse_sgml_book_chapters (parent, new_parent, path, sections):
    out = ""
    for part in parent.findall ("chapter"):
        title = part.find("title").text
        filename = '_'.join(title.split()) + ".markdown"
        out += "### [%s](%s)\n\n" % (title, filename)

        parse_sgml_chapters (part, os.path.join (OUTPUT,
            filename), path, 2, sections)

    with open (os.path.join (OUTPUT, "index.markdown"), 'w') as f:
        f.write (out)

if __name__=="__main__":
    prefix_map = {'xi': 'http://www.w3.org/2003/XInclude'}
    new_root = ET.Element('SECTIONS')
    new_tree = ET.ElementTree(new_root)
    parser = ET.XMLParser(load_dtd=True, resolve_entities=False)

    root = ET.parse (sys.argv[1], parser=parser).getroot()

    path = os.path.dirname (os.path.abspath(sys.argv[1]))
    sections_root = ET.parse (sys.argv[2]).getroot()
    sections = {}
    for section in sections_root.findall ('.//SECTION'):
        sections[section.find('FILE').text] = section
    if root.findall("part"):
        parse_sgml_parts (root, new_root, path, sections)
    else:
        parse_sgml_book_chapters (root, new_root, path, sections)
