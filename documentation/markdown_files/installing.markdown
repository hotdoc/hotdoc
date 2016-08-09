---
short-description: Detailed instructions for installing hotdoc
...

# Installing

## System-wide dependencies

### graphviz

Hotdoc needs [graphviz](http://www.graphviz.org/) to generate object hierarchies, you will thus need to install graphviz-dev, and some libraries it depends depend on the python headers, so you will need to install them too.

### lxml

Hotdoc also uses lxml, which depends on libxml2 and libxslt.

### cmake

For now, hotdoc bundles its own version of [libcmark](https://github.com/jgm/cmark) as a submodule, and builds it using cmake, which thus needs to be installed on the system.

### Command-line install

On Fedora you can install all these dependencies with:

```
dnf install graphviz-devel python-devel libxml2-devel libxslt-devel cmake libyaml-devel
```

And on ubuntu / debian:

```
apt-get install libgraphviz-dev python-dev libxml2-dev libxslt1-dev cmake libyaml-dev
```

I guess it should be similar on Ubuntu / debian, refer to <https://cmake.org/install/> for more info.

## Creating a virtualenv

It is highly recommended to use [virtualenv](https://virtualenv.readthedocs.org/en/latest/) to try out any new python project, and hotdoc is no exception. You can however skip this step if you really do not
care about installing hotdoc system-wide.

> Assuming [pip](https://pip.pypa.io/en/stable/) is installed

```
pip2 install virtualenv
virtualenv hotdoc_env
. hotdoc_env/bin/activate
```

You are now in a virtual environment, to exit it you may call `deactivate`, to enter it again simply call `. hotdoc_env/bin/activate` from the directory in which the environment was created.

## Hotdoc itself

Three main alternatives are available:

* Using pip to get the last released version of hotdoc:
  ```
  pip2 install hotdoc
  ```

* Installing a "read-only" version from a github clone:
  ```
  git clone https://github.com/hotdoc/hotdoc.git
  cd hotdoc
  python2 setup.py install
  ```

* Installing an editable version from a github clone:
  ```
  git clone https://github.com/hotdoc/hotdoc.git
  cd hotdoc
  pip2 install -e .[dev]
  ```

Congratulations, you have successfully installed hotdoc! You may now want to check the [list of available extensions](https://github.com/hotdoc).
