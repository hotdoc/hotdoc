"""
Extension to add links to edit pages on github
"""
import os
import shutil
import subprocess

from hotdoc.utils.loggable import Logger, warn
from hotdoc.core.exceptions import HotdocException
from hotdoc.core.extension import Extension

HERE = os.path.abspath(os.path.dirname(__file__))
PNAME = 'edit-on-github'

Logger.register_warning_code('source-not-in-git-repo', HotdocException,
                             domain=PNAME)


class EditOnGitHubExtension(Extension):
    """Extension to upload generated doc to a git repository"""
    extension_name = PNAME
    argument_prefix = PNAME

    def __init__(self, app, project):
        self.__repo = None
        self.__repo_root = None
        self.__branch = None
        Extension.__init__(self, app, project)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group(
            'Edit on github or gitlab',
            'Add links to edit markdown pages on github or gitlab')

        group.add_argument(
            '--edit-on-github-repository',
            help="Github or gitlab repository to edit pages on",
            default=None)

        group.add_argument(
            '--edit-on-github-branch',
            help="Branch onto which to link for editing",
            default="master")

    def parse_config(self, config):
        super().parse_toplevel_config(config)

        self.__repo = config.get('edit_on_github_repository')
        self.__branch = config.get('edit_on_github_branch', 'master')
        self.__repo_root = None

    def setup(self):
        super().setup()

        if not self.__repo:
            return

        if not shutil.which('git'):
            print(PNAME + ': "git" not present on the system'
                  ', can\' use plugin')
            return

        for ext in self.project.extensions.values():
            ext.formatter.formatting_page_signal.connect(
                self.__formatting_page_cb)

        for ext in list(self.project.extensions.values()):
            template_path = os.path.join(HERE, 'html_templates')
            ext.formatter.engine.loader.searchpath.append(template_path)

    def __get_repo_root(self, page):
        if self.__repo_root:
            return self.__repo_root

        try:
            self.__repo_root = subprocess.check_output(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=os.path.dirname(page.source_file)).decode().strip('\n')
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return self.__repo_root

    def __formatting_page_cb(self, formatter, page):
        # Only allow editing markdown pages
        if page.generated:
            return

        root = self.__get_repo_root(page)
        if not root:
            warn('source-not-in-git-repo',
                 'File %s not in a git repository' % (
                     page.source_file))

        edit_link = self.__repo + '/edit/' + self.__branch + \
            '/' + os.path.relpath(page.source_file, root)

        sitename = "GitHub" if "github" in self.__repo else "GitLab"

        page.output_attrs['html']['edit_button'] = \
            '<a href=%s data-hotdoc-role="edit-button">' \
            'Edit on %s</a>' % (edit_link, sitename)


def get_extension_classes():
    """Nothing important, really"""
    return [EditOnGitHubExtension]
