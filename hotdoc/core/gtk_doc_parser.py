# -*- coding: utf-8 -*-
#!/usr/bin/env python

import CommonMark
import sys
import re
from xml.sax.saxutils import unescape

# Lifted from g-ir-doc-tool, muahaha
class DocScanner(object):
    def __init__(self):
        specs = [
            ('!alpha', r'[a-zA-Z0-9_]+'),
            ('!alpha_dash', r'[a-zA-Z0-9_-]+'),
            ('!anything', r'.*'),
            ('note', r'\n+>\s*<<note_contents:anything>>\s*\n'),
            ('new_paragraph', r'\n\n'),
            ('new_line', r'\n'),
            ('code_start_with_language',
                r'\|\[\<!\-\-\s*language\s*\=\s*\"<<language_name:alpha>>\"\s*\-\-\>'),
            ('code_start', r'\|\['),
            ('code_end', r'\]\|'),
            ('property', r'#<<type_name:alpha>>:(<<property_name:alpha_dash>>)'),
            ('signal', r'#<<type_name:alpha>>::(<<signal_name:alpha_dash>>)'),
            ('type_name', r'#(<<type_name:alpha>>)'),
            ('enum_value', r'%(<<member_name:alpha>>)'),
            ('parameter', r'@<<param_name:alpha>>'),
            ('function_call', r'<<symbol_name:alpha>>\s*\(\)'),
            ('include', r'{{\s*<<include_name:anything>>\s*}}'),
        ]
        self.specs = self.unmangle_specs(specs)
        self.regex = self.make_regex(self.specs)

    def unmangle_specs(self, specs):
        mangled = re.compile('<<([a-zA-Z_:]+)>>')
        specdict = dict((name.lstrip('!'), spec) for name, spec in specs)

        def unmangle(spec, name=None):
            def replace_func(match):
                child_spec_name = match.group(1)

                if ':' in child_spec_name:
                    pattern_name, child_spec_name = child_spec_name.split(':', 1)
                else:
                    pattern_name = None

                child_spec = specdict[child_spec_name]
                # Force all child specs of this one to be unnamed
                unmangled = unmangle(child_spec, None)
                if pattern_name and name:
                    return '(?P<%s_%s>%s)' % (name, pattern_name, unmangled)
                else:
                    return unmangled

            return mangled.sub(replace_func, spec)

        return [(name, unmangle(spec, name)) for name, spec in specs]

    def make_regex(self, specs):
        regex = '|'.join('(?P<%s>%s)' % (name, spec) for name, spec in specs
                         if not name.startswith('!'))
        return re.compile(regex)

    def get_properties(self, name, match):
        groupdict = match.groupdict()
        properties = {name: groupdict.pop(name)}
        name = name + "_"
        for group, value in groupdict.iteritems():
            if group.startswith(name):
                key = group[len(name):]
                properties[key] = value
        return properties

    def scan(self, text):
        pos = 0
        while True:
            match = self.regex.search(text, pos)
            if match is None:
                break

            start = match.start()
            if start > pos:
                yield ('other', text[pos:start], None)

            pos = match.end()
            name = match.lastgroup
            yield (name, match.group(0), self.get_properties(name, match))

        if pos < len(text):
            yield ('other', text[pos:], None)


class GtkDocParser (object):
    def __init__(self, doc_tool=None):
        self.funcs = {
            'other': self.format_other,
            'new_line': self.format_other,
            'new_paragraph': self.format_other,
            'note': self.format_other,
            'include': self.format_other,
            'property': self.format_property,
            'signal': self.format_signal,
            'type_name': self.format_type_name,
            'enum_value': self.format_enum_value,
            'parameter': self.format_parameter,
            'function_call': self.format_function_call,
            'code_start': self.format_code_start,
            'code_start_with_language': self.format_code_start_with_language,
            'code_end': self.format_code_end,
        }

        self.doc_tool = doc_tool

        self.__md_parser = CommonMark.DocParser()
        self.__md_renderer = CommonMark.HTMLRenderer()

    def format_other(self, match, props):
        return match

    def format_property (self, match, props):
        type_name = props['type_name']
        property_name = props['property_name']

        if self.doc_tool is None:
            return u'[](%s:%s)' % (type_name, prop_name)

        linkname = "%s:%s" % (type_name, property_name)
        link = self.doc_tool.link_resolver.get_named_link (linkname)

        if link:
            return u"[“%s”](%s)" % (link.title, link.get_link())
        else:
            return u"the %s's “%s” property" % (type_name, property_name)

    def format_signal (self, match, props):
        type_name = props['type_name']
        signal_name = props['signal_name']
        if self.doc_tool is None:
            return u'[](%s::%s)' % (type_name, signal_name)

        linkname = "%s::%s" % (type_name, signal_name)
        link = self.doc_tool.link_resolver.get_named_link (linkname)

        if link:
            return u"[“%s”](%s)" % (link.title, link.get_link())
        else:
            return u"the %s's “%s” signal" % (type_name, signal_name)

    def format_type_name (self, match, props):
        type_name = props['type_name']

        # It is assumed that when there is a name collision
        # between a struct and a class name, the link is to be made
        # to the class

        if self.doc_tool is None:
            return u'[](%s)' % (type_name)

        class_name = '%s::%s' % (type_name, type_name)
        link = self.doc_tool.link_resolver.get_named_link (class_name)

        if link is None:
            link = self.doc_tool.link_resolver.get_named_link (type_name)

        if link:
            return "[%s](%s)" % (link.title, link.get_link())
        else:
            return match

    def format_enum_value (self, match, props):
        member_name = props['member_name']

        if self.doc_tool is None:
            return '[](%s)' % member_name

        link = self.doc_tool.link_resolver.get_named_link (member_name)

        if link:
            return "[%s](%s)" % (link.title, link.get_link ())
        else:
            return match

    def format_parameter (self, match, props):
        param_name = props['param_name']
        return '_%s_' % param_name

    def format_function_call (self, match, props):
        func_name = props['symbol_name']
        if self.doc_tool is None:
            return '[](%s)' % func_name

        link = self.doc_tool.link_resolver.get_named_link (func_name)

        if link:
            return "[%s()](%s)" % (link.title, link.get_link ())
        else:
            return match

    def format_code_start (self, match, props):
        return "\n```\n"

    def format_code_start_with_language (self, match, props):
        return "\n```%s\n" % props["language_name"] 

    def format_code_end (self, match, props):
        return "\n```\n"

    def translate(self, text, format_='markdown'):
        out = u''

        if not text:
            return out

        _scanner = DocScanner ()
        tokens = _scanner.scan (text)
        in_code = False
        for tok in tokens:
            kind, match, props = tok
            formatted = self.funcs[kind](match, props)
            if kind == "code_end":
                in_code = False
            if in_code:
                out += match
            else:
                out += formatted
            if kind in ["code_start", "format_code_start_with_language"]:
                in_code = True

        if format_ == 'markdown':
            return out
        elif format_ == 'html':
            ast = self.__md_parser.parse (out.encode('utf-8'))
            rendered_text = self.__md_renderer.render(ast)
            return rendered_text

        raise Exception("Unrecognized format %s" % format_)

    def translate_comment (self, comment, format_='markdown'):
        text = unescape(comment.description)
        return self.translate (text, format_)

if __name__ == "__main__":
    gdp = GtkDocParser()
    with open (sys.argv[1], 'r') as f:
        contents = f.read ()
        out = gdp.translate (contents)
        print out

    sys.exit (0)
