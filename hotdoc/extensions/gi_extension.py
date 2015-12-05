import os
import re
import subprocess

from lxml import etree

from hotdoc.core.symbols import *
from hotdoc.core.comment_block import Comment, comment_from_tag
from hotdoc.core.base_extension import BaseExtension
from hotdoc.extensions.gi_html_formatter import GIHtmlFormatter
from hotdoc.core.links import Link
from hotdoc.core.doc_tree import Page
from hotdoc.core.wizard import Skip
from hotdoc.transition_scripts.sgml_to_sections import parse_sections, convert_to_markdown
from hotdoc.transition_scripts.patcher import Patcher
from hotdoc.extensions.gtk_doc_parser import GtkDocParser
from hotdoc.core.doc_tool import HotdocWizard
from hotdoc.extensions.c_extension import validate_c_extension

# FIXME: might conflict with comment_block.Annotation
class Annotation (object):
    def __init__(self, nick, help_text, value=None):
        self.nick = nick
        self.help_text = help_text
        self.value = value

class Flag (object):
    def __init__ (self, nick, link):
        self.nick = nick
        self.link = link

# FIXME: is that subclassing really helpful ?
class RunLastFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run Last",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-LAST:CAPS")


class RunFirstFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run First",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-FIRST:CAPS")


class RunCleanupFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run Cleanup",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-CLEANUP:CAPS")


class NoHooksFlag (Flag):
    def __init__(self):
        Flag.__init__(self, "No Hooks",
"https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-NO-HOOKS:CAPS")


class WritableFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Write", None)


class ReadableFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Read", None)


class ConstructFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Construct", None)


class ConstructOnlyFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Construct Only", None)

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

DEFAULT_HELP = \
"Default parameter value (for in case the shadows-to function has less parameters)"

# VERY DIFFERENT FROM THE PREVIOUS ONE BEWARE :P
OPTIONAL_HELP = \
"NULL may be passed instead of a pointer to a location"

# WTF
TYPE_HELP = \
"Override the parsed C type with given type"

class GIInfo(object):
    def __init__(self, node, parent_name):
        self.node = node
        self.parent_name = re.sub('\.', '', parent_name)

class GIClassInfo(GIInfo):
    def __init__(self, node, parent_name, class_struct_name, is_interface):
        GIInfo.__init__(self, node, parent_name)
        self.class_struct_name = class_struct_name
        self.vmethods = {}
        self.signals = {}
        self.properties = {}
        self.is_interface = is_interface

