import argparse, os

from giscanner.sourcescanner import SourceScanner
from giscanner.annotationparser import GtkDocCommentBlockParser
import sys
import shlex
import subprocess 
from gtk_doc_translator import LegacyTranslator
from giscanner.message import MessageLogger

def create_source_scanner(args, filenames, cflags):
    ss = SourceScanner()
    ss.set_cpp_options (args.cpp_includes,
                        args.cpp_defines,
                        args.cpp_undefines,
                        cflags=cflags)
    ss.parse_files(filenames)

    return ss

# This function makes it easy to pull in additional flags from pkg-config
def PkgConfig(args):
    cmd = ['pkg-config'] + shlex.split(args)
    out = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout
    line = out.readline()[:-1].split(" ")
    return filter(lambda a: a != ' ', line)


class PatchedDoc (object):
    def __init__(self, block, name, translator):
        self.block = block
        self.translator = translator
        self.line = block.position.line
        self.endline = block.position.endline

        annotations = self.build_annotations (block)

        if "SECTION" in name:
            self.new_doc = "%s\n" % name
        else:
            self.new_doc = "%s:%s\n" % (name, annotations)

        if block.short_description:
            self.new_doc += "@short_description: %s\n" % block.short_description
        self.new_doc += self.patch_params ()
        self.new_doc += "\n"
        self.new_doc += translator.translate (block.description)
        self.new_doc += "\n\n"
        self.new_doc += self.patch_tags ()
        self.indent()

    def indent (self):
        indentation = self.block.indentation[0]
        new_doc = "%s/**\n" % indentation [:-1]
        for line in self.new_doc.strip('\n').split('\n'):
            if line:
                new_doc += "%s* %s\n" % (indentation, line)
            else:
                new_doc += "%s*\n" % indentation
        new_doc += "%s*/\n" % indentation
        self.new_doc = new_doc

    def build_annotations (self, annotatable):
        annotations = ""

        for name, ann in annotatable.annotations.iteritems():
            values = ""
            if type (ann) == list:
                for val in ann:
                    values += " %s" % val
            elif hasattr (ann, 'iteritems'):
                for key, val in ann.iteritems():
                    values += " %s=%s" % (key, val)
            new_annotation = " (%s%s)" % (name, values)
            annotations += (new_annotation)

        if annotations:
            annotations += ":"
        return annotations

    def patch_tags (self):
        out = ""
        for tagname, tag in self.block.tags.iteritems():
            annotations = self.build_annotations (tag)
            tag_value = tag.value
            if tag_value is None:
                tag_value = ""
            new_tag = "%s:%s %s%s\n" % (tagname.capitalize (), annotations,
                    tag_value, self.translator.translate (tag.description))
            out += new_tag
        return out

    def patch_params (self):
        new_doc = ""
        for param, param_block in self.block.params.iteritems():
            annotations = self.build_annotations (param_block)
            annotated = "@%s:%s" % (param, annotations)
            new_doc += "%s %s\n" % (annotated, self.translator.translate
                    (param_block.description))
        return new_doc

def translate_one (filename, translator, blocks):
    with open (filename, 'r') as f:
        lines = f.readlines()

    patched_doc = []
    for name, block in blocks:
        patched_doc.append (PatchedDoc (block, name, translator))

    patched_doc.sort(key=lambda x: x.line, reverse=True)
    if patched_doc:
        current_patched_doc = patched_doc.pop()
    else:
        current_patched_doc = None
    out = ""

    for i, line in enumerate (lines):
        lineno = i + 1
        if current_patched_doc:
            if lineno < current_patched_doc.line:
                out += line
            elif lineno == current_patched_doc.line:
                out += current_patched_doc.new_doc
            if lineno == current_patched_doc.endline:
                if patched_doc:
                    current_patched_doc = patched_doc.pop ()
                else:
                    current_patched_doc = None
        else:
            out += line

    return out

def doc_translate (args):
    parser = argparse.ArgumentParser()

    parser.add_argument("--packages", nargs="+",
                      action="store", dest="packages",
                      help="CFlags for source scanning")
    parser.add_argument("-I", nargs="+",
                      action="store", dest="cpp_includes", default=[],
                      help="Pre processor include files")
    parser.add_argument("-D", nargs="+",
                      action="store", dest="cpp_defines",
                      help="Pre processor defines")
    parser.add_argument("-U", nargs="+",
                      action="store", dest="cpp_undefines",
                      help="Pre processor undefines")
    parser.add_argument ("-f", "--filenames", action="store", nargs="+",
            dest="filenames")
    parser.add_argument ("-i", "--inplace", action="store_true",
            dest="inplace")

    logger = MessageLogger.get(namespace=None)

    args = parser.parse_args(args[1:])

    filename_block_map = {}

    translator = LegacyTranslator ()

    cflags = []
    if args.packages:
        for p in args.packages:
            includes = PkgConfig ("--cflags %s" % p)
            for include in includes:
                if include:
                    cflags.append (include)

    cpp_includes = []
    for i in args.cpp_includes:
        cpp_includes.append (os.path.realpath (i))
    args.cpp_includes = cpp_includes

    ss = create_source_scanner (args, args.filenames, cflags)
    print "sources scanned"
    cbp = GtkDocCommentBlockParser()
    blocks = cbp.parse_comment_blocks(ss.get_comments())
    for name, block in blocks.iteritems():
        try:
            blocklist = filename_block_map[block.position.filename]
        except:
            blocklist = []
            filename_block_map[block.position.filename] = blocklist
        blocklist.append ((name, block))

    for filename, blocks in filename_block_map.iteritems():
        if args.inplace:
            print "Translating %s" % filename
        res = translate_one (filename, translator, blocks)
        if args.inplace:
            with open (filename, 'w') as f:
                f.write (res)
        else:
            print res
            pass
