# The smart index

Hotdoc allows its extension to build documentation pages and their
content automatically. On top of that users can override extension
decision about what symbols should be added to what page and in what
order, the combination of those two possibilities is what we call
**smart indexing**.

## Activate smart indexing

Smart indexing is made by a specific extension, for example if you are
documenting a C library you should use the `--c-smart-index` option so
that the C extension takes control and build the index for its section.
Basically, during smart indexing of C code, the extension will build one
output page per header ('.h') file.

## Usage

### Override default indexing behaviour

As previously explained, the user can override default behaviour, and
this is done through a `.markdown` page that has the same name as the
source file. For example, in the case of documenting a C library
where you have the following header file `example-header.h`:

``` c
/**
 * second_function:
 *
 * This is the second function we want to see documented.
 */
int second_function(void);

/**
 * first_function:
 *
 * This is the first function we want to see documented.
 */
int first_function(void);
```

The C extension should document `second_function` first but we can
override the behaviour adding a file called `example-header.h.markdown`
specifying the symbols to be documented in the wanted order as follow:

``` markdown
---
symbols:
    - first_function
    - second_function
....
```
