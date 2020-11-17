import os

from hotdoc.core.extension import Extension
from hotdoc.core.tree import Page
from hotdoc.core.formatter import Formatter
from schema import Schema, SchemaError, And, Use, Optional

PNAME = 'comment-on-github'
HERE = os.path.abspath(os.path.dirname(__file__))

Page.meta_schema[Optional('github-issue-id')] = And(int)

class CommentOnGithubExtension(Extension):
    extension_name = PNAME
    argument_prefix = PNAME

    def __init__(self, app, project):
        self.__repo = None
        Extension.__init__(self, app, project)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group(
            'Comment on github',
            'Allow commenting on the page on github')

        group.add_argument(
            '--comment-on-github-repository',
            help="Github repository to comment on",
            default=None)

    def parse_config(self, config):
        super(CommentOnGithubExtension, self).parse_config(config)
        self.__repo = config.get('comment-on-github-repository')

    def parse_toplevel_config(self, config):
        super().parse_toplevel_config(config)
        template_path = os.path.join(HERE, 'templates')
        Formatter.engine.loader.searchpath.append(template_path)

    def __formatting_page_cb(self, formatter, page):
        if self.__repo is None:
            return

        issue_id = page.meta.get('github-issue-id')

        if issue_id is None:
            return

        template = Formatter.engine.get_template('github_comments.html')

        formatted = template.render({'issue_id': str(issue_id), 'repo': self.__repo})

        page.output_attrs['html']['extra_html'].append(formatted)
        page.output_attrs['html']['scripts'].add(
            os.path.join(HERE, 'scripts', 'github-comment-loader.js'))

    def setup(self):
        super(CommentOnGithubExtension, self).setup()
        for ext in self.project.extensions.values():
            ext.formatter.formatting_page_signal.connect(
                self.__formatting_page_cb)
