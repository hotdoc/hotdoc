import argparse
import json
import glob
import os
from IPython.terminal.embed import InteractiveShellEmbed
from traitlets.config.loader import Config
from distutils.spawn import find_executable

QUICKSTART_HELP = \
"""
| Answer the prompts by returning a value.
|
| Example:
|
| What is your favorite folder ?
|
| >>> import os
| >>> res = os.path.abspath('.')
| >>> print res
| >>> res
|
| The answer will be the value of res, you will be prompted for confirmation.
|
| To skip a question, return None:
|
| >>> None
"""

class Skip(Exception):
    pass

class QuickStartShell(InteractiveShellEmbed):
    def __init__(self):
        cfg = Config()
        prompt_config = cfg.PromptManager
        prompt_config.out_template = 'Answer: '
        InteractiveShellEmbed.__init__(self, banner1='', config=cfg)

    def run_cell(self, raw_cell, **kwargs):
        if raw_cell.strip() == 'None':
            self.skip = True
            self.exit_now = True
            return None

        res = InteractiveShellEmbed.run_cell(self, raw_cell, **kwargs)

        if res.result:
            self.result = res.result
            self.exit_now = True

        return res

    def raw_input(self, prompt):
        res = None
        while res is None:
            try:
                res = InteractiveShellEmbed.raw_input(self, prompt)
            except KeyboardInterrupt:
                print "\nUse ctrl + D to quit"

        return res

    def ask_confirmation(self, prompt='Confirm [y,n]? '):
        res = None
        while res is None:
            user_res = self.raw_input(prompt)
            if user_res == 'y':
                res = True
            elif user_res == 'n':
                res = False
        return res

    def wait_for_continue(self, prompt='Press Enter to continue '):
        self.raw_input(prompt)
        return True

    def ask(self, question, confirm=False):
        self.skip = False
        self.result = None

        confirmed = False

        while not confirmed:
            self(header=question)

            if self.skip:
                raise Skip

            if self.result is None:
                raise EOFError

            confirmed = not confirm or self.ask_confirmation()

        return self.result


class QuickStartArgument(object):
    def __init__(self, wizard, argument, extra_prompt,
            validate_function, finalize_function):
        self.argument = argument
        self.wizard = wizard
        self.extra_prompt = extra_prompt
        self.validate_function = validate_function
        self.finalize_function = finalize_function

    def do_quick_start(self):
        return self.wizard.prompt_key(self.argument.dest,
                prompt='>>> %s ?' % self.argument.help,
                extra_prompt=self.extra_prompt,
                title=self.argument.help,
                validate_function=self.validate_function,
                finalize_function=self.finalize_function)

PROMPT_EXECUTABLE=\
"""
%s is needed for the setup to continue.

Press Enter once it is installed """

