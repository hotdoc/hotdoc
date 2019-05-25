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

ALLOW_NONE_HELP = \
"NULL is OK, both for passing and returning"

TRANSFER_NONE_HELP = \
"Don't free data after the code is done"

TRANSFER_FULL_HELP = \
"Free data after the code is done"

TRANSFER_FLOATING_HELP = \
"Alias for transfer none, used for objects with floating refs"

TRANSFER_CONTAINER_HELP = \
"Free data container after the code is done"

CLOSURE_HELP = \
"This parameter is a closure for callbacks, many bindings can pass NULL to %s"

CLOSURE_DATA_HELP = \
"This parameter is a closure for callbacks, many bindings can pass NULL here"

DIRECTION_OUT_HELP = \
"Parameter for returning results"

DIRECTION_INOUT_HELP = \
"Parameter for input and for returning results"

DIRECTION_IN_HELP = \
"Parameter for input. Default is transfer none"

ARRAY_HELP = \
"Parameter points to an array of items"

ELEMENT_TYPE_HELP = \
"Generic and defining element of containers and arrays"

SCOPE_ASYNC_HELP = \
"The callback is valid until first called"

SCOPE_CALL_HELP = \
"The callback is valid only during the call to the method"

SCOPE_NOTIFIED_HELP=\
"The callback is valid until the GDestroyNotify argument is called"

NULLABLE_HELP = \
"NULL may be passed to the value"

NOT_NULLABLE_HELP = \
"NULL is *not* OK, either for passing or returning"

DEFAULT_HELP = \
"Default parameter value (for in case the shadows-to function has less parameters)"

DESTROY_HELP = \
"The parameter is a 'destroy_data' for callbacks."

# VERY DIFFERENT FROM THE PREVIOUS ONE BEWARE :P
OPTIONAL_HELP = \
"NULL may be passed instead of a pointer to a location"

# WTF
TYPE_HELP = \
"Override the parsed C type with given type"

class GIAnnotation (object):
    def __init__(self, nick, help_text, value=None):
        self.nick = nick
        self.help_text = help_text
        self.value = value


class GIAnnotationParser(object):
    def __init__(self):
        self.__annotation_factories = \
                {"allow-none": self.__make_allow_none_annotation,
                 "transfer": self.__make_transfer_annotation,
                 "inout": self.__make_inout_annotation,
                 "out": self.__make_out_annotation,
                 "in": self.__make_in_annotation,
                 "array": self.__make_array_annotation,
                 "element-type": self.__make_element_type_annotation,
                 "scope": self.__make_scope_annotation,
                 "closure": self.__make_closure_annotation,
                 "nullable": self.__make_nullable_annotation,
                 "type": self.__make_type_annotation,
                 "optional": self.__make_optional_annotation,
                 "default": self.__make_default_annotation,
                 "destroy": self.__make_destroy_annotation,
                }

    def __make_type_annotation (self, annotation, value):
        if not value:
            return None

        return GIAnnotation("type", TYPE_HELP, value[0])

    def __make_nullable_annotation (self, annotation, value):
        return GIAnnotation("nullable", NULLABLE_HELP)

    def __make_optional_annotation (self, annotation, value):
        return GIAnnotation ("optional", OPTIONAL_HELP)

    def __make_allow_none_annotation(self, annotation, value):
        return GIAnnotation ("allow-none", ALLOW_NONE_HELP)

    def __make_transfer_annotation(self, annotation, value):
        if value[0] == "none":
            return GIAnnotation ("transfer: none", TRANSFER_NONE_HELP)
        elif value[0] == "full":
            return GIAnnotation ("transfer: full", TRANSFER_FULL_HELP)
        elif value[0] == "floating":
            return GIAnnotation ("transfer: floating", TRANSFER_FLOATING_HELP)
        elif value[0] == "container":
            return GIAnnotation ("transfer: container", TRANSFER_CONTAINER_HELP)
        else:
            return None

    def __make_inout_annotation (self, annotation, value):
        return GIAnnotation ("inout", DIRECTION_INOUT_HELP)

    def __make_out_annotation (self, annotation, value):
        return GIAnnotation ("out", DIRECTION_OUT_HELP)

    def __make_in_annotation (self, annotation, value):
        return GIAnnotation ("in", DIRECTION_IN_HELP)

    def __make_element_type_annotation (self, annotation, value):
        annotation_val = None
        if type(value) == list:
            annotation_val = value[0]
        return GIAnnotation ("element-type", ELEMENT_TYPE_HELP, annotation_val)

    def __make_array_annotation (self, annotation, value):
        annotation_val = None
        if type(value) == dict:
            annotation_val = ""
            for name, val in value.items():
                annotation_val += "%s=%s" % (name, val)
        return GIAnnotation ("array", ARRAY_HELP, annotation_val)

    def __make_scope_annotation (self, annotation, value):
        if type (value) != list or not value:
            return None

        if value[0] == "async":
            return GIAnnotation ("scope async", SCOPE_ASYNC_HELP)
        elif value[0] == "call":
            return GIAnnotation ("scope call", SCOPE_CALL_HELP)
        elif value[0] == 'notified':
            return GIAnnotation ("scope notified", SCOPE_NOTIFIED_HELP)
        return None

    def __make_closure_annotation (self, annotation, value):
        if type (value) != list or not value:
            return GIAnnotation ("closure", CLOSURE_DATA_HELP)

        return GIAnnotation ("closure", CLOSURE_HELP % value[0])

    def __make_default_annotation (self, annotation, value):
        return GIAnnotation ("default %s" % str (value[0]), DEFAULT_HELP)

    def __make_destroy_annotation (self, annotation, value):
        if value:
            return GIAnnotation ("destroy %s" % str (value[0]), DESTROY_HELP)
        else:
            return GIAnnotation ("destroy", DESTROY_HELP)

    def __make_not_nullable_annotation(self):
        return GIAnnotation("not nullable", NOT_NULLABLE_HELP)

    def __create_annotation (self, annotation_name, annotation_value):
        factory = self.__annotation_factories.get(annotation_name)
        if not factory:
            return None
        return factory (annotation_name, annotation_value)

    def make_annotations (self, parameter):
        if not parameter.comment:
            return []

        if not parameter.comment.annotations:
            return []

        annotations = []

        for ann, val in parameter.comment.annotations.items():
            if ann == "skip":
                continue
            annotation = self.__create_annotation (ann, val.argument)
            if not annotation:
                # Special case for silly specification
                if (ann == 'not' and len(val.argument) == 1 and
                        val.argument[0] == 'nullable'):
                    annotations.append(self.__make_not_nullable_annotation())
                else:
                    print("This parameter annotation is unknown :[" + ann + "]", val.argument)
                continue
            annotations.append (annotation)

        return annotations
