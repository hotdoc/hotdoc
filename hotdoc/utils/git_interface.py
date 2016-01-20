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
