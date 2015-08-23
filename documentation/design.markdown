% Overview of the rendering design
% Mathieu Duponchelle
% July 26, 2015

Dependency scanning.
--------------------

The first time the documentation is built or after cleanup, we skip
directly to 2.

Otherwise, we check our dependency DAG, and detect the stale files.

> This is an optional stage.

Source scanning
---------------

If the build was triggered by a dependency change, we will only parse
the relevant files (usually source files and not headers, which is
extra-fast).

Addition or removal of files will not trigger a full rebuild.

Two steps:

*   Modeling of the exposed interface:
    For C and C++ files, we parse all the provided headers for
    function, struct, enums etc declarations.

*   Extract comments everywhere (as fast as possible).

> This is a mandatory stage

Standalone documentation scanning
---------------------------------

One entry point, the "index file"

If the build was triggered by a dependency change, we will only rebuild
the pages concerned. (If a source file changed, we will only rebuild the
page(s) that included its symbols, and if a standalone file changed, we
will of course only rebuild this one)

Documentation is parsed to pandoc's native format and two filters
are applied (in one pass):

*   Link filter: If the link points to a local path, the file pointed
    to is recursively scanned.

*   BulletPoint filter: If and only if the bullet point contains only a link,
    we check if the contents of its title match a symbol that we know about.

If this is the case, the bullet point is ignored and the symbol is
considered as belonging to the current section.

The rest is left unchanged, we don't store anything for that phase, but
we update the dependency DAG with symbol -> page dependencies.

We explicitly don't track dead links, it is up to the user to figure them out.

> This is an optional stage, we can produce a naive index ourselves too

Section formatting
------------------

At this stage, we know exactly the pages that will need to be created / updated
and in which pages symbols will be documented.

Two things happen then:

*   We prepare a high-level representation for the
    AST nodes associated with the symbol identifiers
(a FUNCTION\_DECL node is translated to a "FunctionSymbol" for example)

*   We match comments with their high-level symbols, splitting them
    in parameter, block and return value descriptions.

    For example, this comment block:

    ```

    /**
     * foo_bar:
     * @foo: a #Foo
     *
     * This function will process a foo in all sorts of manners,
     * see [baz_bar]() for if you need to process a baz.
     *
     * Returns: A #Bar
     */

    ```

    will be split in three separate chunks, one for the return value,
    one for the parameter, and one for the function description.

    Each of these chunks are then possibly preprocessed to translate
    syntax to markdown and apply links.

> This is a mandatory stage

Final rendering.
----------------

We can now use pandoc to render to the final targeted format.

> This is an optional stage
