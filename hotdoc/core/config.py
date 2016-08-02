# -*- coding: utf-8 -*-
#
# Copyright © 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""
Implement a high-level config parser for hotdoc.
"""

import os
import json
import glob

from hotdoc.utils.utils import OrderedSet
from hotdoc.utils.loggable import error


# pylint: disable=too-many-instance-attributes
class ConfigParser(object):
    """
    Helper class to help deal with common extension dependencies.

    This class has two goals:

    * Help extensions retrieve sources and indexes, with
      support for filters and wildcards.
    * Provide a generic way to list all the dependencies
      for a given hotdoc project, without needing to
      import extensions and query them individually, as it
      is costly and we want to make this operation as
      transparent as possible for the build system.

    This implies that extensions with external dependencies
    need to follow several semantic conventions for the arguments
    they expose:

    * When an extension exposes an index, it needs to expose
      an argument named `<prefix>index` to retrieve it.
    * When an extension accepts a list of sources, it needs
      to expose two arguments, one named `<prefix>sources`,
      and the other named `<prefix>source_filters`. With this
      done, `ConfigParser` will automatically provide wildcard
      expansion and filtering.

    Note that `base_extension.BaseExtension` provides helper methods
    to register index and sources options, this documentation should
    only be interesting for 'advanced' use cases.
    """

    def __init__(self, command_line_args=None, conf_file=None, defaults=None):
        """
        Constructor for `ConfigParser`.

        Args:
            command_line_args: list, a list of command line arguments
                that will override the keys defined in `conf_file`,
                or `None`
            conf_file: str, the path to the configuration file. If
                `None`, `ConfigParser` will look for a file named
                `hotdoc.json` in the current directory.
        """

        self.__conf_file = None
        self._conf_dir = None
        contents = '{}'

        if conf_file:
            self.__conf_file = os.path.abspath(conf_file)
            self.__conf_dir = os.path.dirname(self.__conf_file)
            try:
                with open(self.__conf_file, 'r') as _:
                    contents = _.read()
            except IOError:
                pass

        self.__invoke_dir = os.getcwd()

        try:
            self.__config = json.loads(contents)
        except ValueError as ze_error:
            error('invalid-config',
                  'The provided configuration file %s is not valid json.\n'
                  'The exact error was %s.\n'
                  'This often happens because of missing or extra commas, '
                  'but it may be something else, please fix it!\n' %
                  (conf_file, str(ze_error)))

        self.__cli = command_line_args or {}
        self.__defaults = defaults or {}
        index = self.get_index()
        if index:
            self.__base_index_path = os.path.dirname(index)
        else:
            self.__base_index_path = ''

    def __abspath(self, path, from_conf):
        if path is None:
            return None

        if os.path.isabs(path):
            return path
        if from_conf:
            return os.path.abspath(os.path.join(self.__conf_dir, path))
        return os.path.abspath(os.path.join(self.__invoke_dir, path))

    def __resolve_patterns(self, source_patterns, from_conf):
        if source_patterns is None:
            return OrderedSet()

        all_files = OrderedSet()
        for item in source_patterns:
            item = self.__abspath(item, from_conf)
            if '*' in item:
                all_files |= glob.glob(item)
            else:
                all_files.add(item)

        return all_files

    # pylint: disable=no-self-use
    def get_markdown_files(self, dir_):
        """
        Get all the markdown files in a folder, recursively

        Args:
            dir_: str, a toplevel folder to walk.
        """
        md_files = OrderedSet()
        for root, _, files in os.walk(dir_):
            for name in files:
                split = os.path.splitext(name)
                if len(split) == 1:
                    continue
                if split[1] in ('.markdown', '.md', '.yaml'):
                    md_files.add(os.path.join(root, name))
        return md_files

    def get_invoke_dir(self):
        """
        Banana banana
        """
        return self.__invoke_dir

    def get(self, key, default=None):
        """
        Get the value for `key`.

        Gives priority to command-line overrides.

        Args:
            key: str, the key to get the value for.

        Returns:
            object: The value for `key`
        """
        if key in self.__cli:
            return self.__cli[key]
        if key in self.__config:
            return self.__config.get(key)
        if key in self.__defaults:
            return self.__defaults.get(key)
        return default

    def get_index(self, prefix=''):
        """
        Retrieve the absolute path to an index, according to
        `prefix`.

        Args:
            prefix: str, the desired prefix or `None`.

        Returns:
            str: An absolute path, or `None`
        """
        prefixed = '%sindex' % prefix
        if prefixed in self.__cli and self.__cli[prefixed]:
            index = self.__cli.get(prefixed)
            from_conf = False
        else:
            index = self.__config.get('%sindex' % prefix)
            from_conf = True

        if prefix and index:
            return os.path.join(self.__base_index_path, index)

        return self.__abspath(index, from_conf)

    def get_path(self, key, rel_to_cwd=False, rel_to_conf=False):
        """
        Retrieve a path from the config, resolving it against
        the invokation directory or the configuration file directory,
        depending on whether it was passed through the command-line
        or the configuration file.

        Args:
            key: str, the key to lookup the path with

        Returns:
            str: The path, or `None`
        """
        if key in self.__cli:
            path = self.__cli[key]
            from_conf = False
        else:
            path = self.__config.get(key)
            from_conf = True

        if path is None:
            return ""

        res = self.__abspath(path, from_conf)

        if rel_to_cwd:
            return os.path.relpath(res, self.__invoke_dir)
        elif rel_to_conf:
            return os.path.relpath(res, self.__conf_dir)

        return self.__abspath(path, from_conf)

    def get_paths(self, key):
        """
        Same as `ConfigParser.get_path` for a list of paths.

        Args:
            key: str, the key to lookup the paths with

        Returns:
            list: The paths.
        """
        final_paths = []

        if key in self.__cli:
            paths = self.__cli[key] or []
            from_conf = False
        else:
            paths = self.__config.get(key) or []
            from_conf = True

        for path in paths:
            final_path = self.__abspath(path, from_conf)
            if final_path:
                final_paths.append(final_path)

        return final_paths

    def get_sources(self, prefix=''):
        """
        Retrieve a set of absolute paths to sources, according to `prefix`

        `ConfigParser` will perform wildcard expansion and
        filtering.

        Args:
            prefix: str, the desired prefix.

        Returns:
            utils.utils.OrderedSet: The set of sources for the given
                `prefix`.
        """
        prefixed = '%ssources' % prefix

        if prefixed in self.__cli:
            sources = self.__cli.get(prefixed)
            from_conf = False
        else:
            sources = self.__config.get(prefixed)
            from_conf = True

        if sources is None:
            return OrderedSet()

        sources = self.__resolve_patterns(sources, from_conf)

        prefixed = '%ssource_filters' % prefix
        if prefixed in self.__cli:
            filters = self.__cli.get(prefixed)
            from_conf = False
        else:
            filters = self.__config.get(prefixed)
            from_conf = True

        if filters is None:
            return sources

        sources -= self.__resolve_patterns(filters, from_conf)

        return sources

    def get_dependencies(self):
        """
        Retrieve the set of all dependencies for a given configuration.

        Returns:
            utils.utils.OrderedSet: The set of all dependencies for the
                tracked configuration.
        """
        all_deps = OrderedSet()
        for key, _ in self.__config.items():
            if key in self.__cli:
                continue

            if key.endswith('sources'):
                all_deps |= self.get_sources(key[:len('sources') * -1])

        for key, _ in self.__cli.items():
            if key.endswith('sources'):
                all_deps |= self.get_sources(key[:len('sources') * -1])

        if self.__conf_file is not None:
            all_deps.add(self.__conf_file)

        all_deps.add(self.get_path("sitemap", rel_to_cwd=True))

        cwd = os.getcwd()
        return [os.path.relpath(fname, cwd) for fname in all_deps if fname]

    def dump(self, conf_file=None):
        """
        Dump the possibly updated config to a file.

        Args:
            conf_file: str, the destination, or None to overwrite the
                existing configuration.
        """

        if conf_file:
            conf_dir = os.path.dirname(conf_file)
            if not os.path.exists(conf_dir):
                os.makedirs(conf_dir)
        else:
            conf_dir = self.__conf_dir

        final_conf = {}
        for key, value in self.__config.items():
            if key in self.__cli:
                continue
            final_conf[key] = value

        for key, value in self.__cli.items():
            if (key.endswith('index') and not key.endswith('smart_index')) or \
                    key in ['sitemap', 'output']:
                path = self.__abspath(value, from_conf=False)
                if path:
                    relpath = os.path.relpath(path, conf_dir)
                    final_conf[key] = relpath
            elif key.endswith('sources') or key.endswith('source_filters'):
                new_list = []
                for path in value:
                    path = self.__abspath(path, from_conf=False)
                    if path:
                        relpath = os.path.relpath(path, conf_dir)
                        new_list.append(relpath)
                final_conf[key] = new_list
            elif key != 'command':
                final_conf[key] = value

        with open(conf_file or self.__conf_file or 'hotdoc.json', 'w') as _:
            _.write(json.dumps(final_conf, sort_keys=True, indent=4))