# FIXME: this code is quite a mess
class GIRParser(object):
    def __init__(self, doc_tool, gir_file):
        self.namespace = None
        self.gir_class_infos = {}
        self.gir_callable_infos = {}
        self.python_names = {}
        self.c_names = {}
        self.javascript_names = {}
        self.unintrospectable_symbols = {}
        self.gir_children_map = {}
        self.gir_hierarchies = {}
        self.gir_types = {}
        self.global_hierarchy = None
        self.doc_tool = doc_tool

        self.parsed_files = []

        self.callable_nodes = {}

        self.gir_class_map = {}

        self.__parse_gir_file (gir_file)
        self.__create_hierarchies()

    def __create_hierarchies(self):
        for gi_name, klass in self.gir_types.iteritems():
            hierarchy = self.__create_hierarchy (klass)
            self.gir_hierarchies[gi_name] = hierarchy

        hierarchy = []
        for c_name, klass in self.gir_class_infos.iteritems():
            if klass.parent_name != self.namespace:
                continue
            if not klass.node.tag.endswith (('class', 'interface')):
                continue

            gi_name = '%s.%s' % (klass.parent_name, klass.node.attrib['name'])
            klass_name = self.__get_klass_name (klass.node)
            link = Link(None, klass_name, klass_name)
            symbol = QualifiedSymbol(type_tokens=[link])
            parents = reversed(self.gir_hierarchies[gi_name])
            for parent in parents:
                hierarchy.append ((parent, symbol))
                symbol = parent

        self.global_hierarchy = hierarchy

    def __get_klass_name(self, klass):
        klass_name = klass.attrib.get('{%s}type' % self.nsmap['c'])
        if not klass_name:
            klass_name = klass.attrib.get('{%s}type-name' % self.nsmap['glib'])
        return klass_name

    def __create_hierarchy (self, klass):
        klaass = klass
        hierarchy = []
        while (True):
            parent_name = klass.attrib.get('parent')
            if not parent_name:
                break

            if not '.' in parent_name:
                namespace = klass.getparent().attrib['name']
                parent_name = '%s.%s' % (namespace, parent_name)
            parent_class = self.gir_types[parent_name]
            children = self.gir_children_map.get(parent_name)
            klass_name = self.__get_klass_name (klass)

            if not klass_name in children:
                link = Link(None, klass_name, klass_name)
                sym = QualifiedSymbol(type_tokens=[link])
                children[klass_name] = sym

            klass_name = self.__get_klass_name(parent_class)
            link = Link(None, klass_name, klass_name)
            sym = QualifiedSymbol(type_tokens=[link])
            hierarchy.append (sym)

            klass = parent_class

        hierarchy.reverse()
        return hierarchy

    def __parse_gir_file (self, gir_file):
        if gir_file in self.parsed_files:
            return

        self.parsed_files.append (gir_file)

        tree = etree.parse (gir_file)
        root = tree.getroot()

        if self.namespace is None:
            ns = root.find("{http://www.gtk.org/introspection/core/1.0}namespace")
            self.namespace = ns.attrib['name']

        nsmap = {k:v for k,v in root.nsmap.iteritems() if k}
        self.nsmap = nsmap
        for child in root:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}namespace":
                self.__parse_namespace(nsmap, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}include":
                inc_name = child.attrib["name"]
                inc_version = child.attrib["version"]
                gir_file = os.path.join (self.doc_tool.datadir, 'gir-1.0', '%s-%s.gir' % (inc_name,
                    inc_version))
                self.__parse_gir_file (gir_file)

    def __parse_namespace (self, nsmap, ns):
        ns_name = ns.attrib["name"]

        for child in ns:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}class":
                self.__parse_gir_record(nsmap, ns_name, child, is_class=True)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}interface":
                self.__parse_gir_record(nsmap, ns_name, child, is_interface=True)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}record":
                self.__parse_gir_record(nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}callback":
                self.__parse_gir_callback (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}enumeration":
                self.__parse_gir_enum (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}bitfield":
                self.__parse_gir_enum (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}constant":
                self.__parse_gir_constant (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}function":
                self.__parse_gir_function (nsmap, ns_name, child)

    def __parse_gir_record (self, nsmap, ns_name, klass, is_interface=False,
            is_class=False):
        name = '%s.%s' % (ns_name, klass.attrib["name"])
        self.gir_types[name] = klass
        self.gir_children_map[name] = {}
        c_name = klass.attrib.get('{%s}type' % nsmap['c'])
        if not c_name:
            return

        class_struct_name = klass.attrib.get('{http://www.gtk.org/introspection/glib/1.0}type-struct') 

        gi_class_info = GIClassInfo (klass, ns_name, '%s%s' % (ns_name,
            class_struct_name), is_interface)

        if class_struct_name:
            self.gir_class_map['%s%s' % (ns_name, class_struct_name)] = gi_class_info

        if is_class or is_interface:
            self.gir_class_infos[c_name] = gi_class_info
            class_name = '%s::%s' % (c_name, c_name)

            self.c_names[class_name] = c_name
            self.python_names[class_name] = name
            self.javascript_names[class_name] = name

        self.c_names[c_name] = c_name
        self.python_names[c_name] = name
        self.javascript_names[c_name] = name


        for child in klass:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}method":
                child_cname = self.__parse_gir_function (nsmap, name, child,
                        is_method=True)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}function":
                child_cname = self.__parse_gir_function (nsmap, name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}constructor":
                child_cname = self.__parse_gir_function (nsmap, name, child,
                        is_constructor=True)
            elif child.tag == "{http://www.gtk.org/introspection/glib/1.0}signal":
                child_cname = self.__parse_gir_signal (nsmap, c_name, child)
                gi_class_info.signals[child_cname] = child
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}property":
                self.__parse_gir_property (nsmap, c_name, child)
                gi_class_info.properties[child.attrib['name']] = child
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}virtual-method":
                child_cname = self.__parse_gir_vmethod (nsmap, c_name, child)
                gi_class_info.vmethods[child_cname] = child

    def __parse_gir_callable_common (self, callable_, c_id, c_name, python_name,
            js_name, class_name, is_method=False, is_constructor=False):
        introspectable = callable_.attrib.get('introspectable')

        if introspectable == '0':
            self.unintrospectable_symbols[c_id] = True

        self.c_names[c_id] = c_name
        self.python_names[c_id] = python_name
        self.javascript_names[c_id] = js_name

        info = GIInfo (callable_, class_name)
        self.gir_callable_infos[c_id] = info

    def __parse_gir_vmethod (self, nsmap, class_name, vmethod):
        name = vmethod.attrib['name']
        c_id = "%s:::%s---%s" % (class_name, name, 'vfunc')
        self.__parse_gir_callable_common (vmethod, c_id, name, name, name,
                class_name)
        return name

    def __parse_gir_signal (self, nsmap, class_name, signal):
        name = signal.attrib["name"]
        c_id = "%s:::%s---%s" % (class_name, name, 'signal')
        self.__parse_gir_callable_common (signal, c_id, name, name, name, class_name)
        return name

    def __parse_gir_property (self, nsmap, class_name, prop):
        name = prop.attrib["name"]
        c_name = "%s:::%s---%s" % (class_name, name, 'property')

    def __parse_gir_function (self, nsmap, class_name, function,
            is_method=False, is_constructor=False):
        python_name = '%s.%s' % (class_name, function.attrib['name'])
        js_name = '%s.prototype.%s' % (class_name, function.attrib['name'])
        c_name = function.attrib['{%s}identifier' % nsmap['c']]
        self.__parse_gir_callable_common (function, c_name, c_name, python_name,
                js_name, class_name, is_method=is_method,
                is_constructor=is_constructor)
        return c_name

    def __parse_gir_callback (self, nsmap, class_name, function):
        name = '%s.%s' % (class_name, function.attrib['name'])
        c_name = function.attrib['{%s}type' % nsmap['c']]
        self.gir_types[name] = function
        self.__parse_gir_callable_common (function, c_name, c_name, name, name,
                class_name)
        return c_name

    def __parse_gir_constant (self, nsmap, class_name, constant):
        name = '%s.%s' % (class_name, constant.attrib['name'])
        c_name = constant.attrib['{%s}type' % nsmap['c']]
        self.c_names[c_name] = c_name
        self.python_names[c_name] = name
        self.javascript_names[c_name] = name

    def __parse_gir_enum (self, nsmap, class_name, enum):
        name = '%s.%s' % (class_name, enum.attrib['name'])
        self.gir_types[name] = enum
        c_name = enum.attrib['{%s}type' % nsmap['c']]
        self.c_names[c_name] = c_name
        self.python_names[c_name] = name
        self.javascript_names[c_name] = name
        for c in enum:
            if c.tag == "{http://www.gtk.org/introspection/core/1.0}member":
                m_name = '%s.%s' % (name, c.attrib["name"].upper())
                c_name = c.attrib['{%s}identifier' % nsmap['c']]
                self.c_names[c_name] = c_name
                self.python_names[c_name] = m_name
                self.javascript_names[c_name] = m_name

    def __get_gir_type (self, name):
        namespaced = '%s.%s' % (self.namespace, name)
        klass = self.gir_types.get (namespaced)
        if klass is not None:
            return klass
        return self.gir_types.get (name)

    def type_tokens_from_gitype (self, ptype_name):
        qs = None

        if ptype_name == 'none':
            return None

        gitype = self.__get_gir_type (ptype_name)
        if gitype is not None:
            c_type = gitype.attrib['{http://www.gtk.org/introspection/c/1.0}type']
            ptype_name = c_type

        type_link = Link (None, ptype_name, ptype_name)

        tokens = [type_link]
        tokens += '*'

        return tokens

