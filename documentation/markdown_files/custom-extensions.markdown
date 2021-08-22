---
short-description: WIP Instructions for creating custom extensions.
...

# Creating custom extensions

All hotdoc extensions must extend the `Extension` class and provide a
`get_extension_classes` function.

Minimal example extension:

```py
from pathlib import Path
from json import loads

from hotdoc.core.extension import Extension
from hotdoc.core.tree import Page
from hotdoc.core.project import Project
from hotdoc.run_hotdoc import Application
from hotdoc.core.formatter import Formatter

import typing as T

if T.TYPE_CHECKING:
    import argparse

class MyExtension(Extension):
    extension_name = 'my-ext'
    argument_prefix = 'prefix'

    def __init__(self, app: Application, project: Project):
        super().__init__(app, project)
        self._cfg_value = ''
        # More

    @staticmethod
    def add_arguments(parser: 'argparse.ArgumentParser'):
        group = parser.add_argument_group(
            'My extension',
            'My custom hotdoc extension',
        )

        # Add Arguments with `group.add_argument(...)`
        group.add_argument(
            '--prefix-my-config',
            help="My custom config option",
            default='',
        )

    def parse_config(self, config: T.Dict[str, T.Any]) -> None:
        super(self).parse_config(config)
        self._cfg_value = config.get('prefix_my_config')

    def setup(self) -> None:
        super().setup()
        # Custom setup code here

    @staticmethod
    def get_dependencies() -> T.List[T.Type[Extension]]:
        return []  # In case this extension has dependencies on other extensions

def get_extension_classes() -> T.List[T.Type[Extension]]:
    return [MyExtension]
```

# Using custom extensions

One way to use custom extensions to provide the path to the extension module
with the `--extra-extension` option:

```bash
hotdoc --extra-extension /path/to/your/extension.py
```
