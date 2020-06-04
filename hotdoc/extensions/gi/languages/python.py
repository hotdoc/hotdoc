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

"""Python language support for Hotdoc

This extension provides support for providing documentation in Python
"""

from hotdoc.extensions.gi.language import *
from hotdoc.extensions.gi.utils import *
from hotdoc.core.links import Link

# FIXME: Avoid the use of a global dictionary
TRANSLATED = {}

class PythonLanguage(Language):
    language_name = 'python'

    def __init__(self):
        Language.__init__(self)

    @classmethod
    def _create_fundamentals(cls):
        string_link = \
                Link('https://docs.python.org/3/library/functions.html#func-str',
                    'str', None)
        boolean_link = \
                Link('https://docs.python.org/3/library/functions.html#bool',
                        'bool', None)
        true_link = \
                Link('https://docs.python.org/3/library/constants.html#True',
                    'True', None)
        false_link = \
               Link('https://docs.python.org/3/library/constants.html#False',
                    'False', None)
        pointer_link = \
                Link('https://docs.python.org/3/library/functions.html#object',
                    'object', None)
        integer_link = \
                Link('https://docs.python.org/3/library/functions.html#int',
                        'int', None)
        float_link = \
                Link('https://docs.python.org/3/library/functions.html#float',
                        'float', None)
        none_link = \
                Link('https://docs.python.org/3/library/constants.html#None',
                        'None', None)
        list_link = \
                Link('https://docs.python.org/3/library/functions.html#func-list',
                     'list', None)
        gtype_link = \
                Link('https://developer.gnome.org/gobject/stable/'
                        'gobject-Type-Information.html#GType',
                        'GObject.Type', None)

        gvariant_link = \
                Link('https://developer.gnome.org/glib/stable/glib-GVariant.html',
                        'GLib.Variant', None)

        FUNDAMENTALS[cls.language_name] = {
                "none": none_link,
                "gpointer": pointer_link,
                "gconstpointer": pointer_link,
                "gboolean": boolean_link,
                "gint8": integer_link,
                "guint8": integer_link,
                "gint16": integer_link,
                "guint16": integer_link,
                "gint32": integer_link,
                "guint32": integer_link,
                "gchar": integer_link,
                "guchar": integer_link,
                "gshort": integer_link,
                "gushort": integer_link,
                "gint": integer_link,
                "guint": integer_link,
                "gfloat": float_link,
                "gdouble": float_link,
                "GLib.List": list_link,
                "utf8": string_link,
                "gunichar": string_link,
                "filename": string_link,
                "gchararray": string_link,
                "GType": gtype_link,
                "GVariant": gvariant_link,
                "gsize": integer_link,
                "gssize": integer_link,
                "goffset": integer_link,
                "gintptr": integer_link,
                "guintptr": integer_link,
                "glong": integer_link,
                "gulong": integer_link,
                "gint64": integer_link,
                "guint64": integer_link,
                "long double": float_link,
                "long long": integer_link,
                "unsigned long long": integer_link,
                "TRUE": true_link,
                "FALSE": false_link,
                "NULL": none_link,
        }

    def make_translations(self, unique_name, node):
        if node.attrib.get('introspectable') == '0':
            return

        if node.tag == core_ns('member'):
            components = get_gi_name_components(node)
            components[-1] = components[-1].upper()
            gi_name = '.'.join(components)
            TRANSLATED[unique_name] = gi_name
        elif c_ns('identifier') in node.attrib:
            components = get_gi_name_components(node)
            gi_name = '.'.join(components)
            TRANSLATED[unique_name] = gi_name
        elif c_ns('type') in node.attrib:
            components = get_gi_name_components(node)
            gi_name = '.'.join(components)
            TRANSLATED[unique_name] = gi_name
        elif node.tag == core_ns('field'):
            components = []
            get_field_c_name_components(node, components)
            display_name = '.'.join(components[1:])
            TRANSLATED[unique_name] = display_name
        elif node.tag == core_ns('virtual-method'):
            display_name = node.attrib['name']
            TRANSLATED[unique_name] = 'do_%s' % display_name
        elif node.tag == core_ns('property'):
            display_name = node.attrib['name']
            TRANSLATED[unique_name] = display_name.replace('-', '_')
        elif node.attrib.get(glib_ns('fundamental')) == '1':
            components = get_gi_name_components(node)
            gi_name = '.'.join(components)
            TRANSLATED[unique_name] = gi_name
        else:
            TRANSLATED[unique_name] = node.attrib.get('name')

    def get_translation(self, unique_name):
        return TRANSLATED.get (unique_name)


PythonLanguage._create_fundamentals()
def get_language_classes():
    """Nothing important, really"""
    return [PythonLanguage]
