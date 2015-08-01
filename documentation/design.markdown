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
    function, struct, enums etc declarations. We store the
    AST nodes in the symbol database, possibly updating existing
    ones.

*   Extract comments everywhere (as fast as possible). We store
    them in the comments database.

We also clean the databases if a file has been removed.

> This is a mandatory stage

Standalone documentation scanning
---------------------------------

One entry point, the "index file"

If the build was triggered by a dependency change, we will only rebuild
the pages concerned. (If a source file changed, we will only rebuild the
page(s) that included its symbols, and if a standalone file changed, we
will of course only rebuild this one)

Documentation is parsed to pandoc's native format and three filters
are applied (in one pass):

*   Link filter: If the link points to a local path, the file pointed
    to is recursively scanned.

*   Include filter (only in markdown): If a string contains a {{include\_this\_file}}
    paragraph, the contents of the file are scanned and included in place.
Hopefully this can be deprecated once inclusion is standardized.

*   BulletPoint filter: If and only if the bullet point contains only a link,
    we check if the contents of its title match a symbol that we know about.

If this is the case, the bullet point is ignored and the symbol is
considered as belonging to the current section.

The rest is left unchanged, we don't store anything for that phase, but
we update the dependency DAG with symbol -> page dependencies, and
page -> page dependencies in the include case.

We explicitly don't track dead links, it is up to the user to figure them out.

> This is an optional stage, we can produce a naive index ourselves too

Section formatting
------------------

At this stage, we know exactly the pages that will need to be created / updated
and in which pages symbols will be documented.

Two things happen then:

*   We query the symbol database for the AST nodes associated with
    the symbol identifiers, and prepare a high-level representation for them
(a FUNCTION\_DECL node is translated to a "FunctionSymbol" for example)

*   We query the comments database for the comment blocks associated
    with the symbol identifiers, parse them first with the gtk-doc comment
    block parser, then parse the resulting documentation chunks to
    pandoc's native format.

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

    Each of these chunks will then be parsed to pandoc's native format,
    with two filters applied:

    * An include filter, same as the separate documentation one.

    * A link filter, which will parse the title of the link and
      insert the correct link if the title matches a documented symbol
      and the (link) part of the markdown link was empty or contained
      one of the `[function | symbol | signal | ...]` specifiers.

    We possibly add the included files to the comment's dependencies
    field in the comments' database.

We then save our updated dependency DAG, and dot it for possible
examination.

> This is a mandatory stage

Final rendering.
----------------

We can now use pandoc to render to the final targeted format.

At this stage, what we have is a list of files to be created,
and a certain amount of typed documentation in pandoc's format
associated to them (for example the index page only contains
its original markdown translated to pandoc with the links
updated, but a "leaf" page for a class contains a list of
function symbols, which in turn contain a list of parameter
symbols etc ..

These are the objects that get passed to the formatter
subclass, which can choose to render them in any way it sees
fit, using pandoc, possible filters, pandoc's templates or
its own templating mechanism.


> This is an optional stage
