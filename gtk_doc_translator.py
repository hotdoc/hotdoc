#!/usr/bin/env python

from subprocess import PIPE, Popen
import sys
import re

from datetime import datetime

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
            ('heading', r'#+\s+<<heading:anything>>'),
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

def format_other(match, props):
    return match

def format_property (match, props):
    type_name = props['type_name']
    property_name = props['property_name']
    return "[%s:%s](property)" % (type_name, property_name)

def format_signal (match, props):
    type_name = props['type_name']
    signal_name = props['signal_name']
    return "[%s:%s](signal)" % (type_name, signal_name)

def format_type_name (match, props):
    type_name = props['type_name']
    return "[%s]()" % type_name

def format_enum_value (match, props):
    member_name = props['member_name']
    return "[%s]()" % member_name

def format_parameter (match, props):
    param_name = props['param_name']
    return '_%s_' % param_name

def format_function_call (match, props):
    func_name = props['symbol_name']
    return "[%s]()" % func_name

def format_code_start (match, props):
    return "```"

def format_code_start_with_language (match, props):
    return "```%s" % props["language_name"] 

def format_code_end (match, props):
    return "```"

def format_heading (match, props):
    heading_level = 0
    while match[heading_level] == '#':
        heading_level += 1
    return "%s%s" % ('#' * heading_level, props["heading"])

class LegacyTranslator (object):
    def __init__(self):
        self.funcs = {
            'other': format_other,
            'new_line': format_other,
            'new_paragraph': format_other,
            'note': format_other,
            'include': format_other,
            'property': format_property,
            'signal': format_signal,
            'type_name': format_type_name,
            'enum_value': format_enum_value,
            'parameter': format_parameter,
            'function_call': format_function_call,
            'code_start': format_code_start,
            'code_start_with_language': format_code_start_with_language,
            'code_end': format_code_end,
            'heading': format_heading
        }


    def translate (self, text):
        if not text:
            return ""
        out = ""
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
        return out


if __name__ == "__main__":
    lt = LegacyTranslator()
    with open (sys.argv[1], 'r') as f:
        contents = f.read ()
        out = lt.translate (contents)

    sys.exit (0)
