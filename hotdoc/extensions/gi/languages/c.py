# -*- coding: utf-8 -*-
#
# Copyright 2019 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""C language support for Hotdoc

This extension provides support for providing documentation in C
"""

from hotdoc.extensions.gi.language import *
from hotdoc.extensions.gi.utils import *

# FIXME: Avoid the use of a global dictionary
TRANSLATED = {}


class CLanguage(Language):
    language_name = 'c'

    def __init__(self):
        Language.__init__(self)

    def make_translations(self, unique_name, node):
        if node.tag == core_ns('member'):
            TRANSLATED[unique_name] = unique_name
        elif c_ns('identifier') in node.attrib:
            TRANSLATED[unique_name] = unique_name
        elif c_ns('type') in node.attrib:
            TRANSLATED[unique_name] = unique_name
        elif node.tag == core_ns('field'):
            components = []
            get_field_c_name_components(node, components)
            display_name = '.'.join(components[1:])
            TRANSLATED[unique_name] = display_name
        elif node.tag == core_ns('virtual-method'):
            display_name = node.attrib['name']
            TRANSLATED[unique_name] = display_name
        elif node.tag == core_ns('property'):
            display_name = node.attrib['name']
            TRANSLATED[unique_name] = display_name
        elif node.attrib.get(glib_ns('fundamental')) == '1':
            TRANSLATED[unique_name] = node.attrib[glib_ns('type-name')]
        else:
            TRANSLATED[unique_name] = node.attrib.get('name')

    def get_translation(self, unique_name):
        return TRANSLATED.get (unique_name)


FUNDAMENTALS[CLanguage.language_name] = {
        "GParam": Link("https://developer.gnome.org/gobject/stable/gobject-GParamSpec.html#GParamSpec",
            'GParamSpec', 'GParamSpec'),
        "GInterface": Link("https://developer.gnome.org/gobject/stable/gobject-Type-Information.html#GInterfaceInfo",
            'GInterface', 'GInterface')
}


def get_language_classes():
    """Nothing important, really"""
    return [CLanguage]
