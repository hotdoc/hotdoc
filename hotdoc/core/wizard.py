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
| >>> None"""

class Skip(KeyboardInterrupt):
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
    def __init__(self, chief_wizard, argument, prompt_action, extra_prompt):
        self.argument = argument
        self.prompt_action = prompt_action
        self.chief_wizard = chief_wizard
        self.extra_prompt = extra_prompt

    def do_quick_start(self, result_dict):
        if not self.prompt_action:
            raise Skip

        update = True
        current_value = result_dict.get(self.argument.dest)
        if current_value is not None:
            print 'Current value for %s : %s' % (self.argument.dest,
                    current_value)
            update = self.chief_wizard.ask_confirmation('Update [y,n]? ')

        if not update:
            raise Skip

        res = self.prompt_action(self.chief_wizard, self.argument)
        result_dict[self.argument.dest] = res

FILENAMES_PROMPT=\
"""
Note: A list of filenames is expected. You can use
wildcards:

>>> ["../foo/*.c", "../foo/*.h"]

The strings will be evaluated each time the tool is run.

You can of course answer None:

>>> None

You will be prompted for confirmation.
"""

PROMPT_EXECUTABLE=\
"""
%s is needed for the setup to continue.

Press Enter once it is installed """

class QuickStartWizard(object):
    def __init__(self, parser,
            chief_wizard=None,
            prompt_done_action=None):
        self.parser = parser
        self._add_argument = parser.add_argument
        parser.add_argument = self._add_argument_override
        self._add_argument_group = parser.add_argument_group
        parser.add_argument_group = self._add_argument_group_override
        self._qs_objects = []
        self.args = {}
        self.chief_wizard = chief_wizard
        if self.chief_wizard is None:
            self.chief_wizard = self
        self.prompt_done_action = prompt_done_action

    def default_arg_prompt(self, chief_wizard, arg):
        return chief_wizard.qsshell.ask('>>> %s ? ' % arg.help)

    def default_group_prompt(self, chief_wizard, group):
        if type(group) == argparse.ArgumentParser:
            title = group.prog
        else:
            title = group.title

        question = "\nSetting up %s\n" % title
        if group.description:
            question += "\n\nDescription: %s\n" % group.description

        print "Current configuration:\n"
        for qs_object in self._qs_objects:
            if type(qs_object) == QuickStartArgument:
                current_value = chief_wizard.args.get(qs_object.argument.dest)
                print '%s : %s' % (qs_object.argument.dest, current_value)

        question += 'Would you like to configure %s [y,n]? ' % title

        return chief_wizard.ask_confirmation(question)

    def default_main_prompt(self, chief_wizard, chief):
        return self.default_group_prompt(chief_wizard, arg)

    def propose_choice(self, choices, skippable=True):
        self.before_prompt()

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

        return wizard.qsshell.ask_confirmation()

    def prompt_key(self, key, prompt=None, title=None,
            store=True, validate_function=None):
        self.before_prompt()

        if title is None:
            title = key

        if key in self.args:
            print 'Current value for %s : %s' % (title,
                    self.args[key])
            if not self.qsshell.ask_confirmation('Update [y,n]? '):
                return self.args[key]

        if not prompt:
            prompt = 'New value for %s? ' % title

        validated = False

        while not validated:
            res = self.qsshell.ask(prompt)
            if validate_function is None:
                validated = True
            else:
                validated = validate_function(self, res)

        if store:
            self.args[key] = res

        return res

    def _add_argument_group_override(self, parser, *args, **kwargs):
        prompt_done_action = kwargs.pop('prompt_done_action', None)
        res = self._add_argument_group(parser, *args, **kwargs)
        wizard = type(self)(res,
                chief_wizard=self.chief_wizard,
                prompt_done_action=prompt_done_action)
        self._qs_objects.append(wizard)
        return res

    def _add_argument_override(self, parser, *args, **kwargs):
        prompt_action = kwargs.pop('prompt_action', self.default_arg_prompt)
        extra_prompt = kwargs.pop('extra_prompt', None)
        arg = self._add_argument(parser, *args, **kwargs)
        self._qs_objects.append(QuickStartArgument(self.chief_wizard, arg,
            prompt_action, extra_prompt))
        return arg

    def wait_for_continue(self, prompt='Press Enter to continue '):
        self.before_prompt()
        self.qsshell.raw_input(prompt)
        return True

    def prompt_executable(self, executable, prompt=None):
        if prompt is None:
            prompt = PROMPT_EXECUTABLE % executable

        while not find_executable(executable):
            self.wait_for_continue(prompt)

    def before_prompt(self):
        pass

    def quick_start(self):
        qsshell = QuickStartShell()
        self.qsshell = qsshell

        try:
            if not self.do_quick_start(self.args):
                return None
        except EOFError:
            print "Aborting quick start"
            return None

        return self.args

    def do_quick_start(self, args):
        if self == self.chief_wizard:
            prompt = self.default_main_prompt
        else:
            prompt = self.default_group_prompt

        if not prompt(self.chief_wizard, self.parser):
            if self.prompt_done_action:
                self.prompt_done_action(self.chief_wizard, self.parser)
            return False

        for obj in self._qs_objects:
            try:
                obj.do_quick_start(args)
            except Skip:
                pass

        if self.prompt_done_action:
            self.prompt_done_action(self.chief_wizard, self.parser)
