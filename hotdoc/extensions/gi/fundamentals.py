# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
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

from hotdoc.core.links import Link


def _create_javascript_fundamentals():
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

    fundamentals = {
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
    return fundamentals


def _create_python_fundamentals():
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

    fundamentals = {
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

    return fundamentals

FUNDAMENTALS = {'javascript': _create_javascript_fundamentals(),
        'python': _create_python_fundamentals(),
        'c': {}}
