---
short-description: Instructions for cleaning a hotdoc project.
...

# Cleaning

Instructions for cleaning a hotdoc project.

Hotdoc generates its output in the specified directory and a a folder named
`hotdoc-private[hash]` in the folder it's run from.

Assuming the output directory is `built_doc`, a clean command would be:

``` shell
rm -rf hotdoc-private* built_doc
```
