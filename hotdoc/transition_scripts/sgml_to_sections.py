#!/usr/bin/env python
# -*- coding: utf-8 -*-

# FIXME: this is horrible code. horrible.
# Ideally we would want pandoc to rescue us ..

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
    with open (os.path.join (output, new_name + ".markdown"), 'w') as f:
        f.write (converted)
    return os.path.join (output, new_name + ".markdown")

def create_symbol_file (section_node, name, output, ported_comment=None):
    name = '_'.join(name.split())
    child = section_node.getchildren()[-1]
    symbols = child.tail.split("\n")
    with open (os.path.join (output, name + ".markdown"), 'w') as f:
        f.write ("### %s\n\n" % name)

        if ported_comment:
            if ported_comment.short_description:
                f.write('%s\n' % ported_comment.short_description)

            f.write('\n%s\n\n' % ported_comment.description)

        for symbol in symbols:
            if symbol:
                f.write ("* [%s]()\n" % symbol)
    return os.path.join (output, name + ".markdown")

def parse_sgml_chapters (part, filename, path, level, sections, output,
        section_comments):
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
                file_node = section_node.find('FILE')
                if file_node is not None:
                    ported_comment = section_comments.get(file_node.text)
                else:
                    ported_comment = None
                if title_node is not None:
                    new_filename = create_symbol_file (sections[title],
                            title_node.text, output, ported_comment=ported_comment)
                    title = title_node.text
                else:
                    new_filename = create_symbol_file (sections[title], title,
                            output, ported_comment=ported_comment)
            out += "#### [%s](%s)\n\n" % (title, os.path.basename(new_filename))
        else:
            title = elem.find("title").text
            nested_filename = '_'.join(title.split()) + ".markdown"
            out += "### [%s](%s)\n" % (title, nested_filename)
            parse_sgml_chapters (elem, os.path.join (output,
                nested_filename), path, level + 1, sections, output,
                section_comments)

    with open (filename, 'w') as f:
        f.write (out)

def parse_sgml_parts (parent, path, sections, output, section_comments,
        index_name):
    out = ""
    for part in parent.findall ("part"):
        title = part.find("title").text
        filename = '_'.join(title.split()) + ".markdown"
        out += "### [%s](%s)\n\n" % (title, filename)

        parse_sgml_chapters (part, os.path.join (output,
            filename), path, 2, sections, output, section_comments)

    with open (os.path.join (output, index_name), 'w') as f:
        f.write (out)

def parse_sgml_book_chapters (parent, path, sections, output, section_comments,
        index_name):
    out = ""
    for part in parent.findall (".//chapter"):
        title = part.find("title").text
        filename = '_'.join(title.split()) + ".markdown"
        out += "### [%s](%s)\n\n" % (title, filename)

        parse_sgml_chapters (part, os.path.join (output,
            filename), path, 2, sections, output, section_comments)

    with open (os.path.join (output, index_name), 'w') as f:
        f.write (out)

def parse_sections(sections_file):
    sections_root = ET.parse (sections_file).getroot()
    sections = {}
    for section in sections_root.findall ('.//SECTION'):
        sections[section.find('FILE').text] = section

    return sections

def convert_to_markdown(sgml_path, sections_path, output, section_comments,
        index_name):
    prefix_map = {'xi': 'http://www.w3.org/2003/XInclude'}
    parser = ET.XMLParser(load_dtd=True, resolve_entities=False)

    root = ET.parse (sgml_path, parser=parser).getroot()

    sections = parse_sections(sections_path)
    path = os.path.dirname (os.path.abspath(sgml_path))
    if root.findall("part"):
        parse_sgml_parts (root, path, sections, output, section_comments,
                index_name)
    else:
        parse_sgml_book_chapters (root, path, sections, output,
                section_comments, index_name)
