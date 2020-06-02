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

"""JavaScript language support for Hotdoc

This extension provides support for providing documentation in JavaScript
"""

from hotdoc.extensions.gi.language import *
from hotdoc.extensions.gi.utils import *
from hotdoc.core.links import Link

# FIXME: Avoid the use of a global dictionary
TRANSLATED = {}

class JavascriptLanguage(Language):
    language_name = 'javascript'

    def __init__(self):
        Language.__init__(self)

    @classmethod
    def _create_fundamentals(cls):
        string_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/String',
                        'String', None)
        boolean_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'Boolean', None)
        pointer_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Object', 'Object',
                        None)
        true_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'true', None)
        false_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'false', None)
        number_link = \
                Link('https://developer.mozilla.org/en-US/docs/Glossary/Number',
                        'Number', None)
        null_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/null',
                        'null', None)
        gtype_link = \
                Link('https://developer.gnome.org/gobject/stable/'
                        'gobject-Type-Information.html#GType',
                        'GObject.Type', None)

        FUNDAMENTALS[cls.language_name] = {
                'gchararray': string_link,
                'gunichar': string_link,
                'utf8': string_link,
                'gchar': string_link,
                'guchar': number_link,
                'gint8': number_link,
                'guint8': number_link,
                'gint16': number_link,
                'guint16': number_link,
                'gint32': number_link,
                'guint32': number_link,
                'gint64': number_link,
                'guint64': number_link,
                'gshort': number_link,
                'gint': number_link,
                'guint': number_link,
                'glong': number_link,
                'gulong': number_link,
                'gsize': number_link,
                'gssize': number_link,
                'gintptr': number_link,
                'guintptr': number_link,
                'gfloat': number_link,
                'gdouble': number_link,
                'gboolean': number_link,
                'TRUE': true_link,
                'FALSE': false_link,
                'gpointer': pointer_link,
                'GType': gtype_link,
                'NULL': null_link,
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
            components[-1] = 'prototype.%s' % components[-1]
            TRANSLATED[unique_name] = '.'.join(components)
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
            TRANSLATED[unique_name] = 'vfunc_%s' % display_name
        elif node.tag == core_ns('property'):
            display_name = node.attrib['name']
            TRANSLATED[unique_name] = display_name
        elif node.attrib.get(glib_ns('fundamental')) == '1':
            components = get_gi_name_components(node)
            gi_name = '.'.join(components)
            TRANSLATED[unique_name] = gi_name
        else:
            TRANSLATED[unique_name] = node.attrib.get('name')

    def get_translation(self, unique_name):
        return TRANSLATED.get (unique_name)

JavascriptLanguage._create_fundamentals()
def get_language_classes():
    """Nothing important, really"""
    return [JavascriptLanguage]
