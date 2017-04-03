---
short-description: Detailed instructions for installing hotdoc
...

# Installing

## System-wide dependencies

### lxml

Hotdoc uses lxml, which depends on libxml2 and libxslt.

### cmake

For now, hotdoc bundles its own version of [libcmark](https://github.com/jgm/cmark) as a submodule, and builds it using cmake, which thus needs to be installed on the system.

### pyyaml

Hotdoc uses pyyaml to parse yaml ‘front-matter’ metadata in markdown pages, it depends on libyaml.

### Command-line install

On Fedora you can install all these dependencies with:

```
dnf install python-devel libxml2-devel libxslt-devel cmake libyaml-devel
```

And on ubuntu / debian:

```
apt-get install python-dev libxml2-dev libxslt1-dev cmake libyaml-dev
```

We'll be happy to merge updates to this list if you have successfully built hotdoc on another platform.

## Creating a virtualenv

It is highly recommended to use a virtual env to try out any new python project, and hotdoc is no exception. You can however skip this step if you really do not
mind installing hotdoc system-wide.

> Assuming [pip](https://pip.pypa.io/en/stable/) is installed

```
python3 -m pip install virtualenv
python3 -m venv hotdoc_env
. hotdoc_env/bin/activate
```

You are now in a virtual environment, to exit it you may call `deactivate`, to enter it again simply call `. hotdoc_env/bin/activate` from the directory in which the environment was created.

## Hotdoc itself

Three main alternatives are available:

* Using pip to get the last released version of hotdoc:
  ```
  python3 -m install hotdoc
  ```

* Installing a "read-only" version from a github clone:
  ```
  git clone https://github.com/hotdoc/hotdoc.git
  cd hotdoc
  python3 setup.py install
  ```

* Installing an editable version from a github clone:
  ```
  git clone https://github.com/hotdoc/hotdoc.git
  cd hotdoc
  python3 -m pip install -e .[dev]
  ```

Congratulations, you have successfully installed hotdoc! You may now want to check the [list of available extensions](https://github.com/hotdoc).
