## Cleaning

Hotdoc generates its output in the specified directory, a folder named hotdoc-private in the folder it's run from, and a folder named `generated` in the folder where the global index is located.

Assuming the output directory is `html` and the index folder is `markdown_files`, a clean command would be:

```
rm -rf hotdoc-private generated html
```