DESCRIPTION=\
"""
Parse a gir file and add signals, properties, classes
and virtual methods.

Can output documentation for various
languages.

Must be used in combination with the C extension.
"""

PROMPT_GTK_PORT_MAIN=\
"""
Porting from gtk-doc is a bit involved, and you will
want to manually go over generated markdown files to
improve pandoc's conversion (or contribute patches
to pandoc's docbook reader if you know haskell. I don't).

You'll want to make sure you have built the documentation
with gtk-doc first, it should be easy as checking that
there is an xml directory in the old documentation folder.

If not, you'll want to verify you have run make,
and possibly run ./configure --enable-gtk-doc in the
root directory beforehand.

Press Enter once you made sure you're all set. """

PROMPT_SECTIONS_FILE=\
"""
Good.

The first thing this conversion tool will need is the
path to the "sections" file. It usually is located in
the project's documentation folder, with a name such as
'$(project_name)-sections.txt'.

Path to the sections file ? """

PROMPT_SECTIONS_CONVERSION=\
"""
Thanks, I don't know what I would do without you.

Probably just sit there idling.

Anyway, the next step is to go over certain comments
in the source code and either rename them or place
them in the markdown files.

These comments are the "SECTION" comments, which
either document classes and should stay in the source
code, or were generic comments that have nothing to do
in the source code and belong in the standalone markdown
pages.

FYI, I have found %d section comments and %d class comments.

Don't worry, I can do that for you, I'll just need
your permission to slightly modify the source files.

Permission granted [y,n]? """

PROMPT_COMMIT=\
"""
Sweet.

Should I commit the files I modified [y,n]? """

PROMPT_DESTINATION=\
"""
Nice.

We can now finalize the port, by generating the standalone
markdown pages that will form the skeleton of your documentation.

I'll need you to provide me with a directory in which
to output these files (markdown_files seems like a pretty sane
choice but feel free to go wild).

If the directory does not exist it will be created.

Where should I write the markdown pages ? """

PROMPT_SGML_FILE=\
"""
I'll also need the path to the sgml file, it should look
something like $(project_name)-docs.sgml

Path to the SGML file ? """

