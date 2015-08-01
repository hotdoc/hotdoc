% Extension Design Overview
% Mathieu Duponchelle
% July 27, 2015

## Scope of an extension

* An extension can create new types of symbols

* An extension can modify default symbols

* Multiple extensions can be used together

* It is the responsibility of the formatter subclass to handle these new symbols,
  and to advertise the extensions it supports

## Current implementation

No base class for extensions yet, and they are implicitly created. They can
register themselves to a signal API, currently exposing two signals per symbol
type:

* The symbol factory emits a signal for each new created signal, extensions
will be able to either return None if the symbol should be omitted, return
a different object to override the default one, or add per-extension attributes
to the default object and return it.

* The base formatter emits a signal when a symbol is about to be formatted,
extensions need to register to that signal if they wish to add attributes that
contain links that are determined at runtime (links to other symbols for example),
as the link resolver will only be full at that point.

The extension's main entry point is the "setup" virtual function, which takes
two arguments, the base formatter and the symbol factory (more to come)
