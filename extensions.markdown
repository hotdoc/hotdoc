% Extension Design Overview
% Mathieu Duponchelle
% July 27, 2015

## Scope of an extension

* An extension can create new types of symbols

* An extension can modify default symbols

* Multiple extensions can be used together

* It is the responsibility of the formatter subclass to handle these new symbols,
  and to advertise the extensions it supports

## Creating new symbols

While parsing the standalone documentation, we create so-called "Section Symbols".
The extension can choose to add its own symbols to the Section Symbols.
