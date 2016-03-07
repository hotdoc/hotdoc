# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
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
Banana banana
"""

import os

import pygit2 as git


class GitInterface(object):
    """
    Banana banana
    """
    def __init__(self, repo_path=None):
        if repo_path:
            self.repo_path = os.path.abspath(repo_path)
            self.repo = git.Repository(self.repo_path)
            self.index = self.repo.index
            self.commiter = git.Signature('hotdoc', 'hotdoc@hotdoc.net')
        else:
            self.repo_path = None

    def set_repo_path(self, repo_path):
        """
        Banana banana
        """
        if repo_path is None:
            return

        self.repo_path = os.path.abspath(repo_path)
        self.repo = git.Repository(self.repo_path)
        self.index = self.repo.index
        self.commiter = git.Signature('hotdoc', 'hotdoc@hotdoc.net')

    def add(self, filename):
        """
        Banana banana
        """
        filename = os.path.relpath(filename, self.repo_path)
        self.index.add(filename)
        self.index.write()

    def commit(self, author, author_mail, message):
        """
        Banana banana
        """
        author = git.Signature(author, author_mail)
        tree = self.index.write_tree()
        # FIXME: commit on current branch
        # pylint: disable=no-member
        oid = self.repo.create_commit('refs/heads/master',
                                      author, self.commiter, message, tree,
                                      [self.repo.head.get_object().hex])
        return oid
