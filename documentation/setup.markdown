sudo dnf install python-devel
sudo dnf install python-lxml
sudo dnf install clang-devel
sudo dnf install clang-devel.x86_64
sudo dnf install python-pandocfilters.noarch
sudo dnf install haskell-platform
sudo dnf install ghc-pandoc-devel.x86_64
sudo dnf install libxml2-devel
sudo easy_install pip
sudo pip install wheezy.template (Not packaged on fedora 22)
sudo dnf install flex
sudo dnf install bison
sudo dnf install glib2-devel
sudo dnf install clang-devel

cd src/lexer_parsers && python setup.py build
