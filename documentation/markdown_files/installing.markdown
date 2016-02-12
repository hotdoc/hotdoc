## Installing

### System-wide dependencies

> If you install these dependencies successfully on a platform not listed here, or have issues on any platform, opening a simple issue (or a pull request with this file edited) will help immensely!

Hotdoc can optionally use [pygit2](http://www.pygit2.org/) to help with porting projects from other documentation systems.

If you wish to enable that feature, you need to install libgit2. On fedora this can be done with:

```
dnf install libgit2-devel.x86_64
```

And on ubuntu:

```
apt-get install libgit2-dev
```

Adapt to your distribution.

> If your installed version of libgit 2 is older than 0.22.0, this feature will not be enabled

Hotdoc also needs [graphviz](http://www.graphviz.org/) to generate object hierarchies, you will thus need to install graphviz-dev, and some libraries it depends depend on the python headers, so you will need to install them too.

On Fedora this can be done with:

```
dnf install graphviz-devel python-devel
```

And on ubuntu / debian:

```
apt-get install libgraphviz-dev python-dev
```

### Creating a virtualenv

It is highly recommended to use [virtualenv](https://virtualenv.readthedocs.org/en/latest/) to try out any new python project, and hotdoc is no exception. You can however skip this step if you really do not
care about installing hotdoc system-wide.

> Assuming [pip](https://pip.pypa.io/en/stable/) is installed

```
pip install virtualenv
virtualenv hotdoc_env
. hotdoc_env/bin/activate
```

You are now in a virtual environment, to exit it you may call "deactivate", to enter it again simply call `. hotdoc_env/bin/activate` from the directory in which the environment was created.

### Hotdoc itself

Three main alternatives are available:

* Using pip to get the last released version of hotdoc:
  ```
  pip install hotdoc
  ```

* Installing a "read-only" version from a github clone:
  ```
  git clone https://github.com/hotdoc/hotdoc.git
  cd hotdoc
  python setup.py install
  ```

* Installing an editable version from a github clone:
  ```
  git clone https://github.com/hotdoc/hotdoc.git
  cd hotdoc
  pip install -e .[dev]
  ```

Congratulations, you have successfully installed hotdoc! You may now want to check the [list of available extensions](https://github.com/hotdoc).
