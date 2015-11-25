#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

dir_ = os.path.dirname(os.path.abspath(__file__))
sys.path.append (os.path.abspath(os.path.join(dir_, os.pardir, "src")))

import StringIO
from lxml import etree as ET
import subprocess

def db_to_md (content):
    with open ("tmpfile", 'w') as f:
        f.write (content)
    cmd = ['pandoc', '-s', '-f', 'docbook', '-t', 'markdown']
    cmd.append ("tmpfile")
    converted = subprocess.check_output (cmd)
    os.unlink ('tmpfile')
    return converted

def convert_file (filename, new_name, output):
    with open(os.devnull, 'w') as f:
        xincluded = subprocess.check_output (["xmllint", "--xinclude",
            filename], stderr=f)

    converted = db_to_md (xincluded)
    print "writing conversion to", new_name
    with open (os.path.join (output, new_name + ".markdown"), 'w') as f:
        f.write (converted)
    return os.path.join (output, new_name + ".markdown")

def create_symbol_file (section_node, name, output):
    name = '_'.join(name.split())
    child = section_node.getchildren()[-1]
    symbols = child.tail.split("\n")
    print "writing symbols to", name
    with open (os.path.join (output, name + ".markdown"), 'w') as f:
        f.write ("### %s\n\n" % name)
        for symbol in symbols:
            if symbol:
                f.write ("* [%s]()\n" % symbol)
    return os.path.join (output, name + ".markdown")

def parse_sgml_chapters (part, filename, path, level, sections, output):
    out = ""
    out += "# %s\n\n" % part.find("title").text
    for elem in part.iterchildren ("{http://www.w3.org/2003/XInclude}include", "chapter"):
        if elem.tag == "{http://www.w3.org/2003/XInclude}include":
            nested_filename = elem.attrib["href"]
            title = os.path.basename (nested_filename)
            title = os.path.splitext (title)[0]
            if not title in sections:
                new_filename = convert_file (os.path.join (path,
                    nested_filename), title, output)
            else:
                section_node = sections[title]
                title_node = section_node.find("TITLE")
                if title_node is not None:
                    new_filename = create_symbol_file (sections[title],
                            title_node.text, output)
                else:
                    new_filename = create_symbol_file (sections[title], title,
                            output)
            out += "#### [%s](%s)\n\n" % (title, os.path.basename(new_filename))
        else:
            title = elem.find("title").text
            nested_filename = '_'.join(title.split()) + ".markdown"
            out += "### [%s](%s)\n" % (title, nested_filename)
            parse_sgml_chapters (elem, os.path.join (output,
                nested_filename), path, level + 1, sections, output)

    with open (filename, 'w') as f:
        f.write (out)

def parse_sgml_parts (parent, path, sections, output):
    out = ""
    for part in parent.findall ("part"):
        title = part.find("title").text
        filename = '_'.join(title.split()) + ".markdown"
        out += "### [%s](%s)\n\n" % (title, filename)

        parse_sgml_chapters (part, os.path.join (output,
            filename), path, 2, sections, output)

    with open (os.path.join (output, "index.markdown"), 'w') as f:
        f.write (out)

def parse_sgml_book_chapters (parent, path, sections, output):
    out = ""
    for part in parent.findall (".//chapter"):
        title = part.find("title").text
        print title
        filename = '_'.join(title.split()) + ".markdown"
        out += "### [%s](%s)\n\n" % (title, filename)

        parse_sgml_chapters (part, os.path.join (output,
            filename), path, 2, sections, output)

    with open (os.path.join (output, "index.markdown"), 'w') as f:
        f.write (out)

def parse_sections(sections_file):
    sections_root = ET.parse (sections_file).getroot()
    sections = {}
    for section in sections_root.findall ('.//SECTION'):
        sections[section.find('FILE').text] = section

    return sections

def convert_to_markdown(sgml_path, sections_path, output):
    prefix_map = {'xi': 'http://www.w3.org/2003/XInclude'}
    parser = ET.XMLParser(load_dtd=True, resolve_entities=False)

    root = ET.parse (sgml_path, parser=parser).getroot()

    sections = parse_sections(sections_path)
    path = os.path.dirname (os.path.abspath(sgml_path))
    if root.findall("part"):
        parse_sgml_parts (root, path, sections, output)
    else:
        parse_sgml_book_chapters (root, path, sections, output)
