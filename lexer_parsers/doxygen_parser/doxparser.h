#ifndef _DOXPARSER_H_
#define _DOXPARSER_H_

#include <Python.h>
#include <glib.h>

typedef struct
{
  GHashTable *command_map;
  PyObject *current_block;
} DoxParser;

DoxParser *dox_parser_new (void);
void dox_parser_dispose (DoxParser *parser);

PyObject *dox_parser_parse (DoxParser *parser, const char *raw_comment);

#endif
