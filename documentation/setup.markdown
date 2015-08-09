To install better doc tool, you will first need to satisfy the dependencies, on fedora 22 this can be done with:

sudo dnf install haskell-platform glib2-devel flex bison python-devel libxml2-devel libxslt-devel clang-devel ghc-pandoc-devel

Adapt to your distribution.

You can then install it through pypi with:

pip install better_doc_tool

It also works in a virtualenv.
