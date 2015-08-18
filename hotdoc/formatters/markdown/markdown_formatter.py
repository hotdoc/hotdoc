from base_formatter import Formatter

class MarkdownFormatter (Formatter):
    def __format_local_link (self, name):
        return "#%s" % name

    def __format_title (self, title, level=1):
        return "%s%s%s" % ("#" * level, title, self._format_new_paragraph ())

    def _format_line (self, line):
        return "%s%s" % (line, self._format_new_line ())

    def _format_paragraph (self, paragraph):
        return "%s%s" % (paragraph, self._format_new_paragraph ())

    def _get_extension (self):
        return "md"

    def _start_parameter (self, param_name):
        return "+ %s: " % param_name

    def _end_parameter (self):
        return self._format_new_line ()

    def _end_parameters (self):
        return self._format_new_line ()

    def _start_function (self, function_name, param_names):
        prototype = "%s (" % function_name
        for i, param_name in enumerate (param_names):
            if (i != 0):
                prototype += ", "
            prototype += param_name
        prototype += ")"
        return self.__format_title (prototype, level=3)

    def _format_section (self, section_name):
        return self.__format_title ("%s:" % section_name, level=2)

    def _end_function (self):
        return self._format_new_paragraph ()

    def _start_virtual_function (self, function_name):
        return self.__format_title (function_name, level=3)

    def _end_virtual_function (self):
        return self._format_new_paragraph ()

    def _start_signal (self, signal_name):
        return self.__format_title (signal_name, level=3)

    def _end_signal (self):
        return self._format_new_paragraph ()

    def _start_class (self, class_name):
        return self.__format_title (class_name, level=2)

    def _end_class (self):
        return self._format_new_paragraph ()

    def _start_doc_section (self, doc_section_name):
        return self.__format_title (doc_section_name, level=1)

    def _end_doc_section (self):
        return self._format_new_paragraph ()

    def _format_other (self, other):
        return other

    def _format_property (self, node, prop):
        print "formating property"

    def _format_signal (self, node, signal):
        print "formating signal"

    def _format_type_name (self, type_name):
        return "[%s](%s)" % (type_name, self.__format_local_link (type_name))

    def _format_enum_value (self, node, enum):
        print "formating enum value"

    def _format_parameter (self, param_name):
        return '*%s*' % param_name

    def _format_function_call (self, function_name):
        return "[%s](%s)" % (function_name, self.__format_local_link (function_name))

    def _format_code_start (self):
        return "```%s" % self._format_new_line ()

    def _format_code_start_with_language (self, language):
        return "```%s%s" % (language, self._format_new_line ())

    def _format_code_end (self):
        return "```%s" % self._format_new_line ()

    def _format_new_line (self):
        return "\n"

    def _format_new_paragraph (self):
        return "\n\n"

    def _format_note (self, note):
        return "> %s%s" % (note, self._format_new_paragraph ())

    def _format_heading (self, node, title, level):
        print "formating heading"
