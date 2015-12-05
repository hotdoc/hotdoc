from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon import docstring
from docutils.core import publish_doctree
from docutils import nodes
from docutils.parsers.rst import roles
from hotdoc.core.comment_block import Comment

class NativeCommentTranslator(nodes.NodeVisitor):
    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)
        self.current_reference = ''
        self.parent_comments = []

    def visit_document(self, node):
        self.comment = Comment()
        self.comment.description = ''

    def depart_document(self, node):
        pass

    def visit_paragraph(self, node):
        return

    def depart_paragraph (self, node):
        self.comment.description += '\n\n'

    def visit_Text (self, node):
        text = node.astext()
        self.comment.description += text

    def depart_Text(self, node):
        pass

    def visit_literal(self, node):
        text = node.astext()
        self.comment.description += '`'

    def depart_literal(self, node):
        self.comment.description += '`'

    def visit_literal_block(self, node):
        text = node.astext()
        self.comment.description += '\n```\n'

    def depart_literal_block(self, node):
        self.comment.description += '\n```\n'

    def visit_doctest_block(self, node):
        return self.visit_literal_block(node)

    def depart_doctest_block(self, node):
        return self.depart_literal_block(node)

    def visit_note(self, node):
        self.comment.description += '\n> '

    def depart_note(self, node):
        self.comment.description += '\n'

    def visit_reference(self, node):
        self.current_reference = node['refuri']
        self.comment.description += '['

    def depart_reference(self, node):
        self.comment.description += '](%s)' % self.current_reference

    def visit_list_item(self, node):
        self.comment.description += '\n* '

    def depart_list_item(self, node):
        pass

    def visit_problematic(self, node):
        raise nodes.SkipNode

    def visit_system_message(self, node):
        raise nodes.SkipNode

    def visit_title_reference(self, node):
        self.comment.description += '*'

    def depart_title_reference(self, node):
        self.comment.description += '*'

    def visit_emphasis(self, node):
        self.comment.description += '*'

    def depart_emphasis(self, node):
        self.comment.description += '*'

    def visit_bullet_list(self, node):
        pass

    def depart_bullet_list(self, node):
        pass

    def visit_field_body(self, node):
        pass

    def depart_field_body(self, node):
        pass

    def visit_field_name(self, node):
        text = node.astext()
        if text.startswith ('param '):
            param_name = text.split()[1]
            self.comment = Comment(name=param_name,
                    description='')
            parent_comment = self.parent_comments[-1]
            parent_comment.params[param_name] = self.comment
            raise nodes.SkipNode
        elif text.startswith ('type '):
            param_name = text.split()[1]
            parent_comment = self.parent_comments[-1]
            param_comment = parent_comment.params.get(param_name)
            if param_comment:
                self.comment = Comment()
                param_comment.type_comment = self.comment
        elif text == 'returns':
            self.comment = Comment()
            parent_comment = self.parent_comments[-1]
            parent_comment.set_return_block (self.comment)
        elif text == 'rtype':
            parent_comment = self.parent_comments[-1]
            return_comment = parent_comment.tags.get('returns')
            self.comment = Comment()
            return_comment.type_comment = self.comment

    def depart_field_name(self, node):
        pass

    def visit_field(self, node):
        self.parent_comments.append(self.comment)

    def depart_field(self, node):
        self.comment = self.parent_comments.pop()

    def visit_field_list(self, node):
        pass

    def depart_field_list(self, node):
        pass

    def visit_rubric(self, node):
        pass

    def depart_rubric(self, node):
        pass

    def visit_target(self, node):
        raise nodes.SkipNode

def exception_role (name, rawtext, text, lineno, inliner,
        options={}, content=[]):
    return ([nodes.Text(text)], [])

roles.register_local_role ('exc', exception_role)
config = Config(napoleon_use_param=True, napoleon_use_rtype=True)

def google_doc_to_native(doc): 
    rest = docstring.GoogleDocstring(doc, config).__unicode__()
    doctree = publish_doctree(rest)
    #print doctree.asdom().toprettyxml()
    visitor = NativeCommentTranslator (doctree)
    doctree.walkabout (visitor)
    return visitor.comment