class QuickStartWizard(object):
    def __init__(self, group,
            parent=None,
            validate_function=None):
        self.group = group
        self._add_argument = group.add_argument
        group.add_argument = self._add_argument_override
        self._add_argument_group = group.add_argument_group
        group.add_argument_group = self._add_argument_group_override
        self._qs_objects = []
        self.parent = parent
        if parent is None:
            self.parent = self
            self.qsshell = QuickStartShell()
            self.config = {}
        else:
            self.qsshell = parent.qsshell
            self.config = parent.config

        self.validate_function = validate_function

    def group_prompt(self):
        self.before_prompt()

        if type(self.group) == argparse.ArgumentParser:
            title = self.group.prog
        else:
            title = self.group.title

        print "\nSetting up %s" % title
        if self.group.description:
            print "\nDescription: %s" % self.group.description

        print "Current configuration:\n"
        for qs_object in self._qs_objects:
            if type(qs_object) == QuickStartArgument:
                current_value = self.config.get(qs_object.argument.dest)
                print '%s : %s' % (qs_object.argument.dest, current_value)

        question = '\nWould you like to configure %s [y,n]? ' % title

        return self.ask_confirmation(question)

    def main_prompt(self):
        return self.group_prompt()

    def before_prompt(self):
        pass

    def quick_start(self):
        try:
            if not self.do_quick_start():
                return False
        except EOFError:
            print "Aborting quick start"
            return False

        return True

    def before_quick_start(self, obj):
        return

    def do_quick_start(self):
        if self == self.parent:
            prompt = self.main_prompt
        else:
            prompt = self.group_prompt

        if not prompt():
            return False

        for obj in self._qs_objects:
            try:
                self.before_quick_start(obj)
                obj.do_quick_start()
            except Skip:
                pass

        if self.validate_function:
            if not self.validate_function(self):
                return self.do_quick_start()

        return True

    def propose_choice(self, choices, skippable=True, extra_prompt=None):
        self.before_prompt()

        if extra_prompt:
            print extra_prompt

        skip_choice = -1

        if skippable:
            skip_choice = len(choices)
            choices.append("Skip")

        prompt = "Make your choice ["

        for i, choice in enumerate(choices):
            print '%s) %s' % (str(i), choice)
            if i != 0:
                prompt += ','
            prompt += str(i)

        print ""

        prompt += ']? '

        valid_choice = False

        while not valid_choice:
            res = self.qsshell.raw_input(prompt)
            try:
                valid_choice = int(res) in range(len(choices))
            except:
                valid_choice = False

            if not valid_choice:
                print "Invalid choice %s" % res

        if int(res) == skip_choice:
            raise Skip

        return int(res)

    def ask_confirmation(self, prompt='Confirm [y,n]? '):
        res = None
        while res is None:
            user_res = self.qsshell.raw_input(prompt)
            if user_res == 'y':
                res = True
            elif user_res == 'n':
                res = False
        return res

    def prompt_key(self, key, prompt=None, extra_prompt=None, title=None,
            store=True, validate_function=None, finalize_function=None):
        self.before_prompt()

        if title is None:
            title = key

        if key in self.config:
            print 'Current value for %s : %s' % (title,
                    self.config[key])
            if not self.qsshell.ask_confirmation('Update [y,n]? '):
                return self.config[key]

        if extra_prompt:
            print extra_prompt

        if not prompt:
            prompt = 'New value for %s? ' % title

        validated = False

        while not validated:
            res = self.qsshell.ask(prompt)
            if validate_function is None:
                validated = True
            else:
                validated = validate_function(self, res)

        if finalize_function:
            res = finalize_function(self, res)

        if store:
            self.config[key] = res

        return res

    def wait_for_continue(self, prompt='Press Enter to continue '):
        self.before_prompt()
        res = self.qsshell.raw_input(prompt)
        if res.lower() == "you're a wizard harry":
            print "Indeed"
        return True

    def prompt_executable(self, executable, prompt=None):
        if prompt is None:
            prompt = PROMPT_EXECUTABLE % executable

        while not find_executable(executable):
            self.wait_for_continue(prompt)

    @staticmethod
    def validate_folder(wizard, path):
        res = True
        if not os.path.exists(path):
            os.mkdir(path)
            res = True
        elif not os.path.isdir(path):
            print "Path %s is not a folder" % path
            res = False

        return res

    @staticmethod
    def validate_list(wizard, thing):
        res = type(thing) == list
        if not res:
            print "%s is not a list" % thing
        return res

    @staticmethod
    def check_path_is_file(wizard, path):
        res = True

        if not os.path.exists(path):
            print "Path %s does not exist" % path
            res = False
        elif not os.path.isfile(path):
            print "Path %s is not a file" % path
            res = False

        return res

    @staticmethod
    def validate_globs_list(wizard, thing):
        if not wizard.validate_list(wizard, thing):
            return False

        resolved = []
        for item in thing:
            resolved.extend (glob.glob(item))

        print "The expression(s) currently resolve(s) to:"
        print resolved

        return wizard.ask_confirmation()

    def _add_argument_group_override(self, parser, *args, **kwargs):
        validate_function = kwargs.pop('validate_function', None)
        wizard_class = kwargs.pop('wizard_class', type(self.parent))
        res = self._add_argument_group(parser, *args, **kwargs)
        wizard = wizard_class(res,
                parent=self.parent,
                validate_function=validate_function)
        self._qs_objects.append(wizard)
        return res

    def _add_argument_override(self, group, *args, **kwargs):
        validate_function = kwargs.pop('validate_function', None)
        finalize_function = kwargs.pop('finalize_function', None)
        extra_prompt = kwargs.pop('extra_prompt', None)
        no_prompt = kwargs.pop('no_prompt', False)
        arg = self._add_argument(group, *args, **kwargs)

        if not no_prompt:
            self._qs_objects.append(QuickStartArgument(self, arg,
                extra_prompt, validate_function, finalize_function))

        return arg
