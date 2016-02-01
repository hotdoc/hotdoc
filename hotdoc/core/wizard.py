"""
This module implements the core hotdoc wizard
"""

import argparse
import os
import sys

try:
    from hotdoc.utils.git_interface import GitInterface
    HAVE_GIT_INTERFACE = True
except ImportError:
    HAVE_GIT_INTERFACE = False
from hotdoc.utils.loggable import TerminalController
from hotdoc.utils.wizard import (QUICKSTART_HELP, QuickStartArgument,
                                 QuickStartWizard, Skip)

HOTDOC_ASCII =\
    r"""
/**    __  __   ____     ______   ____     ____     ______
 *    / / / /  / __ \   /_  __/  / __ \   / __ \   / ____/
 *   / /_/ /  / / / /    / /    / / / /  / / / /  / /
 *  / __  /  / /_/ /    / /    / /_/ /  / /_/ /  / /___
 * /_/ /_/   \____/    /_/    /_____/   \____/   \____/
 *
 * The Tastiest Documentation Tool.
 */
"""

PROMPT_GIT_REPO =\
    """
If you use git, I can commit the files created or
modified during setup, you will be prompted for confirmation
when that is the case.

The author name and mail address will be 'hotdoc' and
'hotdoc@hotdoc.net'.

Note: here as everywhere else, you can answer None to
skip the question.
"""

PROMPT_ROOT_INDEX =\
    """
I can now create a root index to tie all your sub indexes
together, do you wish me to do that [y,n]? """


# pylint: disable=unused-argument
def validate_git_repo(wizard, path):
    """
    Banana banana
    """
    try:
        GitInterface(path)
        return True
    # pylint: disable=broad-except
    except Exception:
        print "This does not look like a git repo : %s" % path
        return False


class HotdocWizard(QuickStartWizard):
    """
    Banana banana
    """
    # pylint: disable=no-member
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        conf_path = kwargs.pop('conf_path', '')
        QuickStartWizard.__init__(self, *args, **kwargs)
        if self.parent == self:
            self.doc_database = self
            self.comments = {}
            self.symbols = {}
            self.term_controller = TerminalController()
            if HAVE_GIT_INTERFACE:
                self.git_interface = GitInterface()
            else:
                self.git_interface = None
            self.config = {}
            self.conf_path = conf_path
        else:
            self.comments = self.parent.comments
            self.symbols = self.parent.symbols
            self.doc_database = self.parent.doc_database
            self.term_controller = self.parent.term_controller
            self.git_interface = self.parent.git_interface
            self.conf_path = self.parent.conf_path

        self.tag_validators = {}

    def add_comment(self, comment):
        """
        Banana banana
        """
        self.comments[comment.name] = comment

    def get_comment(self, name):
        """
        Banana banana
        """
        return self.comments.get(name)

    def get_or_create_symbol(self, type_, **kwargs):
        """
        Banana banana
        """
        unique_name = kwargs.get('unique_name')
        if not unique_name:
            unique_name = kwargs.get('display_name')
            kwargs['unique_name'] = unique_name

        filename = kwargs.get('filename')
        if filename:
            kwargs['filename'] = os.path.abspath(filename)

        symbol = type_()

        for key, value in kwargs.items():
            setattr(symbol, key, value)

        self.symbols[unique_name] = symbol

        return symbol

    def resolve_config_path(self, path):
        """
        Banana banana
        """
        if path is None:
            return path

        res = os.path.join(self.conf_path, path)
        return os.path.abspath(res)

    def before_prompt(self):
        """
        Banana banana
        """
        self.__clear_screen()

    # pylint: disable=no-self-use
    def get_index_path(self):
        """
        Banana banana
        """
        return None

    # pylint: disable=no-self-use
    def get_index_name(self):
        """
        Banana banana
        """
        return None

    def __create_root_index(self):
        contents = 'Welcome to our documentation!\n'

        for obj in self._qs_objects:
            if isinstance(obj, HotdocWizard):
                index_path = obj.get_index_path()
                index_name = obj.get_index_name()
                if index_path:
                    contents += '\n#### [%s](%s)\n' % (index_name, index_path)

        path = self.prompt_key(
            'index_path',
            prompt='Path to save the created index in',
            store=False,
            validate_function=QuickStartWizard.validate_folder)

        path = os.path.join(path, 'index.markdown')

        with open(path, 'w') as _:
            _.write(contents)

        self.config['index'] = path

    def before_quick_start(self, obj):
        """
        Banana banana
        """
        # pylint: disable=unidiomatic-typecheck
        if type(obj) == QuickStartArgument and obj.argument.dest == 'index':
            if self.config.get('index'):
                return

            self.before_prompt()
            if self.ask_confirmation(PROMPT_ROOT_INDEX):
                self.__create_root_index()
                raise Skip

    def main_prompt(self):
        """
        Banana banana
        """
        prompt = self.term_controller.BOLD +\
            "\nHotdoc started without arguments, starting setup\n" +\
            self.term_controller.NORMAL
        prompt += self.term_controller.CYAN + \
            QUICKSTART_HELP + self.term_controller.NORMAL

        prompt += '\nPress Enter to start setup '
        if not self.wait_for_continue(prompt):
            return False

        if not HAVE_GIT_INTERFACE:
            return True

        repo_path = self.prompt_key(
            'git_repo', prompt=">>> Path to the git repo ? ",
            title="the path to the root of the git repository",
            extra_prompt=PROMPT_GIT_REPO,
            validate_function=validate_git_repo,
            finalize_function=HotdocWizard.finalize_path)

        self.git_interface.set_repo_path(self.resolve_config_path(repo_path))

        return True

    @staticmethod
    def finalize_path(wizard, path):
        """
        Banana banana
        """
        if not path:
            return path

        return os.path.relpath(path, wizard.conf_path)

    @staticmethod
    def finalize_paths(wizard, paths):
        """
        Banana banana
        """
        if not paths:
            return paths

        res = []

        for path in paths:
            res.append(os.path.relpath(path, wizard.conf_path))

        return res

    def __clear_screen(self):
        sys.stdout.write(self.term_controller.CLEAR_SCREEN)
        sys.stdout.write(self.term_controller.RED +
                         self.term_controller.BOLD + HOTDOC_ASCII +
                         self.term_controller.NORMAL)

    def _add_argument_override(self, group, *args, **kwargs):
        set_default = kwargs.get('default')
        kwargs['default'] = argparse.SUPPRESS
        res = QuickStartWizard._add_argument_override(
            self, group, *args, **kwargs)

        if set_default:
            self.config[res.dest] = set_default

        return res
