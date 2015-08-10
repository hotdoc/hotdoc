To install better doc tool, you will first need to satisfy the dependencies, on fedora 22 this can be done with:

sudo dnf install haskell-platform glib2-devel flex bison python-devel libxml2-devel libxslt-devel clang-devel ghc-pandoc-devel

Adapt to your distribution.

You will also need to manually install the clang bindings adapted to your clang installation, for example if clang 3.5
is installed, you will need to run:

pip install clang==3.5

You can then install it through pypi with:

pip install better_doc_tool

It also works in a virtualenv.