def get_section_comments(wizard):
    sections = parse_sections('hotdoc-tmp-sections.txt')
    translator = GtkDocParser()

    section_comments = {}
    class_comments = []

    for comment in wizard.comments.values():
        if not comment.name.startswith('SECTION:'):
            continue
        structure_name = comment.name.split('SECTION:')[1]
        section = sections.get(structure_name)
        if section is None:
            print "That's weird"
            continue

        section_title = section.find('TITLE')
        if section_title is not None:
            section_title = section_title.text
            if wizard.symbols.get(section_title):
                new_name = ('%s::%s' % (section_title,
                    section_title))
                class_comments.append(comment)
                comment.raw_comment = comment.raw_comment.replace(comment.name,
                        new_name)
                continue

        comment.raw_comment = ''
        comment.description = translator.translate(comment.description)
        if comment.short_description:
            comment.short_description = \
            translator.translate(comment.short_description)
        section_comments[structure_name] = comment

    return section_comments, class_comments

def patch_comments(wizard, patcher, comments):
    if not comments:
        return

    for comment in comments:
        patcher.patch(comment.filename, comment.lineno - 1,
                comment.endlineno, comment.raw_comment)

    if wizard.git_interface.repo_path is not None:
        wizard.before_prompt()
        if wizard.ask_confirmation(PROMPT_COMMIT):

            for comment in comments:
                wizard.git_interface.add(comment.filename)

            commit_message = "Port to hotdoc: convert class comments"
            wizard.git_interface.commit('hotdoc', 'hotdoc@hotdoc.net', commit_message)

def translate_section_file(sections_path):
    module_path = os.path.dirname(__file__)
    trans_shscript_path = os.path.join(module_path, '..', 'transition_scripts',
            'translate_sections.sh')
    cmd = [trans_shscript_path, sections_path, 'hotdoc-tmp-sections.txt']
    subprocess.check_call(cmd)

def port_from_gtk_doc(wizard):
    validate_c_extension(wizard)
    patcher = Patcher()

    wizard.wait_for_continue(PROMPT_GTK_PORT_MAIN)
    wizard.prompt_executable('pandoc')
    sections_path = wizard.prompt_key('sections_file',
            prompt=PROMPT_SECTIONS_FILE, store=False,
            validate_function=wizard.check_path_is_file)
    translate_section_file(sections_path)

    section_comments, class_comments = get_section_comments(wizard)

    wizard.before_prompt()

    if not wizard.ask_confirmation(PROMPT_SECTIONS_CONVERSION %
            (len(section_comments), len(class_comments))):
        raise Skip

    patch_comments(wizard, patcher, class_comments +
            section_comments.values())
    sgml_path = wizard.prompt_key('sgml_path',
            prompt=PROMPT_SGML_FILE, store=False,
            validate_function=wizard.check_path_is_file)
    folder = wizard.prompt_key('markdown_folder',
            prompt=PROMPT_DESTINATION, store=False,
            validate_function=wizard.validate_folder)

    convert_to_markdown(sgml_path, 'hotdoc-tmp-sections.txt', folder,
            section_comments, 'gobject-api.markdown')

    os.unlink('hotdoc-tmp-sections.txt')

    return 'gobject-api.markdown'

PROMPT_GI_INDEX=\
"""
You will now need to provide a markdown index for introspected
symbols.

You can learn more about standalone markdown files at [FIXME],
for now suffice to say that these files provide the basic skeleton
for the output documentation, and list which symbols should be
documented in which page.

The index is the root, it will usually link to various subpages.

There are three ways to provide this index:

- Converting existing gtk-doc files.
- Generating one

You can of course skip this phase for now, and come back to it later.

"""

class GIWizard(HotdocWizard):
    def do_quick_start(self):
        if not HotdocWizard.group_prompt(self):
            return False

        self.before_prompt()
        try:
            choice = self.propose_choice(
                    ["Create index from a gtk-doc project",
                    ],
                    extra_prompt=PROMPT_GI_INDEX
                    )

            if choice == 0:
                self.config['gi_index'] = port_from_gtk_doc(self)
        except Skip:
            pass

        return HotdocWizard.do_quick_start(self)

    def get_index_path(self):
        return 'gobject-api'

    def get_index_name(self):
        return 'GObject API'

    def group_prompt(self):
        return True

class GIExtension(BaseExtension):
    EXTENSION_NAME = "gi-extension"

    def __init__(self, doc_tool, config):
        BaseExtension.__init__(self, doc_tool, config)
        self.gir_file = doc_tool.resolve_config_path(config.get('gir_file'))
        self.gi_index = config.get('gi_index')
        self.languages = [l.lower() for l in config.get('languages', [])]
        self.language = 'c'
        self.major_version = config.get('major_version')
        self.gir_parser = None

        doc_tool.doc_tree.page_parser.register_well_known_name ('gobject-api',
                self.gi_index_handler)

        # Make sure C always gets formatted first
        if 'c' in self.languages:
            self.languages.remove ('c')
            self.languages.insert (0, 'c')

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
                }

        self._formatters["html"] = GIHtmlFormatter(self.doc_tool, self)

        self.__translated_names = {}

    @staticmethod
    def add_arguments (parser):
        group = parser.add_argument_group('GObject-introspection extension',
                DESCRIPTION, wizard_class=GIWizard)
        group.add_argument ("--gir-file", action="store",
                dest="gir_file",
                help="Path to the gir file of the documented library",
                finalize_function=HotdocWizard.finalize_path)
        group.add_argument ("--languages", action="store",
                nargs='*',
                help="Languages to translate documentation in")
        group.add_argument ("--major-version", action="store",
                dest="major_version",
                help="Major version of the library")
        group.add_argument ("--gi-index", action="store",
                dest="gi_index",
                help="Path to the GI root markdown file",
                finalize_function=HotdocWizard.finalize_path)

    def __gather_gtk_doc_links (self):
        sgml_dir = os.path.join(self.doc_tool.datadir, "gtk-doc", "html")
        if not os.path.exists(sgml_dir):
            self.warning("no gtk doc to gather links from in %s" % sgml_dir)
            return

        for node in os.listdir(sgml_dir):
            dir_ = os.path.join(sgml_dir, node)
            if os.path.isdir(dir_):
                try:
                    self.__parse_sgml_index(dir_)
                except IOError:
                    pass

    def __parse_sgml_index(self, dir_):
        symbol_map = dict({})
        remote_prefix = ""
        with open(os.path.join(dir_, "index.sgml"), 'r') as f:
            for l in f:
                if l.startswith("<ONLINE"):
                    remote_prefix = l.split('"')[1]
                elif not remote_prefix:
                    break
                elif l.startswith("<ANCHOR"):
                    split_line = l.split('"')
                    filename = split_line[3].split('/', 1)[-1]
                    title = split_line[1].replace('-', '_')

                    if title.endswith (":CAPS"):
                        title = title [:-5]
                    if remote_prefix:
                        href = '%s/%s' % (remote_prefix, filename)
                    else:
                        href = filename

                    link = Link (href, title, title)
                    self.doc_tool.link_resolver.upsert_link (link, external=True)

    def __make_type_annotation (self, annotation, value):
        if not value:
            return None

        return Annotation("type", TYPE_HELP, value[0])

    def __make_nullable_annotation (self, annotation, value):
        return Annotation("nullable", NULLABLE_HELP)

    def __make_optional_annotation (self, annotation, value):
        return Annotation ("optional", OPTIONAL_HELP)

    def __make_allow_none_annotation(self, annotation, value):
        return Annotation ("allow-none", ALLOW_NONE_HELP)

    def __make_transfer_annotation(self, annotation, value):
        if value[0] == "none":
            return Annotation ("transfer: none", TRANSFER_NONE_HELP)
        elif value[0] == "full":
            return Annotation ("transfer: full", TRANSFER_FULL_HELP)
        elif value[0] == "floating":
            return Annotation ("transfer: floating", TRANSFER_FLOATING_HELP)
        elif value[0] == "container":
            return Annotation ("transfer: container", TRANSFER_CONTAINER_HELP)
        else:
            return None

    def __make_inout_annotation (self, annotation, value):
        return Annotation ("inout", DIRECTION_INOUT_HELP)

    def __make_out_annotation (self, annotation, value):
        return Annotation ("out", DIRECTION_OUT_HELP)

    def __make_in_annotation (self, annotation, value):
        return Annotation ("in", DIRECTION_IN_HELP)

    def __make_element_type_annotation (self, annotation, value):
        annotation_val = None
        if type(value) == list:
            annotation_val = value[0]
        return Annotation ("element-type", ELEMENT_TYPE_HELP, annotation_val)

    def __make_array_annotation (self, annotation, value):
        annotation_val = None
        if type(value) == dict:
            annotation_val = ""
            for name, val in value.iteritems():
                annotation_val += "%s=%s" % (name, val)
        return Annotation ("array", ARRAY_HELP, annotation_val)

    def __make_scope_annotation (self, annotation, value):
        if type (value) != list or not value:
            return None

        if value[0] == "async":
            return Annotation ("scope async", SCOPE_ASYNC_HELP)
        elif value[0] == "call":
            return Annotation ("scope call", SCOPE_CALL_HELP)
        elif value[0] == 'notified':
            return Annotation ("scope notified", SCOPE_NOTIFIED_HELP)
        return None

    def __make_closure_annotation (self, annotation, value):
        if type (value) != list or not value:
            return Annotation ("closure", CLOSURE_DATA_HELP)

        return Annotation ("closure", CLOSURE_HELP % value[0])

    def __make_default_annotation (self, annotation, value):
        return Annotation ("default %s" % str (value[0]), DEFAULT_HELP)

    def __create_annotation (self, annotation_name, annotation_value):
        factory = self.__annotation_factories.get(annotation_name)
        if not factory:
            return None
        return factory (annotation_name, annotation_value)

    def __make_annotations (self, parameter):
        if not parameter.comment:
            return []

        if not parameter.comment.annotations:
            return []

        annotations = []

        for ann, val in parameter.comment.annotations.iteritems():
            if ann == "skip":
                continue
            annotation = self.__create_annotation (ann, val.argument)
            if not annotation:
                print "This parameter annotation is unknown :[" + ann + "]", val.argument
                continue
            annotations.append (annotation)

        return annotations

    def __remove_vmethods (self, symbol):
        gir_class_info = self.gir_parser.gir_class_map.get(symbol._make_name())
        if not gir_class_info:
            return

        members = []
        for m in symbol.members:
            if not m.member_name in gir_class_info.vmethods:
                members.append(m)
        symbol.members = members

    def __add_annotations (self, symbol):
        if self.language == 'c':
            annotations = self.__make_annotations (symbol)

            # FIXME: OK this is format time but still seems strange
            extra_content = self.doc_tool.formatter._format_annotations (annotations)
        else:
            extra_content = ''
        symbol.extension_contents['Annotations'] = extra_content

    def __formatting_symbol(self, symbol):
        if type(symbol) in [ReturnValueSymbol, ParameterSymbol]:
            self.__add_annotations (symbol)

        if isinstance (symbol, QualifiedSymbol):
            return

        # FIXME : this is not correct
        c_name = symbol._make_name ()

        if type (symbol) == StructSymbol:
            self.__remove_vmethods(symbol)

        # We discard symbols at formatting time because they might be exposed
        # in other languages
        if self.language != 'c':
            # FIXME: maybe skip symbols that are not in the gir at all.
            if c_name in self.gir_parser.unintrospectable_symbols:
                return False
            if type (symbol) in [FunctionMacroSymbol, ExportedVariableSymbol]:
                return False

        return True

    def update_links(self, symbol):
        if not symbol:
            return

        if isinstance(symbol, QualifiedSymbol):
            link = symbol.type_link
        else:
            link = symbol.link

        if link:
            translated_name = self.__translated_names.get(link.id_)
            if translated_name is not None:
                link.title = translated_name

    def setup_language (self, language):
        self.language = language

        if language == 'c':
            self.__translated_names = self.gir_parser.c_names
        elif language == 'python':
            self.__translated_names = self.gir_parser.python_names
        elif language == 'javascript':
            self.__translated_names = self.gir_parser.javascript_names
        else:
            self.__translated_names = {}

        self.doc_tool.link_resolver.set_translated_names(self.__translated_names)

    def __unnest_type (self, parameter):
        array_nesting = 0
        array = parameter.find('{http://www.gtk.org/introspection/core/1.0}array')
        while array is not None:
            array_nesting += 1
            parameter = array
            array = parameter.find('{http://www.gtk.org/introspection/core/1.0}array')

        return parameter, array_nesting

    def __type_tokens_from_cdecl (self, cdecl):
        indirection = cdecl.count ('*')
        qualified_type = cdecl.strip ('*')
        tokens = []
        for token in qualified_type.split ():
            if token in ["const", "restrict", "volatile"]:
                tokens.append(token)
            else:
                link = Link(None, token, token)
                tokens.append (link)

        for i in range(indirection):
            tokens.append ('*')

        return tokens

    def __type_tokens_and_gi_name_from_gi_node (self, gi_node):
        type_, array_nesting = self.__unnest_type (gi_node)

        varargs = type_.find('{http://www.gtk.org/introspection/core/1.0}varargs')
        if varargs is not None:
            ctype_name = '...'
            ptype_name = 'valist'
        else:
            ptype_ = type_.find('{http://www.gtk.org/introspection/core/1.0}type')
            ctype_name = ptype_.attrib.get('{http://www.gtk.org/introspection/c/1.0}type')
            ptype_name = ptype_.attrib.get('name')

        if ctype_name is not None:
            type_tokens = self.__type_tokens_from_cdecl (ctype_name)
        elif ptype_name is not None:
            type_tokens = self.gir_parser.type_tokens_from_gitype (ptype_name)
        else:
            type_tokens = []

        namespaced = '%s.%s' % (self.gir_parser.namespace, ptype_name)
        if namespaced in self.gir_parser.gir_types:
            ptype_name = namespaced
        return type_tokens, ptype_name

    def __create_parameter_symbol (self, gi_parameter, comment):
        param_name = gi_parameter.attrib['name']
        if comment:
            param_comment = comment.params.get (param_name)
        else:
            param_comment = None

        type_tokens, gi_name = self.__type_tokens_and_gi_name_from_gi_node (gi_parameter)

        res = ParameterSymbol (argname=param_name, type_tokens=type_tokens,
                comment=param_comment)
        res.add_extension_attribute ('gi-extension', 'gi_name', gi_name)

        direction = gi_parameter.attrib.get('direction')
        if direction is None:
            direction = 'in'
        res.add_extension_attribute ('gi-extension', 'direction', direction)

        return res, direction

    def __create_return_value_symbol (self, gi_retval, comment):
        if comment:
            return_tag = comment.tags.get ('returns', None)
            return_comment = comment_from_tag (return_tag)
        else:
            return_comment = None

        type_tokens, gi_name = self.__type_tokens_and_gi_name_from_gi_node(gi_retval)

        res = ReturnValueSymbol (type_tokens=type_tokens, comment=return_comment)
        res.add_extension_attribute ('gi-extension', 'gi_name', gi_name)

        return res

    def __create_parameters_and_retval (self, node, comment):
        gi_parameters = node.find('{http://www.gtk.org/introspection/core/1.0}parameters')

        if gi_parameters is None:
            instance_param = None
            gi_parameters = []
        else:
            instance_param = \
            gi_parameters.find('{http://www.gtk.org/introspection/core/1.0}instance-parameter')
            gi_parameters = gi_parameters.findall('{http://www.gtk.org/introspection/core/1.0}parameter')

        parameters = []

        if instance_param is not None:
            param, direction = self.__create_parameter_symbol (instance_param,
                    comment)
            parameters.append (param)

        out_parameters = []
        for gi_parameter in gi_parameters:
            param, direction = self.__create_parameter_symbol (gi_parameter,
                    comment)
            parameters.append (param)
            if direction != 'in':
                out_parameters.append (param)

        retval = node.find('{http://www.gtk.org/introspection/core/1.0}return-value')
        retval = self.__create_return_value_symbol (retval, comment)
        retval.add_extension_attribute ('gi-extension', 'out_parameters',
                out_parameters)

        return (parameters, retval)

    def __sort_parameters (self, symbol, retval, parameters):
        in_parameters = []
        out_parameters = []

        for i, param in enumerate (parameters):
            if symbol.is_method and i == 0:
                continue

            direction = param.get_extension_attribute ('gi-extension', 'direction')

            if direction == 'in' or direction == 'inout':
                in_parameters.append (param)
            if direction == 'out' or direction == 'inout':
                out_parameters.append (param)

        symbol.add_extension_attribute ('gi-extension',
                'parameters', in_parameters)

        retval.add_extension_attribute('gi-extension', 'out_parameters',
                out_parameters)

    def __create_signal_symbol (self, node, object_name, name):
        unique_name = '%s::%s' % (object_name, name)
        comment = self.doc_tool.get_comment(unique_name)

        parameters, retval = self.__create_parameters_and_retval (node, comment)
        res = self.doc_tool.get_or_create_symbol(SignalSymbol,
                parameters=parameters, return_value=retval,
                comment=comment, display_name=name, unique_name=unique_name)

        flags = []

        when = node.attrib.get('when')
        if when == "first":
            flags.append (RunFirstFlag())
        elif when == "last":
            flags.append (RunLastFlag())
        elif when == "cleanup":
            flags.append (RunCleanupFlag())

        no_hooks = node.attrib.get('no-hooks')
        if no_hooks == '1':
            flags.append (NoHooksFlag())

        # This is incorrect, it's not yet format time
        extra_content = self.get_formatter(self.doc_tool.output_format)._format_flags (flags)
        res.extension_contents['Flags'] = extra_content

        self.__sort_parameters (res, retval, parameters)

        return res

    def __create_property_symbol (self, node, object_name, name):
        unique_name = '%s:%s' % (object_name, name)
        comment = self.doc_tool.get_comment(unique_name)

        type_tokens, gi_name = self.__type_tokens_and_gi_name_from_gi_node(node)
        type_ = QualifiedSymbol (type_tokens=type_tokens)
        type_.add_extension_attribute ('gi-extension', 'gi_name', gi_name)

        flags = []
        writable = node.attrib.get('writable')
        construct = node.attrib.get('construct')
        construct_only = node.attrib.get('construct-only')

        flags.append (ReadableFlag())
        if writable == '1':
            flags.append (WritableFlag())
        if construct_only == '1':
            flags.append (ConstructOnlyFlag())
        elif construct == '1':
            flags.append (ConstructFlag())

        res = self.doc_tool.get_or_create_symbol(PropertySymbol,
                prop_type=type_, comment=comment,
                display_name=name, unique_name=unique_name)

        extra_content = self.get_formatter(self.doc_tool.output_format)._format_flags (flags)
        res.extension_contents['Flags'] = extra_content

        return res

    def __create_vfunc_symbol (self, node, comment, object_name, name):
        unique_name = '%s:::%s' % (object_name, name)

        parameters, retval = self.__create_parameters_and_retval (node, comment)
        symbol = self.doc_tool.get_or_create_symbol(VFunctionSymbol,
                parameters=parameters, 
                return_value=retval, comment=comment, display_name=name,
                unique_name=unique_name)

        self.__sort_parameters (symbol, retval, parameters)

        return symbol

    def __create_class_symbol (self, symbol, gi_name):
        comment_name = '%s::%s' % (symbol.unique_name, symbol.unique_name)
        class_comment = self.doc_tool.get_comment(comment_name)
        hierarchy = self.gir_parser.gir_hierarchies.get (gi_name)
        children = self.gir_parser.gir_children_map.get (gi_name)

        if class_comment:
            class_symbol = self.doc_tool.get_or_create_symbol(ClassSymbol,
                    hierarchy=hierarchy,
                    children=children,
                    comment=class_comment,
                    display_name=symbol.display_name,
                    unique_name=comment_name)
        else:
            class_symbol = self.doc_tool.get_or_create_symbol(ClassSymbol,
                    hierarchy=hierarchy, children=children,
                    display_name=symbol.display_name,
                    unique_name=comment_name)

        return class_symbol

    def __update_function (self, func):
        gi_info = self.gir_parser.gir_callable_infos.get(func.link.id_)

        if not gi_info:
            return

        func.is_method = gi_info.node.tag.endswith ('method')

        gi_params, retval = self.__create_parameters_and_retval (gi_info.node,
                func.comment)

        func_parameters = func.parameters

        if 'throws' in gi_info.node.attrib:
            func_parameters = func_parameters[:-1]
            func.throws = True

        for i, param in enumerate (func_parameters):
            gi_param = gi_params[i]
            gi_name = gi_param.get_extension_attribute ('gi-extension',
                    'gi_name')
            param.add_extension_attribute ('gi-extension', 'gi_name', gi_name)
            direction = gi_param.get_extension_attribute ('gi-extension',
                    'direction')
            param.add_extension_attribute('gi-extension', 'direction',
                    direction)

        gi_name = retval.get_extension_attribute ('gi-extension',
                'gi_name')

        func.return_value.add_extension_attribute ('gi-extension', 'gi_name',
                gi_name)

        self.__sort_parameters (func, func.return_value, func_parameters)

    def __update_struct (self, symbol):
        split = symbol.display_name.split(self.gir_parser.namespace)
        if len (split) < 2:
            return []

        gi_name = '%s.%s' % (self.gir_parser.namespace, split[1])
        if not symbol.display_name in self.gir_parser.gir_class_infos:
            return []

        gi_class_info = self.gir_parser.gir_class_infos[symbol.display_name]

        symbols = []
        gir_node = gi_class_info.node

        class_symbol = self.__create_class_symbol (symbol, gi_name)

        symbols.append (class_symbol)

        klass_name = gir_node.attrib.get('{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0')

        if klass_name:
            for signal_name, signal_node in gi_class_info.signals.iteritems():
                sym = self.__create_signal_symbol (signal_node, klass_name, signal_name)
                symbols.append (sym)

            for prop_name, prop_node in gi_class_info.properties.iteritems():
                sym = self.__create_property_symbol (prop_node, klass_name, prop_name)
                symbols.append (sym)

        class_struct_name = gi_class_info.class_struct_name
        if class_struct_name:
            for vfunc_name, vfunc_node in gi_class_info.vmethods.iteritems():
                parent_comment = self.doc_tool.get_comment(class_struct_name)
                comment = None
                if parent_comment:
                    comment = parent_comment.params.get (vfunc_node.attrib['name'])
                if not comment:
                    continue

                block = Comment (name=vfunc_node.attrib['name'],
                        description=comment.description,
                        filename=parent_comment.filename)
                sym = self.__create_vfunc_symbol (vfunc_node, block,
                        klass_name, vfunc_name)
                symbols.append (sym)

        return symbols

    def __adding_symbol (self, page, symbol):
        res = []

        if isinstance (symbol, FunctionSymbol):
            self.__update_function (symbol)

        elif type (symbol) == StructSymbol:
            res = self.__update_struct (symbol)

        return res

    def gi_index_handler (self, doc_tree):
        gen_contents = ''
        gen_index_page = Page('gen-index')

        for language in self.languages:
            dest = os.path.basename(self.gi_index)
            dest = '%s/%s.html' % (language, os.path.splitext(dest)[0])
            gen_contents += '### [%s API](%s)\n' % \
                    (language.capitalize (), dest)

        doc_tree.page_parser.parse_contents(gen_index_page, gen_contents)

        doc_tree.pages['gen-index'] = gen_index_page
        index_path = os.path.join(doc_tree.prefix, self.gi_index)
        index_path = self.doc_tool.resolve_config_path(index_path)
        gen_index_page.subpages.add(index_path)
        new_page = doc_tree.build_tree(index_path, 'gi-extension')
        return "gen-index"

    def setup (self):
        if not self.gir_file:
            return

        self.__gather_gtk_doc_links()
        self.gir_parser = GIRParser (self.doc_tool, self.gir_file)
        formatter = self.get_formatter(self.doc_tool.output_format)
        self.doc_tool.doc_tree.symbol_added_signal.connect (self.__adding_symbol)
        formatter.formatting_symbol_signals[Symbol].connect(self.__formatting_symbol)
